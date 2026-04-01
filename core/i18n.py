"""界面多语言支持（i18n）

使用方式：
    from core.i18n import t, set_language
    t('app_title')         -> '银行水单脱敏工具' 或 'Bank Statement Redaction Tool'
    set_language('en')     -> 切换为英文
"""
import json
import os

# ---- 语言字典 ----
_STRINGS = {
    'zh': {
        # 主窗口
        'app_title': '银行水单脱敏工具',
        'app_version': 'v1.1',
        'lang_btn': 'English',
        # Tab 标题
        'tab_file': '  📁 文件处理  ',
        'tab_rules': '  ⚙️ 规则配置  ',
        'tab_log': '  📋 脱敏日志  ',
        'tab_banks': '  🏦 银行配置  ',
        # 文件处理 Tab
        'file_bank_label': '银行:',
        'file_bank_all': '通用（不限银行）',
        'file_add_btn': '添加文件',
        'file_clear_btn': '清空列表',
        'file_process_btn': '开始脱敏',
        'file_output_label': '输出目录:',
        'file_open_output': '打开输出目录',
        'file_status_ready': '就绪',
        'file_status_processing': '处理中...',
        'file_status_done': '处理完成',
        'file_col_name': '文件名',
        'file_col_type': '类型',
        'file_col_status': '状态',
        'file_col_count': '脱敏数',
        # 规则配置 Tab
        'rules_pattern_section': '正则模式规则',
        'rules_keyword_section': '关键字标签规则',
        'rules_whitelist_section': '精准脱敏名单 (直接涂黑匹配到的内容，如账号、正则)',
        'rules_whitelist_mode_tip': '注意：向精准名单添加正则时请勾选对应项',
        'rules_bank_label': '当前银行规则视图:',
        'rules_replacement_label': '替换字符:',
        'rules_save_btn': '全部保存',
        'rules_test_btn': '测试规则',
        'col_id': 'ID',
        'col_name': '规则名称(仅备注)',
        'col_regex': '正则表达式',
        'col_enabled': '开启',
        'col_case_sensitive': '大小写',
        'col_labels': '触发关键字(打码上方或左侧的键)',
        'col_account': '希望脱敏的内容 (账号/正则/词汇)',
        'col_note': '备注',
        'btn_add': '添加',
        'btn_edit': '编辑',
        'btn_delete': '删除',
        'btn_toggle': '切换启用',
        'btn_add_account': '添加账号',
        'btn_ok': '确定',
        # 脱敏日志 Tab
        'log_refresh_btn': '刷新',
        'log_save_btn': '保存日志',
        'log_clear_btn': '清空',
        'log_col_file': '文件',
        'log_col_type': '类型',
        'log_col_status': '状态',
        'log_col_count': '脱敏数',
        'log_col_time': '时间',
        # 银行配置 Tab
        'banks_add_btn': '添加银行',
        'banks_edit_btn': '编辑',
        'banks_delete_btn': '删除',
        'banks_col_id': 'ID',
        'banks_col_name': '银行名称',
        'banks_col_enabled': '启用',
        # 提示
        'msg_select_first': '请先选择一条规则',
        'msg_empty_field': '所有字段都不能为空',
        'msg_save_ok': '规则已保存',
        'msg_account_empty': '账号不能为空',
        'dialog_add_pattern': '添加正则模式',
        'dialog_edit_pattern': '编辑正则模式',
        'dialog_add_keyword': '添加关键字规则',
        'dialog_edit_keyword': '编辑关键字规则',
        'dialog_add_account': '添加目标值',
        'dialog_edit_account': '编辑目标值',
        'dialog_test': '规则测试',
        'test_input_label': '输入测试文本:',
        'test_result_label': '匹配结果:',
        'test_run_btn': '执行测试',
        'test_found': '找到',
        'test_found_suffix': '处匹配:',
        'test_redacted_label': '--- 脱敏后文本 ---',
    },
    'en': {
        # Main window
        'app_title': 'Bank Statement Redaction Tool',
        'app_version': 'v1.1',
        'lang_btn': '中文',
        # Tab titles
        'tab_file': '  📁 Files  ',
        'tab_rules': '  ⚙️ Rules  ',
        'tab_log': '  📋 Logs  ',
        'tab_banks': '  🏦 Banks  ',
        # File tab
        'file_bank_label': 'Bank:',
        'file_bank_all': 'Generic (All Banks)',
        'file_add_btn': 'Add Files',
        'file_clear_btn': 'Clear List',
        'file_process_btn': 'Start Redaction',
        'file_output_label': 'Output Dir:',
        'file_open_output': 'Open Output Dir',
        'file_status_ready': 'Ready',
        'file_status_processing': 'Processing...',
        'file_status_done': 'Done',
        'file_col_name': 'Filename',
        'file_col_type': 'Type',
        'file_col_status': 'Status',
        'file_col_count': 'Redacted',
        # Rules tab
        'rules_pattern_section': 'Regex Patterns',
        'rules_keyword_section': 'Keyword Labels',
        'rules_whitelist_section': 'Manual Redaction List (Redact matching content directly)',
        'rules_whitelist_mode_tip': 'Note: Check "Is Regex" when adding a pattern',
        'rules_bank_label': 'Current Bank View:',
        'rules_replacement_label': 'Replacement:',
        'rules_save_btn': 'Save All',
        'rules_test_btn': 'Test Rules',
        'col_id': 'ID',
        'col_name': 'Name (Note only)',
        'col_regex': 'Regex',
        'col_enabled': 'Enabled',
        'col_case_sensitive': 'Case',
        'col_labels': 'Trigger Keywords (Keys)',
        'col_account': 'Content to Redact (Acc/Regex/Word)',
        'col_note': 'Note',
        'btn_add': 'Add',
        'btn_edit': 'Edit',
        'btn_delete': 'Delete',
        'btn_toggle': 'Toggle',
        'btn_add_account': 'Add Account',
        'btn_ok': 'OK',
        # Log tab
        'log_refresh_btn': 'Refresh',
        'log_save_btn': 'Save Log',
        'log_clear_btn': 'Clear',
        'log_col_file': 'File',
        'log_col_type': 'Type',
        'log_col_status': 'Status',
        'log_col_count': 'Redacted',
        'log_col_time': 'Time',
        # Banks tab
        'banks_add_btn': 'Add Bank',
        'banks_edit_btn': 'Edit',
        'banks_delete_btn': 'Delete',
        'banks_col_id': 'ID',
        'banks_col_name': 'Bank Name',
        'banks_col_enabled': 'Enabled',
        # Messages
        'msg_select_first': 'Please select a rule first',
        'msg_empty_field': 'All fields are required',
        'msg_save_ok': 'Rules saved',
        'msg_account_empty': 'Account cannot be empty',
        'dialog_add_pattern': 'Add Regex Pattern',
        'dialog_edit_pattern': 'Edit Regex Pattern',
        'dialog_add_keyword': 'Add Keyword Rule',
        'dialog_edit_keyword': 'Edit Keyword Rule',
        'dialog_add_account': 'Add Value',
        'dialog_edit_account': 'Edit Value',
        'dialog_test': 'Test Rules',
        'test_input_label': 'Input text to test:',
        'test_result_label': 'Match results:',
        'test_run_btn': 'Run Test',
        'test_found': 'Found',
        'test_found_suffix': 'match(es):',
        'test_redacted_label': '--- Redacted Text ---',
    },
}

