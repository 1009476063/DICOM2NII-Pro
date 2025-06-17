"""
DICOM2NII Pro - 统一转换管理器

负责协调和管理所有DICOM转换器的工作，提供统一的转换接口
支持批量处理、进度监控、错误处理等高级功能
"""

import os
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable, Union
from dataclasses import dataclass, field
from datetime import datetime
import threading
import queue
import time

from .converters import get_converter, list_supported_modalities
from .exceptions import ConversionError, DicomValidationError, UnsupportedModalityError
from ..config.settings import settings


@dataclass
class ConversionTask:
    """转换任务"""
    task_id: str
    input_path: Path
    output_path: Path
    modality: Optional[str] = None
    auto_detect: bool = True
    conversion_params: Dict[str, Any] = field(default_factory=dict)
    priority: int = 0  # 优先级，数字越大优先级越高
    created_time: datetime = field(default_factory=datetime.now)
    started_time: Optional[datetime] = None
    completed_time: Optional[datetime] = None
    status: str = "pending"  # pending, running, completed, failed, cancelled
    progress: float = 0.0
    error_message: Optional[str] = None
    result_files: List[Path] = field(default_factory=list)


@dataclass
class ConversionStats:
    """转换统计信息"""
    total_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    cancelled_tasks: int = 0
    total_files_processed: int = 0
    total_processing_time: float = 0.0
    average_time_per_task: float = 0.0
    
    def update_completion(self, task: ConversionTask, processing_time: float):
        """更新完成统计"""
        if task.status == "completed":
            self.completed_tasks += 1
        elif task.status == "failed":
            self.failed_tasks += 1
        elif task.status == "cancelled":
            self.cancelled_tasks += 1
        
        self.total_processing_time += processing_time
        if self.completed_tasks > 0:
            self.average_time_per_task = self.total_processing_time / self.completed_tasks


