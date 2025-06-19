"""
Mammography DICOM to NIfTI Converter

专门用于处理乳腺摄影(MG) DICOM文件的转换器
支持不同体位的乳腺X光图像转换和处理
"""

import os
import logging
import numpy as np
import pydicom
import nibabel as nib
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
import SimpleITK as sitk
from ...utils.image_processing import correct_image_orientation, remove_edge_artifacts

from ..exceptions import ConversionError, DicomValidationError
from .base import BaseDICOMConverter


@dataclass
class MammographyViewInfo:
    """乳腺摄影视图信息"""
    view_position: str
    laterality: str
    full_position: str
    orientation_correction: str


class MammographyConverter(BaseDICOMConverter):
    """
    乳腺摄影DICOM转换器
    
    专门处理乳腺摄影DICOM文件的转换，支持：
    - MLO (Mediolateral Oblique) 内外斜位
    - CC (Craniocaudal) 头足位
    - 左右乳房识别 (L/R)
    - 自动方位检测
    - 敏感信息移除
    - 图像方向修正
    """
    
    def __init__(self, progress_callback=None):
        super().__init__(progress_callback)
        self.logger = logging.getLogger(__name__)
        
        # 乳腺摄影视图类型定义
        self.view_positions = {
            'LMLO': MammographyViewInfo('MLO', 'L', 'LMLO', 'mg_correction'),
            'RMLO': MammographyViewInfo('MLO', 'R', 'RMLO', 'mg_correction'),
            'LCC': MammographyViewInfo('CC', 'L', 'LCC', 'mg_correction'),
            'RCC': MammographyViewInfo('CC', 'R', 'RCC', 'mg_correction'),
        }
    
    def get_mg_view_position(self, dicom_dataset: pydicom.Dataset) -> str:
        """
        从DICOM文件中获取乳腺摄影图像的方位信息
        
        Args:
            dicom_dataset: DICOM数据集
            
        Returns:
            检测到的视图位置（LMLO/RMLO/LCC/RCC）
        """
        try:
            # 从标准DICOM标签获取
            view_position = ''
            laterality = ''
            
            if hasattr(dicom_dataset, 'ViewPosition'):
                view_position = str(dicom_dataset.ViewPosition).upper()
            
            if hasattr(dicom_dataset, 'ImageLaterality'):
                laterality = str(dicom_dataset.ImageLaterality).upper()
            elif hasattr(dicom_dataset, 'Laterality'):
                laterality = str(dicom_dataset.Laterality).upper()
            
            # 组合方位信息
            if laterality and view_position:
                if laterality == 'L':
                    if 'MLO' in view_position:
                        return 'LMLO'
                    elif 'CC' in view_position:
                        return 'LCC'
                elif laterality == 'R':
                    if 'MLO' in view_position:
                        return 'RMLO'
                    elif 'CC' in view_position:
                        return 'RCC'
            
            # 如果无法从标准字段获取，尝试从其他字段获取
            search_fields = [
                'SeriesDescription', 'StudyDescription', 'ImageComments',
                'ProtocolName', 'SeriesNumber', 'AcquisitionNumber'
            ]
            
            for field in search_fields:
                if hasattr(dicom_dataset, field):
                    desc = str(getattr(dicom_dataset, field)).upper()
                    # 直接匹配完整位置
                    for position in self.view_positions.keys():
                        if position in desc:
                            return position
                    
                    # 分别匹配侧别和体位
                    has_left = any(x in desc for x in ['L', 'LEFT', '左'])
                    has_right = any(x in desc for x in ['R', 'RIGHT', '右'])
                    has_mlo = any(x in desc for x in ['MLO', 'MEDIOLATERAL', 'OBLIQUE'])
                    has_cc = any(x in desc for x in ['CC', 'CRANIOCAUDAL', 'CRANIO'])
                    
                    if has_left and has_mlo:
                        return 'LMLO'
                    elif has_left and has_cc:
                        return 'LCC'
                    elif has_right and has_mlo:
                        return 'RMLO'
                    elif has_right and has_cc:
                        return 'RCC'
            
            # 从文件路径获取
            if hasattr(dicom_dataset, 'filename'):
                filepath = str(dicom_dataset.filename).upper()
                for position in self.view_positions.keys():
                    if position in filepath:
                        return position
            
            self.logger.warning("无法确定乳腺摄影视图位置")
            return 'UNKNOWN'
            
        except Exception as e:
            self.logger.error(f"获取视图位置失败: {e}")
            return 'UNKNOWN'
    
    def extract_patient_info(self, dicom_dataset: pydicom.Dataset) -> Tuple[str, str]:
        """
        从DICOM文件中提取患者ID和MG号码
        
        Args:
            dicom_dataset: DICOM数据集
            
        Returns:
            (患者ID, MG号码)
        """
        try:
            patient_id = None
            mg_number = None
            
            # 获取患者ID
            if hasattr(dicom_dataset, 'PatientID'):
                patient_id = str(dicom_dataset.PatientID)
            
            # 从文件路径中获取
            if hasattr(dicom_dataset, 'filename'):
                file_path = str(dicom_dataset.filename)
                path_parts = file_path.split(os.path.sep)
                
                # 查找患者ID（通常是纯数字的文件夹名）
                for part in path_parts:
                    if part.isdigit() and not patient_id:
                        patient_id = part
                
                # 查找MG号码
                for part in path_parts:
                    if 'MG' in part.upper():
                        mg_number = part
                        break
            
            # 从DICOM标签中查找MG号码
            if not mg_number:
                search_fields = ['SeriesDescription', 'StudyDescription', 'StudyID']
                for field in search_fields:
                    if hasattr(dicom_dataset, field):
                        value = str(getattr(dicom_dataset, field))
                        if 'MG' in value.upper():
                            mg_number = value
                            break
            
            # 使用默认值
            if not patient_id:
                patient_id = "UNKNOWN"
            if not mg_number:
                mg_number = "MG001"
            
            return patient_id, mg_number
            
        except Exception as e:
            self.logger.warning(f"提取患者信息失败: {e}")
            return "UNKNOWN", "MG001"
    
    def remove_sensitive_info(self, img_array: np.ndarray) -> np.ndarray:
        """
        移除图像中的敏感信息（如患者标识、日期等）
        
        Args:
            img_array: 原始图像数组
            
        Returns:
            清理后的图像数组
        """
        try:
            height, width = img_array.shape
            clean_img = img_array.copy()
            
            # 获取背景值（通常是图像的最小值）
            background_value = img_array.min()
            
            # 移除顶部和底部边缘区域（通常包含敏感信息）
            top_margin = int(height * 0.1)  # 顶部10%
            bottom_margin = int(height * 0.1)  # 底部10%
            
            clean_img[:top_margin, :] = background_value
            clean_img[-bottom_margin:, :] = background_value
            
            # 可选：移除左右边缘
            left_margin = int(width * 0.05)  # 左侧5%
            right_margin = int(width * 0.05)  # 右侧5%
            
            clean_img[:, :left_margin] = background_value
            clean_img[:, -right_margin:] = background_value
            
            return clean_img
            
        except Exception as e:
            self.logger.error(f"移除敏感信息失败: {e}")
            return img_array
    
    def correct_image_orientation(self, img_array: np.ndarray, view_position: str) -> np.ndarray:
        """
        根据乳腺摄影视图位置修正图像方向
        
        Args:
            img_array: 原始图像数组
            view_position: 视图位置（LMLO/RMLO/LCC/RCC）
            
        Returns:
            修正后的图像数组
        """
        try:
            if view_position in self.view_positions:
                # 乳腺摄影图像统一进行逆时针旋转90度
                return np.rot90(img_array, k=-1)
            else:
                # 未知位置不进行旋转
                return img_array
                
        except Exception as e:
            self.logger.error(f"图像方向修正失败: {e}")
            return img_array
    
    def convert_to_nifti(self, input_path: str, output_path: str, 
                        conversion_params: Optional[Dict[str, Any]] = None) -> bool:
        """
        转换乳腺摄影DICOM到NIfTI格式
        
        Args:
            input_path: 输入路径（单个DICOM文件或目录）
            output_path: 输出NIfTI文件路径
            conversion_params: 转换参数
            
        Returns:
            转换是否成功
        """
        try:
            self.progress_callback(0, "开始乳腺摄影转换...")
            
            # 发现DICOM文件
            dicom_files = self.discover_dicom_files(input_path)
            if not dicom_files:
                                 raise DicomValidationError(f"未找到DICOM文件: {input_path}")
            
            self.progress_callback(20, f"发现 {len(dicom_files)} 个DICOM文件")
            
            # 乳腺摄影通常是单文件处理
            success_count = 0
            
            for i, dicom_file in enumerate(dicom_files):
                try:
                    # 验证DICOM文件
                    if not self.validate_dicom_file(dicom_file):
                        continue
                    
                    # 读取DICOM文件
                    ds = pydicom.dcmread(dicom_file)
                    img_array = ds.pixel_array
                    
                    self.progress_callback(30 + i * 20, f"处理文件 {i+1}/{len(dicom_files)}")
                    
                    # 获取患者信息
                    patient_id, mg_number = self.extract_patient_info(ds)
                    
                    # 获取视图位置
                    view_position = self.get_mg_view_position(ds)
                    if view_position == 'UNKNOWN':
                        self.logger.warning(f"无法确定视图位置: {dicom_file}")
                        view_position = "UNKNOWN"
                    
                    # 构建输出文件名
                    base_dir = os.path.dirname(output_path)
                    if view_position != 'UNKNOWN':
                        output_file = os.path.join(base_dir, f"{patient_id}_{mg_number}_{view_position}.nii")
                    else:
                        filename = os.path.splitext(os.path.basename(dicom_file))[0]
                        output_file = os.path.join(base_dir, f"{patient_id}_{mg_number}_{filename}.nii")
                    
                    self.progress_callback(50 + i * 20, f"处理图像: {view_position}")
                    
                    # 移除敏感信息
                    clean_img = self.remove_sensitive_info(img_array)
                    
                    # 修正图像方向
                    corrected_img = self.correct_image_orientation(clean_img, view_position)
                    
                    # 创建仿射矩阵
                    affine = np.eye(4)
                    if hasattr(ds, 'PixelSpacing'):
                        pixel_spacing = ds.PixelSpacing
                        affine[0, 0] = float(pixel_spacing[0])
                        affine[1, 1] = float(pixel_spacing[1])
                    
                    # 创建NIfTI图像
                    nii_img = nib.Nifti1Image(corrected_img, affine)
                    
                    # 保存文件
                    os.makedirs(os.path.dirname(output_file), exist_ok=True)
                    nib.save(nii_img, output_file)
                    
                    success_count += 1
                    self.logger.info(f"成功转换: {output_file}")
                    
                except Exception as e:
                    self.logger.error(f"转换单个文件失败 {dicom_file}: {e}")
                    continue
            
            if success_count > 0:
                self.progress_callback(100, f"乳腺摄影转换完成，成功转换 {success_count} 个文件")
                return True
            else:
                raise ConversionError("没有成功转换任何文件")
            
        except Exception as e:
            error_msg = f"乳腺摄影转换失败: {str(e)}"
            self.logger.error(error_msg)
            self.progress_callback(-1, error_msg)
            return False
    
    def get_conversion_info(self, input_path: str) -> Dict[str, Any]:
        """
        获取乳腺摄影转换信息
        
        Args:
            input_path: 输入路径
            
        Returns:
            转换信息字典
        """
        try:
            dicom_files = self.discover_dicom_files(input_path)
            if not dicom_files:
                return {"error": "未找到DICOM文件"}
            
            # 分析所有文件的视图位置
            view_positions = []
            patient_ids = set()
            
            for dicom_file in dicom_files:
                try:
                    ds = pydicom.dcmread(dicom_file)
                    view_pos = self.get_mg_view_position(ds)
                    view_positions.append(view_pos)
                    
                    patient_id, _ = self.extract_patient_info(ds)
                    patient_ids.add(patient_id)
                    
                except Exception:
                    continue
            
            # 统计视图位置
            view_counts = {}
            for pos in view_positions:
                view_counts[pos] = view_counts.get(pos, 0) + 1
            
            info = {
                "modality": "MG",
                "files_count": len(dicom_files),
                "patients_count": len(patient_ids),
                "view_positions": view_counts,
                "is_mammography": True,
            }
            
            # 获取第一个文件的详细信息
            if dicom_files:
                first_dicom = pydicom.dcmread(dicom_files[0])
                info.update({
                    "study_date": getattr(first_dicom, 'StudyDate', 'Unknown'),
                    "series_description": getattr(first_dicom, 'SeriesDescription', 'Unknown'),
                })
                
                if hasattr(first_dicom, 'pixel_array'):
                    img_shape = first_dicom.pixel_array.shape
                    info["image_size"] = f"{img_shape[1]}x{img_shape[0]}"
            
            return info
            
        except Exception as e:
            return {"error": f"获取转换信息失败: {e}"}

    def _process_series(self, series_dir: Path, output_filename: Path) -> sitk.Image:
        """
        Processes a single mammography series.
        This now includes orientation correction and artifact removal based on config.
        """
        reader = sitk.ImageSeriesReader()
        dicom_names = reader.GetGDCMSeriesFileNames(str(series_dir))
        if not dicom_names:
            raise FileNotFoundError(f"No DICOM files found in series: {series_dir}")
        reader.SetFileNames(dicom_names)
        
        try:
            image = reader.Execute()
        except Exception as e:
            self.log(f"Failed to read DICOM series with SimpleITK: {e}", level="ERROR")
            self.log("Attempting fallback with pydicom...", level="INFO")
            image = self._fallback_dcm_reader(series_dir)

        # --- 新增的影像组学预处理步骤 ---
        if self.config.correct_orientation:
            self.log("Attempting to correct image orientation...", level="INFO")
            image = correct_image_orientation(image)

        if self.config.remove_edge_info:
            self.log("Attempting to remove edge artifacts...", level="INFO")
            image = remove_edge_artifacts(image)
        
        return image 