#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文件名: ct_converter.py
功能描述: CT影像DICOM转换器
创建日期: 2025-01-23
作者: Claude AI Assistant
版本: v0.1.0-dev

基于legacy代码重构的CT影像专用转换器，支持单层和多层CT数据转换。
"""

import os
import glob
import numpy as np
import nibabel as nib
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import pydicom
from pydicom.errors import InvalidDicomError

from .base import BaseDICOMConverter, ConversionResult
from ..exceptions import DicomReadError, DicomValidationError, ConversionError, ProcessingError
from ...config.settings import ConversionSettings


class CTConverter(BaseDICOMConverter):
    """CT影像转换器"""
    
    def __init__(self, input_path: Path, output_path: Path, 
                 config: Optional[ConversionSettings] = None):
        """
        初始化CT转换器
        
        Args:
            input_path: 输入DICOM文件或目录路径
            output_path: 输出NIfTI文件路径
            config: 转换配置
        """
        super().__init__(input_path, output_path, config)
        self.modality = "CT"
        
        # CT特定参数
        self.window_center = None
        self.window_width = None
        self.rescale_slope = 1.0
        self.rescale_intercept = 0.0
    
    def get_supported_modalities(self) -> List[str]:
        """获取支持的模态"""
        return ["CT", "CBCT"]
    
    def discover_files(self) -> List[Path]:
        """
        发现CT DICOM文件
        
        Returns:
            DICOM文件路径列表，按实例号排序
        """
        dicom_files = []
        
        try:
            if self.input_path.is_file():
                # 单个文件
                if self._is_dicom_file(self.input_path):
                    dicom_files.append(self.input_path)
            else:
                # 目录搜索
                dicom_files = self._find_dicom_files_in_directory(self.input_path)
            
            if not dicom_files:
                raise ConversionError(self.__class__.__name__, 
                                    f"在路径 {self.input_path} 中未找到DICOM文件")
            
            # 按实例号排序
            sorted_files = self._sort_by_instance_number(dicom_files)
            
            self.logger.info(f"发现 {len(sorted_files)} 个CT DICOM文件")
            return sorted_files
            
        except Exception as e:
            raise ConversionError(self.__class__.__name__, 
                                f"文件发现失败: {str(e)}")
    
    def _find_dicom_files_in_directory(self, directory: Path) -> List[Path]:
        """在目录中查找DICOM文件"""
        dicom_files = []
        
        # 搜索模式
        search_patterns = [
            "*.dcm", "*.DCM", 
            "*CT*", "*ct*",
            "[0-9]*-[0-9]*",  # 数字模式文件
        ]
        
        for pattern in search_patterns:
            for file_path in directory.glob(pattern):
                if file_path.is_file() and self._is_dicom_file(file_path):
                    dicom_files.append(file_path)
        
        # 递归搜索子目录（仅一层）
        for subdir in directory.iterdir():
            if subdir.is_dir():
                for pattern in search_patterns:
                    for file_path in subdir.glob(pattern):
                        if file_path.is_file() and self._is_dicom_file(file_path):
                            dicom_files.append(file_path)
        
        # 去重
        return list(set(dicom_files))
    
    def _is_dicom_file(self, file_path: Path) -> bool:
        """检查文件是否为DICOM文件"""
        try:
            # 快速检查：只读取元数据，不读取像素数据
            ds = pydicom.dcmread(str(file_path), stop_before_pixels=True)
            
            # 检查是否为CT影像
            if hasattr(ds, 'Modality'):
                return ds.Modality in ['CT', 'CBCT']
            
            # 如果没有模态信息，检查其他特征
            return hasattr(ds, 'PixelData') or hasattr(ds, 'pixel_array')
            
        except (InvalidDicomError, Exception):
            return False
    
    def _sort_by_instance_number(self, files: List[Path]) -> List[Path]:
        """按实例号排序文件"""
        file_instance_pairs = []
        
        for file_path in files:
            try:
                ds = pydicom.dcmread(str(file_path), stop_before_pixels=True)
                instance_number = getattr(ds, 'InstanceNumber', 0)
                file_instance_pairs.append((file_path, int(instance_number)))
            except Exception:
                # 如果无法读取实例号，使用文件名中的数字
                import re
                numbers = re.findall(r'\d+', file_path.name)
                instance_number = int(numbers[-1]) if numbers else 0
                file_instance_pairs.append((file_path, instance_number))
        
        # 按实例号排序
        file_instance_pairs.sort(key=lambda x: x[1])
        return [pair[0] for pair in file_instance_pairs]
    
    def validate_dicom_files(self, files: List[Path]) -> bool:
        """
        验证DICOM文件
        
        Args:
            files: DICOM文件路径列表
            
        Returns:
            验证是否通过
        """
        try:
            if not files:
                raise DicomValidationError("empty_file_list", "文件列表为空")
            
            # 读取第一个文件作为参考
            ref_ds = pydicom.dcmread(str(files[0]), stop_before_pixels=True)
            
            # 检查基本DICOM属性
            required_attrs = ['Rows', 'Columns', 'PixelSpacing']
            for attr in required_attrs:
                if not hasattr(ref_ds, attr):
                    raise DicomValidationError("missing_attribute", 
                                             f"缺少必需属性: {attr}")
            
            # 检查模态
            if hasattr(ref_ds, 'Modality') and ref_ds.Modality not in self.get_supported_modalities():
                raise DicomValidationError("unsupported_modality", 
                                         f"不支持的模态: {ref_ds.Modality}")
            
            # 检查系列一致性（针对多文件）
            if len(files) > 1:
                if not self._validate_series_consistency(files, ref_ds):
                    raise DicomValidationError("series_inconsistency", 
                                             "系列文件不一致")
            
            self.logger.info(f"DICOM文件验证通过: {len(files)} 个文件")
            return True
            
        except DicomValidationError:
            raise
        except Exception as e:
            raise DicomValidationError("validation_error", f"验证过程出错: {str(e)}")
    
    def _validate_series_consistency(self, files: List[Path], ref_ds) -> bool:
        """验证系列文件一致性"""
        try:
            ref_rows = ref_ds.Rows
            ref_columns = ref_ds.Columns
            ref_pixel_spacing = ref_ds.PixelSpacing
            
            for file_path in files[1:]:  # 跳过第一个文件（参考文件）
                ds = pydicom.dcmread(str(file_path), stop_before_pixels=True)
                
                # 检查图像尺寸
                if ds.Rows != ref_rows or ds.Columns != ref_columns:
                    return False
                
                # 检查像素间距
                if hasattr(ds, 'PixelSpacing'):
                    if abs(ds.PixelSpacing[0] - ref_pixel_spacing[0]) > 1e-6 or \
                       abs(ds.PixelSpacing[1] - ref_pixel_spacing[1]) > 1e-6:
                        return False
            
            return True
            
        except Exception:
            return False
    
    def extract_metadata(self, files: List[Path]) -> Dict[str, Any]:
        """
        提取CT元数据
        
        Args:
            files: DICOM文件路径列表
            
        Returns:
            元数据字典
        """
        try:
            # 读取第一个文件作为参考
            ref_ds = pydicom.dcmread(str(files[0]), stop_before_pixels=True)
            
            # 基本图像信息
            metadata = {
                'modality': getattr(ref_ds, 'Modality', 'CT'),
                'rows': ref_ds.Rows,
                'columns': ref_ds.Columns,
                'number_of_slices': len(files),
                'pixel_spacing': list(ref_ds.PixelSpacing) if hasattr(ref_ds, 'PixelSpacing') else [1.0, 1.0],
                'slice_thickness': getattr(ref_ds, 'SliceThickness', 1.0),
                'patient_position': getattr(ref_ds, 'PatientPosition', ''),
                'image_orientation': list(getattr(ref_ds, 'ImageOrientationPatient', [1, 0, 0, 0, 1, 0])),
            }
            
            # CT特定信息
            self.rescale_slope = float(getattr(ref_ds, 'RescaleSlope', 1.0))
            self.rescale_intercept = float(getattr(ref_ds, 'RescaleIntercept', 0.0))
            
            metadata['rescale_slope'] = self.rescale_slope
            metadata['rescale_intercept'] = self.rescale_intercept
            
            # 窗宽窗位
            self.window_center = getattr(ref_ds, 'WindowCenter', None)
            self.window_width = getattr(ref_ds, 'WindowWidth', None)
            
            if self.window_center is not None:
                metadata['window_center'] = float(self.window_center)
            if self.window_width is not None:
                metadata['window_width'] = float(self.window_width)
            
            # 设备信息
            metadata['manufacturer'] = getattr(ref_ds, 'Manufacturer', '').strip()
            metadata['model_name'] = getattr(ref_ds, 'ManufacturerModelName', '').strip()
            
            # 扫描参数
            metadata['kvp'] = getattr(ref_ds, 'KVP', None)
            metadata['tube_current'] = getattr(ref_ds, 'XRayTubeCurrent', None)
            
            self.logger.info(f"提取元数据完成: {metadata['rows']}x{metadata['columns']}x{metadata['number_of_slices']}")
            return metadata
            
        except Exception as e:
            raise ProcessingError("metadata_extraction", f"元数据提取失败: {str(e)}")
    
    def process_image_data(self, files: List[Path]) -> np.ndarray:
        """
        处理CT图像数据
        
        Args:
            files: DICOM文件路径列表
            
        Returns:
            处理后的3D图像数组
        """
        try:
            image_arrays = []
            
            for i, file_path in enumerate(files):
                # 报告进度
                progress = 0.6 + 0.2 * (i / len(files))
                self._report_progress("处理图像数据", progress, str(file_path.name))
                
                # 读取DICOM文件
                ds = pydicom.dcmread(str(file_path))
                
                # 获取像素数组
                pixel_array = ds.pixel_array.astype(np.float32)
                
                # 应用Rescale
                if self.config.apply_rescale:
                    pixel_array = pixel_array * self.rescale_slope + self.rescale_intercept
                
                image_arrays.append(pixel_array)
            
            # 堆叠为3D数组
            image_3d = np.stack(image_arrays, axis=0)
            
            # 应用预处理
            if self.config.normalize_orientation:
                image_3d = self._normalize_orientation(image_3d)
            
            self.logger.info(f"图像数据处理完成: {image_3d.shape}, 数据类型: {image_3d.dtype}")
            return image_3d
            
        except Exception as e:
            raise ProcessingError("image_processing", f"图像数据处理失败: {str(e)}")
    
    def _normalize_orientation(self, image_3d: np.ndarray) -> np.ndarray:
        """标准化图像方向"""
        # 根据配置的方向标准进行调整
        # 这里实现基本的方向标准化
        if self.config.orientation == "LPS":
            # 应用必要的翻转和旋转
            pass
        
        return image_3d
    
    def save_nifti(self, image_data: np.ndarray, metadata: Dict[str, Any]) -> bool:
        """
        保存为NIfTI格式
        
        Args:
            image_data: 图像数据
            metadata: 元数据
            
        Returns:
            是否保存成功
        """
        try:
            # 构建仿射变换矩阵
            affine = self._build_affine_matrix(metadata)
            
            # 转换数据类型
            if self.config.data_type == "int16":
                image_data = image_data.astype(np.int16)
            elif self.config.data_type == "float32":
                image_data = image_data.astype(np.float32)
            
            # 创建NIfTI图像
            nifti_img = nib.Nifti1Image(image_data, affine)
            
            # 设置NIfTI头信息
            header = nifti_img.header
            header.set_xyzt_units('mm', 'sec')
            
            # 添加描述
            description = f"CT converted from DICOM - {metadata.get('manufacturer', 'Unknown')}"
            header['descrip'] = description.encode('utf-8')[:79]  # NIfTI限制79字符
            
            # 保存文件
            if self.config.output_format == "nii.gz":
                # 确保输出文件名以.nii.gz结尾
                if not str(self.output_path).endswith('.nii.gz'):
                    self.output_path = self.output_path.with_suffix('.nii.gz')
            else:
                # 确保输出文件名以.nii结尾
                if not str(self.output_path).endswith('.nii'):
                    self.output_path = self.output_path.with_suffix('.nii')
            
            nib.save(nifti_img, str(self.output_path))
            
            self.logger.info(f"NIfTI文件保存成功: {self.output_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"NIfTI文件保存失败: {str(e)}")
            return False
    
    def _build_affine_matrix(self, metadata: Dict[str, Any]) -> np.ndarray:
        """构建仿射变换矩阵"""
        # 基本的仿射矩阵构建
        affine = np.eye(4)
        
        # 设置像素间距
        pixel_spacing = metadata.get('pixel_spacing', [1.0, 1.0])
        slice_thickness = metadata.get('slice_thickness', 1.0)
        
        affine[0, 0] = pixel_spacing[0]
        affine[1, 1] = pixel_spacing[1]  
        affine[2, 2] = slice_thickness
        
        return affine
    
    def estimate_processing_time(self) -> Optional[float]:
        """估算处理时间"""
        if not self._dicom_files:
            return None
        
        # 基于文件数量的简单估算
        base_time_per_file = 0.1  # 秒
        return len(self._dicom_files) * base_time_per_file
    
    def estimate_memory_usage(self) -> Optional[float]:
        """估算内存使用量"""
        if not self._dicom_files:
            return None
        
        try:
            # 读取第一个文件估算内存使用
            ds = pydicom.dcmread(str(self._dicom_files[0]), stop_before_pixels=True)
            
            # 计算单个切片的内存使用（假设16位）
            bytes_per_slice = ds.Rows * ds.Columns * 2  # 2字节每像素
            total_bytes = bytes_per_slice * len(self._dicom_files)
            
            # 转换为GB，考虑处理过程中的临时内存使用（乘以3）
            return (total_bytes * 3) / (1024 ** 3)
            
        except Exception:
            return None 