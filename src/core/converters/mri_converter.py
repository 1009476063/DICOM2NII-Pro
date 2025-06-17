"""
MRI DICOM to NIfTI Converter

专门用于处理MRI DICOM文件的转换器，支持多种MRI序列类型的转换
包括DCE、DWI、ADC等序列的特定处理方式
"""

import os
import logging
import numpy as np
import pydicom
import nibabel as nib
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass

from ..exceptions import ConversionError, DicomValidationError
from .base import BaseDICOMConverter


@dataclass
class MRISequenceInfo:
    """MRI序列信息"""
    modality: str
    sequence_name: str
    orientation_correction: str
    requires_3d: bool = True
    special_processing: bool = False


class MRIConverter(BaseDICOMConverter):
    """
    MRI DICOM转换器
    
    专门处理MRI DICOM文件的转换，支持：
    - DCE (Dynamic Contrast Enhanced) 序列
    - DWI (Diffusion Weighted Imaging) 序列  
    - ADC (Apparent Diffusion Coefficient) 序列
    - T1、T2等常规MRI序列
    - 自动识别序列类型
    - 图像方向修正
    """
    
    def __init__(self, progress_callback=None):
        super().__init__(progress_callback)
        self.logger = logging.getLogger(__name__)
        
        # MRI序列类型定义
        self.sequence_types = {
            'DCE': MRISequenceInfo('DCE', 'Dynamic Contrast Enhanced', 'dce_correction'),
            'DWI': MRISequenceInfo('DWI', 'Diffusion Weighted Imaging', 'dce_correction'),
            'ADC': MRISequenceInfo('ADC', 'Apparent Diffusion Coefficient', 'dce_correction'),
            'T1': MRISequenceInfo('T1', 'T1 Weighted', 'standard_correction'),
            'T2': MRISequenceInfo('T2', 'T2 Weighted', 'standard_correction'),
            'FLAIR': MRISequenceInfo('FLAIR', 'Fluid Attenuated Inversion Recovery', 'standard_correction'),
        }
    
    def detect_sequence_type(self, dicom_path: str, first_dicom: pydicom.Dataset) -> str:
        """
        检测MRI序列类型
        
        Args:
            dicom_path: DICOM文件路径
            first_dicom: 第一个DICOM文件
            
        Returns:
            检测到的序列类型
        """
        try:
            # 从路径中检测
            path_upper = str(dicom_path).upper()
            for seq_type in self.sequence_types.keys():
                if seq_type in path_upper:
                    return seq_type
            
            # 从DICOM标签中检测
            sequence_fields = [
                'SeriesDescription', 'SequenceName', 'StudyDescription', 
                'ProtocolName', 'ImageComments'
            ]
            
            for field in sequence_fields:
                if hasattr(first_dicom, field):
                    value = str(getattr(first_dicom, field)).upper()
                    for seq_type in self.sequence_types.keys():
                        if seq_type in value:
                            return seq_type
                    
                    # 特殊关键词匹配
                    if 'DYNAMIC' in value or 'CONTRAST' in value:
                        return 'DCE'
                    elif 'DIFFUSION' in value or 'DWI' in value:
                        return 'DWI'
                    elif 'ADC' in value or 'APPARENT' in value:
                        return 'ADC'
                    elif 'FLAIR' in value:
                        return 'FLAIR'
                    elif 'T1' in value:
                        return 'T1'
                    elif 'T2' in value:
                        return 'T2'
            
            # 默认类型
            self.logger.warning(f"无法确定序列类型，使用默认: {dicom_path}")
            return 'T1'
            
        except Exception as e:
            self.logger.error(f"检测序列类型失败: {e}")
            return 'T1'
    
    def correct_image_orientation(self, img_array: np.ndarray, sequence_type: str) -> np.ndarray:
        """
        根据MRI序列类型修正图像方向
        
        Args:
            img_array: 原始图像数组
            sequence_type: 序列类型
            
        Returns:
            修正后的图像数组
        """
        try:
            sequence_info = self.sequence_types.get(sequence_type)
            if not sequence_info:
                return img_array
            
            if sequence_info.orientation_correction == 'dce_correction':
                # DCE/DWI/ADC序列的方向修正
                # 1. 顺时针旋转90度
                if img_array.ndim == 3:
                    # 对3D数组的每个切片进行处理
                    corrected = np.zeros_like(img_array)
                    for i in range(img_array.shape[2]):
                        slice_img = np.rot90(img_array[:, :, i], k=1)
                        corrected[:, :, i] = np.fliplr(slice_img)
                else:
                    # 2D图像
                    rotated = np.rot90(img_array, k=1)
                    corrected = np.fliplr(rotated)
                
                return corrected
            
            else:
                # 标准序列暂不进行方向修正
                return img_array
                
        except Exception as e:
            self.logger.error(f"图像方向修正失败: {e}")
            return img_array
    
    def build_3d_volume(self, dicom_files: List[str]) -> Tuple[np.ndarray, pydicom.Dataset]:
        """
        构建3D图像卷
        
        Args:
            dicom_files: DICOM文件列表
            
        Returns:
            (3D图像数组, 参考DICOM数据集)
        """
        try:
            # 按切片位置排序
            sorted_files = self.sort_dicom_files(dicom_files)
            
            # 读取第一个文件获取基本信息
            ref_dicom = pydicom.dcmread(sorted_files[0])
            
            # 创建3D数组
            img_shape = list(ref_dicom.pixel_array.shape)
            img_shape.append(len(sorted_files))
            img3d = np.zeros(img_shape, dtype=ref_dicom.pixel_array.dtype)
            
            # 读取所有切片
            for i, dicom_file in enumerate(sorted_files):
                ds = pydicom.dcmread(dicom_file)
                img_data = ds.pixel_array
                
                # 应用rescale如果存在
                if hasattr(ds, 'RescaleSlope') and hasattr(ds, 'RescaleIntercept'):
                    slope = float(ds.RescaleSlope)
                    intercept = float(ds.RescaleIntercept)
                    if slope != 1.0 or intercept != 0.0:
                        img_data = img_data * slope + intercept
                
                img3d[:, :, i] = img_data
            
            return img3d, ref_dicom
            
        except Exception as e:
            raise ConversionError(f"构建3D图像卷失败: {e}")
    
    def create_affine_matrix(self, dicom_dataset: pydicom.Dataset) -> np.ndarray:
        """
        为MRI图像创建仿射变换矩阵
        
        Args:
            dicom_dataset: DICOM数据集
            
        Returns:
            4x4仿射变换矩阵
        """
        try:
            # 获取体素间距
            if hasattr(dicom_dataset, 'PixelSpacing'):
                pixel_spacing = dicom_dataset.PixelSpacing
                voxel_size = [float(pixel_spacing[0]), float(pixel_spacing[1])]
            else:
                voxel_size = [1.0, 1.0]
            
            # 获取切片厚度
            if hasattr(dicom_dataset, 'SliceThickness'):
                slice_thickness = float(dicom_dataset.SliceThickness)
            elif hasattr(dicom_dataset, 'SpacingBetweenSlices'):
                slice_thickness = float(dicom_dataset.SpacingBetweenSlices)
            else:
                slice_thickness = 1.0
            
            voxel_size.append(slice_thickness)
            
            # 创建仿射矩阵
            affine = np.eye(4)
            affine[0, 0] = voxel_size[0]
            affine[1, 1] = voxel_size[1]
            affine[2, 2] = voxel_size[2]
            
            # 如果有图像方向信息，可以进一步完善
            if hasattr(dicom_dataset, 'ImageOrientationPatient'):
                orientation = dicom_dataset.ImageOrientationPatient
                if len(orientation) == 6:
                    # 构建方向矩阵（简化版本）
                    row_cosines = np.array(orientation[:3])
                    col_cosines = np.array(orientation[3:])
                    
                    affine[0, :3] = row_cosines * voxel_size[0]
                    affine[1, :3] = col_cosines * voxel_size[1]
            
            return affine
            
        except Exception as e:
            self.logger.warning(f"创建仿射矩阵失败，使用默认: {e}")
            return np.eye(4)
    
    def convert_to_nifti(self, input_path: str, output_path: str, 
                        conversion_params: Optional[Dict[str, Any]] = None) -> bool:
        """
        转换MRI DICOM到NIfTI格式
        
        Args:
            input_path: 输入路径（文件或目录）
            output_path: 输出NIfTI文件路径
            conversion_params: 转换参数
            
        Returns:
            转换是否成功
        """
        try:
            self.progress_callback(0, "开始MRI转换...")
            
            # 发现DICOM文件
            dicom_files = self.discover_dicom_files(input_path)
            if not dicom_files:
                raise DicomValidationError(f"未找到DICOM文件: {input_path}")
            
            self.progress_callback(20, f"发现 {len(dicom_files)} 个DICOM文件")
            
            # 验证DICOM文件
            valid_files = []
            for i, file_path in enumerate(dicom_files):
                if self.validate_dicom_file(file_path):
                    valid_files.append(file_path)
                
                # 更新进度
                progress = 20 + (i / len(dicom_files)) * 20
                self.progress_callback(progress, f"验证文件 {i+1}/{len(dicom_files)}")
            
            if not valid_files:
                raise DicomValidationError("没有有效的DICOM文件")
            
            self.progress_callback(40, f"验证通过 {len(valid_files)} 个文件")
            
            # 检测序列类型
            first_dicom = pydicom.dcmread(valid_files[0])
            sequence_type = self.detect_sequence_type(input_path, first_dicom)
            self.progress_callback(50, f"检测到序列类型: {sequence_type}")
            
            # 构建图像数据
            if len(valid_files) == 1:
                # 单文件转换
                img_array = first_dicom.pixel_array
                ref_dicom = first_dicom
            else:
                # 多文件3D卷转换
                img_array, ref_dicom = self.build_3d_volume(valid_files)
            
            self.progress_callback(70, "构建图像数据完成")
            
            # 方向修正
            corrected_img = self.correct_image_orientation(img_array, sequence_type)
            self.progress_callback(80, "图像方向修正完成")
            
            # 创建仿射矩阵
            affine_matrix = self.create_affine_matrix(ref_dicom)
            
            # 创建NIfTI图像
            nii_img = nib.Nifti1Image(corrected_img, affine_matrix)
            
            # 保存文件
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            nib.save(nii_img, output_path)
            
            self.progress_callback(100, f"MRI转换完成: {output_path}")
            self.logger.info(f"成功转换MRI: {input_path} -> {output_path}")
            
            return True
            
        except Exception as e:
            error_msg = f"MRI转换失败: {str(e)}"
            self.logger.error(error_msg)
            self.progress_callback(-1, error_msg)
            return False
    
    def get_conversion_info(self, input_path: str) -> Dict[str, Any]:
        """
        获取MRI转换信息
        
        Args:
            input_path: 输入路径
            
        Returns:
            转换信息字典
        """
        try:
            dicom_files = self.discover_dicom_files(input_path)
            if not dicom_files:
                return {"error": "未找到DICOM文件"}
            
            first_dicom = pydicom.dcmread(dicom_files[0])
            sequence_type = self.detect_sequence_type(input_path, first_dicom)
            
            info = {
                "modality": "MRI",
                "sequence_type": sequence_type,
                "files_count": len(dicom_files),
                "is_3d": len(dicom_files) > 1,
                "patient_id": getattr(first_dicom, 'PatientID', 'Unknown'),
                "study_date": getattr(first_dicom, 'StudyDate', 'Unknown'),
                "series_description": getattr(first_dicom, 'SeriesDescription', 'Unknown'),
            }
            
            # 图像信息
            if hasattr(first_dicom, 'pixel_array'):
                img_shape = first_dicom.pixel_array.shape
                info["image_size"] = f"{img_shape[1]}x{img_shape[0]}"
                
                if len(dicom_files) > 1:
                    info["volume_size"] = f"{img_shape[1]}x{img_shape[0]}x{len(dicom_files)}"
            
            return info
            
        except Exception as e:
            return {"error": f"获取转换信息失败: {e}"} 