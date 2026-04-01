"""扫描引擎单元测试"""
import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from core.scanner import Scanner


@pytest.fixture
def scanner():
    """创建使用默认规则的扫描器"""
    rules_file = os.path.join(os.path.dirname(__file__), '..', 'rules.json')
    return Scanner(rules_file)


class TestPatternScan:
    """正则模式扫描测试"""

    def test_bank_account_16_digits(self, scanner):
        text = '账号为1234567890123456，请核实'
        matches = scanner.scan_text(text)
        matched_texts = [m.matched_text for m in matches]
        assert '1234567890123456' in matched_texts

    def test_bank_account_19_digits(self, scanner):
        text = '卡号：6222021234567890123'
        matches = scanner.scan_text(text)
        matched_texts = [m.matched_text for m in matches]
        assert '6222021234567890123' in matched_texts

    def test_phone_number(self, scanner):
        text = '联系电话：13812345678'
        matches = scanner.scan_text(text)
        matched_texts = [m.matched_text for m in matches]
        assert '13812345678' in matched_texts

    def test_id_card(self, scanner):
        text = '身份证号：440102199001011234'
        matches = scanner.scan_text(text)
        matched_texts = [m.matched_text for m in matches]
        assert '440102199001011234' in matched_texts

    def test_no_false_positive_short_number(self, scanner):
        text = '订单号12345'
        matches = scanner.scan_text(text)
        # 5位数字不应匹配银行账号
        bank_matches = [m for m in matches if m.rule_id == 'bank_account']
        assert len(bank_matches) == 0


class TestKeywordScan:
    """关键字标签扫描测试"""

    def test_payer_name(self, scanner):
        text = '付款人：张三丰'
        matches = scanner.scan_text(text)
        matched_texts = [m.matched_text for m in matches]
        assert '张三丰' in matched_texts

    def test_payer_account(self, scanner):
        text = '付款账号：6222021234567890123'
        matches = scanner.scan_text(text)
        # 应同时被正则和关键字匹配
        assert len(matches) >= 1

    def test_payer_bank(self, scanner):
        text = '付款行：工商银行北京分行'
        matches = scanner.scan_text(text)
        matched_texts = [m.matched_text for m in matches]
        assert '工商银行北京分行' in matched_texts

    def test_multiple_labels(self, scanner):
        text = '付款人：张三\n付款账号：6222021234567890123\n手机号：13812345678'
        matches = scanner.scan_text(text)
        assert len(matches) >= 3  # 至少3处匹配


class TestRedaction:
    """脱敏替换测试"""

    def test_redact_text(self, scanner):
        text = '付款人：张三丰，手机号：13812345678'
        result = scanner.redact_text(text)
        assert '张三丰' not in result
        assert '13812345678' not in result
        assert '****' in result

    def test_redact_preserves_structure(self, scanner):
        text = '付款人：张三丰'
        result = scanner.redact_text(text)
        assert result.startswith('付款人')


class TestKeyValueScan:
    """键值对扫描测试"""

    def test_kv_pair_match(self, scanner):
        pairs = [('付款人', '张三丰'), ('金额', '50000')]
        matches = scanner.scan_key_value_pairs(pairs)
        matched_values = [m.value_text for m in matches]
        assert '张三丰' in matched_values

    def test_kv_pair_regex_in_value(self, scanner):
        pairs = [('账号信息', '6222021234567890123')]
        matches = scanner.scan_key_value_pairs(pairs)
        assert len(matches) >= 1


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
