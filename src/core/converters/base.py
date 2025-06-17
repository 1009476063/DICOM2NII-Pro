#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文件名: base.py
功能描述: DICOM转换器抽象基类
创建日期: 2025-01-23
作者: Claude AI Assistant
版本: v0.1.0-dev

定义了所有DICOM转换器必须实现的接口和通用功能。
"""

import os
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Dict, Any, Optional, Union, Tuple
from dataclasses import dataclass
from datetime import datetime

from ..exceptions import (
    DicomReadError, DicomValidationError, 
    ConversionError, ProcessingError, FileSystemError
)
from ...config.settings import ConversionSettings, settings


@dataclass
class ConversionResult:
    """转换结果数据类"""
    
    success: bool
    input_path: Path
    output_path: Optional[Path] = None
    error_message: Optional[str] = None
    error_code: Optional[str] = None
    processing_time: Optional[float] = None
    file_count: int = 0
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class ProgressInfo:
    """进度信息数据类"""
    
    current_step: str
    progress: float  # 0.0 to 1.0
    total_files: int
    processed_files: int
    current_file: Optional[str] = None
    estimated_time_remaining: Optional[float] = None


class BaseDICOMConverter(ABC):
    """DICOM转换器抽象基类"""
    
    def __init__(self, input_path: Union[str, Path], 
                 output_path: Union[str, Path],
                 config: Optional[ConversionSettings] = None):
        """
        初始化转换器
        
        Args:
            input_path: 输入文件或目录路径
            output_path: 输出文件路径
            config: 转换配置，如果为None则使用默认配置
        """
        self.input_path = Path(input_path)
        self.output_path = Path(output_path)
        self.config = config or settings.conversion
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # 进度回调函数
        self.progress_callback = None
        
        # 转换过程中的数据
        self._dicom_files: List[Path] = []
        self._metadata: Dict[str, Any] = {}
        self._start_time: Optional[datetime] = None
        
        # 验证路径
        self._validate_paths()
    
    def _validate_paths(self) -> None:
        """验证输入输出路径"""
        if not self.input_path.exists():
            raise FileSystemError(
                "read", str(self.input_path), 
                f"输入路径不存在: {self.input_path}"
            )
        
        # 确保输出目录存在
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 检查输出路径的写权限
        if not os.access(self.output_path.parent, os.W_OK):
            raise FileSystemError(
                "write", str(self.output_path.parent),
                f"输出目录无写权限: {self.output_path.parent}"
            )
    
    def set_progress_callback(self, callback) -> None:
        """
        设置进度回调函数
        
        Args:
            callback: 进度回调函数，接收ProgressInfo参数
        """
        self.progress_callback = callback
    
    def _report_progress(self, step: str, progress: float, 
                        current_file: Optional[str] = None) -> None:
        """报告进度"""
        if self.progress_callback:
            progress_info = ProgressInfo(
                current_step=step,
                progress=progress,
                total_files=len(self._dicom_files),
                processed_files=int(progress * len(self._dicom_files)),
                current_file=current_file
            )
            self.progress_callback(progress_info)
    
    @abstractmethod
    def discover_files(self) -> List[Path]:
        """
        发现和收集DICOM文件
        
        Returns:
            DICOM文件路径列表
        """
        pass
    
    @abstractmethod
    def validate_dicom_files(self, files: List[Path]) -> bool:
        """
        验证DICOM文件
        
        Args:
            files: DICOM文件路径列表
            
        Returns:
            验证是否通过
        """
        pass
    
    @abstractmethod
    def extract_metadata(self, files: List[Path]) -> Dict[str, Any]:
        """
        提取DICOM元数据
        
        Args:
            files: DICOM文件路径列表
            
        Returns:
            元数据字典
        """
        pass
    
    @abstractmethod
    def process_image_data(self, files: List[Path]) -> Any:
        """
        处理图像数据
        
        Args:
            files: DICOM文件路径列表
            
        Returns:
            处理后的图像数据
        """
        pass
    
    @abstractmethod
    def save_nifti(self, image_data: Any, metadata: Dict[str, Any]) -> bool:
        """
        保存为NIfTI格式
        
        Args:
            image_data: 图像数据
            metadata: 元数据
            
        Returns:
            是否保存成功
        """
        pass
    
    def convert(self) -> ConversionResult:
        """
        执行转换过程
        
        Returns:
            转换结果
        """
        self._start_time = datetime.now()
        
        try:
            self.logger.info(f"开始转换: {self.input_path} -> {self.output_path}")
            
            # 1. 发现文件
            self._report_progress("发现DICOM文件", 0.0)
            self._dicom_files = self.discover_files()
            
            if not self._dicom_files:
                raise ConversionError(
                    self.__class__.__name__, 
                    "未找到有效的DICOM文件"
                )
            
            self.logger.info(f"发现 {len(self._dicom_files)} 个DICOM文件")
            
            # 2. 验证文件
            if self.config.validate_dicom:
                self._report_progress("验证DICOM文件", 0.2)
                if not self.validate_dicom_files(self._dicom_files):
                    raise DicomValidationError(
                        "file_validation", 
                        "DICOM文件验证失败"
                    )
            
            # 3. 提取元数据
            self._report_progress("提取元数据", 0.4)
            self._metadata = self.extract_metadata(self._dicom_files)
            
            # 4. 处理图像数据
            self._report_progress("处理图像数据", 0.6)
            image_data = self.process_image_data(self._dicom_files)
            
            # 5. 保存NIfTI文件
            self._report_progress("保存NIfTI文件", 0.8)
            if not self.save_nifti(image_data, self._metadata):
                raise ConversionError(
                    self.__class__.__name__, 
                    "NIfTI文件保存失败"
                )
            
            # 6. 验证输出
            if self.config.verify_output:
                self._report_progress("验证输出文件", 0.9)
                if not self._verify_output():
                    raise ConversionError(
                        self.__class__.__name__, 
                        "输出文件验证失败"
                    )
            
            self._report_progress("转换完成", 1.0)
            
            # 计算处理时间
            processing_time = (datetime.now() - self._start_time).total_seconds()
            
            self.logger.info(f"转换成功完成，耗时: {processing_time:.2f}秒")
            
            return ConversionResult(
                success=True,
                input_path=self.input_path,
                output_path=self.output_path,
                processing_time=processing_time,
                file_count=len(self._dicom_files),
                metadata=self._metadata
            )
            
        except Exception as e:
            processing_time = None
            if self._start_time:
                processing_time = (datetime.now() - self._start_time).total_seconds()
            
            error_code = getattr(e, 'error_code', 'UNKNOWN')
            error_message = str(e)
            
            self.logger.error(f"转换失败: {error_message}")
            
            return ConversionResult(
                success=False,
                input_path=self.input_path,
                output_path=None,
                error_message=error_message,
                error_code=error_code,
                processing_time=processing_time,
                file_count=len(self._dicom_files),
                metadata=self._metadata
            )
    
    def _verify_output(self) -> bool:
        """验证输出文件"""
        try:
            if not self.output_path.exists():
                return False
            
            # 检查文件大小
            if self.output_path.stat().st_size == 0:
                return False
            
            # 如果是NIfTI文件，可以尝试加载验证
            if self.output_path.suffix in ['.nii', '.gz']:
                try:
                    import nibabel as nib
                    nib.load(str(self.output_path))
                    return True
                except Exception:
                    return False
            
            return True
            
        except Exception:
            return False
    
    def get_supported_modalities(self) -> List[str]:
        """
        获取支持的模态列表
        
        Returns:
            支持的模态列表
        """
        return []
    
    def estimate_processing_time(self) -> Optional[float]:
        """
        估算处理时间
        
        Returns:
            预估处理时间（秒），如果无法估算则返回None
        """
        return None
    
    def estimate_memory_usage(self) -> Optional[float]:
        """
        估算内存使用量
        
        Returns:
            预估内存使用量（GB），如果无法估算则返回None
        """
        return None
    
    def cleanup(self) -> None:
        """清理临时文件和资源"""
        pass
    
    def __enter__(self):
        """上下文管理器入口"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.cleanup() 