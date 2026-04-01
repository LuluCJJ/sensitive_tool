"""规则配置标签页"""
import json
import tkinter as tk
from tkinter import messagebox
import ttkbootstrap as ttk
from ttkbootstrap.constants import *

from config import RULES_FILE


class RulesTab(ttk.Frame):
    """规则配置标签页"""

    def __init__(self, parent, redactor):
        super().__init__(parent, padding=15)
        self.redactor = redactor
        self.rules_file = RULES_FILE
        self._build_ui()
        self._load_rules()

    def _build_ui(self):
        # 上半部分：正则模式
        pattern_frame = ttk.LabelFrame(self, text='正则模式规则')
        pattern_frame.pack(fill=BOTH, expand=True, pady=(0, 10))

        # 正则模式列表
        cols_p = ('id', 'name', 'regex', 'enabled')
        self.pattern_tree = ttk.Treeview(pattern_frame, columns=cols_p,
                                          show='headings', height=5)
        self.pattern_tree.heading('id', text='ID')
        self.pattern_tree.heading('name', text='名称')
        self.pattern_tree.heading('regex', text='正则表达式')
        self.pattern_tree.heading('enabled', text='启用')
        self.pattern_tree.column('id', width=100)
        self.pattern_tree.column('name', width=100)
        self.pattern_tree.column('regex', width=250)
        self.pattern_tree.column('enabled', width=60, anchor=CENTER)
        self.pattern_tree.pack(fill=BOTH, expand=True, pady=(0, 5))

        p_btn_frame = ttk.Frame(pattern_frame)
        p_btn_frame.pack(fill=X)
        ttk.Button(p_btn_frame, text='添加', style='success-outline.TButton',
                   command=self._add_pattern).pack(side=LEFT, padx=(0, 3))
        ttk.Button(p_btn_frame, text='编辑', style='info-outline.TButton',
                   command=self._edit_pattern).pack(side=LEFT, padx=(0, 3))
        ttk.Button(p_btn_frame, text='删除', style='danger-outline.TButton',
                   command=self._delete_pattern).pack(side=LEFT, padx=(0, 3))
        ttk.Button(p_btn_frame, text='切换启用', style='warning-outline.TButton',
                   command=self._toggle_pattern).pack(side=LEFT)

        # 下半部分：关键字标签
        keyword_frame = ttk.LabelFrame(self, text='关键字标签规则')
        keyword_frame.pack(fill=BOTH, expand=True, pady=(0, 10))

        cols_k = ('id', 'name', 'labels', 'enabled')
        self.keyword_tree = ttk.Treeview(keyword_frame, columns=cols_k,
                                          show='headings', height=5)
        self.keyword_tree.heading('id', text='ID')
        self.keyword_tree.heading('name', text='名称')
        self.keyword_tree.heading('labels', text='标签列表')
        self.keyword_tree.heading('enabled', text='启用')
        self.keyword_tree.column('id', width=100)
        self.keyword_tree.column('name', width=100)
        self.keyword_tree.column('labels', width=250)
        self.keyword_tree.column('enabled', width=60, anchor=CENTER)
        self.keyword_tree.pack(fill=BOTH, expand=True, pady=(0, 5))

        k_btn_frame = ttk.Frame(keyword_frame)
        k_btn_frame.pack(fill=X)
        ttk.Button(k_btn_frame, text='添加', style='success-outline.TButton',
                   command=self._add_keyword).pack(side=LEFT, padx=(0, 3))
        ttk.Button(k_btn_frame, text='编辑', style='info-outline.TButton',
                   command=self._edit_keyword).pack(side=LEFT, padx=(0, 3))
        ttk.Button(k_btn_frame, text='删除', style='danger-outline.TButton',
                   command=self._delete_keyword).pack(side=LEFT, padx=(0, 3))
        ttk.Button(k_btn_frame, text='切换启用', style='warning-outline.TButton',
                   command=self._toggle_keyword).pack(side=LEFT)

        # 底部：替换字符 + 保存 + 测试
        bottom_frame = ttk.Frame(self)
        bottom_frame.pack(fill=X)

        ttk.Label(bottom_frame, text='替换字符:').pack(side=LEFT)
        self.replacement_var = tk.StringVar(value='****')
        ttk.Entry(bottom_frame, textvariable=self.replacement_var,
                  width=10).pack(side=LEFT, padx=5)

        ttk.Button(bottom_frame, text='保存规则', style='success.TButton',
                   command=self._save_rules).pack(side=RIGHT, padx=(5, 0))
        ttk.Button(bottom_frame, text='测试规则', style='info.TButton',
                   command=self._test_rules).pack(side=RIGHT)

    def _load_rules(self):
        """从文件加载规则到 UI"""
        try:
            with open(self.rules_file, 'r', encoding='utf-8') as f:
                rules = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            rules = {'patterns': [], 'keywords': [], 'replacement': '****'}

        self.replacement_var.set(rules.get('replacement', '****'))

        # 加载正则模式
        for item in self.pattern_tree.get_children():
            self.pattern_tree.delete(item)
        for p in rules.get('patterns', []):
            self.pattern_tree.insert('', END, values=(
                p['id'], p['name'], p['regex'],
                '✓' if p.get('enabled', True) else '✗'
            ))

        # 加载关键字
        for item in self.keyword_tree.get_children():
            self.keyword_tree.delete(item)
        for k in rules.get('keywords', []):
            labels_str = ', '.join(k.get('labels', []))
            self.keyword_tree.insert('', END, values=(
                k['id'], k['name'], labels_str,
                '✓' if k.get('enabled', True) else '✗'
            ))

    def _save_rules(self):
        """保存规则到文件"""
        rules = {
            'patterns': [],
            'keywords': [],
            'replacement': self.replacement_var.get() or '****',
        }

        for item in self.pattern_tree.get_children():
            values = self.pattern_tree.item(item, 'values')
            rules['patterns'].append({
                'id': values[0],
                'name': values[1],
                'regex': values[2],
                'enabled': values[3] == '✓',
            })

        for item in self.keyword_tree.get_children():
            values = self.keyword_tree.item(item, 'values')
            labels = [l.strip() for l in values[2].split(',') if l.strip()]
            rules['keywords'].append({
                'id': values[0],
                'name': values[1],
                'labels': labels,
                'action': 'redact_value',
                'enabled': values[3] == '✓',
            })

        with open(self.rules_file, 'w', encoding='utf-8') as f:
            json.dump(rules, f, ensure_ascii=False, indent=2)

        self.redactor.reload_rules()
        messagebox.showinfo('成功', '规则已保存')

    def _add_pattern(self):
        self._pattern_dialog('添加正则模式')

    def _edit_pattern(self):
        selected = self.pattern_tree.selection()
        if not selected:
            messagebox.showwarning('提示', '请先选择一条规则')
            return
        values = self.pattern_tree.item(selected[0], 'values')
        self._pattern_dialog('编辑正则模式', selected[0], values)

    def _pattern_dialog(self, title, item=None, values=None):
        """正则模式编辑对话框"""
        dialog = tk.Toplevel(self)
        dialog.title(title)
        dialog.geometry('400x200')
        dialog.transient(self)
        dialog.grab_set()

        frame = ttk.Frame(dialog, padding=15)
        frame.pack(fill=BOTH, expand=True)

        ttk.Label(frame, text='ID:').grid(row=0, column=0, sticky=W, pady=3)
        id_var = tk.StringVar(value=values[0] if values else '')
        ttk.Entry(frame, textvariable=id_var).grid(row=0, column=1, sticky=EW, pady=3)

        ttk.Label(frame, text='名称:').grid(row=1, column=0, sticky=W, pady=3)
        name_var = tk.StringVar(value=values[1] if values else '')
        ttk.Entry(frame, textvariable=name_var).grid(row=1, column=1, sticky=EW, pady=3)

        ttk.Label(frame, text='正则:').grid(row=2, column=0, sticky=W, pady=3)
        regex_var = tk.StringVar(value=values[2] if values else '')
        ttk.Entry(frame, textvariable=regex_var).grid(row=2, column=1, sticky=EW, pady=3)

        frame.columnconfigure(1, weight=1)

        def save():
            if not id_var.get() or not name_var.get() or not regex_var.get():
                messagebox.showwarning('提示', '所有字段都不能为空')
                return
            new_values = (id_var.get(), name_var.get(), regex_var.get(), '✓')
            if item:
                self.pattern_tree.item(item, values=new_values)
            else:
                self.pattern_tree.insert('', END, values=new_values)
            dialog.destroy()

        ttk.Button(frame, text='确定', style='success.TButton',
                   command=save).grid(row=3, column=1, sticky=E, pady=(10, 0))

    def _delete_pattern(self):
        selected = self.pattern_tree.selection()
        if selected:
            self.pattern_tree.delete(selected[0])

    def _toggle_pattern(self):
        selected = self.pattern_tree.selection()
        if not selected:
            return
        values = list(self.pattern_tree.item(selected[0], 'values'))
        values[3] = '✗' if values[3] == '✓' else '✓'
        self.pattern_tree.item(selected[0], values=values)

    def _add_keyword(self):
        self._keyword_dialog('添加关键字规则')

    def _edit_keyword(self):
        selected = self.keyword_tree.selection()
        if not selected:
            messagebox.showwarning('提示', '请先选择一条规则')
            return
        values = self.keyword_tree.item(selected[0], 'values')
        self._keyword_dialog('编辑关键字规则', selected[0], values)

    def _keyword_dialog(self, title, item=None, values=None):
        """关键字规则编辑对话框"""
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

        ttk.Label(frame, text='名称:').grid(row=1, column=0, sticky=W, pady=3)
        name_var = tk.StringVar(value=values[1] if values else '')
        ttk.Entry(frame, textvariable=name_var).grid(row=1, column=1, sticky=EW, pady=3)

        ttk.Label(frame, text='标签:').grid(row=2, column=0, sticky=W, pady=3)
        labels_var = tk.StringVar(value=values[2] if values else '')
        ttk.Entry(frame, textvariable=labels_var).grid(row=2, column=1, sticky=EW, pady=3)
        ttk.Label(frame, text='多个标签用逗号分隔',
                  font=('', 8), foreground='gray').grid(row=3, column=1, sticky=W)

        frame.columnconfigure(1, weight=1)

        def save():
            if not id_var.get() or not name_var.get() or not labels_var.get():
                messagebox.showwarning('提示', '所有字段都不能为空')
                return
            new_values = (id_var.get(), name_var.get(), labels_var.get(), '✓')
            if item:
                self.keyword_tree.item(item, values=new_values)
            else:
                self.keyword_tree.insert('', END, values=new_values)
            dialog.destroy()

        ttk.Button(frame, text='确定', style='success.TButton',
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

    def _test_rules(self):
        """打开规则测试窗口"""
        dialog = tk.Toplevel(self)
        dialog.title('规则测试')
        dialog.geometry('500x400')
        dialog.transient(self)

        frame = ttk.Frame(dialog, padding=15)
        frame.pack(fill=BOTH, expand=True)

        ttk.Label(frame, text='输入测试文本:').pack(anchor=W)
        text_input = tk.Text(frame, height=6, wrap=tk.WORD)
        text_input.pack(fill=X, pady=(3, 8))
        text_input.insert('1.0',
            '付款人：张三\n付款账号：6222021234567890123\n手机号：13812345678')

        ttk.Label(frame, text='匹配结果:').pack(anchor=W)
        result_text = tk.Text(frame, height=10, wrap=tk.WORD, state=tk.DISABLED)
        result_text.pack(fill=BOTH, expand=True, pady=(3, 8))

        def run_test():
            # 先保存当前规则
            self._save_rules()
            test_str = text_input.get('1.0', tk.END).strip()
            if not test_str:
                return

            matches = self.redactor.scanner.scan_text(test_str)
            redacted = self.redactor.scanner.redact_text(test_str, matches)

            result_text.configure(state=tk.NORMAL)
            result_text.delete('1.0', tk.END)
            result_text.insert(tk.END, f'找到 {len(matches)} 处匹配:\n\n')
            for m in matches:
                result_text.insert(tk.END,
                    f'  [{m.rule_name}] "{m.matched_text}" '
                    f'(位置 {m.start}-{m.end}, 类型: {m.match_type})\n')
            result_text.insert(tk.END, f'\n--- 脱敏后文本 ---\n{redacted}')
            result_text.configure(state=tk.DISABLED)

        ttk.Button(frame, text='执行测试', style='success.TButton',
                   command=run_test).pack(anchor=E)
