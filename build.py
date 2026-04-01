import os
import sys
import PyInstaller.__main__

def build():
    app_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 规则文件配置
    rules_data = f'rules.json;.'

    args = [
        'main.py',
        '--name=银行水单脱敏工具',
        '--windowed',
        '--onefile',
        '--clean',
        f'--add-data={rules_data}',
        '--add-data=models;models',
        # 隐藏 paddleocr 相关的警告和弹窗
        '--noconsole',
        # PaddleOCR 依赖项
        '--hidden-import=paddleocr',
        '--hidden-import=paddle',
        '--hidden-import=requests',
        '--hidden-import=yaml',
        '--hidden-import=et_xmlfile',
        '--collect-all=paddleocr',
        '--collect-all=paddle',
        '--collect-all=Cython',
        '--collect-all=pyclipper',
        '--collect-all=shapely',
        '--collect-all=imageio',
        '--collect-all=imgaug',
        '--collect-all=imaug',
        '--collect-all=lmdb',
        '--collect-all=skimage',
        '--collect-all=imgaug',
        '--collect-all=scipy',
        '--hidden-import=numpy',
        '--collect-all=numpy',
        '--hidden-import=fitz',
        '--collect-all=fitz',
        '--hidden-import=PIL',
        '--collect-all=PIL',
        # 清理
        '--log-level=WARN',
    ]

    print("开始打包...")
    PyInstaller.__main__.run(args)
    print("打包完成！输出位于 dist 目录。")

if __name__ == '__main__':
    build()
