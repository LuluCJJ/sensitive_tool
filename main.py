"""银行水单脱敏工具 - 入口"""
import sys
import os

# 确保项目根目录在 Python 路径中
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 为了防止 PyInstaller 打包时漏掉动态引用的巨型依赖，这里显式全量导入
import numpy
import PIL
import fitz
import cv2
import shapely
import pyclipper
import paddle
import paddleocr
import requests
import yaml
import Cython
import shapely
import pyclipper
import imageio
import imgaug

from gui.app import MainApp


def main():
    app = MainApp()
    app.run()


if __name__ == '__main__':
    main()
