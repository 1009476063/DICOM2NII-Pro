"""
DICOM2NII Pro - 设置面板组件

转换参数设置面板
"""

import tkinter as tk
from tkinter import ttk, filedialog
from typing import Dict, Any
from pathlib import Path


class SettingsPanel:
    """设置面板组件"""
    
    def __init__(self, parent):
        """初始化设置面板"""
        self.frame = ttk.LabelFrame(parent, text="转换设置", padding=10)
        
        # 设置变量
        self.output_dir_var = tk.StringVar(value=str(Path.cwd() / "output"))
        self.modality_var = tk.StringVar(value="自动检测")
        self.auto_detect_var = tk.BooleanVar(value=True)
        self.remove_private_var = tk.BooleanVar(value=True)
        
        # 创建组件
        self._create_widgets()
    
    def _create_widgets(self):
        """创建子组件"""
        # 输出目录设置
        ttk.Label(self.frame, text="输出目录:").pack(anchor=tk.W)
        
        dir_frame = ttk.Frame(self.frame)
        dir_frame.pack(fill=tk.X, pady=5)
        
        self.dir_entry = ttk.Entry(dir_frame, textvariable=self.output_dir_var)
        self.dir_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        ttk.Button(dir_frame, text="浏览", command=self._browse_output_dir).pack(side=tk.RIGHT, padx=(5, 0))
        
        # 模态类型设置
        ttk.Label(self.frame, text="模态类型:").pack(anchor=tk.W, pady=(10, 0))
        modality_combo = ttk.Combobox(
            self.frame,
            textvariable=self.modality_var,
            values=["自动检测", "CT", "MRI", "MG", "RT"],
            state="readonly"
        )
        modality_combo.pack(fill=tk.X, pady=5)
        
        # 自动检测设置
        ttk.Checkbutton(
            self.frame,
            text="启用自动模态检测",
            variable=self.auto_detect_var
        ).pack(anchor=tk.W, pady=5)
        
        # 高级设置
        ttk.Label(self.frame, text="高级设置:").pack(anchor=tk.W, pady=(10, 0))
        
        ttk.Checkbutton(
            self.frame,
            text="移除私有标签",
            variable=self.remove_private_var
        ).pack(anchor=tk.W, pady=2)
        
        # 预设按钮
        preset_frame = ttk.Frame(self.frame)
        preset_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(preset_frame, text="CT预设", command=lambda: self._load_preset("CT")).pack(side=tk.LEFT, padx=2)
        ttk.Button(preset_frame, text="MRI预设", command=lambda: self._load_preset("MRI")).pack(side=tk.LEFT, padx=2)
        ttk.Button(preset_frame, text="默认设置", command=self._reset_settings).pack(side=tk.LEFT, padx=2)
    
    def _browse_output_dir(self):
        """浏览输出目录"""
        directory = filedialog.askdirectory(
            title="选择输出目录",
            initialdir=self.output_dir_var.get()
        )
        if directory:
            self.output_dir_var.set(directory)
    
    def _load_preset(self, modality: str):
        """加载预设"""
        self.modality_var.set(modality)
        self.auto_detect_var.set(False)
        
        if modality == "CT":
            # CT专用设置
            pass
        elif modality == "MRI":
            # MRI专用设置
            pass
    
    def _reset_settings(self):
        """重置为默认设置"""
        self.modality_var.set("自动检测")
        self.auto_detect_var.set(True)
        self.remove_private_var.set(True)
    
    def get_output_directory(self) -> str:
        """获取输出目录"""
        return self.output_dir_var.get()
    
    def get_conversion_settings(self) -> Dict[str, Any]:
        """获取转换设置"""
        modality = self.modality_var.get()
        if modality == "自动检测":
            modality = None
        
        return {
            'modality': modality,
            'auto_detect': self.auto_detect_var.get(),
            'conversion_params': {
                'remove_private_tags': self.remove_private_var.get()
            }
        } 