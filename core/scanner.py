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
    match_type: str    # 'pattern' 或 'keyword' 或 'whitelist'
    trigger: str = ''  # 触发溯源信息


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

    def __init__(self, rules_file: str = None, bank_id: str = None):
        self.rules_file = rules_file or RULES_FILE
        self.bank_id = bank_id  # None = 全局规则
        self.keywords = []   # [(id, name, labels, action)]
        self.replacement = '****'
        self.account_whitelist = []  # [(value, note)]
        self.load_rules()

    def load_rules(self, bank_id: str = None):
        """从 rules.json 加载规则

        Args:
            bank_id: 指定银行时，在全局规则基础上叠加该银行的私有额外规则。
            不传或传 None 则仅加载全局规则。
        """
        if bank_id is not None:
            self.bank_id = bank_id

        try:
            with open(self.rules_file, 'r', encoding='utf-8') as f:
                rules = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            rules = {'patterns': [], 'keywords': [], 'replacement': '****'}

        self.replacement = rules.get('replacement', '****')

        # 加载账号白名单 （提取 value, note, is_regex）
        self.account_whitelist = []
        for item in rules.get('account_whitelist', []):
            if item.get('enabled', True) and item.get('value', '').strip():
                self.account_whitelist.append({
                    'value': item['value'],
                    'note': item.get('note', ''),
                    'is_regex': item.get('is_regex', False)
                })

        # 确定基础关键字规则
        base_keywords = rules.get('keywords', [])

        # 如果指定了银行，叠加该银行的私有额外规则
        if self.bank_id:
            bank_data = next(
                (b for b in rules.get('banks', [])
                 if b['id'] == self.bank_id and b.get('enabled', True)),
                None
            )
            if bank_data:
                disabled = set(bank_data.get('disabled_global_rules', []))
                base_keywords = [k for k in base_keywords
                                 if k['id'] not in disabled]
                # 叠加银行私有规则
                base_keywords += bank_data.get('extra_keywords', [])

        # 编译正则模式
        # 移除 patterns 正则加载，现在全部统一在 account_whitelist 中处理

        # 加载关键字标签
        self.keywords = []
        for k in base_keywords:
            if not k.get('enabled', True):
                continue
            self.keywords.append((
                k['id'],
                k['name'],
                k.get('labels', []),
                k.get('action', 'redact_value'),
            ))

    def scan_text(self, text: str) -> list[ScanMatch]:
        """扫描纯文本，返回所有匹配结果"""
        matches = []

        # ---- 精确账号或正则模式 (由 account_whitelist 处理) ----
        for acc in self.account_whitelist:
            value = acc['value']
            note = acc['note']
            is_regex = acc['is_regex']
            rule_name = f'账号规则({note})' if note else '账号规则'
            
            if is_regex:
                try:
                    pattern = re.compile(value)
                    for m in pattern.finditer(text):
                        matches.append(ScanMatch(
                            rule_id='whitelist_regex',
                            rule_name=rule_name,
                            matched_text=m.group(),
                            start=m.start(),
                            end=m.end(),
                            match_type='whitelist',
                            trigger=f'命中白名单正则: {value}'
                        ))
                except re.error:
                    pass
            else:
                start = 0
                while True:
                    idx = text.find(value, start)
                    if idx == -1:
                        break
                    matches.append(ScanMatch(
                        rule_id='whitelist_exact',
                        rule_name=rule_name,
                        matched_text=value,
                        start=idx,
                        end=idx + len(value),
                        match_type='whitelist',
                        trigger=f'命中精确账号: {value}'
                    ))
                    start = idx + len(value)

        # 关键字标签扫描
        for rule_id, rule_name, labels, action in self.keywords:
            for label in labels:
                # 严谨的边界匹配：对于全英文标签，强制两边加词边界限制
                # 以避免 "Account" 去匹配 "Beneficiary Account"
                is_pure_english = bool(re.match(r'^[A-Za-z0-9\s/.-]+$', label))
                if is_pure_english:
                    # 前后均不得跟其他英文字母（即词边界保护）
                    r_str = r'(?<![A-Za-z0-9])' + re.escape(label) + r'(?![A-Za-z0-9])[：:\s]*([^\s,，;；\n]+)'
                else:
                    r_str = re.escape(label) + r'[：:\s]*([^\s,，;；\n]+)'

                label_pattern = re.compile(r_str, re.UNICODE | re.IGNORECASE)
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
                            trigger=f'命中关键字标签(Key): {label}'
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
