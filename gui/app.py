"""主窗口"""
import ttkbootstrap as ttk
from ttkbootstrap.constants import *

from core.redactor import Redactor
from core.i18n import t, set_language, get_language
from gui.file_tab import FileTab
from gui.rules_tab import RulesTab
from gui.log_tab import LogTab
from gui.banks_tab import BanksTab


class MainApp:
    """主应用窗口"""

    def __init__(self):
        # 创建主窗口
        self.root = ttk.Window(
            title=t('app_title'),
            themename='cosmo',
            size=(900, 680),
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

        self._title_label = ttk.Label(
            header, text=f'🏦 {t("app_title")}', font=('', 16, 'bold'))
        self._title_label.pack(side=LEFT)
        ttk.Label(header, text=t('app_version'),
                  font=('', 10), foreground='gray').pack(side=LEFT, padx=10)

        # 语言切换按钮（右上角）
        self._lang_btn = ttk.Button(
            header, text=t('lang_btn'),
            style='info-outline.TButton',
            width=8,
            command=self._toggle_language,
        )
        self._lang_btn.pack(side=RIGHT)

        ttk.Separator(self.root).pack(fill=X)

        # 标签页
        self._notebook = ttk.Notebook(self.root, padding=5)
        self._notebook.pack(fill=BOTH, expand=True, padx=10, pady=10)

        # 文件处理标签页
        self.file_tab = FileTab(self._notebook, self.redactor)
        self._notebook.add(self.file_tab, text=t('tab_file'))

        # 规则配置标签页
        self.rules_tab = RulesTab(self._notebook, self.redactor)
        self._notebook.add(self.rules_tab, text=t('tab_rules'))

        # 脱敏日志标签页
        self.log_tab = LogTab(self._notebook, self.redactor)
        self._notebook.add(self.log_tab, text=t('tab_log'))

        # 银行配置标签页
        self.banks_tab = BanksTab(
            self._notebook, self.redactor,
            on_banks_changed=self._on_banks_changed,
        )
        self._notebook.add(self.banks_tab, text=t('tab_banks'))

        # 切换到日志标签页时自动刷新
        self._notebook.bind('<<NotebookTabChanged>>', self._on_tab_changed)

    def _on_tab_changed(self, event):
        """标签页切换回调"""
        current = self._notebook.index(self._notebook.select())
        if current == 2:  # 日志标签页
            self.log_tab.on_tab_selected()

    def _on_banks_changed(self):
        """银行列表变化时刷新文件/规则 Tab 的下拉框"""
        if hasattr(self.file_tab, '_refresh_banks'):
            self.file_tab._refresh_banks()
        if hasattr(self.rules_tab, '_refresh_bank_selector'):
            self.rules_tab._refresh_bank_selector()

    def _toggle_language(self):
        """切换中英文"""
        new_lang = 'en' if get_language() == 'zh' else 'zh'
        set_language(new_lang)
        self._refresh_lang()

    def _refresh_lang(self):
        """刷新所有界面文字"""
        self.root.title(t('app_title'))
        self._title_label.config(text=f'🏦 {t("app_title")}')
        self._lang_btn.config(text=t('lang_btn'))

        # 刷新 Tab 标题
        self._notebook.tab(0, text=t('tab_file'))
        self._notebook.tab(1, text=t('tab_rules'))
        self._notebook.tab(2, text=t('tab_log'))
        self._notebook.tab(3, text=t('tab_banks'))

        # 刷新各 Tab 内容
        for tab in [self.file_tab, self.rules_tab, self.log_tab, self.banks_tab]:
            if hasattr(tab, 'refresh_lang'):
                tab.refresh_lang()

    def run(self):
        self.root.mainloop()
