"""银行配置标签页

功能：
- 管理银行列表（增删改、启用/停用）
- 每个银行有独立的额外关键字和正则规则（在规则配置页中编辑）
- 本 Tab 只负责银行元信息的管理
"""
import json
import tkinter as tk
from tkinter import messagebox
import ttkbootstrap as ttk
from ttkbootstrap.constants import *

from config import RULES_FILE
from core.i18n import t


class BanksTab(ttk.Frame):
    """银行配置标签页"""

    def __init__(self, parent, redactor, on_banks_changed=None):
        """
        Args:
            on_banks_changed: 银行列表发生变化时的回调（用于刷新其他 Tab 的下拉框）
        """
        super().__init__(parent, padding=15)
        self.redactor = redactor
        self.rules_file = RULES_FILE
        self.on_banks_changed = on_banks_changed
        self._build_ui()
        self._load_banks()

    def _build_ui(self):
        # 说明文字
        tip = ttk.Label(
            self,
            text='在此管理银行列表。在「规则配置」页选择具体银行后，\n'
                 '可为该银行配置额外的私有关键字/正则规则（在全局规则之上叠加）。',
            foreground='gray', font=('', 9),
        )
        tip.pack(anchor=W, pady=(0, 10))

        # 银行列表
        list_frame = ttk.LabelFrame(self, text='已配置银行')
        list_frame.pack(fill=BOTH, expand=True, pady=(0, 10))

        cols = ('id', 'name', 'enabled', 'extra_rules')
        self.tree = ttk.Treeview(list_frame, columns=cols,
                                 show='headings', height=12)
        self.tree.heading('id', text='银行 ID')
        self.tree.heading('name', text='银行名称')
        self.tree.heading('enabled', text='启用')
        self.tree.heading('extra_rules', text='私有规则数')
        self.tree.column('id', width=130)
        self.tree.column('name', width=200)
        self.tree.column('enabled', width=60, anchor=CENTER)
        self.tree.column('extra_rules', width=100, anchor=CENTER)
        self.tree.pack(fill=BOTH, expand=True, pady=(0, 5))

        # 操作按钮
        btn_frame = ttk.Frame(list_frame)
        btn_frame.pack(fill=X)
        ttk.Button(btn_frame, text='添加银行', style='success-outline.TButton',
                   command=self._add_bank).pack(side=LEFT, padx=(0, 3))
        ttk.Button(btn_frame, text='编辑', style='info-outline.TButton',
                   command=self._edit_bank).pack(side=LEFT, padx=(0, 3))
        ttk.Button(btn_frame, text='删除', style='danger-outline.TButton',
                   command=self._delete_bank).pack(side=LEFT, padx=(0, 3))
        ttk.Button(btn_frame, text='切换启用', style='warning-outline.TButton',
                   command=self._toggle_bank).pack(side=LEFT, padx=(0, 3))
        ttk.Button(btn_frame, text='保存', style='success.TButton',
                   command=self._save_banks).pack(side=RIGHT)

    def _load_banks(self):
        """从 rules.json 加载银行列表"""
        try:
            with open(self.rules_file, 'r', encoding='utf-8') as f:
                rules = json.load(f)
        except Exception:
            rules = {}

        for item in self.tree.get_children():
            self.tree.delete(item)

        for b in rules.get('banks', []):
            extra_count = (len(b.get('extra_keywords', [])) +
                           len(b.get('extra_patterns', [])))
            self.tree.insert('', END, values=(
                b['id'],
                b['name'],
                '✓' if b.get('enabled', True) else '✗',
                extra_count,
            ))

    def _save_banks(self):
        """将当前列表保存回 rules.json"""
        try:
            with open(self.rules_file, 'r', encoding='utf-8') as f:
                rules = json.load(f)
        except Exception:
            rules = {}

        # 保留原有银行的 extra_patterns / extra_keywords
        old_banks = {b['id']: b for b in rules.get('banks', [])}
        new_banks = []
        for item in self.tree.get_children():
            values = self.tree.item(item, 'values')
            bid = values[0]
            old = old_banks.get(bid, {})
            
            # 如果是全新银行（没有历史配置记录），则自动注入默认的关键字标签加速启动
            extra_keywords = old.get('extra_keywords')
            if extra_keywords is None:
                extra_keywords = [
                    {
                        "id": "tpl_account_num",
                        "name": "账号(模板)",
                        "labels": ["Account Number", "Account No", "Account", "Account:"],
                        "action": "redact_value",
                        "enabled": True
                    },
                    {
                        "id": "tpl_iban",
                        "name": "IBAN(模板)",
                        "labels": ["IBAN", "IBAN:"],
                        "action": "redact_value",
                        "enabled": True
                    }
                ]

            new_banks.append({
                'id': bid,
                'name': values[1],
                'enabled': values[2] == '✓',
                'extra_keywords': extra_keywords,
                'disabled_global_rules': old.get('disabled_global_rules', []),
            })

        rules['banks'] = new_banks
        with open(self.rules_file, 'w', encoding='utf-8') as f:
            json.dump(rules, f, ensure_ascii=False, indent=2)

        messagebox.showinfo('成功', '银行配置已保存')
        if self.on_banks_changed:
            self.on_banks_changed()

    def _add_bank(self):
        self._bank_dialog('添加银行')

    def _edit_bank(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning('提示', '请先选择一个银行')
            return
        values = self.tree.item(selected[0], 'values')
        self._bank_dialog('编辑银行', selected[0], values)

    def _bank_dialog(self, title, item=None, values=None):
        """银行信息编辑对话框"""
        dialog = tk.Toplevel(self)
        dialog.title(title)
        dialog.geometry('380x150')
        dialog.transient(self)
        dialog.grab_set()

        frame = ttk.Frame(dialog, padding=15)
        frame.pack(fill=BOTH, expand=True)

        ttk.Label(frame, text='银行 ID:').grid(row=0, column=0, sticky=W, pady=5)
        id_var = tk.StringVar(value=values[0] if values else '')
        id_entry = ttk.Entry(frame, textvariable=id_var)
        id_entry.grid(row=0, column=1, sticky=EW, pady=5)
        # 编辑时禁止修改 ID（防止破坏关联）
        if item:
            id_entry.configure(state='readonly')

        ttk.Label(frame, text='银行名称:').grid(row=1, column=0, sticky=W, pady=5)
        name_var = tk.StringVar(value=values[1] if values else '')
        ttk.Entry(frame, textvariable=name_var).grid(
            row=1, column=1, sticky=EW, pady=5)

        frame.columnconfigure(1, weight=1)

        def save():
            if not id_var.get().strip() or not name_var.get().strip():
                messagebox.showwarning('提示', '银行 ID 和名称不能为空')
                return
            # 检查 ID 唯一性（新增时）
            if not item:
                existing_ids = [
                    self.tree.item(i, 'values')[0]
                    for i in self.tree.get_children()
                ]
                if id_var.get().strip() in existing_ids:
                    messagebox.showwarning('提示', f'银行 ID "{id_var.get()}" 已存在')
                    return
            new_values = (
                id_var.get().strip(), name_var.get().strip(), '✓', '0')
            if item:
                # 保留原有的私有规则数
                old_v = self.tree.item(item, 'values')
                new_values = (
                    old_v[0], name_var.get().strip(), old_v[2], old_v[3])
                self.tree.item(item, values=new_values)
            else:
                self.tree.insert('', END, values=new_values)
            dialog.destroy()

        ttk.Button(frame, text='确定', style='success.TButton',
                   command=save).grid(row=2, column=1, sticky=E, pady=(10, 0))

    def _delete_bank(self):
        selected = self.tree.selection()
        if not selected:
            return
        name = self.tree.item(selected[0], 'values')[1]
        if messagebox.askyesno('确认删除', f'确定删除银行「{name}」及其所有私有规则吗？'):
            self.tree.delete(selected[0])

    def _toggle_bank(self):
        selected = self.tree.selection()
        if not selected:
            return
        values = list(self.tree.item(selected[0], 'values'))
        values[2] = '✗' if values[2] == '✓' else '✓'
        self.tree.item(selected[0], values=values)

    def refresh_lang(self):
        """切换语言后刷新（银行 Tab 文字较少，此处仅做占位）"""
        pass
