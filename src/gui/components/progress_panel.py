"""
DICOM2NII Pro - 进度面板组件

显示转换任务的进度信息
"""

import tkinter as tk
from tkinter import ttk
from typing import Dict, Any


class ProgressPanel:
    """进度面板组件"""
    
    def __init__(self, parent):
        """初始化进度面板"""
        self.frame = ttk.LabelFrame(parent, text="转换进度", padding=10)
        
        # 创建进度显示组件
        self._create_widgets()
    
    def _create_widgets(self):
        """创建子组件"""
        # 总体进度
        ttk.Label(self.frame, text="总体进度:").pack(anchor=tk.W)
        self.overall_progress = ttk.Progressbar(
            self.frame, 
            length=300, 
            mode='determinate'
        )
        self.overall_progress.pack(fill=tk.X, pady=5)
        
        self.overall_label = ttk.Label(self.frame, text="0%")
        self.overall_label.pack(anchor=tk.W)
        
        # 任务列表
        ttk.Label(self.frame, text="任务详情:").pack(anchor=tk.W, pady=(10, 0))
        
        # 创建任务树视图
        self.task_tree = ttk.Treeview(
            self.frame,
            columns=('status', 'progress', 'message'),
            show='tree headings',
            height=10
        )
        
        # 设置列标题
        self.task_tree.heading('#0', text='任务ID')
        self.task_tree.heading('status', text='状态')
        self.task_tree.heading('progress', text='进度')
        self.task_tree.heading('message', text='消息')
        
        # 设置列宽
        self.task_tree.column('#0', width=100)
        self.task_tree.column('status', width=80)
        self.task_tree.column('progress', width=80)
        self.task_tree.column('message', width=200)
        
        # 添加滚动条
        scrollbar = ttk.Scrollbar(self.frame, orient=tk.VERTICAL, command=self.task_tree.yview)
        self.task_tree.configure(yscrollcommand=scrollbar.set)
        
        # 布局
        self.task_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    def update_progress(self, progress_info: Dict[str, Any]):
        """更新进度信息"""
        # 更新总体进度
        overall_progress = progress_info.get('overall_progress', 0.0)
        self.overall_progress['value'] = overall_progress * 100
        self.overall_label.config(text=f"{overall_progress*100:.1f}%")
        
        # 更新任务详情
        task_details = progress_info.get('task_details', {})
        
        # 清空现有项目
        for item in self.task_tree.get_children():
            self.task_tree.delete(item)
        
        # 添加任务项目
        for task_id, details in task_details.items():
            status = details.get('status', 'unknown')
            progress = details.get('progress', 0.0)
            message = details.get('error_message') or '处理中...'
            
            self.task_tree.insert('', 'end', 
                                text=task_id,
                                values=(status, f"{progress*100:.1f}%", message))
    
    def update_task_progress(self, task_id: str, progress: float, message: str):
        """更新单个任务进度"""
        # 查找任务项目
        for item in self.task_tree.get_children():
            if self.task_tree.item(item, 'text') == task_id:
                current_values = list(self.task_tree.item(item, 'values'))
                current_values[1] = f"{progress*100:.1f}%"
                current_values[2] = message
                self.task_tree.item(item, values=current_values)
                break 