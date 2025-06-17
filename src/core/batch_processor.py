"""
DICOM2NII Pro - 批量处理模块

支持目录扫描、智能分组、批量任务生成和转换管理
"""

import os
import logging
from pathlib import Path
from typing import Dict, List, Optional, Set, Union, Any, Tuple
from dataclasses import dataclass, field
import re
import pydicom
from collections import defaultdict, Counter

from .conversion_manager import ConversionManager, ConversionTask
from .exceptions import DicomValidationError, ConversionError


@dataclass
class DicomSeries:
    """DICOM序列信息"""
    series_uid: str
    series_description: str
    modality: str
    patient_id: str
    study_uid: str
    series_number: Optional[int] = None
    acquisition_date: Optional[str] = None
    files: List[Path] = field(default_factory=list)
    total_instances: int = 0
    
    def __post_init__(self):
        self.total_instances = len(self.files)
    
    @property
    def series_name(self) -> str:
        """生成序列名称"""
        parts = []
        if self.series_number:
            parts.append(f"S{self.series_number:03d}")
        if self.series_description:
            # 清理序列描述，移除特殊字符
            clean_desc = re.sub(r'[^\w\-_\s]', '', self.series_description)
            clean_desc = re.sub(r'\s+', '_', clean_desc.strip())
            parts.append(clean_desc)
        else:
            parts.append(self.modality)
        return "_".join(parts)


@dataclass
class BatchScanResult:
    """批量扫描结果"""
    total_dicom_files: int = 0
    valid_dicom_files: int = 0
    total_series: int = 0
    patients: Dict[str, Dict] = field(default_factory=dict)  # patient_id -> patient_info
    series_by_modality: Dict[str, List[DicomSeries]] = field(default_factory=dict)
    scan_errors: List[str] = field(default_factory=list)
    scan_warnings: List[str] = field(default_factory=list)
    
    def get_summary(self) -> Dict[str, Any]:
        """获取扫描摘要"""
        modality_counts = {mod: len(series_list) for mod, series_list in self.series_by_modality.items()}
        
        return {
            "total_dicom_files": self.total_dicom_files,
            "valid_dicom_files": self.valid_dicom_files,
            "total_series": self.total_series,
            "total_patients": len(self.patients),
            "modality_distribution": modality_counts,
            "error_count": len(self.scan_errors),
            "warning_count": len(self.scan_warnings)
        }


