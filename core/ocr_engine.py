"""PaddleOCR 封装模块

提供统一的 OCR 接口，返回识别文字及其在图片中的坐标。
"""
import os
import sys
from dataclasses import dataclass

# 禁用 oneDNN 解决 PaddlePaddle 3.x (PIR) 在某些环境下的指令集不支持报错
os.environ['FLAGS_use_onednn'] = '0'
os.environ['PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK'] = 'True'


@dataclass
class OCRResult:
    """单个 OCR 识别结果"""
    text: str           # 识别的文字
    confidence: float   # 置信度
    box: list           # 边界框 [[x1,y1],[x2,y2],[x3,y3],[x4,y4]]

    @property
    def x_min(self) -> int:
        return int(min(p[0] for p in self.box))

    @property
    def y_min(self) -> int:
        return int(min(p[1] for p in self.box))

    @property
    def x_max(self) -> int:
        return int(max(p[0] for p in self.box))

    @property
    def y_max(self) -> int:
        return int(max(p[1] for p in self.box))


class OCREngine:
    """OCR 引擎封装"""

    def __init__(self, use_gpu: bool = False):
        self._ocr = None
        self.use_gpu = use_gpu

    def _ensure_initialized(self):
        """延迟初始化 PaddleOCR（使用打包内的本地模型，禁用网络请求）"""
        if self._ocr is None:
            from paddleocr import PaddleOCR
            
            # 确定模型路径
            if getattr(sys, 'frozen', False):
                # 打包后的临时目录
                base_path = sys._MEIPASS
            else:
                # 开发环境路径 (project_root/models)
                base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            
            det_dir = os.path.join(base_path, 'models', 'det')
            rec_dir = os.path.join(base_path, 'models', 'rec')
            cls_dir = os.path.join(base_path, 'models', 'cls')

            self._ocr = PaddleOCR(
                det_model_dir=det_dir,
                rec_model_dir=rec_dir,
                cls_model_dir=cls_dir,
                use_angle_cls=True,
                lang='ch',
                use_gpu=self.use_gpu,
                show_log=False,
                enable_mkldnn=False,
            )

    def recognize(self, image_path: str) -> list[OCRResult]:
        """对图片执行 OCR 识别

        Args:
            image_path: 图片文件路径

        Returns:
            OCR 识别结果列表
        """
        self._ensure_initialized()

        result = self._ocr.ocr(image_path, cls=True)
        if not result or not result[0]:
            return []

        ocr_results = []
        for line in result[0]:
            box = line[0]       # [[x1,y1],[x2,y2],[x3,y3],[x4,y4]]
            text = line[1][0]   # 识别文字
            conf = line[1][1]   # 置信度
            ocr_results.append(OCRResult(
                text=text,
                confidence=conf,
                box=box,
            ))

        return ocr_results

    def recognize_from_image(self, image) -> list[OCRResult]:
        """对 PIL Image 或 numpy 数组执行 OCR

        Args:
            image: PIL Image 对象或 numpy 数组

        Returns:
            OCR 识别结果列表
        """
        import numpy as np
        from PIL import Image

        self._ensure_initialized()

        # 如果是 PIL Image，转为 numpy 数组
        if isinstance(image, Image.Image):
            image = np.array(image)

        result = self._ocr.ocr(image, cls=True)
        if not result or not result[0]:
            return []

        ocr_results = []
        for line in result[0]:
            box = line[0]
            text = line[1][0]
            conf = line[1][1]
            ocr_results.append(OCRResult(
                text=text,
                confidence=conf,
                box=box,
            ))

        return ocr_results
