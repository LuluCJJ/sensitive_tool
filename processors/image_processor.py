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
                        m.trigger
                    )

        # 2. 关键字标签扫描：找到标签后，遮罩其右侧或下方的相邻实体
        import re
        for i, ocr_item in enumerate(ocr_results):
            text = ocr_item.text.strip()
            # 遍历所有关键字规则
            for rule_id, rule_name, labels, action, case_sens in self.scanner.keywords:
                matched_label = None
                for label in labels:
                    if not label.strip(): continue
                    
                    flags = 0 if case_sens else re.IGNORECASE
                    is_pure_eng = bool(re.match(r'^[a-zA-Z0-9\s.-]+$', label))
                    
                    if is_pure_eng:
                        pattern = re.compile(r'(?<![a-zA-Z0-9])' + re.escape(label) + r'(?![a-zA-Z0-9])', flags)
                    else:
                        pattern = re.compile(re.escape(label), flags)
                        
                    if pattern.search(text):
                        matched_label = label
                        break
                
                if matched_label:
                    # 触发成功，寻找邻近值
                    value_items = self._find_adjacent_value(ocr_item, ocr_results, i)
                    for val_item in value_items:
                        mask_regions.append((
                            val_item.x_min, val_item.y_min,
                            val_item.x_max, val_item.y_max
                        ))
                        self._add_log_entry(
                            log, rule_id, rule_name,
                            val_item.text,
                            f'{location_prefix} 标签"{matched_label}"的值',
                            'keyword',
                            f'由关键字标签关联: {matched_label}'
                        )
                    break # 找到第一个匹配的规则标签即跳过本文字框，防止重复打码同个值

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
        y_threshold = label_height * 0.6

        right_candidates = [] # [(distance, score, item)]
        below_candidates = [] # [(distance, score, item)]

        for j, item in enumerate(all_items):
            if j == label_index: continue
            
            # 如果候选框本身就是另一个关键字标签，则它是竞争对手而不是我们要找的 Value
            if self._is_label(item.text): continue
            
            item_y_center = (item.y_min + item.y_max) / 2
            score = self._score_as_account(item.text)
            
            # 1. 检查右侧
            if (abs(item_y_center - label_y_center) < y_threshold 
                    and item.x_min > label_item.x_max - 10):
                dist = item.x_min - label_item.x_max
                if dist < 250: # 距离限制
                    right_candidates.append((dist, score, item))
            
            # 2. 检查下方
            else:
                x_overlap = (min(item.x_max, label_item.x_max) - 
                             max(item.x_min, label_item.x_min))
                if x_overlap > 0 and item.y_min > label_item.y_min:
                    dist = item.y_min - label_item.y_max
                    if dist < 80: # 垂直距离限制
                        below_candidates.append((dist, score, item))

        # 评分与决策逻辑：优先高分，其次近距离
        def pick_best(candidates):
            if not candidates: return None
            # 按照分数降序(x[1])、距离升序(x[0])排列
            candidates.sort(key=lambda x: (-x[1], x[0]))
            return candidates[0]

        best_right = pick_best(right_candidates)
        best_below = pick_best(below_candidates)

        final_choice = None
        if best_right:
            # 如果右侧得分很高(>=0.5)，优先选右侧
            if best_right[1] >= 0.5:
                final_choice = best_right[2]
            # 否则看下方有没有分更高的
            elif best_below and best_below[1] > best_right[1]:
                final_choice = best_below[2]
            else:
                final_choice = best_right[2]
        elif best_below:
            final_choice = best_below[2]

        if final_choice and self._score_as_account(final_choice.text) >= 0.3:
            return [final_choice]
        return []

    def _is_label(self, text: str) -> bool:
        """检查文本是否是系统预设的关键字标签"""
        import re
        text_clean = text.strip()
        if not text_clean:
            return False
            
        for _, _, labels, _, case_sens in self.scanner.keywords:
            for lbl in labels:
                lbl_clean = lbl.strip()
                if not lbl_clean: continue
                
                flags = 0 if case_sens else re.IGNORECASE
                # 检查是否为纯英文/数字标签
                is_pure_eng = bool(re.match(r'^[a-zA-Z0-9\s.-]+$', lbl_clean))
                
                if is_pure_eng:
                    # 使用正则检测词边界，防止 CITIBANK 匹配到 IBAN 这样的片段
                    pattern = re.compile(r'(?<![a-zA-Z0-9])' + re.escape(lbl_clean) + r'(?![a-zA-Z0-9])', flags)
                    if pattern.search(text_clean):
                        return True
                else:
                    # 中文或混合字符匹配
                    if case_sens:
                        if lbl_clean in text_clean: return True
                    else:
                        if lbl_clean.lower() in text_clean.lower(): return True
        return False

    @staticmethod
    def _score_as_account(text: str) -> float:
        """对文本内容打分，评估其为账号/IBAN的可能性"""
        import re
        text = text.strip()
        if not text:
            return 0.0

        # 防护：如果是明显的值说明文字或标签属性，惩罚得分
        text_lower = text.lower()
        punish_words = ['amount', 'reference', 'ref', 'date', 'name', 'bal', 'balance', 'fee', 'charge']
        for w in punish_words:
            if w in text_lower:
                return 0.0  # 绝对不可能是纯数字账号

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
