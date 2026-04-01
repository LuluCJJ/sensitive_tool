"""功能验证测试脚本 - 验证本次4个新功能

运行方式: .venv_stable\Scripts\python.exe test_new_features.py
"""
import json
import os
import sys
import pathlib
import tempfile
import shutil

# 确保项目根目录在 path 里
sys.path.insert(0, str(pathlib.Path(__file__).parent))

RULES_FILE = pathlib.Path('rules.json')
PASS = '✅'
FAIL = '❌'
results = []

def report(name, ok, detail=''):
    mark = PASS if ok else FAIL
    msg = f'{mark} {name}'
    if detail:
        msg += f'\n     {detail}'
    print(msg)
    results.append((name, ok))

def backup_rules():
    return json.loads(RULES_FILE.read_text('utf-8'))

def restore_rules(orig):
    RULES_FILE.write_text(json.dumps(orig, ensure_ascii=False, indent=2), 'utf-8')

# ============================================================
# 测试 1 - i18n 模块
# ============================================================
print('\n=== 测试 1: i18n 中英文切换 ===')
from core.i18n import t, set_language, get_language

set_language('zh')
zh_title = t('app_title')
zh_btn   = t('lang_btn')
report('中文 app_title', zh_title == '银行水单脱敏工具', f'got: {zh_title}')
report('中文 lang_btn 显示 English', zh_btn == 'English', f'got: {zh_btn}')

set_language('en')
en_title = t('app_title')
en_btn   = t('lang_btn')
report('English app_title', 'Bank' in en_title, f'got: {en_title}')
report('English lang_btn 显示 中文', en_btn == '中文', f'got: {en_btn}')

set_language('zh')  # 恢复中文

# ============================================================
# 测试 2 - 账号白名单模式
# ============================================================
print('\n=== 测试 2: 账号白名单精确脱敏 ===')
orig_rules = backup_rules()

from core.scanner import Scanner

# 2a: 白名单模式 - 只脱敏名单内账号
rules = json.loads(RULES_FILE.read_text('utf-8'))
rules['use_whitelist_mode'] = True
rules['account_whitelist'] = [
    {'value': 'GB29NWBK60161331926819', 'note': '付款IBAN', 'enabled': True},
    {'value': '6222021234567890123',    'note': '付款账号', 'enabled': True},
]
RULES_FILE.write_text(json.dumps(rules, ensure_ascii=False, indent=2), 'utf-8')

scanner = Scanner()
text = '付款IBAN: GB29NWBK60161331926819  收款IBAN: DE89370400440532013000  付款账号: 6222021234567890123'
matches = scanner.scan_text(text)
match_texts = [m.matched_text for m in matches]

report('白名单模式: 命中付款IBAN',    'GB29NWBK60161331926819' in match_texts)
report('白名单模式: 命中付款账号',    '6222021234567890123' in match_texts)
report('白名单模式: 收款IBAN未误伤',  'DE89370400440532013000' not in match_texts,
       f'matches={match_texts}')
report('白名单模式: 正则被禁用(无正则match)', 
       all(m.match_type == 'whitelist' for m in matches if m.match_type != 'keyword'))

# 2b: 关闭白名单模式 - 正则恢复
rules['use_whitelist_mode'] = False
rules['account_whitelist'] = []
RULES_FILE.write_text(json.dumps(rules, ensure_ascii=False, indent=2), 'utf-8')
scanner2 = Scanner()
matches2 = scanner2.scan_text('账号: 6222021234567890123')
report('正则模式: 正则正常工作', len(matches2) > 0, f'matches={[m.matched_text for m in matches2]}')

restore_rules(orig_rules)

# ============================================================
# 测试 3 - 银行维度规则 (bank_id)
# ============================================================
print('\n=== 测试 3: 银行维度规则叠加 ===')
orig_rules = backup_rules()

rules = json.loads(RULES_FILE.read_text('utf-8'))
rules['banks'] = [
    {
        'id': 'test_bank',
        'name': '测试银行',
        'enabled': True,
        'extra_keywords': [
            {
                'id': 'test_kw', 'name': '测试银行专属关键字',
                'labels': ['测试行账号'], 'action': 'redact_value', 'enabled': True
            }
        ],
        'extra_patterns': [],
        'disabled_global_rules': [],
    }
]
RULES_FILE.write_text(json.dumps(rules, ensure_ascii=False, indent=2), 'utf-8')

# 全局 scanner（不含测试银行关键字）
s_global = Scanner()
global_kw_ids = [k[0] for k in s_global.keywords]
report('全局模式: 不含银行私有关键字', 'test_kw' not in global_kw_ids,
       f'keywords={global_kw_ids}')

# 银行专属 scanner
s_bank = Scanner(bank_id='test_bank')
bank_kw_ids = [k[0] for k in s_bank.keywords]
report('银行模式: 包含银行私有关键字', 'test_kw' in bank_kw_ids,
       f'keywords={bank_kw_ids}')

# 银行 scanner 仍能扫描全局规则 (测试关键字 ABCDEFG 以免被正则去重)
matches_bank = s_bank.scan_text('账号: 6222021234567890123 测试行账号: ABCDEFG')
rule_ids = [m.rule_id for m in matches_bank]
report('银行模式: 全局正则仍有效', 'bank_account' in rule_ids or any(m.matched_text == '6222021234567890123' for m in matches_bank))
report('银行模式: 银行私有关键字有效', 'test_kw' in rule_ids)

restore_rules(orig_rules)

# ============================================================
# 测试 4 - 图片处理器 _score_as_account
# ============================================================
print('\n=== 测试 4: 智能感知 _score_as_account 打分 ===')
from processors.image_processor import ImageProcessor

cases = [
    ('6222021234567890123',  1.0, '纯银行账号(19位数字)'),
    ('GB29NWBK60161331926819', 1.0, 'IBAN格式'),
    ('1234567890123456',     1.0, '16位纯数字'),
    ('123456789',            0.8, '9位数字'),
    ('1234付款',             0.6, '4位以上数字混合'),
    ('张三',                 0.1, '纯中文'),
    ('John Doe',             0.1, '纯英文'),
]

for text, expected, desc in cases:
    score = ImageProcessor._score_as_account(text)
    ok = abs(score - expected) < 0.05
    report(f'打分[{desc}]: 期望≈{expected}', ok, f'实际={score:.2f}')

# ============================================================
# 汇总
# ============================================================
print('\n' + '='*50)
total = len(results)
passed = sum(1 for _, ok in results if ok)
failed = total - passed
print(f'测试结果: {passed}/{total} 通过, {failed} 失败')
if failed == 0:
    print('🎉 全部通过！可以打包 EXE。')
else:
    print('⚠️  有失败项，请检查后再打包。')
    for name, ok in results:
        if not ok:
            print(f'  {FAIL} {name}')
