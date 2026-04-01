"""内置正则模式库"""
import re


# 预编译的常用敏感信息模式
BUILTIN_PATTERNS = {
    'bank_account': {
        'name': '银行账号',
        'description': '16-19位数字银行卡/账号',
        'regex': r'(?<!\d)\d{16,19}(?!\d)',
    },
    'phone': {
        'name': '手机号码',
        'description': '11位手机号',
        'regex': r'(?<!\d)1[3-9]\d{9}(?!\d)',
    },
    'id_card': {
        'name': '身份证号',
        'description': '18位身份证号码',
        'regex': r'(?<!\d)\d{17}[\dXx](?![\dXx])',
    },
    'iban': {
        'name': 'IBAN账号',
        'description': '国际银行账号',
        'regex': r'\b[A-Z]{2}\d{2}[A-Z0-9]{4,30}\b',
    },
    'swift_code': {
        'name': 'SWIFT代码',
        'description': '银行SWIFT/BIC代码',
        'regex': r'\b[A-Z]{4}[A-Z]{2}[A-Z0-9]{2}([A-Z0-9]{3})?\b',
    },
}


def compile_pattern(regex_str: str) -> re.Pattern:
    """编译正则表达式，失败时返回 None"""
    try:
        return re.compile(regex_str)
    except re.error:
        return None