# ---- 当前语言状态 ----
_current_lang = 'zh'
_config_path = os.path.join(
    os.path.expanduser('~'), '.sensitive_tool', 'config.json'
)


def _load_lang_config():
    """从用户配置文件加载语言设置"""
    global _current_lang
    try:
        if os.path.exists(_config_path):
            with open(_config_path, 'r', encoding='utf-8') as f:
                cfg = json.load(f)
                _current_lang = cfg.get('language', 'zh')
    except Exception:
        _current_lang = 'zh'


def _save_lang_config():
    """保存语言设置到用户配置文件"""
    try:
        os.makedirs(os.path.dirname(_config_path), exist_ok=True)
        cfg = {}
        if os.path.exists(_config_path):
            with open(_config_path, 'r', encoding='utf-8') as f:
                cfg = json.load(f)
        cfg['language'] = _current_lang
        with open(_config_path, 'w', encoding='utf-8') as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def set_language(lang: str):
    """切换语言（'zh' 或 'en'）"""
    global _current_lang
    if lang in _STRINGS:
        _current_lang = lang
        _save_lang_config()


def get_language() -> str:
    """获取当前语言"""
    return _current_lang


def t(key: str) -> str:
    """获取当前语言的界面文字

    Args:
        key: 字符串 key

    Returns:
        对应语言的文本，找不到时返回 key 本身
    """
    return _STRINGS.get(_current_lang, {}).get(key, key)


# 启动时加载语言配置
_load_lang_config()
