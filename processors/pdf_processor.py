"""PDF 文件脱敏处理器

处理策略（统一遮罩方案）：
1. 用 PyMuPDF 将每页渲染为高分辨率图片
2. 用 OCR 识别文字及坐标
3. 扫描敏感信息，在匹配位置绘制黑色遮罩
4. 将处理后的图片重新合成为 PDF
"""
import fitz  # PyMuPDF
from PIL import Image
import io

from processors.image_processor import ImageProcessor
from core.scanner import Scanner
from core.ocr_engine import OCREngine
from core.logger import RedactionLog
from config import PDF_RENDER_DPI


class PDFProcessor(ImageProcessor):
    """PDF 文件处理器（继承图片处理器的遮罩能力）"""

    def __init__(self, scanner: Scanner, ocr_engine: OCREngine):
        super().__init__(scanner, ocr_engine)

    def process(self, input_path: str, output_path: str, log: RedactionLog) -> bool:
        doc = fitz.open(input_path)
        processed_images = []

        for page_num in range(len(doc)):
            page = doc[page_num]
            location_prefix = f'第{page_num + 1}页'

            # 渲染页面为图片
            mat = fitz.Matrix(PDF_RENDER_DPI / 72, PDF_RENDER_DPI / 72)
            pix = page.get_pixmap(matrix=mat)
            img = Image.frombytes('RGB', [pix.width, pix.height], pix.samples)

            # 用图片处理器的逻辑进行脱敏
            img = self._process_image(img, log, location_prefix)
            processed_images.append(img)

        doc.close()

        # 将处理后的图片合成为新的 PDF
        self._images_to_pdf(processed_images, output_path)
        return True

    def _images_to_pdf(self, images: list[Image.Image], output_path: str):
        """将图片列表合成为 PDF"""
        if not images:
            return

        # 使用 Pillow 保存为 PDF
        first = images[0]
        if len(images) == 1:
            first.save(output_path, 'PDF', resolution=PDF_RENDER_DPI)
        else:
            rest = images[1:]
            first.save(output_path, 'PDF', resolution=PDF_RENDER_DPI,
                       save_all=True, append_images=rest)
