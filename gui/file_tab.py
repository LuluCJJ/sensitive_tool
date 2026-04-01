"""文件处理标签页"""
import os
import threading
import tkinter as tk
from tkinter import filedialog, messagebox
import ttkbootstrap as ttk
from ttkbootstrap.constants import *

from config import SUPPORTED_EXTENSIONS, OUTPUT_DIR


class FileTab(ttk.Frame):
    """文件处理标签页"""

    def __init__(self, parent, redactor):
        super().__init__(parent, padding=15)
        self.redactor = redactor
        self.file_paths = []
        self._processing = False
        self._build_ui()

    def _build_ui(self):
        # ---- 顶部：文件选择区 ----
        select_frame = ttk.LabelFrame(self, text='文件选择')
        select_frame.pack(fill=X, pady=(0, 10))

        btn_frame = ttk.Frame(select_frame)
        btn_frame.pack(fill=X)

        ttk.Button(btn_frame, text='选择文件', style='primary.TButton',
                   command=self._select_files).pack(side=LEFT, padx=(0, 5))
        ttk.Button(btn_frame, text='清空列表', style='secondary.TButton',
                   command=self._clear_files).pack(side=LEFT, padx=(0, 5))

        ext_str = ', '.join(SUPPORTED_EXTENSIONS.keys())
        ttk.Label(select_frame, text=f'支持格式: {ext_str}',
                  font=('', 9), foreground='gray').pack(anchor=W, pady=(5, 0))

        # ---- 中部：文件列表 ----
        list_frame = ttk.LabelFrame(self, text='文件列表')
        list_frame.pack(fill=BOTH, expand=True, pady=(0, 10))

        # 树形列表
        columns = ('filename', 'type', 'status')
        self.tree = ttk.Treeview(list_frame, columns=columns, show='headings',
                                 height=10, style='info.Treeview')
        self.tree.heading('filename', text='文件名')
        self.tree.heading('type', text='类型')
        self.tree.heading('status', text='状态')
        self.tree.column('filename', width=350)
        self.tree.column('type', width=80, anchor=CENTER)
        self.tree.column('status', width=120, anchor=CENTER)

        scrollbar = ttk.Scrollbar(list_frame, orient=VERTICAL,
                                  command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side=LEFT, fill=BOTH, expand=True)
        scrollbar.pack(side=RIGHT, fill=Y)

        # ---- 底部：操作区 ----
        action_frame = ttk.Frame(self)
        action_frame.pack(fill=X)

        self.progress_var = tk.DoubleVar(value=0)
        self.progress_bar = ttk.Progressbar(action_frame, variable=self.progress_var,
                                            maximum=100, style='success.Striped.Horizontal.TProgressbar')
        self.progress_bar.pack(fill=X, pady=(0, 8))

        self.status_label = ttk.Label(action_frame, text='就绪',
                                      font=('', 9), foreground='gray')
        self.status_label.pack(side=LEFT)

        btn_right = ttk.Frame(action_frame)
        btn_right.pack(side=RIGHT)

        ttk.Button(btn_right, text='打开输出目录', style='info.TButton',
                   command=self._open_output_dir).pack(side=LEFT, padx=(0, 5))
        self.start_btn = ttk.Button(btn_right, text='开始脱敏',
                                    style='success.TButton',
                                    command=self._start_processing)
        self.start_btn.pack(side=LEFT)

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
        self.status_label.configure(text='就绪')

    def _start_processing(self):
        if self._processing:
            return
        if not self.file_paths:
            messagebox.showwarning('提示', '请先选择文件')
            return

        self._processing = True
        self.start_btn.configure(state=DISABLED)
        self.redactor.reload_rules()

        # 在后台线程处理
        thread = threading.Thread(target=self._process_thread, daemon=True)
        thread.start()

    def _process_thread(self):
        """后台处理线程"""
        total = len(self.file_paths)
        items = list(self.tree.get_children())

        for i, (file_path, item) in enumerate(zip(self.file_paths, items)):
            # 更新状态
            self.after(0, lambda it=item: self.tree.set(it, 'status', '处理中...'))
            self.after(0, lambda v=(i / total * 100): self.progress_var.set(v))
            self.after(0, lambda t=f'正在处理 {i+1}/{total}...':
                       self.status_label.configure(text=t))

            log = self.redactor.process_file(file_path)

            # 更新结果
            if log.status == 'success':
                status_text = f'完成 (脱敏{log.redaction_count}处)'
            else:
                status_text = f'失败: {log.error_message[:20]}'

            self.after(0, lambda it=item, s=status_text:
                       self.tree.set(it, 'status', s))

        # 保存日志
        log_path = self.redactor.save_logs()

        # 完成
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
