import re
from core.scanner import Scanner, ScanMatch
import json
import os

def test_word_boundary():
    # 创建模拟规则
    rules = {
        "keywords": [
            {
                "id": "tpl_iban",
                "name": "IBAN",
                "labels": ["IBAN"],
                "action": "redact_value",
                "case_sensitive": False,
                "enabled": True
            }
        ],
        "account_whitelist": [],
        "replacement": "****"
    }
    
    with open('verify_rules.json', 'w', encoding='utf-8') as f:
        json.dump(rules, f)
        
    scanner = Scanner('verify_rules.json')
    
    # 测试 1: CITIBANK (不应匹配 IBAN)
    text1 = "Our bank is CITIBANK."
    matches1 = scanner.scan_text(text1)
    print(f"Test 1 (CITIBANK): Found {len(matches1)} matches. (Expected: 0)")
    
    # 测试 2: 孤立的 IBAN (应当匹配)
    text2 = "My IBAN is GB123456"
    matches2 = scanner.scan_text(text2)
    print(f"Test 2 (Isolated IBAN): Found {len(matches2)} matches. (Expected: 1)")
    if matches2:
        print(f"  Matched text: {matches2[0].matched_text}")

    os.remove('verify_rules.json')

if __name__ == "__main__":
    test_word_boundary()
