#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化的MICS GUI测试程序
用于验证GUI框架是否正常工作
"""

import tkinter as tk
from tkinter import ttk, messagebox
import sys
from pathlib import Path

# 添加src目录到Python路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

try:
    from auth.license_manager import license_manager
    LICENSE_AVAILABLE = True
except ImportError:
    LICENSE_AVAILABLE = False

class SimpleMicsWindow:
    """简化的MICS主窗口"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("MICS - Medical Imaging Image Conversion System v1.0.0")
        self.root.geometry("800x600")
        self.root.minsize(600, 400)
        
        self._create_ui()
        
    def _create_ui(self):
        """创建用户界面"""
        # 创建主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 标题
        title_label = ttk.Label(
            main_frame, 
            text="🏥 MICS - Medical Imaging Image Conversion System",
            font=("Arial", 16, "bold")
        )
        title_label.pack(pady=(0, 20))
        
        # 版本信息
        version_label = ttk.Label(
            main_frame,
            text="版本: v1.0.0 | 作者: TanX | 开发日期: 2025-06-01",
            font=("Arial", 10)
        )
        version_label.pack(pady=(0, 10))
        
        # 授权状态框架
        auth_frame = ttk.LabelFrame(main_frame, text="授权状态", padding="10")
        auth_frame.pack(fill=tk.X, pady=(0, 20))
        
        if LICENSE_AVAILABLE:
            try:
                is_valid, message = license_manager.validate_license()
                license_info = license_manager.get_license_info()
                
                status_text = f"{'✅ 授权有效' if is_valid else '❌ 授权无效'}"
                if license_info:
                    status_text += f"\n许可证类型: {license_info.license_type}"
                    status_text += f"\n用户: {license_info.user_name}"
                    status_text += f"\n组织: {license_info.organization}"
                    status_text += f"\n剩余天数: {license_info.days_remaining}"
                
                ttk.Label(auth_frame, text=status_text).pack(anchor=tk.W)
            except Exception as e:
                ttk.Label(auth_frame, text=f"❌ 授权检查失败: {e}").pack(anchor=tk.W)
        else:
            ttk.Label(auth_frame, text="❌ 授权模块不可用").pack(anchor=tk.W)
        
        # 功能按钮框架
        button_frame = ttk.LabelFrame(main_frame, text="功能模块", padding="10")
        button_frame.pack(fill=tk.X, pady=(0, 20))
        
        # 按钮网格
        ttk.Button(button_frame, text="📂 打开DICOM文件", command=self._open_file).grid(row=0, column=0, padx=5, pady=5, sticky='ew')
        ttk.Button(button_frame, text="📁 打开DICOM文件夹", command=self._open_folder).grid(row=0, column=1, padx=5, pady=5, sticky='ew')
        
        ttk.Button(button_frame, text="🔄 开始转换", command=self._start_conversion).grid(row=1, column=0, padx=5, pady=5, sticky='ew')
        ttk.Button(button_frame, text="⚙️ 设置", command=self._show_settings).grid(row=1, column=1, padx=5, pady=5, sticky='ew')
        
        ttk.Button(button_frame, text="🔐 许可证管理", command=self._manage_license).grid(row=2, column=0, padx=5, pady=5, sticky='ew')
        ttk.Button(button_frame, text="ℹ️ 关于", command=self._show_about).grid(row=2, column=1, padx=5, pady=5, sticky='ew')
        
        # 配置列权重
        button_frame.grid_columnconfigure(0, weight=1)
        button_frame.grid_columnconfigure(1, weight=1)
        
        # 状态信息
        status_frame = ttk.LabelFrame(main_frame, text="状态信息", padding="10")
        status_frame.pack(fill=tk.BOTH, expand=True)
        
        self.status_text = tk.Text(status_frame, height=8, wrap=tk.WORD, state=tk.DISABLED)
        scrollbar = ttk.Scrollbar(status_frame, orient=tk.VERTICAL, command=self.status_text.yview)
        self.status_text.configure(yscrollcommand=scrollbar.set)
        
        self.status_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self._log_message("🎉 MICS GUI界面初始化完成！")
        self._log_message("📝 这是简化版GUI界面，用于测试基本功能")
        self._log_message("🔧 完整功能正在开发中...")
        
    def _log_message(self, message):
        """记录消息到状态文本框"""
        self.status_text.config(state=tk.NORMAL)
        self.status_text.insert(tk.END, f"{message}\n")
        self.status_text.see(tk.END)
        self.status_text.config(state=tk.DISABLED)
        
    def _open_file(self):
        self._log_message("🔍 打开DICOM文件功能 - 开发中")
        
    def _open_folder(self):
        self._log_message("🔍 打开DICOM文件夹功能 - 开发中")
        
    def _start_conversion(self):
        self._log_message("🔄 DICOM转换功能 - 开发中")
        
    def _show_settings(self):
        self._log_message("⚙️ 设置功能 - 开发中")
        
    def _manage_license(self):
        """许可证管理"""
        if LICENSE_AVAILABLE:
            self._log_message("🔐 启动许可证管理...")
            # 这里可以调用许可证管理对话框
            messagebox.showinfo("许可证管理", "许可证管理功能正在开发中")
        else:
            messagebox.showerror("错误", "许可证模块不可用")
            
    def _show_about(self):
        """显示关于信息"""
        about_text = """
🏥 MICS - Medical Imaging Image Conversion System

📊 版本: v1.0.0
👨‍💻 作者: TanX
📅 开发日期: 2025-06-01
🔗 GitHub: https://github.com/TanX-009/MICS

💼 功能特性:
• DICOM到NIfTI格式转换
• 批量处理支持
• 多种医学影像模态支持
• 现代化GUI界面
• 完善的授权管理系统

© 2025 MICS by TanX
        """
        messagebox.showinfo("关于 MICS", about_text)
        
    def run(self):
        """运行GUI"""
        try:
            self.root.mainloop()
        except KeyboardInterrupt:
            print("\n⚠️ 用户中断操作")
            return 130

def main():
    """主函数"""
    print("=" * 60)
    print("🏥 MICS - Medical Imaging Image Conversion System")
    print("📊 版本: v1.0.0 | 作者: TanX")
    print("🔗 GitHub: https://github.com/TanX-009/MICS")
    print("=" * 60)
    print("🎨 启动简化版GUI界面...")
    
    try:
        app = SimpleMicsWindow()
        app.run()
        return 0
    except Exception as e:
        print(f"❌ GUI启动失败: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 