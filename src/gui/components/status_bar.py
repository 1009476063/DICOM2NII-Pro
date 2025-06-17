"""
DICOM2NII Pro - 状态栏组件

显示应用程序状态信息
"""

import tkinter as tk
from tkinter import ttk


class StatusBar:
    """状态栏组件"""
    
    def __init__(self, parent):
        """初始化状态栏"""
        self.frame = ttk.Frame(parent, relief=tk.SUNKEN, borderwidth=1)
        
        # 创建状态标签
        self.status_label = ttk.Label(
            self.frame, 
            text="就绪", 
            relief=tk.SUNKEN, 
            anchor=tk.W,
            padding=5
        )
        self.status_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # 任务计数标签
        self.task_label = ttk.Label(
            self.frame,
            text="任务: 0/0",
            relief=tk.SUNKEN,
            anchor=tk.CENTER,
            padding=5,
            width=15
        )
        self.task_label.pack(side=tk.RIGHT)
        
        # 进度指示器
        self.progress_var = tk.StringVar(value="")
        self.progress_label = ttk.Label(
            self.frame,
            textvariable=self.progress_var,
            relief=tk.SUNKEN,
            anchor=tk.CENTER,
            padding=5,
            width=10
        )
        self.progress_label.pack(side=tk.RIGHT)
        
        # 版权信息和GitHub链接
        self.copyright_label = ttk.Label(
            self.frame,
            text="© 2025 MICS by TanX | GitHub",
            relief=tk.SUNKEN,
            anchor=tk.CENTER,
            padding=5,
            cursor="hand2"
        )
        self.copyright_label.pack(side=tk.RIGHT, padx=(5, 0))
        
        # 绑定GitHub链接点击事件
        self.copyright_label.bind("<Button-1>", self._open_github)
    
    def set_status(self, message: str):
        """设置状态消息"""
        self.status_label.config(text=message)
    
    def set_task_count(self, total: int, completed: int):
        """设置任务计数"""
        self.task_label.config(text=f"任务: {completed}/{total}")
        
        # 更新进度百分比
        if total > 0:
            percentage = (completed / total) * 100
            self.progress_var.set(f"{percentage:.1f}%")
        else:
            self.progress_var.set("")
    
    def set_progress(self, progress: float):
        """设置进度百分比"""
        self.progress_var.set(f"{progress:.1f}%")
    
    def _open_github(self, event):
        """打开GitHub链接"""
        import webbrowser
        webbrowser.open("https://github.com/TanX-009/MICS") 