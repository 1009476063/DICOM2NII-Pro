"""
DICOM2NII Pro - 文件浏览器组件

文件和文件夹选择浏览器
"""

import tkinter as tk
from tkinter import ttk
from pathlib import Path
from typing import List


class FileBrowser:
    """文件浏览器组件"""
    
    def __init__(self, parent):
        """初始化文件浏览器"""
        self.frame = ttk.LabelFrame(parent, text="文件浏览器", padding=10)
        
        # 创建组件
        self._create_widgets()
    
    def _create_widgets(self):
        """创建子组件"""
        # 配置frame的grid
        self.frame.grid_rowconfigure(1, weight=1)
        self.frame.grid_columnconfigure(0, weight=1)
        
        # 工具栏
        toolbar = ttk.Frame(self.frame)
        toolbar.grid(row=0, column=0, sticky='ew', pady=(0, 10))
        
        ttk.Button(toolbar, text="添加文件", command=self._add_files).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="添加文件夹", command=self._add_folder).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="移除选中", command=self._remove_selected).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="清空", command=self._clear_all).pack(side=tk.LEFT, padx=2)
        
        # 创建树视图容器
        tree_container = ttk.Frame(self.frame)
        tree_container.grid(row=1, column=0, sticky='nsew')
        tree_container.grid_rowconfigure(0, weight=1)
        tree_container.grid_columnconfigure(0, weight=1)
        
        # 文件列表
        self.file_tree = ttk.Treeview(
            tree_container,
            columns=('type', 'size', 'path'),
            show='tree headings',
            selectmode='extended'
        )
        
        # 设置列标题
        self.file_tree.heading('#0', text='名称')
        self.file_tree.heading('type', text='类型')
        self.file_tree.heading('size', text='大小')
        self.file_tree.heading('path', text='路径')
        
        # 设置列宽
        self.file_tree.column('#0', width=200)
        self.file_tree.column('type', width=80)
        self.file_tree.column('size', width=100)
        self.file_tree.column('path', width=300)
        
        # 添加滚动条
        v_scrollbar = ttk.Scrollbar(tree_container, orient=tk.VERTICAL, command=self.file_tree.yview)
        h_scrollbar = ttk.Scrollbar(tree_container, orient=tk.HORIZONTAL, command=self.file_tree.xview)
        
        self.file_tree.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        # 布局树视图和滚动条
        self.file_tree.grid(row=0, column=0, sticky='nsew')
        v_scrollbar.grid(row=0, column=1, sticky='ns')
        h_scrollbar.grid(row=1, column=0, sticky='ew')
    
    def _add_files(self):
        """添加文件（占位方法）"""
        # 这个方法将由主窗口调用
        pass
    
    def _add_folder(self):
        """添加文件夹（占位方法）"""
        # 这个方法将由主窗口调用
        pass
    
    def _remove_selected(self):
        """移除选中的项目"""
        selected_items = self.file_tree.selection()
        for item in selected_items:
            self.file_tree.delete(item)
    
    def _clear_all(self):
        """清空所有项目"""
        for item in self.file_tree.get_children():
            self.file_tree.delete(item)
    
    def add_file(self, file_path: str):
        """添加文件到列表"""
        path = Path(file_path)
        
        if not path.exists():
            return
        
        # 获取文件信息
        file_type = "文件夹" if path.is_dir() else "文件"
        file_size = self._format_size(path.stat().st_size) if path.is_file() else "-"
        
        # 插入到树视图
        self.file_tree.insert('', 'end',
                            text=path.name,
                            values=(file_type, file_size, str(path.parent)))
    
    def add_folder(self, folder_path: str):
        """添加文件夹到列表"""
        self.add_file(folder_path)
    
    def get_selected_files(self) -> List[str]:
        """获取选中的文件列表"""
        selected_files = []
        
        for item in self.file_tree.selection():
            file_name = self.file_tree.item(item, 'text')
            file_path = self.file_tree.item(item, 'values')[2]  # 路径列
            full_path = str(Path(file_path) / file_name)
            selected_files.append(full_path)
        
        return selected_files
    
    def get_all_files(self) -> List[str]:
        """获取所有文件列表"""
        all_files = []
        
        for item in self.file_tree.get_children():
            file_name = self.file_tree.item(item, 'text')
            file_path = self.file_tree.item(item, 'values')[2]  # 路径列
            full_path = str(Path(file_path) / file_name)
            all_files.append(full_path)
        
        return all_files
    
    def _format_size(self, size_bytes: int) -> str:
        """格式化文件大小"""
        if size_bytes == 0:
            return "0 B"
        
        size_names = ["B", "KB", "MB", "GB", "TB"]
        i = 0
        while size_bytes >= 1024 and i < len(size_names) - 1:
            size_bytes /= 1024.0
            i += 1
        
        return f"{size_bytes:.1f} {size_names[i]}" 