class BatchProcessor:
    """
    批量处理器
    
    功能：
    - 扫描目录寻找DICOM文件
    - 智能分组和序列识别
    - 生成批量转换任务
    - 监控转换进度
    """
    
    def __init__(self, conversion_manager: Optional[ConversionManager] = None):
        """
        初始化批量处理器
        
        Args:
            conversion_manager: 转换管理器实例，None时使用默认实例
        """
        self.logger = logging.getLogger(__name__)
        self.conversion_manager = conversion_manager
        
        # DICOM文件扩展名
        self.dicom_extensions = {'.dcm', '.dicom', '.ima', ''}  # 空字符串表示无扩展名
        
        # 支持的模态类型
        self.supported_modalities = {'CT', 'MR', 'MRI', 'MG', 'US', 'RT', 'RTSTRUCT', 'RTPLAN', 'RTDOSE'}
    
    def scan_directory(self, root_path: Union[str, Path], 
                      recursive: bool = True,
                      max_depth: int = 10,
                      patient_filter: Optional[List[str]] = None,
                      modality_filter: Optional[List[str]] = None) -> BatchScanResult:
        """
        扫描目录寻找DICOM文件并分组
        
        Args:
            root_path: 根目录路径
            recursive: 是否递归扫描子目录
            max_depth: 最大递归深度
            patient_filter: 患者ID过滤列表
            modality_filter: 模态类型过滤列表
            
        Returns:
            扫描结果
        """
        root_path = Path(root_path)
        if not root_path.exists():
            raise DicomValidationError("path", f"扫描路径不存在: {root_path}")
        
        self.logger.info(f"开始扫描目录: {root_path}")
        result = BatchScanResult()
        
        # 扫描DICOM文件
        dicom_files = self._find_dicom_files(root_path, recursive, max_depth)
        result.total_dicom_files = len(dicom_files)
        
        if not dicom_files:
            self.logger.warning(f"在 {root_path} 中未找到DICOM文件")
            return result
        
        self.logger.info(f"找到 {len(dicom_files)} 个可能的DICOM文件")
        
        # 解析DICOM文件并分组
        series_dict = defaultdict(list)  # series_uid -> DicomSeries
        
        for dicom_file in dicom_files:
            try:
                series_info = self._parse_dicom_file(dicom_file)
                if not series_info:
                    continue
                
                # 应用过滤器
                if patient_filter and series_info.patient_id not in patient_filter:
                    continue
                if modality_filter and series_info.modality not in modality_filter:
                    continue
                
                series_dict[series_info.series_uid].append((dicom_file, series_info))
                result.valid_dicom_files += 1
                
            except Exception as e:
                error_msg = f"解析DICOM文件失败 {dicom_file}: {e}"
                result.scan_errors.append(error_msg)
                self.logger.error(error_msg)
        
        # 构建序列对象
        for series_uid, file_info_list in series_dict.items():
            if not file_info_list:
                continue
            
            # 使用第一个文件的信息作为序列信息
            first_file, first_info = file_info_list[0]
            series = DicomSeries(
                series_uid=series_uid,
                series_description=first_info.series_description,
                modality=first_info.modality,
                patient_id=first_info.patient_id,
                study_uid=first_info.study_uid,
                series_number=first_info.series_number,
                acquisition_date=first_info.acquisition_date,
                files=[file_path for file_path, _ in file_info_list]
            )
            
            # 按模态分组
            if series.modality not in result.series_by_modality:
                result.series_by_modality[series.modality] = []
            result.series_by_modality[series.modality].append(series)
            
            # 记录患者信息
            if series.patient_id not in result.patients:
                result.patients[series.patient_id] = {
                    'patient_id': series.patient_id,
                    'studies': set(),
                    'modalities': set(),
                    'series_count': 0
                }
            
            result.patients[series.patient_id]['studies'].add(series.study_uid)
            result.patients[series.patient_id]['modalities'].add(series.modality)
            result.patients[series.patient_id]['series_count'] += 1
        
        result.total_series = sum(len(series_list) for series_list in result.series_by_modality.values())
        
        # 转换set为list以便JSON序列化
        for patient_info in result.patients.values():
            patient_info['studies'] = list(patient_info['studies'])
            patient_info['modalities'] = list(patient_info['modalities'])
        
        self.logger.info(
            f"扫描完成: {result.valid_dicom_files} 个有效文件, "
            f"{result.total_series} 个序列, "
            f"{len(result.patients)} 个患者"
        )
        
        return result
    
    def generate_conversion_tasks(self, scan_result: BatchScanResult,
                                output_root: Union[str, Path],
                                naming_template: str = "{patient_id}/{study_date}/{series_name}",
                                selected_series: Optional[List[str]] = None,
                                conversion_params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        根据扫描结果生成转换任务
        
        Args:
            scan_result: 扫描结果
            output_root: 输出根目录
            naming_template: 命名模板
            selected_series: 选择的序列UID列表，None表示全部
            conversion_params: 转换参数
            
        Returns:
            任务信息列表
        """
        output_root = Path(output_root)
        output_root.mkdir(parents=True, exist_ok=True)
        
        tasks = []
        conversion_params = conversion_params or {}
        
        for modality, series_list in scan_result.series_by_modality.items():
            for series in series_list:
                # 检查是否选择了该序列
                if selected_series and series.series_uid not in selected_series:
                    continue
                
                try:
                    # 生成输出路径
                    output_path = self._generate_output_path(
                        series, output_root, naming_template
                    )
                    
                    # 创建临时目录存放该序列的DICOM文件
                    temp_input_dir = output_path.parent / f"temp_{series.series_uid[:8]}"
                    temp_input_dir.mkdir(parents=True, exist_ok=True)
                    
                    # 复制或链接DICOM文件到临时目录
                    # 这里为了简化，我们直接使用原始文件路径
                    # 在实际应用中，可能需要将同一序列的文件复制到同一目录
                    
                    if len(series.files) == 1:
                        input_path = series.files[0]
                    else:
                        # 多文件序列，使用第一个文件的目录
                        input_path = series.files[0].parent
                    
                    # 创建任务信息
                    task_info = {
                        'input_path': str(input_path),
                        'output_path': str(output_path),
                        'modality': modality,
                        'auto_detect': False,  # 已经知道模态类型
                        'conversion_params': conversion_params.copy(),
                        'priority': self._calculate_priority(series),
                        # 额外信息
                        'series_uid': series.series_uid,
                        'patient_id': series.patient_id,
                        'series_description': series.series_description,
                        'file_count': len(series.files)
                    }
                    
                    tasks.append(task_info)
                    
                except Exception as e:
                    self.logger.error(f"生成任务失败 {series.series_uid}: {e}")
        
        self.logger.info(f"生成了 {len(tasks)} 个转换任务")
        return tasks
    
    def submit_batch_conversion(self, tasks: List[Dict[str, Any]],
                              conversion_manager: Optional[ConversionManager] = None) -> List[str]:
        """
        提交批量转换任务
        
        Args:
            tasks: 任务信息列表
            conversion_manager: 转换管理器，None时使用默认实例
            
        Returns:
            任务ID列表
        """
        manager = conversion_manager or self.conversion_manager
        if not manager:
            raise ConversionError("manager", "未提供转换管理器")
        
        # 清理任务参数
        clean_tasks = []
        for task in tasks:
            clean_task = {
                'input_path': task['input_path'],
                'output_path': task['output_path'],
                'modality': task.get('modality'),
                'auto_detect': task.get('auto_detect', True),
                'conversion_params': task.get('conversion_params', {}),
                'priority': task.get('priority', 0)
            }
            clean_tasks.append(clean_task)
        
        task_ids = manager.add_batch_tasks(clean_tasks)
        
        self.logger.info(f"提交了 {len(task_ids)} 个批量转换任务")
        return task_ids
    
    def _find_dicom_files(self, root_path: Path, recursive: bool, max_depth: int) -> List[Path]:
        """寻找DICOM文件"""
        dicom_files = []
        
        def scan_directory(directory: Path, current_depth: int):
            if current_depth > max_depth:
                return
            
            try:
                for item in directory.iterdir():
                    if item.is_file():
                        # 检查文件扩展名
                        if (item.suffix.lower() in self.dicom_extensions or 
                            item.suffix == '' and self._is_likely_dicom(item)):
                            dicom_files.append(item)
                    elif item.is_dir() and recursive:
                        scan_directory(item, current_depth + 1)
            except PermissionError:
                self.logger.warning(f"无权限访问目录: {directory}")
            except Exception as e:
                self.logger.error(f"扫描目录时出错 {directory}: {e}")
        
        scan_directory(root_path, 0)
        return dicom_files
    
    def _is_likely_dicom(self, file_path: Path) -> bool:
        """判断文件是否可能是DICOM文件"""
        try:
            # 检查文件大小
            if file_path.stat().st_size < 128:
                return False
            
            # 检查DICOM魔术字节
            with open(file_path, 'rb') as f:
                f.seek(128)
                magic = f.read(4)
                return magic == b'DICM'
        except Exception:
            return False
    
    def _parse_dicom_file(self, file_path: Path) -> Optional[DicomSeries]:
        """解析DICOM文件信息"""
        try:
            ds = pydicom.dcmread(file_path, force=True, stop_before_pixels=True)
            
            # 检查必要的标签
            required_tags = ['SeriesInstanceUID', 'Modality', 'PatientID', 'StudyInstanceUID']
            for tag in required_tags:
                if not hasattr(ds, tag):
                    self.logger.debug(f"DICOM文件缺少必要标签 {tag}: {file_path}")
                    return None
            
            # 提取信息
            series_info = DicomSeries(
                series_uid=str(ds.SeriesInstanceUID),
                series_description=getattr(ds, 'SeriesDescription', '').strip(),
                modality=str(ds.Modality).upper(),
                patient_id=str(ds.PatientID),
                study_uid=str(ds.StudyInstanceUID),
                series_number=getattr(ds, 'SeriesNumber', None),
                acquisition_date=getattr(ds, 'AcquisitionDate', None) or getattr(ds, 'StudyDate', None)
            )
            
            # 检查模态是否支持
            if series_info.modality not in self.supported_modalities:
                self.logger.debug(f"不支持的模态类型 {series_info.modality}: {file_path}")
                return None
            
            return series_info
            
        except Exception as e:
            self.logger.debug(f"解析DICOM文件失败 {file_path}: {e}")
            return None
    
    def _generate_output_path(self, series: DicomSeries, output_root: Path, 
                            naming_template: str) -> Path:
        """生成输出路径"""
        # 准备模板变量
        template_vars = {
            'patient_id': self._sanitize_filename(series.patient_id),
            'study_uid': series.study_uid[:8],  # 缩短UID
            'series_uid': series.series_uid[:8],
            'series_name': self._sanitize_filename(series.series_name),
            'series_number': f"S{series.series_number:03d}" if series.series_number else "S000",
            'modality': series.modality,
            'study_date': series.acquisition_date or "unknown"
        }
        
        # 应用模板
        try:
            relative_path = naming_template.format(**template_vars)
        except KeyError as e:
            self.logger.warning(f"命名模板变量错误 {e}, 使用默认命名")
            relative_path = f"{template_vars['patient_id']}/{template_vars['series_name']}"
        
        # 添加.nii.gz扩展名
        output_path = output_root / relative_path
        if not output_path.suffix:
            output_path = output_path.with_suffix('.nii.gz')
        
        return output_path
    
    def _sanitize_filename(self, filename: str) -> str:
        """清理文件名，移除非法字符"""
        if not filename:
            return "unknown"
        
        # 替换非法字符
        sanitized = re.sub(r'[<>:"/\\|?*]', '_', filename)
        # 移除多余的空格和下划线
        sanitized = re.sub(r'[\s_]+', '_', sanitized)
        # 移除首尾的下划线
        sanitized = sanitized.strip('_')
        
        return sanitized or "unknown"
    
    def _calculate_priority(self, series: DicomSeries) -> int:
        """计算任务优先级"""
        priority = 0
        
        # CT和MRI优先级较高
        if series.modality in ['CT', 'MRI', 'MR']:
            priority += 10
        
        # 文件数量多的序列优先级较高
        priority += min(len(series.files) // 10, 5)
        
        return priority
    
    def get_conversion_progress(self, task_ids: List[str],
                              conversion_manager: Optional[ConversionManager] = None) -> Dict[str, Any]:
        """
        获取批量转换进度
        
        Args:
            task_ids: 任务ID列表
            conversion_manager: 转换管理器
            
        Returns:
            进度信息
        """
        manager = conversion_manager or self.conversion_manager
        if not manager:
            return {"error": "未提供转换管理器"}
        
        progress_info = {
            "total_tasks": len(task_ids),
            "completed": 0,
            "failed": 0,
            "running": 0,
            "pending": 0,
            "cancelled": 0,
            "overall_progress": 0.0,
            "task_details": {}
        }
        
        total_progress = 0.0
        
        for task_id in task_ids:
            task = manager.get_task_status(task_id)
            if task:
                status = task.status
                progress_info[status] = progress_info.get(status, 0) + 1
                progress_info["task_details"][task_id] = {
                    "status": status,
                    "progress": task.progress,
                    "error_message": task.error_message
                }
                total_progress += task.progress
            else:
                progress_info["pending"] += 1
                progress_info["task_details"][task_id] = {
                    "status": "unknown",
                    "progress": 0.0,
                    "error_message": None
                }
        
        if task_ids:
            progress_info["overall_progress"] = total_progress / len(task_ids)
        
        return progress_info 