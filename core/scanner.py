"""敏感信息扫描引擎

支持两种扫描模式：
1. 正则模式扫描 - 按正则表达式匹配敏感信息（如银行账号、手机号）
2. 关键字标签扫描 - 按标签找到字段名，然后脱敏其后的值
"""
import re
import json
from dataclasses import dataclass, field
from typing import Optional

from config import RULES_FILE


@dataclass
class ScanMatch:
    """一条扫描匹配结果"""
    rule_id: str       # 规则ID
    rule_name: str     # 规则名称（中文）
    matched_text: str  # 匹配到的文本
    start: int         # 在原文中的起始位置
    end: int           # 在原文中的结束位置
    match_type: str    # 'pattern' 或 'keyword'


@dataclass
class KeywordScanMatch:
    """关键字标签扫描结果（用于结构化数据如表格）"""
    rule_id: str
    rule_name: str
    label: str           # 匹配到的标签文本
    value_text: str      # 标签对应的值（需要脱敏的部分）
    match_type: str = 'keyword'


class Scanner:
    """敏感信息扫描器"""

    def __init__(self, rules_file: str = None):
        self.rules_file = rules_file or RULES_FILE
        self.patterns = []   # [(id, name, compiled_regex)]
        self.keywords = []   # [(id, name, labels, action)]
        self.replacement = '****'
        self.load_rules()

    def load_rules(self):
        """从 rules.json 加载规则"""
        try:
            with open(self.rules_file, 'r', encoding='utf-8') as f:
                rules = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            rules = {'patterns': [], 'keywords': [], 'replacement': '****'}

        self.replacement = rules.get('replacement', '****')

        # 编译正则模式
        self.patterns = []
        for p in rules.get('patterns', []):
            if not p.get('enabled', True):
                continue
            try:
                compiled = re.compile(p['regex'])
                self.patterns.append((p['id'], p['name'], compiled))
            except re.error:
                pass  # 跳过无效正则

        # 加载关键字标签
        self.keywords = []
        for k in rules.get('keywords', []):
            if not k.get('enabled', True):
                continue
            self.keywords.append((
                k['id'],
                k['name'],
                k.get('labels', []),
                k.get('action', 'redact_value'),
            ))

    def scan_text(self, text: str) -> list[ScanMatch]:
        """扫描纯文本，返回所有匹配结果

        Args:
            text: 待扫描文本

        Returns:
            匹配结果列表
        """
        matches = []

        # 1. 正则模式扫描
        for rule_id, rule_name, pattern in self.patterns:
            for m in pattern.finditer(text):
                matches.append(ScanMatch(
                    rule_id=rule_id,
                    rule_name=rule_name,
                    matched_text=m.group(),
                    start=m.start(),
                    end=m.end(),
                    match_type='pattern',
                ))

        # 2. 关键字标签扫描（在纯文本中查找 "标签：值" 或 "标签:值" 模式）
        for rule_id, rule_name, labels, action in self.keywords:
            for label in labels:
                # 匹配 "标签：值" 或 "标签: 值"，值为非空白字符串
                label_pattern = re.compile(
                    re.escape(label) + r'[：:\s]*([^\s,，;；\n]+)',
                    re.UNICODE
                )
                for m in label_pattern.finditer(text):
                    value = m.group(1)
                    if value and value != self.replacement:
                        matches.append(ScanMatch(
                            rule_id=rule_id,
                            rule_name=rule_name,
                            matched_text=value,
                            start=m.start(1),
                            end=m.end(1),
                            match_type='keyword',
                        ))

        # 去重（同一位置可能被多个规则匹配）
        seen = set()
        unique_matches = []
        for m in matches:
            key = (m.start, m.end)
            if key not in seen:
                seen.add(key)
                unique_matches.append(m)

        return sorted(unique_matches, key=lambda x: x.start)

    def scan_key_value_pairs(self, pairs: list[tuple[str, str]]) -> list[KeywordScanMatch]:
        """扫描键值对（用于表格等结构化数据）

        Args:
            pairs: [(key, value)] 键值对列表

        Returns:
            匹配结果列表
        """
        matches = []
        for key, value in pairs:
            if not key or not value:
                continue
            key_clean = key.strip()
            for rule_id, rule_name, labels, action in self.keywords:
                for label in labels:
                    if label in key_clean:
                        matches.append(KeywordScanMatch(
                            rule_id=rule_id,
                            rule_name=rule_name,
                            label=label,
                            value_text=value.strip(),
                        ))
                        break
            # 同时对 value 做正则扫描
            for rule_id, rule_name, pattern in self.patterns:
                for m in pattern.finditer(value):
                    matches.append(KeywordScanMatch(
                        rule_id=rule_id,
                        rule_name=rule_name,
                        label=key_clean,
                        value_text=m.group(),
                    ))
        return matches

    def redact_text(self, text: str, matches: list[ScanMatch] = None) -> str:
        """对文本执行脱敏替换

        Args:
            text: 原始文本
            matches: 扫描匹配结果（可选，不提供则自动扫描）

        Returns:
            脱敏后的文本
        """
        if matches is None:
            matches = self.scan_text(text)

        if not matches:
            return text

        # 从后往前替换，避免位置偏移
        result = text
        for m in sorted(matches, key=lambda x: x.start, reverse=True):
            result = result[:m.start] + self.replacement + result[m.end:]

        return result
