import os
import pydicom
import nibabel as nib
import numpy as np
from pathlib import Path

def get_mg_view_position(ds):
    """
    从DICOM文件中获取乳腺摄影图像的方位信息
    """
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

def correct_image_orientation(img_array, modality):
    """
    根据模态类型修正图像方向
    
    Args:
        img_array: 图像数组
        modality: 图像类型（DCE/DWI/ADC/MG等）或视图位置(LMLO/RMLO/LCC/RCC)
    Returns:
        修正后的图像数组
    """
    if isinstance(modality, str) and modality in ['LMLO', 'RMLO', 'LCC', 'RCC']:
        # MG图像逆时针旋转90度（k=-1）
        return np.rot90(img_array, k=-1)
    elif modality in ['DCE', 'DWI', 'ADC']:
        # 1. 先顺时针旋转90度（k=1）
        rotated = np.rot90(img_array, k=1)
        # 2. 左右翻转
        return np.fliplr(rotated)
    return img_array

def remove_sensitive_info(img_array):
    """
    移除图像中的敏感信息
    """
    height, width = img_array.shape
    top_margin = int(height * 0.1)
    bottom_margin = int(height * 0.1)
    
    clean_img = img_array.copy()
    background_value = img_array.min()
    clean_img[:top_margin, :] = background_value
    clean_img[-bottom_margin:, :] = background_value
    
    return clean_img

def get_patient_id_and_mg_number(ds):
    """
    从DICOM文件中获取患者ID和MG号码
    """
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
            raise ValueError("无法获取患者ID")
        if not mg_number:
            # 如果仍然找不到MG号码，从文件夹名中提取
            for part in path_parts:
                if 'MG' in part:
                    mg_number = part
                    break
            if not mg_number:
                raise ValueError("无法获取MG号码")
            
        return patient_id, mg_number
    except Exception as e:
        print(f"警告: 获取ID或MG号码失败: {str(e)}")
        print(f"文件路径: {ds.filename if hasattr(ds, 'filename') else 'unknown'}")
        raise

def convert_single_dicom_to_nifti(dicom_file, output_nii_path, modality):
    """
    转换单个DICOM文件到NIfTI格式
    """
    try:
        # 读取DICOM文件
        ds = pydicom.read_file(dicom_file)
        img_array = ds.pixel_array
        
        if modality == 'MG':
            # 获取患者ID和MG号码
            patient_id, mg_number = get_patient_id_and_mg_number(ds)
            
            # 获取方位信息
            view_position = get_mg_view_position(ds)
            if view_position == 'UNKNOWN':
                raise ValueError(f"无法确定图像方位: {dicom_file}")
            
            # 构建新的输出文件名
            base_dir = os.path.dirname(output_nii_path)
            output_nii_path = os.path.join(base_dir, f"{patient_id}_{mg_number}_{view_position}.nii")
            
            # 移除敏感信息
            img_array = remove_sensitive_info(img_array)
            
            # 修正图像方向
            img_array = correct_image_orientation(img_array, view_position)
        
        # 创建NIfTI图像
        affine = np.eye(4)
        nii_img = nib.Nifti1Image(img_array, affine)
        
        # 确保输出目录存在
        os.makedirs(os.path.dirname(output_nii_path), exist_ok=True)
        
        # 保存NIfTI文件
        nib.save(nii_img, output_nii_path)
        print(f"成功转换: {output_nii_path}")
        
    except Exception as e:
        print(f"转换失败 {dicom_file}: {str(e)}")

def convert_dicom_series_to_nifti(dicom_folder, output_nii_path, modality):
    """
    转换DICOM序列到NIfTI格式
    """
    try:
        # 获取所有DICOM文件并按文件名排序
        dicom_files = sorted([os.path.join(dicom_folder, f) for f in os.listdir(dicom_folder)
                            if f.endswith('.dcm') or f.upper().endswith('DICOM')])
        
        if not dicom_files:
            print(f"警告: {dicom_folder} 中未找到DICOM文件")
            return
            
        if 'MG' in dicom_folder:  # MG图像单独处理
            for dicom_file in dicom_files:
                convert_single_dicom_to_nifti(dicom_file, output_nii_path, 'MG')
        else:
            # 读取第一个DICOM文件获取基本信息
            ref_dicom = pydicom.read_file(dicom_files[0])
            
            # 创建3D数组
            img_shape = list(ref_dicom.pixel_array.shape)
            img_shape.append(len(dicom_files))
            img3d = np.zeros(img_shape, dtype=ref_dicom.pixel_array.dtype)
            
            # 读取所有DICOM文件
            for i, dicom_file in enumerate(dicom_files):
                ds = pydicom.read_file(dicom_file)
                img3d[:, :, i] = ds.pixel_array
            
            # 对所有模态进行方向修正
            img3d = correct_image_orientation(img3d, modality)
            
            # 创建和保存NIfTI文件
            nii_img = nib.Nifti1Image(img3d, np.eye(4))
            os.makedirs(os.path.dirname(output_nii_path), exist_ok=True)
            nib.save(nii_img, output_nii_path)
            print(f"成功转换: {output_nii_path}")
            
    except Exception as e:
        print(f"转换失败 {dicom_folder}: {str(e)}")

def get_modality_from_path(path):
    """
    从路径中提取模态信息
    """
    path = path.upper()
    if 'DCE' in path:
        return 'DCE'
    elif 'DWI' in path:
        return 'DWI'
    elif 'ADC' in path:
        return 'ADC'
    elif 'MG' in path:
        return 'MG'
    return 'UNKNOWN'

def process_patient_folder(patient_folder):
    """
    处理患者文件夹
    """
    # 获取患者ID（从文件夹名称）
    patient_id = os.path.basename(patient_folder)
    
    # 遍历所有子文件夹
    for root, dirs, files in os.walk(patient_folder):
        # 检查是否有DICOM文件
        dicom_files = [f for f in files if f.endswith('.dcm') or f.upper().endswith('DICOM')]
        if not dicom_files:
            continue
            
        # 获取相对路径
        rel_path = os.path.relpath(root, patient_folder)
        
        # 获取模态信息
        modality = get_modality_from_path(rel_path)
        
        # 创建输出路径
        if modality == 'MG':
            # MG图像的输出路径会在转换函数中重新构建
            nii_output_path = os.path.join(patient_folder, "temp.nii")
        else:
            # 其他序列使用 ID_模态 的命名方式
            nii_output_path = os.path.join(patient_folder, f"{patient_id}_{modality}.nii")
        
        # 转换DICOM到NIfTI
        convert_dicom_series_to_nifti(root, nii_output_path, modality)

def main():
    # 基础目录
    base_dir = r"F:\x\Download20250108"
    
    # 获取所有患者文件夹
    patient_folders = [os.path.join(base_dir, d) for d in os.listdir(base_dir)
                      if os.path.isdir(os.path.join(base_dir, d))]
    
    # 处理每个患者文件夹
    for patient_folder in patient_folders:
        print(f"\n处理患者文件夹: {patient_folder}")
        process_patient_folder(patient_folder)

if __name__ == "__main__":
    main()