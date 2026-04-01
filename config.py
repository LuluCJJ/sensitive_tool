"""应用配置常量"""
import os
import sys

# 获取应用运行时的临时资源目录（PyInstaller _MEIPASS）
if getattr(sys, 'frozen', False):
    APP_DIR = os.path.dirname(sys.executable)
    BUNDLE_DIR = sys._MEIPASS
else:
    APP_DIR = os.path.dirname(os.path.abspath(__file__))
    BUNDLE_DIR = APP_DIR

# 文件路径
RULES_FILE = os.path.join(APP_DIR, 'rules.json')

# 如果打包后的目录下没有 rules.json，把它从 bundle 里复制出来以提供默认配置
if getattr(sys, 'frozen', False) and not os.path.exists(RULES_FILE):
    import shutil
    default_rules = os.path.join(BUNDLE_DIR, 'rules.json')
    if os.path.exists(default_rules):
        shutil.copy2(default_rules, RULES_FILE)
OUTPUT_DIR = os.path.join(APP_DIR, 'output')
LOG_DIR = os.path.join(APP_DIR, 'logs')

# 支持的文件类型
SUPPORTED_EXTENSIONS = {
    '.docx': 'word',
    '.xlsx': 'excel',
    '.pdf': 'pdf',
    '.png': 'image',
    '.jpg': 'image',
    '.jpeg': 'image',
    '.bmp': 'image',
    '.tiff': 'image',
    '.tif': 'image',
}

# 默认替换字符
DEFAULT_REPLACEMENT = '****'

# PDF 渲染 DPI（越高越清晰，但处理越慢）
PDF_RENDER_DPI = 200

# OCR 配置
OCR_LANG = 'ch'  # PaddleOCR 中文
OCR_USE_GPU = False

# 确保输出目录存在
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)
