"""图片脱敏处理器

处理策略：
1. 用 OCR 识别图片中的文字及其坐标
2. 对识别文本进行敏感信息扫描
3. 在匹配位置绘制黑色矩形遮罩
4. 保存处理后的图片
"""
from PIL import Image, ImageDraw

from processors.base import BaseProcessor
from core.scanner import Scanner, ScanMatch
from core.ocr_engine import OCREngine, OCRResult
from core.logger import RedactionLog


class ImageProcessor(BaseProcessor):
    """图片文件处理器"""

    def __init__(self, scanner: Scanner, ocr_engine: OCREngine):
        super().__init__(scanner)
        self.ocr_engine = ocr_engine

    def process(self, input_path: str, output_path: str, log: RedactionLog) -> bool:
        img = Image.open(input_path).convert('RGB')
        img = self._process_image(img, log, '图片')
        img.save(output_path)
        return True

    def _process_image(self, img: Image.Image, log: RedactionLog,
                       location_prefix: str) -> Image.Image:
        """处理单张图片，返回脱敏后的图片"""
        # OCR 识别
        ocr_results = self.ocr_engine.recognize_from_image(img)
        if not ocr_results:
            return img

        # 找出需要遮罩的区域
        mask_regions = self._find_mask_regions(ocr_results, log, location_prefix)

        # 绘制黑色遮罩
        if mask_regions:
            draw = ImageDraw.Draw(img)
            for region in mask_regions:
                # 稍微扩大遮罩区域以确保完全覆盖
                padding = 3
                draw.rectangle(
                    [region[0] - padding, region[1] - padding,
                     region[2] + padding, region[3] + padding],
                    fill='black'
                )

        return img

    def _find_mask_regions(self, ocr_results: list[OCRResult],
                           log: RedactionLog,
                           location_prefix: str) -> list[tuple]:
        """找出所有需要遮罩的区域

        Args:
            ocr_results: OCR 识别结果
            log: 脱敏日志
            location_prefix: 位置前缀

        Returns:
            需要遮罩的区域列表 [(x_min, y_min, x_max, y_max), ...]
        """
        mask_regions = []

        # 1. 对每个 OCR 结果做正则扫描
        for ocr_item in ocr_results:
            matches = self.scanner.scan_text(ocr_item.text)
            if matches:
                # 整个文本框区域都需要遮罩
                mask_regions.append((
                    ocr_item.x_min, ocr_item.y_min,
                    ocr_item.x_max, ocr_item.y_max
                ))
                for m in matches:
                    self._add_log_entry(
                        log, m.rule_id, m.rule_name,
                        m.matched_text,
                        f'{location_prefix} OCR文本: {ocr_item.text}',
                        m.match_type,
                    )

        # 2. 关键字标签扫描：找到标签后，遮罩其右侧或下方的相邻文本框
        for i, ocr_item in enumerate(ocr_results):
            text = ocr_item.text.strip()
            for rule_id, rule_name, labels, action in self.scanner.keywords:
                for label in labels:
                    if label in text:
                        # 找到标签，查找相邻的值文本框
                        value_items = self._find_adjacent_value(
                            ocr_item, ocr_results, i)
                        for val_item in value_items:
                            mask_regions.append((
                                val_item.x_min, val_item.y_min,
                                val_item.x_max, val_item.y_max
                            ))
                            self._add_log_entry(
                                log, rule_id, rule_name,
                                val_item.text,
                                f'{location_prefix} 标签"{label}"的值',
                                'keyword',
                            )
                        break

        return mask_regions

    def _find_adjacent_value(self, label_item: OCRResult,
                             all_items: list[OCRResult],
                             label_index: int) -> list[OCRResult]:
        """找到标签文本框右侧或下方的相邻值文本框

        策略：
        - 优先找同一行中，在标签右侧的文本框
        - 如果没有，则找正下方的文本框
        """
        result = []
        label_y_center = (label_item.y_min + label_item.y_max) / 2
        label_height = label_item.y_max - label_item.y_min
        y_threshold = label_height * 0.6  # 同行判定容差

        # 找同行右侧
        right_candidates = []
        for j, item in enumerate(all_items):
            if j == label_index:
                continue
            item_y_center = (item.y_min + item.y_max) / 2
            # 在同一行（y 坐标接近）且在右侧
            if (abs(item_y_center - label_y_center) < y_threshold
                    and item.x_min > label_item.x_max - 10):
                right_candidates.append((item.x_min, item))

        if right_candidates:
            # 取最近的右侧文本框
            right_candidates.sort(key=lambda x: x[0])
            result.append(right_candidates[0][1])
        else:
            # 没有右侧的，找正下方的
            below_candidates = []
            for j, item in enumerate(all_items):
                if j == label_index:
                    continue
                x_overlap = (min(item.x_max, label_item.x_max) -
                             max(item.x_min, label_item.x_min))
                # x 有重叠且在下方
                if x_overlap > 0 and item.y_min > label_item.y_min:
                    below_candidates.append((item.y_min, item))

            if below_candidates:
                below_candidates.sort(key=lambda x: x[0])
                result.append(below_candidates[0][1])

        return result
