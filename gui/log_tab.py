"""脱敏日志标签页"""
import json
import os
import tkinter as tk
from tkinter import filedialog
import ttkbootstrap as ttk
from ttkbootstrap.constants import *

from config import LOG_DIR
from core.i18n import t


class LogTab(ttk.Frame):
    """脱敏日志标签页"""

    def __init__(self, parent, redactor):
        super().__init__(parent, padding=15)
        self.redactor = redactor
        self._build_ui()

    def _build_ui(self):
        # 顶部：操作栏
        top_frame = ttk.Frame(self)
        top_frame.pack(fill=X, pady=(0, 10))

        self._refresh_btn = ttk.Button(top_frame, text=t('log_refresh_btn'),
                                        style='info.TButton',
                                        command=self._refresh)
        self._refresh_btn.pack(side=LEFT, padx=(0, 5))
        self._export_btn = ttk.Button(top_frame, text=t('log_save_btn'),
                                      style='secondary.TButton',
                                      command=self._export_log)
        self._export_btn.pack(side=LEFT)

        # 中部：日志列表
        self._list_frame = ttk.LabelFrame(self, text='历史脱敏记录')
        self._list_frame.pack(fill=BOTH, expand=True, pady=(0, 10))

        cols = ('time', 'files', 'redactions')
        self.log_tree = ttk.Treeview(self._list_frame, columns=cols,
                                      show='headings', height=6)
        self.log_tree.heading('time', text=t('log_col_time'))
        self.log_tree.heading('files', text=t('file_col_name'))
        self.log_tree.heading('redactions', text=t('log_col_count'))
        self.log_tree.column('time', width=180)
        self.log_tree.column('files', width=80, anchor=CENTER)
        self.log_tree.column('redactions', width=80, anchor=CENTER)
        self.log_tree.pack(fill=BOTH, expand=True, pady=(0, 5))
        self.log_tree.bind('<<TreeviewSelect>>', self._on_log_select)

        # 下部：日志详情
        detail_frame = ttk.LabelFrame(self, text='详细信息')
        detail_frame.pack(fill=BOTH, expand=True)

        self.detail_text = tk.Text(detail_frame, height=10, wrap=tk.WORD,
                                   state=tk.DISABLED, font=('Consolas', 9))
        scrollbar = ttk.Scrollbar(detail_frame, orient=VERTICAL,
                                  command=self.detail_text.yview)
        self.detail_text.configure(yscrollcommand=scrollbar.set)
        self.detail_text.pack(side=LEFT, fill=BOTH, expand=True)
        scrollbar.pack(side=RIGHT, fill=Y)

        self._log_data = []

    def _refresh(self):
        """刷新日志列表"""
        for item in self.log_tree.get_children():
            self.log_tree.delete(item)

        self._log_data = self.redactor.logger.load_history()
        for log in self._log_data:
            self.log_tree.insert('', END, values=(
                log.get('session_time', ''),
                log.get('total_files', 0),
                log.get('total_redactions', 0),
            ))

    def _on_log_select(self, event):
        """选中日志时显示详情"""
        selected = self.log_tree.selection()
        if not selected:
            return

        idx = self.log_tree.index(selected[0])
        if idx < len(self._log_data):
            log = self._log_data[idx]
            self._show_detail(log)

    def _show_detail(self, log_data: dict):
        """显示日志详情"""
        self.detail_text.configure(state=tk.NORMAL)
        self.detail_text.delete('1.0', tk.END)

        self.detail_text.insert(tk.END,
            f"时间: {log_data.get('session_time', '')}\n"
            f"文件数: {log_data.get('total_files', 0)}\n"
            f"脱敏总数: {log_data.get('total_redactions', 0)}\n"
            f"{'='*50}\n\n")

        for file_log in log_data.get('files', []):
            status_icon = '✓' if file_log['status'] == 'success' else '✗'
            self.detail_text.insert(tk.END,
                f"{status_icon} {file_log['filename']} "
                f"({file_log['file_type']}) "
                f"- 脱敏{file_log['redaction_count']}处\n")

            if file_log['status'] == 'error':
                self.detail_text.insert(tk.END,
                    f"  错误: {file_log['error_message']}\n")

            for entry in file_log.get('entries', []):
                rule_name = entry.get('rule_name', '')
                orig_txt = entry.get('original_text', '')
                loc = entry.get('location', '')
                trigger = entry.get('trigger', '')
                
                self.detail_text.insert(tk.END,
                    f"  · [{rule_name}] "
                    f"\"{orig_txt}\" "
                    f"@ {loc}")
                if trigger:
                    self.detail_text.insert(tk.END, f"  <= ({trigger})")
                self.detail_text.insert(tk.END, '\n')
            self.detail_text.insert(tk.END, '\n')

        self.detail_text.configure(state=tk.DISABLED)

    def _export_log(self):
        """导出选中的日志"""
        selected = self.log_tree.selection()
        if not selected:
            return

        idx = self.log_tree.index(selected[0])
        if idx >= len(self._log_data):
            return

        log = self._log_data[idx]
        filepath = filedialog.asksaveasfilename(
            title='导出日志',
            defaultextension='.json',
            filetypes=[('JSON文件', '*.json'), ('文本文件', '*.txt')],
            initialfile=f"redaction_log_{log.get('session_time', 'export')}.json"
        )

        if filepath:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(log, f, ensure_ascii=False, indent=2)

    def on_tab_selected(self):
        """标签页被选中时自动刷新"""
        self._refresh()

    def refresh_lang(self):
        """切换语言后刷新 UI 文字"""
        self._refresh_btn.config(text=t('log_refresh_btn'))
        self._export_btn.config(text=t('log_save_btn'))
        self.log_tree.heading('time', text=t('log_col_time'))
        self.log_tree.heading('files', text=t('file_col_name'))
        self.log_tree.heading('redactions', text=t('log_col_count'))
