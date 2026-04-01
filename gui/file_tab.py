"""文件处理标签页"""
import os
import threading
import tkinter as tk
from tkinter import filedialog, messagebox
import ttkbootstrap as ttk
from ttkbootstrap.constants import *

from config import SUPPORTED_EXTENSIONS, OUTPUT_DIR, RULES_FILE
from core.i18n import t
import json


class FileTab(ttk.Frame):
    """文件处理标签页"""

    def __init__(self, parent, redactor):
        super().__init__(parent, padding=15)
        self.redactor = redactor
        self.file_paths = []
        self._processing = False
        self._build_ui()

    def _build_ui(self):
        # ---- 顶部工具栏：银行选择 ----
        toolbar = ttk.Frame(self)
        toolbar.pack(fill=X, pady=(0, 8))

        self._bank_label = ttk.Label(toolbar, text=t('file_bank_label'))
        self._bank_label.pack(side=LEFT, padx=(0, 5))

        self._bank_var = tk.StringVar()
        self._bank_combo = ttk.Combobox(
            toolbar, textvariable=self._bank_var,
            state='readonly', width=24,
        )
        self._bank_combo.pack(side=LEFT)
        self._refresh_banks()

        # ---- 顶部：文件选择区 ----
        self._select_frame = ttk.LabelFrame(self, text=t('file_add_btn'))
        self._select_frame.pack(fill=X, pady=(0, 10))

        btn_frame = ttk.Frame(self._select_frame)
        btn_frame.pack(fill=X)

        self._add_btn = ttk.Button(btn_frame, text=t('file_add_btn'),
                                   style='primary.TButton',
                                   command=self._select_files)
        self._add_btn.pack(side=LEFT, padx=(0, 5))
        self._clear_btn = ttk.Button(btn_frame, text=t('file_clear_btn'),
                                     style='secondary.TButton',
                                     command=self._clear_files)
        self._clear_btn.pack(side=LEFT, padx=(0, 5))

        ext_str = ', '.join(SUPPORTED_EXTENSIONS.keys())
        ttk.Label(self._select_frame, text=f'支持格式: {ext_str}',
                  font=('', 9), foreground='gray').pack(anchor=W, pady=(5, 0))

        # ---- 中部：文件列表 ----
        self._list_frame = ttk.LabelFrame(self, text=t('file_col_name'))
        self._list_frame.pack(fill=BOTH, expand=True, pady=(0, 10))

        columns = ('filename', 'type', 'status')
        self.tree = ttk.Treeview(self._list_frame, columns=columns,
                                 show='headings', height=10,
                                 style='info.Treeview')
        self._col_name = ttk.Label()  # placeholder for heading refs
        self.tree.heading('filename', text=t('file_col_name'))
        self.tree.heading('type', text=t('file_col_type'))
        self.tree.heading('status', text=t('file_col_status'))
        self.tree.column('filename', width=350)
        self.tree.column('type', width=80, anchor=CENTER)
        self.tree.column('status', width=120, anchor=CENTER)

        scrollbar = ttk.Scrollbar(self._list_frame, orient=VERTICAL,
                                  command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side=LEFT, fill=BOTH, expand=True)
        scrollbar.pack(side=RIGHT, fill=Y)

        # ---- 底部：操作区 ----
        action_frame = ttk.Frame(self)
        action_frame.pack(fill=X)

        self.progress_var = tk.DoubleVar(value=0)
        self.progress_bar = ttk.Progressbar(
            action_frame, variable=self.progress_var,
            maximum=100, style='success.Striped.Horizontal.TProgressbar')
        self.progress_bar.pack(fill=X, pady=(0, 8))

        self.status_label = ttk.Label(action_frame, text=t('file_status_ready'),
                                      font=('', 9), foreground='gray')
        self.status_label.pack(side=LEFT)

        btn_right = ttk.Frame(action_frame)
        btn_right.pack(side=RIGHT)

        self._open_output_btn = ttk.Button(
            btn_right, text=t('file_open_output'),
            style='info.TButton', command=self._open_output_dir)
        self._open_output_btn.pack(side=LEFT, padx=(0, 5))
        self.start_btn = ttk.Button(
            btn_right, text=t('file_process_btn'),
            style='success.TButton', command=self._start_processing)
        self.start_btn.pack(side=LEFT)

    def _refresh_banks(self):
        """从 rules.json 读取银行列表，刷新下拉框"""
        banks = [t('file_bank_all')]
        try:
            with open(RULES_FILE, 'r', encoding='utf-8') as f:
                rules = json.load(f)
            for b in rules.get('banks', []):
                if b.get('enabled', True):
                    banks.append(f"{b['name']}  [{b['id']}]")
        except Exception:
            pass
        current = self._bank_var.get()
        self._bank_combo['values'] = banks
        # 保持已选项，否则回到第一项
        if current in banks:
            self._bank_var.set(current)
        else:
            self._bank_var.set(banks[0])

    def _get_selected_bank_id(self) -> str | None:
        """解析当前选中的银行 ID，通用返回 None"""
        val = self._bank_var.get()
        if not val or '[' not in val:
            return None
        # 格式: "银行名称  [bank_id]"
        return val.split('[')[-1].rstrip(']').strip()

    def refresh_lang(self):
        """切换语言后刷新 UI 文字"""
        self._bank_label.config(text=t('file_bank_label'))
        self._add_btn.config(text=t('file_add_btn'))
        self._clear_btn.config(text=t('file_clear_btn'))
        self.tree.heading('filename', text=t('file_col_name'))
        self.tree.heading('type', text=t('file_col_type'))
        self.tree.heading('status', text=t('file_col_status'))
        self.status_label.config(text=t('file_status_ready'))
        self._open_output_btn.config(text=t('file_open_output'))
        self.start_btn.config(text=t('file_process_btn'))
        self._refresh_banks()

    def _select_files(self):
        filetypes = [
            ('所有支持格式', '*.docx *.xlsx *.pdf *.png *.jpg *.jpeg *.bmp *.tiff *.tif'),
            ('Word文档', '*.docx'),
            ('Excel表格', '*.xlsx'),
            ('PDF文件', '*.pdf'),
            ('图片文件', '*.png *.jpg *.jpeg *.bmp *.tiff *.tif'),
        ]
        files = filedialog.askopenfilenames(
            title='选择银行水单文件',
            filetypes=filetypes
        )
        if files:
            for f in files:
                if f not in self.file_paths:
                    self.file_paths.append(f)
                    ext = os.path.splitext(f)[1].lower()
                    file_type = SUPPORTED_EXTENSIONS.get(ext, '未知')
                    self.tree.insert('', END, values=(
                        os.path.basename(f), file_type, '待处理'))

    def _clear_files(self):
        self.file_paths.clear()
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.progress_var.set(0)
        self.status_label.configure(text=t('file_status_ready'))

    def _start_processing(self):
        if self._processing:
            return
        if not self.file_paths:
            messagebox.showwarning('提示', '请先选择文件')
            return

        self._processing = True
        self.start_btn.configure(state=DISABLED)

        # 按选中银行重载规则
        bank_id = self._get_selected_bank_id()
        self.redactor.reload_rules(bank_id=bank_id)

        # 在后台线程处理
        thread = threading.Thread(target=self._process_thread, daemon=True)
        thread.start()

    def _process_thread(self):
        """后台处理线程"""
        total = len(self.file_paths)
        items = list(self.tree.get_children())

        for i, (file_path, item) in enumerate(zip(self.file_paths, items)):
            self.after(0, lambda it=item: self.tree.set(it, 'status', '处理中...'))
            self.after(0, lambda v=(i / total * 100): self.progress_var.set(v))
            self.after(0, lambda txt=f'正在处理 {i+1}/{total}...':
                       self.status_label.configure(text=txt))

            log = self.redactor.process_file(file_path)

            if log.status == 'success':
                status_text = f'完成 (脱敏{log.redaction_count}处)'
            else:
                status_text = f'失败: {log.error_message[:20]}'

            self.after(0, lambda it=item, s=status_text:
                       self.tree.set(it, 'status', s))

        self.redactor.save_logs()

        self.after(0, lambda: self.progress_var.set(100))
        self.after(0, lambda: self.status_label.configure(
            text=f'处理完成！共 {total} 个文件'))
        self.after(0, lambda: self.start_btn.configure(state=NORMAL))
        self._processing = False

        self.after(0, lambda: messagebox.showinfo(
            '完成', f'脱敏处理完成！\n共处理 {total} 个文件\n'
                   f'输出目录: {OUTPUT_DIR}'))

    def _open_output_dir(self):
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        os.startfile(OUTPUT_DIR)
