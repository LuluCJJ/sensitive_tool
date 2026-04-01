"""主窗口"""
import ttkbootstrap as ttk
from ttkbootstrap.constants import *

from core.redactor import Redactor
from gui.file_tab import FileTab
from gui.rules_tab import RulesTab
from gui.log_tab import LogTab


class MainApp:
    """主应用窗口"""

    def __init__(self):
        # 创建主窗口
        self.root = ttk.Window(
            title='银行水单脱敏工具',
            themename='cosmo',
            size=(800, 600),
            resizable=(True, True),
        )
        self.root.place_window_center()

        # 创建脱敏调度器
        self.redactor = Redactor()

        self._build_ui()

    def _build_ui(self):
        # 标题栏
        header = ttk.Frame(self.root, padding=(15, 10))
        header.pack(fill=X)

        ttk.Label(header, text='🏦 银行水单脱敏工具',
                  font=('', 16, 'bold')).pack(side=LEFT)
        ttk.Label(header, text='v1.0',
                  font=('', 10), foreground='gray').pack(side=LEFT, padx=10)

        ttk.Separator(self.root).pack(fill=X)

        # 标签页
        notebook = ttk.Notebook(self.root, padding=5)
        notebook.pack(fill=BOTH, expand=True, padx=10, pady=10)

        # 文件处理标签页
        self.file_tab = FileTab(notebook, self.redactor)
        notebook.add(self.file_tab, text='  📁 文件处理  ')

        # 规则配置标签页
        self.rules_tab = RulesTab(notebook, self.redactor)
        notebook.add(self.rules_tab, text='  ⚙️ 规则配置  ')

        # 脱敏日志标签页
        self.log_tab = LogTab(notebook, self.redactor)
        notebook.add(self.log_tab, text='  📋 脱敏日志  ')

        # 切换到日志标签页时自动刷新
        notebook.bind('<<NotebookTabChanged>>', self._on_tab_changed)
        self._notebook = notebook

    def _on_tab_changed(self, event):
        """标签页切换回调"""
        current = self._notebook.index(self._notebook.select())
        if current == 2:  # 日志标签页
            self.log_tab.on_tab_selected()

    def run(self):
        self.root.mainloop()
