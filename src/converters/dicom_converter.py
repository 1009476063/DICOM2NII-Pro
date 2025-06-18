#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MICS DICOM转换器

集成多种DICOM转换功能，包括：
- CT图像转换
- MRI图像转换 
- 乳腺摄影转换
- 放疗数据转换
"""

import os
import logging
import numpy as np
from pathlib import Path
from typing import List, Dict, Any, Optional, Callable
import threading
import time

from ..core.conversion_config import (
    BaseConversionConfig, CTConversionConfig, MRIConversionConfig,
    MammographyConversionConfig, UltrasoundConversionConfig
)

try:
    import pydicom
    import nibabel as nib
    import SimpleITK as sitk
    DICOM_AVAILABLE = True
except ImportError:
    DICOM_AVAILABLE = False
    sitk = None # To avoid linting errors

class ProgressInfo:
    """进度信息类"""
    def __init__(self, current: int, total: int, message: str = ""):
        self.current = current
        self.total = total
        self.message = message
        self.percentage = (current / total * 100) if total > 0 else 0

class DicomConverter:
    """DICOM转换器主类"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.is_cancelled = False
        self.progress_callback: Optional[Callable[[ProgressInfo], None]] = None
        
    def set_progress_callback(self, callback: Callable[[ProgressInfo], None]):
        """设置进度回调函数"""
        self.progress_callback = callback
        
    def _update_progress(self, current: int, total: int, message: str = ""):
        """更新进度"""
        if self.progress_callback:
            # The callback in the worker expects percentage and message
            percentage = int((current / total) * 100) if total > 0 else 0
            self.progress_callback(percentage, message)
            
    def _get_mg_view_position(self, ds):
        """从DICOM文件中获取乳腺摄影图像的方位信息"""
        try:
            view_position = ds.ViewPosition if hasattr(ds, 'ViewPosition') else ''
            laterality = ds.ImageLaterality if hasattr(ds, 'ImageLaterality') else ''
            
            # 组合方位信息
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
            for field in ['SeriesDescription', 'StudyDescription', 'ImageComments']:
                if hasattr(ds, field):
                    desc = getattr(ds, field).upper()
                    if 'RCC' in desc:
                        return 'RCC'
                    elif 'LCC' in desc:
                        return 'LCC'
                    elif 'RMLO' in desc:
                        return 'RMLO'
                    elif 'LMLO' in desc:
                        return 'LMLO'
            
            return 'UNKNOWN'
        except:
            return 'UNKNOWN'

    def _correct_image_orientation(self, img_array, modality):
        """根据模态类型修正图像方向"""
        if isinstance(modality, str) and modality in ['LMLO', 'RMLO', 'LCC', 'RCC']:
            # MG图像逆时针旋转90度（k=-1）
            return np.rot90(img_array, k=-1)
        elif modality in ['DCE', 'DWI', 'ADC']:
            # 1. 先顺时针旋转90度（k=1）
            rotated = np.rot90(img_array, k=1)
            # 2. 左右翻转
            return np.fliplr(rotated)
        return img_array

    def _remove_sensitive_info(self, img_array):
        """移除图像中的敏感信息"""
        height, width = img_array.shape
        top_margin = int(height * 0.1)
        bottom_margin = int(height * 0.1)
        
        clean_img = img_array.copy()
        background_value = img_array.min()
        clean_img[:top_margin, :] = background_value
        clean_img[-bottom_margin:, :] = background_value
        
        return clean_img

    def _get_patient_id_and_mg_number(self, ds):
        """从DICOM文件中获取患者ID和MG号码"""
        try:
            # 获取患者ID - 从文件路径中获取
            file_path = ds.filename if hasattr(ds, 'filename') else ''
            path_parts = file_path.split(os.path.sep)
            patient_id = None
            mg_number = None
            
            # 从路径中查找患者ID（通常是纯数字的文件夹名）
            for part in path_parts:
                if part.isdigit():
                    patient_id = part
                    break
            
            # 从路径中查找MG号码
            for part in path_parts:
                if 'MG' in part:
                    # 提取MG号码
                    mg_start = part.find('MG')
                    mg_part = part[mg_start:]
                    # 提取MG和后面的数字
                    mg_number = ''.join(c for c in mg_part if c.isdigit() or c in 'MGmg')
                    if mg_number:
                        break
            
            # 如果从路径中找不到，尝试从DICOM标签中获取
            if not patient_id:
                patient_id = ds.PatientID if hasattr(ds, 'PatientID') else None
                if not patient_id:
                    for field in ['StudyID', 'SeriesNumber']:
                        if hasattr(ds, field):
                            potential_id = getattr(ds, field)
                            if potential_id and str(potential_id).isdigit():
                                patient_id = str(potential_id)
                                break
            
            if not mg_number:
                # 从DICOM标签中查找MG号码
                for field in ['SeriesDescription', 'StudyDescription', 'StudyID']:
                    if hasattr(ds, field):
                        value = str(getattr(ds, field))
                        if 'MG' in value.upper():
                            start_idx = value.upper().find('MG')
                            mg_part = value[start_idx:]
                            mg_number = ''.join(c for c in mg_part if c.isdigit() or c.upper() in ['M', 'G'])
                            if mg_number:
                                break
            
            if not patient_id:
                patient_id = "UNKNOWN_PATIENT"
            if not mg_number:
                mg_number = "MG_UNKNOWN"
                
            return patient_id, mg_number
        except Exception as e:
            self.logger.warning(f"获取ID或MG号码失败: {str(e)}")
            return "UNKNOWN_PATIENT", "MG_UNKNOWN"

    def _detect_modality(self, dicom_path: str) -> str:
        """自动检测DICOM文件的模态类型"""
        try:
            ds = pydicom.read_file(dicom_path, stop_before_pixels=True)
            
            # 检查模态字段
            modality = getattr(ds, 'Modality', '').upper()
            if modality == 'MG':
                return 'mammography'
            elif modality == 'CT':
                return 'ct'
            elif modality == 'MR':
                return 'mri'
            elif modality in ['RTPLAN', 'RTDOSE', 'RTSTRUCT']:
                return 'radiotherapy'
            
            # 从序列描述中推断
            series_desc = getattr(ds, 'SeriesDescription', '').upper()
            if any(keyword in series_desc for keyword in ['MG', 'MAMMO', '乳腺']):
                return 'mammography'
            elif any(keyword in series_desc for keyword in ['CT', 'COMPUTED']):
                return 'ct'
            elif any(keyword in series_desc for keyword in ['MR', 'MAGNETIC']):
                return 'mri'
            elif any(keyword in series_desc for keyword in ['RT', 'RADIO', '放疗']):
                return 'radiotherapy'
            
            # 默认返回CT
            return 'ct'
            
        except Exception as e:
            self.logger.warning(f"无法检测模态类型 {dicom_path}: {e}")
            return 'ct'

    def convert_single_file(self, input_path: str, output_path: str, 
                          conversion_type: str = 'auto') -> bool:
        """转换单个DICOM文件"""
        try:
            if not DICOM_AVAILABLE:
                raise RuntimeError("PyDicom和NiBabel库不可用")
                
            self._update_progress(0, 1, f"读取DICOM文件: {Path(input_path).name}")
            
            # 读取DICOM文件
            ds = pydicom.read_file(input_path)
            img_array = ds.pixel_array
            
            # 自动检测模态类型
            if conversion_type == 'auto':
                conversion_type = self._detect_modality(input_path)
            
            self._update_progress(1, 3, f"处理图像数据...")
            
            # 根据模态类型处理图像
            if conversion_type == 'mammography':
                # 获取患者ID和MG号码
                patient_id, mg_number = self._get_patient_id_and_mg_number(ds)
                
                # 获取方位信息
                view_position = self._get_mg_view_position(ds)
                
                # 构建新的输出文件名
                base_dir = os.path.dirname(output_path)
                output_path = os.path.join(base_dir, f"{patient_id}_{mg_number}_{view_position}.nii")
                
                # 移除敏感信息
                img_array = self._remove_sensitive_info(img_array)
                
                # 修正图像方向
                img_array = self._correct_image_orientation(img_array, view_position)
            
            self._update_progress(2, 3, f"创建NIfTI文件...")
            
            # 创建NIfTI图像
            affine = np.eye(4)
            nii_img = nib.Nifti1Image(img_array, affine)
            
            # 确保输出目录存在
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # 保存NIfTI文件
            nib.save(nii_img, output_path)
            
            self._update_progress(3, 3, f"转换完成: {Path(output_path).name}")
            
            self.logger.info(f"成功转换: {input_path} -> {output_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"转换失败 {input_path}: {str(e)}")
            return False

    def convert_series(self, input_folder: str, output_path: str, 
                      conversion_type: str = 'auto') -> bool:
        """转换DICOM序列"""
        try:
            if not DICOM_AVAILABLE:
                raise RuntimeError("PyDicom和NiBabel库不可用")
                
            # 获取所有DICOM文件并按文件名排序
            dicom_files = []
            for ext in ['.dcm', '.dicom', '.ima', '.img']:
                dicom_files.extend(Path(input_folder).glob(f'*{ext}'))
                dicom_files.extend(Path(input_folder).glob(f'*{ext.upper()}'))
            
            # 尝试查找没有扩展名的DICOM文件
            for file_path in Path(input_folder).iterdir():
                if file_path.is_file() and not file_path.suffix:
                    try:
                        pydicom.read_file(file_path, stop_before_pixels=True)
                        dicom_files.append(file_path)
                    except:
                        pass
            
            dicom_files = sorted(list(set(dicom_files)))
            
            if not dicom_files:
                self.logger.warning(f"在 {input_folder} 中未找到DICOM文件")
                return False
            
            total_files = len(dicom_files)
            self._update_progress(0, total_files, "读取DICOM序列...")
            
            # 读取所有DICOM文件
            img_arrays = []
            for i, dicom_file in enumerate(dicom_files):
                if self.is_cancelled:
                    return False
                    
                try:
                    ds = pydicom.read_file(dicom_file)
                    img_arrays.append(ds.pixel_array)
                    self._update_progress(i + 1, total_files, f"读取文件 {i+1}/{total_files}")
                except Exception as e:
                    self.logger.warning(f"读取文件失败 {dicom_file}: {e}")
                    continue
            
            if not img_arrays:
                raise RuntimeError("没有成功读取任何DICOM文件")
            
            self._update_progress(total_files, total_files + 1, "组合3D图像...")
            
            # 组合为3D数组
            volume = np.stack(img_arrays, axis=-1)
            
            # 创建NIfTI图像
            affine = np.eye(4)
            nii_img = nib.Nifti1Image(volume, affine)
            
            # 确保输出目录存在
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # 保存NIfTI文件
            nib.save(nii_img, output_path)
            
            self._update_progress(total_files + 1, total_files + 1, "转换完成")
            
            self.logger.info(f"成功转换序列: {input_folder} -> {output_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"序列转换失败 {input_folder}: {str(e)}")
            return False

    def convert_batch(self, input_files: List[str], output_dir: str, 
                     conversion_type: str = 'auto') -> Dict[str, Any]:
        """批量转换DICOM文件"""
        results = {
            'success_count': 0,
            'failed_count': 0,
            'total_count': len(input_files),
            'failed_files': []
        }
        
        for i, input_file in enumerate(input_files):
            if self.is_cancelled:
                break
                
            try:
                input_path = Path(input_file)
                
                # 构建输出文件名
                if input_path.is_file():
                    output_name = input_path.stem + '.nii'
                    output_path = Path(output_dir) / output_name
                    
                    success = self.convert_single_file(str(input_path), str(output_path), conversion_type)
                else:
                    # 处理文件夹（序列）
                    output_name = input_path.name + '.nii'
                    output_path = Path(output_dir) / output_name
                    
                    success = self.convert_series(str(input_path), str(output_path), conversion_type)
                
                if success:
                    results['success_count'] += 1
                else:
                    results['failed_count'] += 1
                    results['failed_files'].append(str(input_path))
                    
            except Exception as e:
                self.logger.error(f"批量转换错误 {input_file}: {e}")
                results['failed_count'] += 1
                results['failed_files'].append(input_file)
                
            # 更新总体进度
            self._update_progress(i + 1, len(input_files), 
                                f"已完成 {i+1}/{len(input_files)} 个文件")
        
        return results

    def cancel(self):
        """取消转换"""
        self.is_cancelled = True
        
    def reset(self):
        """重置状态"""
        self.is_cancelled = False

    def process_directory_with_config(self, config):
        """
        Main entry point for processing a directory based on a config object.
        """
        self.logger.info(f"Starting processing with config: {config}")
        self._update_progress(0, 100, "Initializing...")

        patient_dirs = [d for d in Path(config.input_dir).iterdir() if d.is_dir()]
        total_patients = len(patient_dirs)
        self.logger.info(f"Found {total_patients} patient directories.")

        for i, patient_dir in enumerate(patient_dirs):
            if self.is_cancelled:
                self.logger.warning("Processing cancelled by user.")
                self._update_progress(i, total_patients, "Processing cancelled.")
                break
            
            patient_id = patient_dir.name
            self.logger.info(f"Processing patient {i+1}/{total_patients}: {patient_id}")
            self._update_progress(i, total_patients, f"Processing patient: {patient_id}")

            try:
                self._process_patient_series(patient_dir, patient_id, config)
            except Exception as e:
                self.logger.error(f"Failed to process patient {patient_id}. Error: {e}", exc_info=True)
                # Optionally, signal this specific error to the UI
                self._update_progress(i, total_patients, f"ERROR processing {patient_id}: {e}")

        self._update_progress(100, 100, "All patients processed.")
        self.logger.info("Finished processing directory.")

    def _process_patient_series(self, patient_dir: Path, patient_id: str, config: BaseConversionConfig):
        """Processes a single patient's DICOM series based on the specific config type."""
        # 1. Read DICOM series
        self.logger.info(f"Reading DICOM series from: {patient_dir}")
        reader = sitk.ImageSeriesReader()
        dicom_names = reader.GetGDCMSeriesFileNames(str(patient_dir))
        if not dicom_names:
            self.logger.warning(f"No DICOM series found in {patient_dir}")
            return
        reader.SetFileNames(dicom_names)
        image = reader.Execute()

        # 2. Apply transformations based on config type
        if isinstance(config, CTConversionConfig):
            # Apply CT-specific preprocessing
            if config.resample:
                image = self._resample_image(image, config.new_voxel_size, config.interpolator)
            if config.discretize:
                image = self._discretize_intensity(image, config.discretization_type, config.discretization_value)

        elif isinstance(config, MRIConversionConfig):
            # Apply MRI-specific preprocessing
            if config.n4_bias_correction:
                image = self._apply_n4_correction(image)
            if config.skull_stripping:
                image = self._perform_skull_stripping(image)
            if config.normalization_method != "None":
                image = self._normalize_intensity(image, config.normalization_method)
            if config.discretize:
                image = self._discretize_intensity(image, config.discretization_type, config.discretization_value)
        
        # Other modalities like Mammography can be added here
        # elif isinstance(config, MammographyConversionConfig):
        #     ...

        # 3. Save the result
        output_filename = Path(config.output_dir) / f"{patient_id}_{config.modality}.nii.gz"
        self.logger.info(f"Saving processed image to {output_filename}")
        sitk.WriteImage(image, str(output_filename))

    def _apply_n4_correction(self, image: sitk.Image) -> sitk.Image:
        self.logger.info("Applying N4 Bias Field Correction...")
        # Create a mask image
        mask_image = sitk.OtsuThreshold(image, 0, 1, 200)
        # Cast to the correct image type
        image = sitk.Cast(image, sitk.sitkFloat32)
        corrector = sitk.N4BiasFieldCorrectionImageFilter()
        corrected_image = corrector.Execute(image, mask_image)
        return sitk.Cast(corrected_image, image.GetPixelID())

    def _resample_image(self, image: sitk.Image, new_spacing: tuple, interpolator: str) -> sitk.Image:
        self.logger.info(f"Resampling image to voxel size: {new_spacing}")
        resampler = sitk.ResampleImageFilter()
        
        # Set interpolator
        interpolator_map = {
            "sitkLinear": sitk.sitkLinear,
            "sitkNearestNeighbor": sitk.sitkNearestNeighbor,
            "sitkBSpline": sitk.sitkBSpline
        }
        resampler.SetInterpolator(interpolator_map.get(interpolator, sitk.sitkLinear))
        
        # Calculate new size and set output parameters
        original_spacing = image.GetSpacing()
        original_size = image.GetSize()
        
        new_size = [
            int(round(orig_size * orig_space / new_space))
            for orig_size, orig_space, new_space in zip(original_size, original_spacing, new_spacing)
        ]
        
        resampler.SetOutputSpacing(new_spacing)
        resampler.SetOutputOrigin(image.GetOrigin())
        resampler.SetOutputDirection(image.GetDirection())
        resampler.SetSize(new_size)
        
        return resampler.Execute(image)

    def _perform_skull_stripping(self, image: sitk.Image) -> sitk.Image:
        self.logger.info("Performing skull stripping...")
        # This is a placeholder for a real skull-stripping algorithm.
        # A simple approach is using thresholding and morphological operations.
        # For real applications, a more robust library like FSL's BET or ANTs would be better.
        otsu_filter = sitk.OtsuMultipleThresholdsImageFilter()
        otsu_filter.SetNumberOfThresholds(2)
        thresholded = otsu_filter.Execute(image)
        
        # Assume the brain is the largest connected component
        connected_components = sitk.ConnectedComponent(thresholded == 2)
        sorted_components = sitk.RelabelComponent(connected_components, sortByObjectSize=True)
        brain_mask = sorted_components == 1
        
        # Fill holes in the mask
        brain_mask = sitk.BinaryMorphologicalClosing(brain_mask, (5, 5, 5))
        
        return sitk.Mask(image, brain_mask)

    def _normalize_intensity(self, image: sitk.Image, method: str) -> sitk.Image:
        self.logger.info(f"Normalizing intensity using: {method}")
        # Placeholder for real normalization. Z-Score is common.
        if method == "ZScore":
            stats = sitk.StatisticsImageFilter()
            stats.Execute(image)
            mean = stats.GetMean()
            std_dev = stats.GetStandardDeviation()
            if std_dev > 0:
                return sitk.ShiftScale(image, -mean, 1.0/std_dev)
            return image # or handle case of zero std dev
        # Other methods like WhiteStripe would need more complex implementation
        self.logger.warning(f"Normalization method '{method}' is not fully implemented.")
        return image

    def _discretize_intensity(self, image: sitk.Image, dis_type: str, value: float) -> sitk.Image:
        self.logger.info(f"Discretizing intensity with {dis_type}: {value}")
        # Implementation for intensity discretization
        if dis_type == "FixedBinWidth":
            # Bin width
            bin_width = value
            # Formula: floor( (I - min) / bin_width ) * bin_width + min
            # Using SimpleITK filters is safer
            return sitk.Discretize(image, binWidth=bin_width)
        elif dis_type == "FixedBinCount":
            # Bin count
            num_bins = int(value)
            return sitk.Discretize(image, numberOfBins=num_bins)
        return image 