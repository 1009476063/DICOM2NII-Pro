"""
DICOM2NII Pro - 主窗口

现代化的医学影像转换软件主界面
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
from pathlib import Path
from typing import Optional, List, Dict, Any
import logging

from ..core.conversion_manager import ConversionManager
from ..core.batch_processor import BatchProcessor
from .components.progress_panel import ProgressPanel
from .components.settings_panel import SettingsPanel
from .components.file_browser import FileBrowser
from .components.status_bar import StatusBar


class MainWindow:
    """
    DICOM2NII Pro 主窗口
    
    提供现代化的GUI界面，包括：
    - 文件浏览和选择
    - 转换设置配置
    - 批量处理管理
    - 进度监控
    - 状态显示
    """
    
    def __init__(self):
        """初始化主窗口"""
        self.logger = logging.getLogger(__name__)
        
        # 创建主窗口
        self.root = tk.Tk()
        self.root.title("DICOM2NII Pro - 专业医学影像转换软件")
        self.root.geometry("1200x800")
        self.root.minsize(1000, 600)
        
        # 设置图标
        try:
            # 可以添加图标文件
            # self.root.iconbitmap("resources/icon.ico")
            pass
        except:
            pass
        
        # 创建转换管理器
        self.conversion_manager = ConversionManager(max_workers=2)
        self.batch_processor = BatchProcessor(self.conversion_manager)
        
        # 设置回调
        self.conversion_manager.add_progress_callback(self._on_progress_update)
        self.conversion_manager.add_completion_callback(self._on_task_completed)
        self.conversion_manager.add_error_callback(self._on_task_error)
        
        # 当前任务ID列表
        self.current_task_ids: List[str] = []
        
        # 创建UI组件
        self._create_ui()
        
        # 设置关闭事件
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
        
        self.logger.info("主窗口初始化完成")
    
    def _create_ui(self):
        """创建用户界面"""
        # 创建主菜单
        self._create_menu()
        
        # 创建工具栏
        self._create_toolbar()
        
        # 创建主面板
        self._create_main_panel()
        
        # 创建状态栏
        self._create_status_bar()
    
    def _create_menu(self):
        """创建菜单栏"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # 文件菜单
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="文件", menu=file_menu)
        file_menu.add_command(label="打开DICOM文件...", command=self._open_dicom_file)
        file_menu.add_command(label="打开DICOM文件夹...", command=self._open_dicom_folder)
        file_menu.add_separator()
        file_menu.add_command(label="退出", command=self._on_closing)
        
        # 转换菜单
        convert_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="转换", menu=convert_menu)
        convert_menu.add_command(label="开始转换", command=self._start_conversion)
        convert_menu.add_command(label="暂停转换", command=self._pause_conversion)
        convert_menu.add_command(label="恢复转换", command=self._resume_conversion)
        convert_menu.add_command(label="停止转换", command=self._stop_conversion)
        
        # 工具菜单
        tools_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="工具", menu=tools_menu)
        tools_menu.add_command(label="批量扫描", command=self._batch_scan)
        tools_menu.add_command(label="清理输出", command=self._cleanup_output)
        
        # 帮助菜单
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="帮助", menu=help_menu)
        help_menu.add_command(label="用户手册", command=self._show_help)
        help_menu.add_command(label="关于", command=self._show_about)
    
    def _create_toolbar(self):
        """创建工具栏"""
        toolbar = ttk.Frame(self.root)
        toolbar.pack(side=tk.TOP, fill=tk.X, padx=5, pady=2)
        
        # 文件操作按钮
        ttk.Button(toolbar, text="打开文件", command=self._open_dicom_file).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="打开文件夹", command=self._open_dicom_folder).pack(side=tk.LEFT, padx=2)
        
        # 分隔符
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=5)
        
        # 转换控制按钮
        self.start_btn = ttk.Button(toolbar, text="开始转换", command=self._start_conversion)
        self.start_btn.pack(side=tk.LEFT, padx=2)
        
        self.pause_btn = ttk.Button(toolbar, text="暂停", command=self._pause_conversion, state=tk.DISABLED)
        self.pause_btn.pack(side=tk.LEFT, padx=2)
        
        self.stop_btn = ttk.Button(toolbar, text="停止", command=self._stop_conversion, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=2)
        
        # 分隔符
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=5)
        
        # 批量处理按钮
        ttk.Button(toolbar, text="批量扫描", command=self._batch_scan).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="设置", command=self._show_settings).pack(side=tk.LEFT, padx=2)
    
    def _create_main_panel(self):
        """创建主面板"""
        # 创建主面板容器
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 创建垂直分割面板
        paned_window = ttk.PanedWindow(main_frame, orient=tk.VERTICAL)
        paned_window.pack(fill=tk.BOTH, expand=True)
        
        # 上半部分：文件浏览器
        self.file_browser = FileBrowser(paned_window)
        paned_window.add(self.file_browser.frame, weight=3)
        
        # 下半部分：水平分割
        bottom_paned = ttk.PanedWindow(paned_window, orient=tk.HORIZONTAL)
        paned_window.add(bottom_paned, weight=2)
        
        # 左侧：进度面板
        self.progress_panel = ProgressPanel(bottom_paned)
        bottom_paned.add(self.progress_panel.frame, weight=2)
        
        # 右侧：设置面板
        self.settings_panel = SettingsPanel(bottom_paned)
        bottom_paned.add(self.settings_panel.frame, weight=1)
    
    def _create_status_bar(self):
        """创建状态栏"""
        self.status_bar = StatusBar(self.root)
        self.status_bar.frame.pack(side=tk.BOTTOM, fill=tk.X)
        
        # 设置初始状态
        self.status_bar.set_status("就绪")
        self.status_bar.set_task_count(0, 0)
    
    def _open_dicom_file(self):
        """打开DICOM文件"""
        file_path = filedialog.askopenfilename(
            title="选择DICOM文件",
            filetypes=[
                ("DICOM files", "*.dcm *.dicom"),
                ("All files", "*.*")
            ]
        )
        
        if file_path:
            self.file_browser.add_file(file_path)
            self.status_bar.set_status(f"已添加文件: {Path(file_path).name}")
    
    def _open_dicom_folder(self):
        """打开DICOM文件夹"""
        folder_path = filedialog.askdirectory(
            title="选择包含DICOM文件的文件夹"
        )
        
        if folder_path:
            self.file_browser.add_folder(folder_path)
            self.status_bar.set_status(f"已添加文件夹: {Path(folder_path).name}")
    
    def _start_conversion(self):
        """开始转换"""
        # 获取选中的文件
        selected_files = self.file_browser.get_selected_files()
        if not selected_files:
            messagebox.showwarning("警告", "请先选择要转换的文件或文件夹")
            return
        
        # 获取输出目录
        output_dir = self.settings_panel.get_output_directory()
        if not output_dir:
            messagebox.showwarning("警告", "请设置输出目录")
            return
        
        # 获取转换设置
        conversion_settings = self.settings_panel.get_conversion_settings()
        
        # 开始转换任务
        self._start_conversion_task(selected_files, output_dir, conversion_settings)
    
    def _start_conversion_task(self, input_files: List[str], output_dir: str, settings: Dict[str, Any]):
        """启动转换任务"""
        try:
            self.status_bar.set_status("正在准备转换任务...")
            
            # 创建转换任务
            tasks = []
            for input_file in input_files:
                input_path = Path(input_file)
                output_path = Path(output_dir) / f"{input_path.stem}.nii.gz"
                
                task_info = {
                    'input_path': str(input_path),
                    'output_path': str(output_path),
                    'modality': settings.get('modality'),
                    'auto_detect': settings.get('auto_detect', True),
                    'conversion_params': settings.get('conversion_params', {}),
                    'priority': 0
                }
                tasks.append(task_info)
            
            # 提交任务
            self.current_task_ids = self.batch_processor.submit_batch_conversion(
                tasks, self.conversion_manager
            )
            
            # 更新UI状态
            self.start_btn.config(state=tk.DISABLED)
            self.pause_btn.config(state=tk.NORMAL)
            self.stop_btn.config(state=tk.NORMAL)
            
            self.status_bar.set_status("转换进行中...")
            self.status_bar.set_task_count(len(self.current_task_ids), 0)
            
            # 启动进度监控
            self._start_progress_monitor()
            
        except Exception as e:
            self.logger.error(f"启动转换任务失败: {e}")
            messagebox.showerror("错误", f"启动转换失败: {e}")
    
    def _pause_conversion(self):
        """暂停转换"""
        self.conversion_manager.pause_processing()
        self.status_bar.set_status("转换已暂停")
        self.pause_btn.config(text="恢复")
        self.pause_btn.config(command=self._resume_conversion)
    
    def _resume_conversion(self):
        """恢复转换"""
        self.conversion_manager.resume_processing()
        self.status_bar.set_status("转换已恢复")
        self.pause_btn.config(text="暂停")
        self.pause_btn.config(command=self._pause_conversion)
    
    def _stop_conversion(self):
        """停止转换"""
        if messagebox.askyesno("确认", "确定要停止当前转换吗？"):
            # 取消所有任务
            for task_id in self.current_task_ids:
                self.conversion_manager.cancel_task(task_id)
            
            self._reset_ui_state()
            self.status_bar.set_status("转换已停止")
    
    def _batch_scan(self):
        """批量扫描"""
        folder_path = filedialog.askdirectory(
            title="选择要扫描的文件夹"
        )
        
        if not folder_path:
            return
        
        # 在新线程中执行扫描
        def scan_thread():
            try:
                self.status_bar.set_status("正在扫描...")
                
                scan_result = self.batch_processor.scan_directory(
                    folder_path,
                    recursive=True
                )
                
                # 在主线程中更新UI
                self.root.after(0, lambda: self._on_scan_completed(scan_result))
                
            except Exception as e:
                self.logger.error(f"扫描失败: {e}")
                self.root.after(0, lambda: messagebox.showerror("错误", f"扫描失败: {e}"))
        
        threading.Thread(target=scan_thread, daemon=True).start()
    
    def _on_scan_completed(self, scan_result):
        """扫描完成回调"""
        summary = scan_result.get_summary()
        
        # 显示扫描结果
        result_text = f"""扫描完成！
        
找到 {summary['total_dicom_files']} 个DICOM文件
有效文件: {summary['valid_dicom_files']}
识别序列: {summary['total_series']}
患者数量: {summary['total_patients']}

模态分布:
"""
        
        for modality, count in summary['modality_distribution'].items():
            result_text += f"  {modality}: {count} 个序列\n"
        
        if summary['error_count'] > 0:
            result_text += f"\n错误数量: {summary['error_count']}"
        
        messagebox.showinfo("扫描结果", result_text)
        self.status_bar.set_status("扫描完成")
    
    def _show_settings(self):
        """显示设置对话框"""
        # 这里可以实现设置对话框
        messagebox.showinfo("设置", "设置功能正在开发中...")
    
    def _cleanup_output(self):
        """清理输出"""
        if messagebox.askyesno("确认", "确定要清理输出目录吗？"):
            # 实现清理逻辑
            messagebox.showinfo("清理", "清理功能正在开发中...")
    
    def _show_help(self):
        """显示帮助"""
        help_text = """DICOM2NII Pro 用户手册

基本操作：
1. 点击"打开文件"或"打开文件夹"选择要转换的DICOM数据
2. 在设置面板中配置输出目录和转换参数
3. 点击"开始转换"执行转换
4. 在进度面板中监控转换进度

批量处理：
1. 使用"批量扫描"功能扫描大量DICOM数据
2. 系统会自动识别序列和模态类型
3. 可以选择性地转换特定序列

支持的模态类型：
- CT (计算机断层扫描)
- MRI (磁共振成像)
- MG (乳腺摄影)
- RT (放疗数据)
"""
        
        # 创建帮助窗口
        help_window = tk.Toplevel(self.root)
        help_window.title("帮助")
        help_window.geometry("600x400")
        
        text_widget = tk.Text(help_window, wrap=tk.WORD, padx=10, pady=10)
        text_widget.pack(fill=tk.BOTH, expand=True)
        text_widget.insert(tk.END, help_text)
        text_widget.config(state=tk.DISABLED)
    
    def _show_about(self):
        """显示关于信息"""
        about_text = """DICOM2NII Pro v1.0.0

专业的医学影像格式转换软件

特点：
• 支持多种DICOM模态类型
• 智能序列识别和分组
• 批量处理和转换管理
• 现代化的用户界面
• 详细的进度监控

技术支持：
请访问我们的GitHub仓库获取更多信息和技术支持。

© 2024 DICOM2NII Pro Team
"""
        messagebox.showinfo("关于 DICOM2NII Pro", about_text)
    
    def _start_progress_monitor(self):
        """启动进度监控"""
        def update_progress():
            if not self.current_task_ids:
                return
            
            progress_info = self.batch_processor.get_conversion_progress(
                self.current_task_ids, self.conversion_manager
            )
            
            # 更新进度面板
            self.progress_panel.update_progress(progress_info)
            
            # 更新状态栏
            self.status_bar.set_task_count(
                progress_info['total_tasks'],
                progress_info['completed']
            )
            
            # 检查是否全部完成
            if (progress_info['completed'] + progress_info['failed'] >= 
                progress_info['total_tasks']):
                self._on_all_tasks_completed(progress_info)
            else:
                # 继续监控
                self.root.after(1000, update_progress)
        
        # 启动监控
        self.root.after(100, update_progress)
    
    def _on_all_tasks_completed(self, progress_info):
        """所有任务完成回调"""
        self._reset_ui_state()
        
        # 显示完成信息
        completed = progress_info['completed']
        failed = progress_info['failed']
        total = progress_info['total_tasks']
        
        if failed == 0:
            self.status_bar.set_status(f"转换完成！成功转换 {completed} 个文件")
            messagebox.showinfo("转换完成", f"成功转换 {completed} 个文件")
        else:
            self.status_bar.set_status(f"转换完成！成功 {completed} 个，失败 {failed} 个")
            messagebox.showwarning("转换完成", f"成功转换 {completed} 个文件，{failed} 个文件转换失败")
        
        # 清理任务ID
        self.current_task_ids.clear()
    
    def _reset_ui_state(self):
        """重置UI状态"""
        self.start_btn.config(state=tk.NORMAL)
        self.pause_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.DISABLED)
        self.pause_btn.config(text="暂停")
        self.pause_btn.config(command=self._pause_conversion)
    
    def _on_progress_update(self, task_id: str, progress: float, message: str):
        """进度更新回调"""
        # 在主线程中更新UI
        self.root.after(0, lambda: self.progress_panel.update_task_progress(task_id, progress, message))
    
    def _on_task_completed(self, task):
        """任务完成回调"""
        self.logger.info(f"任务完成: {task.task_id}")
    
    def _on_task_error(self, task, error):
        """任务错误回调"""
        self.logger.error(f"任务失败: {task.task_id} - {error}")
    
    def _on_closing(self):
        """窗口关闭事件"""
        if self.current_task_ids:
            if not messagebox.askyesno("确认退出", "还有转换任务正在进行，确定要退出吗？"):
                return
        
        # 停止转换管理器
        self.conversion_manager.stop_workers()
        
        # 销毁窗口
        self.root.destroy()
    
    def run(self):
        """运行应用程序"""
        self.logger.info("启动DICOM2NII Pro GUI")
        self.root.mainloop()


if __name__ == "__main__":
    # 设置日志
    logging.basicConfig(level=logging.INFO)
    
    # 创建并运行主窗口
    app = MainWindow()
    app.run() 