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

        # 1. 对每个 OCR 结果做正则扫描（仅对自身就是值的情况涂黑本身）
        for ocr_item in ocr_results:
            matches = self.scanner.scan_text(ocr_item.text)
            # 过滤掉 keyword，不遮罩“钥匙”标签自身
            valid_matches = [m for m in matches if m.match_type != 'keyword']
            if valid_matches:
                # 整个文本框区域都需要遮罩
                mask_regions.append((
                    ocr_item.x_min, ocr_item.y_min,
                    ocr_item.x_max, ocr_item.y_max
                ))
                for m in valid_matches:
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
        """找到标签文本框关联的值文本框（三层智能策略）

        策略：
        Layer 1 - 方向候选收集：收集右侧（同行）和正下方的所有候选框
        Layer 2 - 数字置信度过滤：对每个候选框内容打分，优先选数字/IBAN格式
        Layer 3 - 距离加权：同分情况下优先最近的候选框
        """
        label_y_center = (label_item.y_min + label_item.y_max) / 2
        label_height = label_item.y_max - label_item.y_min
        y_threshold = label_height * 0.6  # 同行判定容差

        # Layer 1: 分方向收集候选框
        right_candidates = []  # [(distance, score, item)]
        below_candidates = []  # [(distance, score, item)]

        for j, item in enumerate(all_items):
            if j == label_index:
                continue
            item_y_center = (item.y_min + item.y_max) / 2
            score = self._score_as_account(item.text)

            # 右侧：同行 + 在右边
            if (abs(item_y_center - label_y_center) < y_threshold
                    and item.x_min > label_item.x_max - 10):
                dist = item.x_min - label_item.x_max
                right_candidates.append((dist, score, item))

            # 下方：x 有重叠 + 在下面
            else:
                x_overlap = (min(item.x_max, label_item.x_max) -
                             max(item.x_min, label_item.x_min))
                if x_overlap > 0 and item.y_min > label_item.y_min:
                    dist = item.y_min - label_item.y_max
                    below_candidates.append((dist, score, item))

        # Layer 2 + 3: 按分数降序、距离升序排列，取最优
        def best(candidates):
            if not candidates:
                return None
            # score 越高越好，distance 越小越好
            candidates.sort(key=lambda x: (-x[1], x[0]))
            return candidates[0][2]

        best_right = best(right_candidates)
        best_below = best(below_candidates)

        # 决策：右侧分数 >= 0.5 优先选右侧，否则选下方（如果下方分数更高）
        best_candidate = None
        if best_right is not None:
            right_score = right_candidates[0][1] if right_candidates else 0
            below_score = below_candidates[0][1] if below_candidates else 0
            # 右侧有高置信度数字，或右侧比下方分更高/相当 → 选右侧
            if right_score >= 0.5 or right_score >= below_score:
                best_candidate = best_right
            elif best_below is not None:
                best_candidate = best_below
            else:
                best_candidate = best_right
        elif best_below is not None:
            best_candidate = best_below

        if best_candidate is not None:
            # 防御性校验
            score = self._score_as_account(best_candidate.text)
            # 1. 得分太低（纯文本）直接丢弃
            if score < 0.3:
                return []
            # 2. 如果候选框自己就是个其他的系统 Label，丢弃
            if self._is_label(best_candidate.text):
                return []
            return [best_candidate]

        return []

    def _is_label(self, text: str) -> bool:
        """检查文本本身是否是系统里配置的一个规则标签(Key)"""
        text_lower = text.strip().lower()
        if not text_lower:
            return False
        for _, _, labels, _ in self.scanner.keywords:
            for lbl in labels:
                lbl_lower = lbl.strip().lower()
                # 简单包含判断或被包含判断，防止长短标签相互覆盖
                if lbl_lower in text_lower or text_lower in lbl_lower:
                    return True
        return False

    @staticmethod
    def _score_as_account(text: str) -> float:
        """对文本内容打分，评估其为账号/IBAN的可能性

        Returns:
            0.0 ~ 1.0 的置信度分数
        """
        import re
        text = text.strip()
        if not text:
            return 0.0

        # 纯 16-19 位数字 → 银行账号格式
        if re.match(r'^\d{16,19}$', text):
            return 1.0

        # IBAN 格式：2字母 + 2数字 + 4-30位字母数字
        if re.match(r'^[A-Z]{2}\d{2}[A-Z0-9]{4,30}$', text):
            return 1.0

        # 含有 4 位以上连续数字（可能是账号片段）
        digits = re.findall(r'\d+', text)
        max_digit_run = max((len(d) for d in digits), default=0)
        if max_digit_run >= 8:
            return 0.8
        if max_digit_run >= 4:
            return 0.6

        # 全部是数字（但位数不够16）
        if text.isdigit():
            return 0.4

        # 混合文本（含少量数字）
        digit_ratio = sum(c.isdigit() for c in text) / len(text)
        if digit_ratio > 0.3:
            return 0.3

        # 纯中文 / 纯英文 / 其他
        return 0.1
