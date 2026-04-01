"""规则配置标签页"""
import json
import tkinter as tk
from tkinter import messagebox
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from ttkbootstrap.scrolled import ScrolledFrame

from config import RULES_FILE
from core.i18n import t


class RulesTab(ttk.Frame):
    """规则配置标签页"""

    def __init__(self, parent, redactor):
        super().__init__(parent, padding=15)
        self.redactor = redactor
        self.rules_file = RULES_FILE
        self._current_bank_id = None  # None = 全局规则
        self._build_bank_selector()
        self._build_ui()
        self._load_rules()

    def _build_bank_selector(self):
        """构建顶部银行选择器"""
        bar = ttk.Frame(self)
        bar.pack(fill=X, pady=(0, 8))
        self._bank_label = ttk.Label(bar, text=t('rules_bank_label'))
        self._bank_label.pack(side=LEFT, padx=(0, 5))
        self._bank_var = tk.StringVar()
        self._bank_combo = ttk.Combobox(
            bar, textvariable=self._bank_var, state='readonly', width=26)
        self._bank_combo.pack(side=LEFT)
        self._bank_combo.bind('<<ComboboxSelected>>', self._on_bank_changed)
        self._refresh_bank_selector()

    def _refresh_bank_selector(self):
        """刷新银行下拉框列表"""
        options = [f"◆ {t('file_bank_all')}"]
        try:
            with open(self.rules_file, 'r', encoding='utf-8') as f:
                rules = json.load(f)
            for b in rules.get('banks', []):
                options.append(f"{b['name']}  [{b['id']}]")
        except Exception:
            pass
        current = self._bank_var.get()
        self._bank_combo['values'] = options
        if current in options:
            self._bank_var.set(current)
        else:
            self._bank_var.set(options[0])

    def _on_bank_changed(self, event=None):
        """银行切换时重新加载对应规则"""
        val = self._bank_var.get()
        if '[' in val:
            self._current_bank_id = val.split('[')[-1].rstrip(']').strip()
        else:
            self._current_bank_id = None
        self._load_rules()

    def _build_ui(self):
        # 底部操作栏：替换字符 + 保存 + 测试
        bottom_frame = ttk.Frame(self)
        bottom_frame.pack(fill=X, side=BOTTOM, pady=(10, 0))

        self._replacement_label = ttk.Label(bottom_frame, text=t('rules_replacement_label'))
        self._replacement_label.pack(side=LEFT)
        self.replacement_var = tk.StringVar(value='****')
        ttk.Entry(bottom_frame, textvariable=self.replacement_var, width=10).pack(side=LEFT, padx=5)

        self._btn_save = ttk.Button(bottom_frame, text=t('rules_save_btn'), style='success.TButton',
                                    command=self._save_rules)
        self._btn_save.pack(side=RIGHT, padx=(5, 0))
        self._btn_test = ttk.Button(bottom_frame, text=t('rules_test_btn'), style='info.TButton',
                                    command=self._test_rules)
        self._btn_test.pack(side=RIGHT)

        # 主内容区域采用 ScrolledFrame
        self.scroll_frame = ScrolledFrame(self, autohide=True)
        self.scroll_frame.pack(fill=BOTH, expand=True)
        main_container = self.scroll_frame.container

        # -----------------------------
        # 关键字标签规则区域
        # -----------------------------
        self._keyword_frame = ttk.LabelFrame(main_container, text=t('rules_keyword_section'))
        self._keyword_frame.pack(fill=X, pady=(0, 10))

        cols_k = ('id', 'name', 'labels', 'enabled')
        self.keyword_tree = ttk.Treeview(self._keyword_frame, columns=cols_k, show='headings', height=6)
        self.keyword_tree.heading('id', text=t('col_id'))
        self.keyword_tree.heading('name', text=t('col_name'))
        self.keyword_tree.heading('labels', text=t('col_labels'))
        self.keyword_tree.heading('enabled', text=t('col_enabled'))
        self.keyword_tree.column('id', width=100)
        self.keyword_tree.column('name', width=120)
        self.keyword_tree.column('labels', width=300)
        self.keyword_tree.column('enabled', width=60, anchor=CENTER)
        self.keyword_tree.pack(fill=X, expand=True, pady=(0, 5))

        k_btn_frame = ttk.Frame(self._keyword_frame)
        k_btn_frame.pack(fill=X)
        self._btn_k_add = ttk.Button(k_btn_frame, text=t('btn_add'), style='success-outline.TButton', command=self._add_keyword)
        self._btn_k_add.pack(side=LEFT, padx=(0, 3))
        self._btn_k_edit = ttk.Button(k_btn_frame, text=t('btn_edit'), style='info-outline.TButton', command=self._edit_keyword)
        self._btn_k_edit.pack(side=LEFT, padx=(0, 3))
        self._btn_k_del = ttk.Button(k_btn_frame, text=t('btn_delete'), style='danger-outline.TButton', command=self._delete_keyword)
        self._btn_k_del.pack(side=LEFT, padx=(0, 3))
        self._btn_k_tg = ttk.Button(k_btn_frame, text=t('btn_toggle'), style='warning-outline.TButton', command=self._toggle_keyword)
        self._btn_k_tg.pack(side=LEFT)

        # -----------------------------
        # 账号 / 正则 精确匹配名单区域
        # -----------------------------
        self._whitelist_frame = ttk.LabelFrame(main_container, text=t('rules_whitelist_section'))
        self._whitelist_frame.pack(fill=X, pady=(0, 10))

        mode_frame = ttk.Frame(self._whitelist_frame)
        mode_frame.pack(fill=X, pady=(0, 5))
        # 移除 whitelist_mode_var 开关，现在默认全开启模式以简化逻辑

        cols_w = ('value', 'note', 'is_regex', 'enabled')
        self.whitelist_tree = ttk.Treeview(self._whitelist_frame, columns=cols_w, show='headings', height=5)
        self.whitelist_tree.heading('value', text=t('col_account'))
        self.whitelist_tree.heading('note', text=t('col_note'))
        self.whitelist_tree.heading('is_regex', text='正则?')
        self.whitelist_tree.heading('enabled', text=t('col_enabled'))
        self.whitelist_tree.column('value', width=250)
        self.whitelist_tree.column('note', width=150)
        self.whitelist_tree.column('is_regex', width=60, anchor=CENTER)
        self.whitelist_tree.column('enabled', width=60, anchor=CENTER)
        self.whitelist_tree.pack(fill=X, expand=True, pady=(0, 5))

        w_btn_frame = ttk.Frame(self._whitelist_frame)
        w_btn_frame.pack(fill=X)
        self._btn_w_add = ttk.Button(w_btn_frame, text=t('btn_add_account'), style='success-outline.TButton', command=self._add_whitelist)
        self._btn_w_add.pack(side=LEFT, padx=(0, 3))
        self._btn_w_edit = ttk.Button(w_btn_frame, text=t('btn_edit'), style='info-outline.TButton', command=self._edit_whitelist)
        self._btn_w_edit.pack(side=LEFT, padx=(0, 3))
        self._btn_w_del = ttk.Button(w_btn_frame, text=t('btn_delete'), style='danger-outline.TButton', command=self._delete_whitelist)
        self._btn_w_del.pack(side=LEFT, padx=(0, 3))
        self._btn_w_tg = ttk.Button(w_btn_frame, text=t('btn_toggle'), style='warning-outline.TButton', command=self._toggle_whitelist)
        self._btn_w_tg.pack(side=LEFT)


    def _load_rules(self):
        """从文件加载规则到 UI"""
        try:
            with open(self.rules_file, 'r', encoding='utf-8') as f:
                rules = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            rules = {'keywords': [], 'replacement': '****'}

        self.replacement_var.set(rules.get('replacement', '****'))

        # 确定当前要展示的规则源：全局 or 银行私有
        if self._current_bank_id:
            bank_data = next(
                (b for b in rules.get('banks', []) if b['id'] == self._current_bank_id), None)
            keywords_to_show = bank_data.get('extra_keywords', []) if bank_data else []
        else:
            keywords_to_show = rules.get('keywords', [])

        # 加载关键字
        for item in self.keyword_tree.get_children():
            self.keyword_tree.delete(item)
        for k in keywords_to_show:
            labels_str = ', '.join(k.get('labels', []))
            self.keyword_tree.insert('', END, values=(
                k.get('id', ''), k.get('name', ''), labels_str,
                '✓' if k.get('enabled', True) else '✗'
            ))

        # 加载账号列表
        # (移除 whitelist_mode_var 设置)
        for item in self.whitelist_tree.get_children():
            self.whitelist_tree.delete(item)
        for w in rules.get('account_whitelist', []):
            self.whitelist_tree.insert('', END, values=(
                w.get('value', ''),
                w.get('note', ''),
                '✓' if w.get('is_regex', False) else '✗',
                '✓' if w.get('enabled', True) else '✗',
            ))

    def _save_rules(self):
        """保存规则到文件"""
        try:
            with open(self.rules_file, 'r', encoding='utf-8') as f:
                rules = json.load(f)
        except Exception:
            rules = {'keywords': [], 'banks': [],
                     'replacement': '****', 'use_whitelist_mode': True,
                     'account_whitelist': []}

        ui_keywords = []
        for item in self.keyword_tree.get_children():
            values = self.keyword_tree.item(item, 'values')
            labels = [la.strip() for la in values[2].split(',') if la.strip()]
            ui_keywords.append({
                'id': values[0], 'name': values[1],
                'labels': labels, 'action': 'redact_value',
                'enabled': values[3] == '✓',
            })

        if self._current_bank_id:
            banks = rules.get('banks', [])
            target = next((b for b in banks if b['id'] == self._current_bank_id), None)
            if target:
                target['extra_keywords'] = ui_keywords
                if 'extra_patterns' in target:
                    del target['extra_patterns'] # 清理旧数据
            rules['banks'] = banks
        else:
            rules['keywords'] = ui_keywords
            if 'patterns' in rules:
                del rules['patterns'] # 清理全局旧模式

        # 精确名单全局保存
        rules['replacement'] = self.replacement_var.get() or '****'
        # 强制启用统一模式
        rules['use_whitelist_mode'] = True
        if 'patterns' in rules:
            del rules['patterns']
            
        rules['account_whitelist'] = []
        for item in self.whitelist_tree.get_children():
            values = self.whitelist_tree.item(item, 'values')
            rules['account_whitelist'].append({
                'value': values[0], 'note': values[1],
                'is_regex': values[2] == '✓',
                'enabled': values[3] == '✓',
            })

        with open(self.rules_file, 'w', encoding='utf-8') as f:
            json.dump(rules, f, ensure_ascii=False, indent=2)

        self.redactor.reload_rules()
        messagebox.showinfo('成功', t('msg_save_ok'))

    # ---- 关键字操作 ----
    def _add_keyword(self):
        self._keyword_dialog(t('dialog_add_keyword'))

    def _edit_keyword(self):
        selected = self.keyword_tree.selection()
        if not selected:
            messagebox.showwarning('提示', t('msg_select_first'))
            return
        values = self.keyword_tree.item(selected[0], 'values')
        self._keyword_dialog(t('dialog_edit_keyword'), selected[0], values)

    def _keyword_dialog(self, title, item=None, values=None):
        dialog = tk.Toplevel(self)
        dialog.title(title)
        dialog.geometry('450x220')
        dialog.transient(self)
        dialog.grab_set()

        frame = ttk.Frame(dialog, padding=15)
        frame.pack(fill=BOTH, expand=True)

        ttk.Label(frame, text='ID:').grid(row=0, column=0, sticky=W, pady=3)
        id_var = tk.StringVar(value=values[0] if values else '')
        ttk.Entry(frame, textvariable=id_var).grid(row=0, column=1, sticky=EW, pady=3)

        ttk.Label(frame, text=t('col_name')+':').grid(row=1, column=0, sticky=W, pady=3)
        name_var = tk.StringVar(value=values[1] if values else '')
        ttk.Entry(frame, textvariable=name_var).grid(row=1, column=1, sticky=EW, pady=3)

        ttk.Label(frame, text=t('col_labels')+':').grid(row=2, column=0, sticky=W, pady=3)
        labels_var = tk.StringVar(value=values[2] if values else '')
        ttk.Entry(frame, textvariable=labels_var).grid(row=2, column=1, sticky=EW, pady=3)
        ttk.Label(frame, text='多个标签用逗号分隔', font=('', 8), foreground='gray').grid(row=3, column=1, sticky=W)

        frame.columnconfigure(1, weight=1)

        def save():
            if not id_var.get() or not name_var.get() or not labels_var.get():
                messagebox.showwarning('提示', t('msg_empty_field'))
                return
            new_values = (id_var.get(), name_var.get(), labels_var.get(), values[3] if values else '✓')
            if item:
                self.keyword_tree.item(item, values=new_values)
            else:
                self.keyword_tree.insert('', END, values=new_values)
            dialog.destroy()

        ttk.Button(frame, text=t('btn_ok'), style='success.TButton',
                   command=save).grid(row=4, column=1, sticky=E, pady=(10, 0))

    def _delete_keyword(self):
        selected = self.keyword_tree.selection()
        if selected:
            self.keyword_tree.delete(selected[0])

    def _toggle_keyword(self):
        selected = self.keyword_tree.selection()
        if not selected:
            return
        values = list(self.keyword_tree.item(selected[0], 'values'))
        values[3] = '✗' if values[3] == '✓' else '✓'
        self.keyword_tree.item(selected[0], values=values)

    # ---- 账号/正则白名单操作 ----
    def _add_whitelist(self):
        self._whitelist_dialog(t('dialog_add_account'))

    def _edit_whitelist(self):
        selected = self.whitelist_tree.selection()
        if not selected:
            messagebox.showwarning('提示', t('msg_select_first'))
            return
        values = self.whitelist_tree.item(selected[0], 'values')
        self._whitelist_dialog(t('dialog_edit_account'), selected[0], values)

    def _whitelist_dialog(self, title, item=None, values=None):
        dialog = tk.Toplevel(self)
        dialog.title(title)
        dialog.geometry('420x200')
        dialog.transient(self)
        dialog.grab_set()

        frame = ttk.Frame(dialog, padding=15)
        frame.pack(fill=BOTH, expand=True)

        ttk.Label(frame, text=t('col_account')+':').grid(row=0, column=0, sticky=W, pady=5)
        value_var = tk.StringVar(value=values[0] if values else '')
        ttk.Entry(frame, textvariable=value_var, width=35).grid(row=0, column=1, sticky=EW, pady=5)

        ttk.Label(frame, text=t('col_note')+':').grid(row=1, column=0, sticky=W, pady=5)
        note_var = tk.StringVar(value=values[1] if values else '')
        ttk.Entry(frame, textvariable=note_var, width=35).grid(row=1, column=1, sticky=EW, pady=5)
        
        is_regex_var = tk.BooleanVar(value=(values[2] == '✓') if values else False)
        ttk.Checkbutton(frame, text='是否为正则表达式', variable=is_regex_var).grid(row=2, column=1, sticky=W, pady=5)

        frame.columnconfigure(1, weight=1)

        def save():
            if not value_var.get().strip():
                messagebox.showwarning('提示', t('msg_account_empty'))
                return
            new_values = (
                value_var.get().strip(), 
                note_var.get().strip(), 
                '✓' if is_regex_var.get() else '✗',
                values[3] if values else '✓'
            )
            if item:
                self.whitelist_tree.item(item, values=new_values)
            else:
                self.whitelist_tree.insert('', END, values=new_values)
            dialog.destroy()

        ttk.Button(frame, text=t('btn_ok'), style='success.TButton',
                   command=save).grid(row=3, column=1, sticky=E, pady=(10, 0))

    def _delete_whitelist(self):
        selected = self.whitelist_tree.selection()
        if selected:
            self.whitelist_tree.delete(selected[0])

    def _toggle_whitelist(self):
        selected = self.whitelist_tree.selection()
        if not selected:
            return
        values = list(self.whitelist_tree.item(selected[0], 'values'))
        values[3] = '✗' if values[3] == '✓' else '✓'
        self.whitelist_tree.item(selected[0], values=values)

    # ---- 测试规则 ----
    def _test_rules(self):
        """测试脱敏打码效果"""
        dialog = tk.Toplevel(self)
        dialog.title(t('dialog_test'))
        dialog.geometry('600x550')
        dialog.transient(self)

        frame = ttk.Frame(dialog, padding=15)
        frame.pack(fill=BOTH, expand=True)

        ttk.Label(frame, text=t('test_input_label')).pack(anchor=W)
        text_input = tk.Text(frame, height=6, wrap=tk.WORD)
        text_input.pack(fill=X, pady=(3, 8))
        text_input.insert('1.0',
            '付款人：张三\n账号：6222021234567890123\n金额：100.00')

        ttk.Label(frame, text=t('test_result_label')).pack(anchor=W)
        result_text = tk.Text(frame, height=15, wrap=tk.WORD)
        result_text.pack(fill=BOTH, expand=True, pady=(3, 8))

        def run_test():
            self._save_rules()
            test_str = text_input.get('1.0', tk.END).strip()
            if not test_str: return

            matches = self.redactor.scanner.scan_text(test_str)
            redacted = self.redactor.scanner.redact_text(test_str, matches)

            result_text.delete('1.0', tk.END)
            result_text.insert(tk.END, f"{t('test_found')} {len(matches)} {t('test_found_suffix')}\n\n")
            for m in matches:
                result_text.insert(tk.END,
                    f'  [{m.rule_name}] -> "{m.matched_text}" (Type: {m.match_type})\n')
            
            result_text.insert(tk.END, f"\n{t('test_redacted_label')}\n\n{redacted}")

        ttk.Button(frame, text=t('test_run_btn'), style='success.TButton',
                   command=run_test).pack(anchor=E)

    def refresh_lang(self):
        """刷新文字"""
        self._bank_label.config(text=t('rules_bank_label'))
        self._refresh_bank_selector()
        self._replacement_label.config(text=t('rules_replacement_label'))
        self._btn_save.config(text=t('rules_save_btn'))
        self._btn_test.config(text=t('rules_test_btn'))
        
        self._keyword_frame.config(text=t('rules_keyword_section'))
        self.keyword_tree.heading('id', text=t('col_id'))
        self.keyword_tree.heading('name', text=t('col_name'))
        self.keyword_tree.heading('labels', text=t('col_labels'))
        self.keyword_tree.heading('enabled', text=t('col_enabled'))
        self._btn_k_add.config(text=t('btn_add'))
        self._btn_k_edit.config(text=t('btn_edit'))
        self._btn_k_del.config(text=t('btn_delete'))
        self._btn_k_tg.config(text=t('btn_toggle'))

        self._whitelist_frame.config(text=t('rules_whitelist_section'))
        self._whitelist_mode_chk.config(text=t('rules_whitelist_mode_tip'))
        self.whitelist_tree.heading('value', text=t('col_account'))
        self.whitelist_tree.heading('note', text=t('col_note'))
        self.whitelist_tree.heading('enabled', text=t('col_enabled'))
        self._btn_w_add.config(text=t('btn_add_account'))
        self._btn_w_edit.config(text=t('btn_edit'))
        self._btn_w_del.config(text=t('btn_delete'))
        self._btn_w_tg.config(text=t('btn_toggle'))
