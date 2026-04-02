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
        
        # 0. 预处理：合并水平相邻且属于同一行的文字框（解决标签被拆分问题）
        merged_results = self._merge_adjacent_boxes(ocr_results)

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
        # 使用合并后的结果进行标签匹配
        import re
        for i, ocr_item in enumerate(merged_results):
            text = ocr_item.text.strip()
            # 遍历所有关键字规则
            for rule_id, rule_name, labels, action, case_sens in self.scanner.keywords:
                matched_label = None
                for label in labels:
                    if not label.strip(): continue
                    
                    flags = 0 if case_sens else re.IGNORECASE
                    is_pure_eng = bool(re.match(r'^[a-zA-Z0-9\s.-]+$', label))
                    
                    if is_pure_eng:
                        # 兼容 OCR 结果中可能缺失的空格或其他符号
                        safe_label = re.escape(label).replace(r'\ ', r'[-\s/_]*')
                        pattern = re.compile(r'(?<![a-zA-Z0-9])' + safe_label + r'(?![a-zA-Z0-9])', flags)
                    else:
                        pattern = re.compile(re.escape(label), flags)
                        
                    if pattern.search(text):
                        matched_label = label
                        break
                
                if matched_label:
                    # --- 新增：同文字框自检逻辑 ---
                    # 即使 Label 和 Value 被合在同一个 OCR 框内（如 "IBAN:666"），也能正确识别
                    inner_matches = self.scanner.scan_text(text)
                    # 关键修复：不再遮盖整个文字框，而是通过比例计算只遮盖具体的值
                    for m in inner_matches:
                        # 质量校验：如果检测到的“值”评分过低（如 IBAN Number 中的 Number），则跳过
                        if self._score_as_account(m.matched_text) >= 0.3:
                            total_len = len(text)
                            if total_len > 0:
                                W = ocr_item.x_max - ocr_item.x_min
                                # 计算比例坐标：将文字框宽度 W 按字符索引平分
                                # target_x_min = x_min + (start_idx / total_len) * W
                                # target_x_max = x_min + (end_idx / total_len) * W
                                sub_x_min = int(ocr_item.x_min + (m.start / total_len) * W)
                                sub_x_max = int(ocr_item.x_min + (m.end / total_len) * W)
                                
                                mask_regions.append((
                                    sub_x_min, ocr_item.y_min,
                                    sub_x_max, ocr_item.y_max
                                ))
                                
                                self._add_log_entry(
                                    log, rule_id, rule_name,
                                    m.matched_text,
                                    f'{location_prefix} 标签"{matched_label}"框内值',
                                    'keyword_inner',
                                    f'同文字框内精准匹配: {matched_label}'
                                )
                    else:
                        # --- 原有：寻找外部邻近值逻辑 ---
                        # 在原始 OCR 结果中查找邻近值（因合并后的结果可能跨度过大不便定位）
                        value_items = self._find_adjacent_value(ocr_item, ocr_results, -1) # 使用 -1 跳过 label_index 检查，因 ocr_item 是合并的
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

    def _merge_adjacent_boxes(self, ocr_results: list[OCRResult]) -> list[OCRResult]:
        """合并水平相邻且垂直对齐的文字框
        
        策略：按行分组，合并间距小于阈值的相邻框
        """
        if not ocr_results:
            return []
            
        # 1. 按中心 Y 轴高度分行（容差为行高的 0.3 倍）
        rows = []
        for item in sorted(ocr_results, key=lambda x: x.y_min):
            found_row = False
            item_y_mid = (item.y_min + item.y_max) / 2
            item_h = item.y_max - item.y_min
            
            for row in rows:
                row_y_mid = (row[0].y_min + row[0].y_max) / 2
                if abs(item_y_mid - row_y_mid) < item_h * 0.4:
                    row.append(item)
                    found_row = True
                    break
            if not found_row:
                rows.append([item])
        
        merged_all = []
        for row in rows:
            # 每行按 X 轴排序
            row.sort(key=lambda x: x.x_min)
            
            merged_row = []
            if not row: continue
            
            current = row[0]
            for next_item in row[1:]:
                # 计算间距（如果间距小于当前行高的 1.2 倍，则合并）
                gap = next_item.x_min - current.x_max
                h = current.y_max - current.y_min
                
                if gap < h * 1.2:
                    # 合并为一个新的 OCRResult
                    new_text = f"{current.text} {next_item.text}"
                    new_box = [
                        [min(current.x_min, next_item.x_min), min(current.y_min, next_item.y_min)],
                        [max(current.x_max, next_item.x_max), min(current.y_min, next_item.y_min)],
                        [max(current.x_max, next_item.x_max), max(current.y_max, next_item.y_max)],
                        [min(current.x_min, next_item.x_min), max(current.y_max, next_item.y_max)]
                    ]
                    current = OCRResult(text=new_text, confidence=(current.confidence + next_item.confidence)/2, box=new_box)
                else:
                    merged_row.append(current)
                    current = next_item
            merged_row.append(current)
            merged_all.extend(merged_row)
            
        return merged_all

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

        right_candidates = [] # [(distance, score, item, index)]
        below_candidates = [] # [(distance, score, item, index)]

        for j, item in enumerate(all_items):
            if j == label_index: continue
            
            # 如果候选框本身就是另一个关键字标签，则它是竞争对手而不是我们要找的 Value
            is_another_label = self._is_label(item.text)
            
            item_y_center = (item.y_min + item.y_max) / 2
            score = self._score_as_account(item.text)
            
            # --- 优化策略：计算 Y 轴重合度 ---
            overlap_y = max(0, min(item.y_max, label_item.y_max) - max(item.y_min, label_item.y_min))
            y_overlap_ratio = overlap_y / label_height if label_height > 0 else 0
            
            # 1. 检查右侧 (水平对齐优先)
            if y_overlap_ratio > 0.5 and item.x_min > label_item.x_max - 10:
                dist = item.x_min - label_item.x_max
                # 大跨度逻辑：水平对齐时，距离限制放宽到 1000px
                if dist < 1000:
                    if is_another_label:
                        # 核心互斥逻辑：如果在搜寻 Value 的路上遇到了另一个 Label，则立即切断（防止抢夺跨列数据）
                        pass 
                    else:
                        right_candidates.append((dist, score, item, j))
            
            # 2. 检查下方 (列对齐模式)
            elif not is_another_label: # 下方查找时不考虑 Label
                x_overlap = (min(item.x_max, label_item.x_max) - 
                             max(item.x_min, label_item.x_min))
                if x_overlap > 0 and item.y_min > label_item.y_min:
                    dist = item.y_min - label_item.y_max
                    if dist < 120: # 垂直距离限制稍微放宽
                        below_candidates.append((dist, score, item, j))

        # --- 核心机制：水平阻断检查 ---
        # 针对右侧候选，如果 Label 和候选 Value 之间存在另一个 Label，则该 Value 无效
        final_right_candidates = []
        for dist, score, item, item_idx in right_candidates:
            blocked = False
            for k_check, label_check in enumerate(all_items):
                if k_check == label_index or k_check == item_idx: continue
                
                # 只有当潜在阻断者与当前 Label 在垂直方向上有重合（即在同一行）时，才触发水平阻断
                check_overlap_y = min(label_item.y_max, label_check.y_max) - max(label_item.y_min, label_check.y_min)
                check_y_ratio = check_overlap_y / (label_item.y_max - label_item.y_min)
                
                if (check_y_ratio > 0.5 and 
                    label_item.x_max < label_check.x_min < item.x_min and 
                    self._is_label(label_check.text)):
                    blocked = True
                    break
            if not blocked:
                final_right_candidates.append((dist, score, item))

        # 评分与决策逻辑：优先高分，其次近距离
        def pick_best(candidates):
            if not candidates: return None
            # 按照分数降序(x[1])、距离升序(x[0])排列
            candidates.sort(key=lambda x: (-x[1], x[0]))
            return candidates[0]

        best_right = pick_best(final_right_candidates)
        best_below = pick_best([(c[0], c[1], c[2]) for c in below_candidates])

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
                    # 关键修复：将空格替换为可选的连字符、空格或下划线，以对 OCR 结果具备容错性
                    safe_label = re.escape(lbl_clean).replace(r'\ ', r'[-\s/_]*')
                    # 使用正则检测词边界，防止 CITIBANK 匹配到 IBAN 这样的片段
                    pattern = re.compile(r'(?<![a-zA-Z0-9])' + safe_label + r'(?![a-zA-Z0-9])', flags)
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
        # 基础分：只要是纯数字就给 0.5 (高于 0.3 的引导阈值)
        if text.isdigit():
            return 0.5

        # 混合文本（含少量数字）
        digit_ratio = sum(c.isdigit() for c in text) / len(text)
        if digit_ratio > 0.3:
            return 0.3

        # 纯中文 / 纯英文 / 其他
        return 0.1
