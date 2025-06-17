"""
DICOM2NII Pro - GUI包

现代化的医学影像转换软件图形用户界面
基于tkinter构建，提供专业的用户体验
"""

__version__ = "1.0.0"
__author__ = "DICOM2NII Pro Team"

from .main_window import MainWindow
from .components import *

__all__ = [
    'MainWindow'
]