class ConversionManager:
    """
    统一转换管理器
    
    提供以下功能：
    - 统一的转换接口
    - 批量处理管理
    - 进度监控和回调
    - 错误处理和重试
    - 转换队列管理
    - 性能统计
    """
    
    def __init__(self, max_workers: int = 1, auto_start: bool = True):
        """
        初始化转换管理器
        
        Args:
            max_workers: 最大并发工作线程数
            auto_start: 是否自动开始处理队列
        """
        self.max_workers = max_workers
        self.logger = logging.getLogger(__name__)
        
        # 任务队列和管理
        self.task_queue = queue.PriorityQueue()
        self.active_tasks: Dict[str, ConversionTask] = {}
        self.completed_tasks: Dict[str, ConversionTask] = {}
        self.task_counter = 0
        
        # 线程管理
        self.workers: List[threading.Thread] = []
        self.shutdown_event = threading.Event()
        self.pause_event = threading.Event()
        
        # 回调函数
        self.progress_callbacks: List[Callable] = []
        self.completion_callbacks: List[Callable] = []
        self.error_callbacks: List[Callable] = []
        
        # 统计信息
        self.stats = ConversionStats()
        
        # 启动工作线程
        if auto_start:
            self.start_workers()
    
    def start_workers(self):
        """启动工作线程"""
        if self.workers:
            self.logger.warning("工作线程已经启动")
            return
        
        self.shutdown_event.clear()
        self.pause_event.set()  # 初始状态为运行
        
        for i in range(self.max_workers):
            worker = threading.Thread(
                target=self._worker_thread,
                name=f"ConversionWorker-{i+1}",
                daemon=True
            )
            worker.start()
            self.workers.append(worker)
        
        self.logger.info(f"启动了 {self.max_workers} 个转换工作线程")
    
    def stop_workers(self, timeout: float = 30.0):
        """停止工作线程"""
        self.shutdown_event.set()
        
        # 等待所有线程完成
        for worker in self.workers:
            worker.join(timeout=timeout)
            if worker.is_alive():
                self.logger.warning(f"工作线程 {worker.name} 未能在超时时间内停止")
        
        self.workers.clear()
        self.logger.info("所有工作线程已停止")
    
    def pause_processing(self):
        """暂停处理"""
        self.pause_event.clear()
        self.logger.info("转换处理已暂停")
    
    def resume_processing(self):
        """恢复处理"""
        self.pause_event.set()
        self.logger.info("转换处理已恢复")
    
    def add_task(self, input_path: Union[str, Path], output_path: Union[str, Path],
                 modality: Optional[str] = None, auto_detect: bool = True,
                 conversion_params: Optional[Dict[str, Any]] = None,
                 priority: int = 0) -> str:
        """
        添加转换任务
        
        Args:
            input_path: 输入路径
            output_path: 输出路径
            modality: 指定模态类型，None时自动检测
            auto_detect: 是否自动检测模态
            conversion_params: 转换参数
            priority: 优先级
            
        Returns:
            任务ID
        """
        self.task_counter += 1
        task_id = f"task_{self.task_counter:06d}"
        
        task = ConversionTask(
            task_id=task_id,
            input_path=Path(input_path),
            output_path=Path(output_path),
            modality=modality,
            auto_detect=auto_detect,
            conversion_params=conversion_params or {},
            priority=priority
        )
        
        # 将任务加入队列（优先级队列，优先级高的先处理）
        self.task_queue.put((-priority, task.created_time, task))
        self.stats.total_tasks += 1
        
        self.logger.info(f"添加转换任务 {task_id}: {input_path} -> {output_path}")
        return task_id
    
    def add_batch_tasks(self, tasks: List[Dict[str, Any]]) -> List[str]:
        """
        批量添加转换任务
        
        Args:
            tasks: 任务列表，每个任务包含input_path, output_path等参数
            
        Returns:
            任务ID列表
        """
        task_ids = []
        
        for task_info in tasks:
            task_id = self.add_task(**task_info)
            task_ids.append(task_id)
        
        self.logger.info(f"批量添加了 {len(task_ids)} 个转换任务")
        return task_ids
    
    def cancel_task(self, task_id: str) -> bool:
        """
        取消任务
        
        Args:
            task_id: 任务ID
            
        Returns:
            是否成功取消
        """
        # 检查活动任务
        if task_id in self.active_tasks:
            task = self.active_tasks[task_id]
            task.status = "cancelled"
            self.logger.info(f"取消活动任务 {task_id}")
            return True
        
        # TODO: 从队列中移除待处理任务（PriorityQueue不支持直接移除）
        self.logger.warning(f"任务 {task_id} 无法取消，可能已完成或不存在")
        return False
    
    def get_task_status(self, task_id: str) -> Optional[ConversionTask]:
        """获取任务状态"""
        if task_id in self.active_tasks:
            return self.active_tasks[task_id]
        elif task_id in self.completed_tasks:
            return self.completed_tasks[task_id]
        else:
            return None
    
    def get_queue_status(self) -> Dict[str, Any]:
        """获取队列状态"""
        return {
            "queue_size": self.task_queue.qsize(),
            "active_tasks": len(self.active_tasks),
            "completed_tasks": len(self.completed_tasks),
            "total_tasks": self.stats.total_tasks,
            "is_paused": not self.pause_event.is_set(),
            "workers_count": len(self.workers)
        }
    
    def get_statistics(self) -> ConversionStats:
        """获取转换统计信息"""
        return self.stats
    
    def add_progress_callback(self, callback: Callable[[str, float, str], None]):
        """添加进度回调函数"""
        self.progress_callbacks.append(callback)
    
    def add_completion_callback(self, callback: Callable[[ConversionTask], None]):
        """添加完成回调函数"""
        self.completion_callbacks.append(callback)
    
    def add_error_callback(self, callback: Callable[[ConversionTask, Exception], None]):
        """添加错误回调函数"""
        self.error_callbacks.append(callback)
    
    def _worker_thread(self):
        """工作线程主循环"""
        thread_name = threading.current_thread().name
        self.logger.info(f"转换工作线程 {thread_name} 启动")
        
        while not self.shutdown_event.is_set():
            try:
                # 等待暂停状态解除
                self.pause_event.wait()
                
                if self.shutdown_event.is_set():
                    break
                
                # 从队列获取任务
                try:
                    priority, created_time, task = self.task_queue.get(timeout=1.0)
                except queue.Empty:
                    continue
                
                # 处理任务
                self._process_task(task)
                self.task_queue.task_done()
                
            except Exception as e:
                self.logger.error(f"工作线程 {thread_name} 发生未捕获异常: {e}")
        
        self.logger.info(f"转换工作线程 {thread_name} 停止")
    
    def _process_task(self, task: ConversionTask):
        """处理单个转换任务"""
        task.started_time = datetime.now()
        task.status = "running"
        task.progress = 0.0
        
        self.active_tasks[task.task_id] = task
        
        try:
            self.logger.info(f"开始处理任务 {task.task_id}: {task.input_path}")
            
            # 自动检测模态类型
            if task.auto_detect and not task.modality:
                task.modality = self._detect_modality(task.input_path)
                if not task.modality:
                    raise UnsupportedModalityError(
                        "auto_detect", 
                        f"无法自动检测模态类型: {task.input_path}"
                    )
            
            # 创建进度回调
            def progress_callback(progress: int, message: str):
                task.progress = progress / 100.0
                for callback in self.progress_callbacks:
                    try:
                        callback(task.task_id, task.progress, message)
                    except Exception as e:
                        self.logger.warning(f"进度回调函数执行失败: {e}")
            
            # 获取转换器并执行转换
            converter = get_converter(task.modality, progress_callback)
            success = converter.convert_to_nifti(
                str(task.input_path),
                str(task.output_path),
                task.conversion_params
            )
            
            if success:
                task.status = "completed"
                task.progress = 1.0
                task.completed_time = datetime.now()
                
                # 记录结果文件
                if task.output_path.exists():
                    task.result_files.append(task.output_path)
                
                # 计算处理时间
                processing_time = (task.completed_time - task.started_time).total_seconds()
                self.stats.update_completion(task, processing_time)
                
                self.logger.info(f"任务 {task.task_id} 转换成功，耗时 {processing_time:.2f}秒")
                
                # 调用完成回调
                for callback in self.completion_callbacks:
                    try:
                        callback(task)
                    except Exception as e:
                        self.logger.warning(f"完成回调函数执行失败: {e}")
            else:
                raise ConversionError("conversion", "转换器返回失败状态")
        
        except Exception as e:
            task.status = "failed"
            task.error_message = str(e)
            task.completed_time = datetime.now()
            
            processing_time = (task.completed_time - task.started_time).total_seconds()
            self.stats.update_completion(task, processing_time)
            
            self.logger.error(f"任务 {task.task_id} 转换失败: {e}")
            
            # 调用错误回调
            for callback in self.error_callbacks:
                try:
                    callback(task, e)
                except Exception as callback_error:
                    self.logger.warning(f"错误回调函数执行失败: {callback_error}")
        
        finally:
            # 移动到完成任务列表
            if task.task_id in self.active_tasks:
                del self.active_tasks[task.task_id]
            self.completed_tasks[task.task_id] = task
    
    def _detect_modality(self, input_path: Path) -> Optional[str]:
        """
        自动检测模态类型
        
        Args:
            input_path: 输入路径
            
        Returns:
            检测到的模态类型
        """
        try:
            # 简单的路径匹配检测
            path_str = str(input_path).upper()
            
            # CT检测
            if any(keyword in path_str for keyword in ['CT', 'HEAD-CT', 'BASELINE-HEAD-CT']):
                return 'CT'
            
            # MRI检测
            if any(keyword in path_str for keyword in ['MRI', 'MR', 'DCE', 'DWI', 'ADC', 'T1', 'T2', 'FLAIR']):
                return 'MRI'
            
            # 乳腺摄影检测
            if any(keyword in path_str for keyword in ['MG', 'MAMMOGRAPHY', 'BREAST', 'MLO', 'CC']):
                return 'MG'
            
            # 放疗检测
            if any(keyword in path_str for keyword in ['RT', 'RTSTRUCT', 'RTPLAN', 'RTDOSE']):
                return 'RT'
            
            # 如果路径检测失败，尝试通过DICOM文件检测
            if input_path.is_dir():
                dicom_files = list(input_path.glob('*.dcm')) or list(input_path.glob('*'))
                if dicom_files:
                    return self._detect_modality_from_dicom(dicom_files[0])
            elif input_path.suffix.lower() in ['.dcm', '.dicom']:
                return self._detect_modality_from_dicom(input_path)
            
            return None
            
        except Exception as e:
            self.logger.warning(f"模态检测失败: {e}")
            return None
    
    def _detect_modality_from_dicom(self, dicom_file: Path) -> Optional[str]:
        """从DICOM文件检测模态"""
        try:
            import pydicom
            ds = pydicom.dcmread(dicom_file, force=True)
            
            if hasattr(ds, 'Modality'):
                modality = str(ds.Modality).upper()
                if modality in ['CT']:
                    return 'CT'
                elif modality in ['MR', 'MRI']:
                    return 'MRI'
                elif modality in ['MG']:
                    return 'MG'
                elif modality in ['RTSTRUCT', 'RTPLAN', 'RTDOSE']:
                    return 'RT'
            
            return None
            
        except Exception as e:
            self.logger.warning(f"从DICOM文件检测模态失败: {e}")
            return None
    
    def wait_for_completion(self, timeout: Optional[float] = None) -> bool:
        """
        等待所有任务完成
        
        Args:
            timeout: 超时时间（秒）
            
        Returns:
            是否所有任务都完成
        """
        start_time = time.time()
        
        while True:
            if self.task_queue.empty() and not self.active_tasks:
                return True
            
            if timeout and (time.time() - start_time) > timeout:
                return False
            
            time.sleep(0.1)
    
    def cleanup_completed_tasks(self, keep_recent: int = 100):
        """
        清理已完成的任务
        
        Args:
            keep_recent: 保留最近的任务数量
        """
        if len(self.completed_tasks) > keep_recent:
            # 按完成时间排序，保留最新的
            sorted_tasks = sorted(
                self.completed_tasks.items(),
                key=lambda x: x[1].completed_time or datetime.min,
                reverse=True
            )
            
            tasks_to_keep = dict(sorted_tasks[:keep_recent])
            removed_count = len(self.completed_tasks) - len(tasks_to_keep)
            
            self.completed_tasks = tasks_to_keep
            self.logger.info(f"清理了 {removed_count} 个已完成的任务记录")
    
    def __enter__(self):
        """上下文管理器入口"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.stop_workers()


# 全局转换管理器实例
conversion_manager = ConversionManager(max_workers=settings.conversion.max_memory_gb // 2 or 1) 