"""脱敏调度器

统一调度各类文件的脱敏处理。
"""
import os
import traceback
from typing import Callable, Optional

from config import SUPPORTED_EXTENSIONS, OUTPUT_DIR
from core.scanner import Scanner
from core.ocr_engine import OCREngine
from core.logger import RedactionLogger, RedactionLog
from processors.word_processor import WordProcessor
from processors.excel_processor import ExcelProcessor
from processors.image_processor import ImageProcessor
from processors.pdf_processor import PDFProcessor


class Redactor:
    """脱敏调度器"""

    def __init__(self, rules_file: str = None, output_dir: str = None):
        self.scanner = Scanner(rules_file)
        self.ocr_engine = OCREngine(use_gpu=False)
        self.logger = RedactionLogger()
        self.output_dir = output_dir or OUTPUT_DIR

        # 初始化各处理器
        self.processors = {
            'word': WordProcessor(self.scanner),
            'excel': ExcelProcessor(self.scanner),
            'image': ImageProcessor(self.scanner, self.ocr_engine),
            'pdf': PDFProcessor(self.scanner, self.ocr_engine),
        }

        os.makedirs(self.output_dir, exist_ok=True)

    def reload_rules(self):
        """重新加载脱敏规则"""
        self.scanner.load_rules()

    def process_file(self, file_path: str,
                     progress_callback: Optional[Callable] = None) -> RedactionLog:
        """处理单个文件

        Args:
            file_path: 文件路径
            progress_callback: 进度回调 (status_text)

        Returns:
            脱敏日志
        """
        filename = os.path.basename(file_path)
        ext = os.path.splitext(filename)[1].lower()

        # 判断文件类型
        file_type = SUPPORTED_EXTENSIONS.get(ext)
        if not file_type:
            log = self.logger.create_log(filename, 'unknown')
            self.logger.finish_log(log, status='error',
                                   error_message=f'不支持的文件类型: {ext}')
            return log

        # 创建日志
        log = self.logger.create_log(filename, file_type)

        if progress_callback:
            progress_callback(f'正在处理: {filename}')

        # 确定输出路径
        name, orig_ext = os.path.splitext(filename)
        # PDF 和图片类型输出对应格式
        if file_type == 'pdf':
            output_ext = '.pdf'
        elif file_type == 'image':
            output_ext = '.png'  # 统一输出 PNG
        else:
            output_ext = orig_ext
        output_path = os.path.join(self.output_dir, f'{name}_redacted{output_ext}')

        # 处理文件
        try:
            processor = self.processors[file_type]
            processor.process(file_path, output_path, log)
            self.logger.finish_log(log, status='success', output_path=output_path)
        except Exception as e:
            tb_str = traceback.format_exc()
            self.logger.finish_log(log, status='error', error_message=str(e))
            log.traceback = tb_str

        return log

    def process_files(self, file_paths: list[str],
                      progress_callback: Optional[Callable] = None,
                      file_callback: Optional[Callable] = None) -> list[RedactionLog]:
        """批量处理文件

        Args:
            file_paths: 文件路径列表
            progress_callback: 总体进度回调 (current, total, status_text)
            file_callback: 单个文件完成回调 (log)

        Returns:
            所有文件的脱敏日志
        """
        logs = []
        total = len(file_paths)

        for i, file_path in enumerate(file_paths):
            if progress_callback:
                progress_callback(i, total, f'处理第 {i+1}/{total} 个文件')

            log = self.process_file(file_path)
            logs.append(log)

            if file_callback:
                file_callback(log)

        if progress_callback:
            progress_callback(total, total, '处理完成')

        return logs

    def save_logs(self) -> str:
        """保存本次会话日志，返回日志文件路径"""
        return self.logger.save_session()
