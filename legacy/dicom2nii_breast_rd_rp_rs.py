import os
import glob
import pydicom
import numpy as np
import nibabel as nib
from pydicom.errors import InvalidDicomError

def find_dicom_files(directory, modality=None):
    """查找指定目录下的DICOM文件"""
    dicom_files = []
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith('.dcm') or file.startswith('CT') or file.startswith('RS') or file.startswith('RD') or file.startswith('RP'):
                file_path = os.path.join(root, file)
                try:
                    dcm = pydicom.dcmread(file_path, force=True, stop_before_pixels=True)
                    if modality is None or (hasattr(dcm, 'Modality') and dcm.Modality == modality):
                        dicom_files.append(file_path)
                except:
                    continue
    return dicom_files

def convert_ct_to_nifti(dicom_dir, output_path):
    """直接转换CT DICOM文件为NIfTI格式"""
    try:
        # 查找所有CT文件
        dicom_files = []
        for root, _, files in os.walk(dicom_dir):
            for file in files:
                if file.startswith('CT'):
                    dicom_files.append(os.path.join(root, file))
        
        if not dicom_files:
            print("未找到CT文件")
            return False, None
            
        print(f"找到{len(dicom_files)}个CT文件")
        
        # 读取第一个DICOM以获取基本信息
        ref_dicom = pydicom.dcmread(dicom_files[0])
        
        # 按实例号排序
        sorted_files = []
        for file in dicom_files:
            try:
                dcm = pydicom.dcmread(file)
                sorted_files.append((file, dcm.InstanceNumber))
            except:
                continue
        
        sorted_files.sort(key=lambda x: x[1])
        sorted_files = [x[0] for x in sorted_files]
        
        # 读取所有DICOM文件
        all_slices = []
        for file in sorted_files:
            try:
                dcm = pydicom.dcmread(file)
                all_slices.append(dcm)
            except:
                continue
                
        print(f"成功读取{len(all_slices)}个切片")
        
        # 提取像素数据
        pixel_data = np.stack([s.pixel_array for s in all_slices])
        
        # 调整一些DICOM标签或转换
        if hasattr(ref_dicom, 'RescaleSlope'):
            pixel_data = pixel_data * float(ref_dicom.RescaleSlope)
        if hasattr(ref_dicom, 'RescaleIntercept'):
            pixel_data = pixel_data + float(ref_dicom.RescaleIntercept)
            
        # 创建仿射矩阵
        pixel_spacing = ref_dicom.PixelSpacing
        slice_thickness = ref_dicom.SliceThickness
        
        affine = np.eye(4)
        affine[0, 0] = pixel_spacing[0]
        affine[1, 1] = pixel_spacing[1]
        affine[2, 2] = slice_thickness
        
        # 创建NIfTI图像
        nifti_img = nib.Nifti1Image(pixel_data, affine)
        
        # 保存NIfTI文件
        nib.save(nifti_img, output_path)
        print(f"成功保存CT图像: {output_path}")
        return True, nifti_img
    except Exception as e:
        print(f"CT转换失败: {str(e)}")
        return False, None

def convert_rtdose_to_nifti(dose_file, output_path):
    """转换RTDOSE DICOM为NIfTI格式"""
    try:
        # 读取剂量文件
        dose_dcm = pydicom.dcmread(dose_file)
        
        # 提取像素数据和剂量缩放因子
        dose_array = dose_dcm.pixel_array * float(dose_dcm.DoseGridScaling)
        
        # 构建仿射矩阵
        pixel_spacing = dose_dcm.PixelSpacing
        grid_offsets = dose_dcm.GridFrameOffsetVector
        slice_spacing = abs(grid_offsets[1] - grid_offsets[0]) if len(grid_offsets) > 1 else 1.0
        
        # 创建仿射矩阵
        affine = np.eye(4)
        affine[0, 0] = pixel_spacing[0]
        affine[1, 1] = pixel_spacing[1]
        affine[2, 2] = slice_spacing
        
        # 创建NIfTI图像
        nifti_img = nib.Nifti1Image(dose_array, affine)
        
        # 保存NIfTI文件
        nib.save(nifti_img, output_path)
        print(f"成功保存剂量文件: {output_path}")
        return True
    except Exception as e:
        print(f"剂量文件转换失败: {str(e)}")
        return False

def convert_rtstruct_to_masks(rs_file, ct_path, output_dir):
    """改进的RT Structure到mask文件转换"""
    try:
        # 读取RT Structure文件
        rs_dcm = pydicom.dcmread(rs_file, force=True)
        
        # 读取CT图像以获取尺寸
        ref_ct_nii = nib.load(ct_path)
        ct_shape = ref_ct_nii.shape
        ct_affine = ref_ct_nii.affine
        
        # 检查RT Structure文件结构
        print("检查RT Structure文件结构...")
        
        # 尝试不同方式获取ROI信息
        roi_names = {}
        roi_contour_data = {}
        
        # 方法1：通过StructureSetROI序列
        if hasattr(rs_dcm, 'StructureSetROISequence'):
            for roi in rs_dcm.StructureSetROISequence:
                roi_number = roi.ROINumber
                roi_name = roi.ROIName
                roi_names[roi_number] = roi_name
            print(f"通过StructureSetROISequence找到{len(roi_names)}个ROI")
        
        # 方法2：直接使用ROIContourSequence
        if hasattr(rs_dcm, 'ROIContourSequence'):
            for i, roi_contour in enumerate(rs_dcm.ROIContourSequence):
                # 尝试获取名称
                roi_number = getattr(roi_contour, 'ReferencedROINumber', i+1)
                
                # 如果已经有名字，使用已有的
                if roi_number in roi_names:
                    roi_name = roi_names[roi_number]
                else:
                    # 否则创建一个默认名字
                    roi_name = f"ROI_{roi_number}"
                    roi_names[roi_number] = roi_name
                
                # 保存轮廓数据
                if hasattr(roi_contour, 'ContourSequence'):
                    roi_contour_data[roi_number] = roi_contour.ContourSequence
            
            print(f"通过ROIContourSequence找到{len(roi_contour_data)}个ROI轮廓")
        
        if not roi_names:
            print("无法找到任何ROI信息")
            return False
        
        # 创建每个ROI的mask
        masks_created = 0
        for roi_number, roi_name in roi_names.items():
            # 清理ROI名称，替换非法字符
            roi_name_safe = ''.join(c if c.isalnum() else '_' for c in roi_name)
            
            # 创建空白mask
            mask = np.zeros(ct_shape, dtype=np.uint8)
            
            # 获取轮廓数据
            if roi_number not in roi_contour_data:
                print(f"未找到ROI {roi_name} (ID: {roi_number})的轮廓数据")
                continue
                
            contour_sequence = roi_contour_data[roi_number]
            
            # 填充mask
            for contour in contour_sequence:
                if not hasattr(contour, 'ContourData'):
                    continue
                    
                # 获取轮廓点
                contour_data = np.array(contour.ContourData).reshape((-1, 3))
                
                # 计算切片索引
                slice_pos = contour_data[0, 2]  # 取第一个点的Z坐标
                
                # 计算在体积中的索引
                ct_origin = ct_affine[:3, 3]
                slice_spacing = ct_affine[2, 2]
                slice_index = int((slice_pos - ct_origin[2]) / slice_spacing)
                
                # 确保索引在有效范围内
                if 0 <= slice_index < ct_shape[0]:
                    # 根据轮廓生成2D mask (简化处理)
                    xy_points = contour_data[:, :2]
                    img_shape = ct_shape[1:]
                    
                    # 转换点到像素坐标
                    pixel_spacing = [ct_affine[1, 1], ct_affine[0, 0]]
                    img_origin = [ct_origin[1], ct_origin[0]]
                    
                    pixel_coords = []
                    for point in xy_points:
                        y = int((point[0] - img_origin[0]) / pixel_spacing[0])
                        x = int((point[1] - img_origin[1]) / pixel_spacing[1])
                        if 0 <= x < img_shape[0] and 0 <= y < img_shape[1]:
                            pixel_coords.append([x, y])
                    
                    # 如果有足够的点，标记区域
                    if len(pixel_coords) > 2:
                        # 简化处理：标记轮廓点
                        for x, y in pixel_coords:
                            mask[slice_index, x, y] = 1
                        
                        # 标记周围区域(扩散)
                        for i in range(-3, 4):
                            for j in range(-3, 4):
                                for x, y in pixel_coords:
                                    nx, ny = x+i, y+j
                                    if 0 <= nx < img_shape[0] and 0 <= ny < img_shape[1]:
                                        mask[slice_index, nx, ny] = 1
            
            # 保存mask为NIfTI文件
            mask_path = os.path.join(output_dir, f"mask_{roi_name_safe}.nii.gz")
            mask_img = nib.Nifti1Image(mask, ct_affine)
            nib.save(mask_img, mask_path)
            print(f"成功创建mask: {mask_path}")
            masks_created += 1
        
        print(f"共创建了{masks_created}个mask文件")
        return masks_created > 0
    except Exception as e:
        print(f"转换RT Structure到mask时出错: {str(e)}")
        return False

def process_rp_file(rp_file, output_dir):
    """处理计划文件并提取信息，保存为文本文件"""
    try:
        rp_dcm = pydicom.dcmread(rp_file)
        
        # 提取计划信息
        plan_info = {
            'RTPlanLabel': getattr(rp_dcm, 'RTPlanLabel', ''),
            'RTPlanName': getattr(rp_dcm, 'RTPlanName', ''),
            'RTPlanDescription': getattr(rp_dcm, 'RTPlanDescription', '')
        }
        
        # 尝试提取更多信息
        if hasattr(rp_dcm, 'FractionGroupSequence'):
            fg = rp_dcm.FractionGroupSequence[0]
            plan_info['NumberOfFractions'] = getattr(fg, 'NumberOfFractions', '')
            plan_info['NumberOfBeams'] = getattr(fg, 'NumberOfBeams', '')
        
        # 保存为文本文件
        plan_path = os.path.join(output_dir, 'plan_info.txt')
        with open(plan_path, 'w', encoding='utf-8') as f:
            for key, value in plan_info.items():
                f.write(f"{key}: {value}\n")
        
        print(f"成功保存计划文件: {plan_path}")
        return True
    except Exception as e:
        print(f"处理计划文件失败: {str(e)}")
        return False

def convert_dicom_to_nifti(dicom_dir, nii_output_base):
    """转换DICOM文件到NIFTI格式"""
    try:
        # 获取相对路径作为输出子目录
        base_dir = os.path.dirname(os.path.dirname(dicom_dir))  # BREAST目录
        rel_path = os.path.relpath(dicom_dir, base_dir)  # 相对路径
        nii_output_dir = os.path.join(nii_output_base, rel_path)
        os.makedirs(nii_output_dir, exist_ok=True)
        
        print(f"处理目录: {dicom_dir}")
        print(f"输出目录: {nii_output_dir}")
        
        # 1. 处理CT图像
        ct_path = os.path.join(nii_output_dir, 'image.nii.gz')
        success, _ = convert_ct_to_nifti(dicom_dir, ct_path)
        
        # 只有当CT转换成功后才继续
        if success:
            # 2. 查找并处理其他文件
            rs_files = glob.glob(os.path.join(dicom_dir, "**", "RS*.dcm"), recursive=True)
            rd_files = glob.glob(os.path.join(dicom_dir, "**", "RD*.dcm"), recursive=True)
            rp_files = glob.glob(os.path.join(dicom_dir, "**", "RP*.dcm"), recursive=True)
            
            # 如果没有找到RS文件，尝试更广泛地搜索
            if not rs_files:
                print("尝试更广泛地搜索RT Structure文件...")
                for root, _, files in os.walk(dicom_dir):
                    for file in files:
                        if "RS" in file.upper():
                            rs_files.append(os.path.join(root, file))
                            break
            
            # 处理RT Structure
            if rs_files:
                print("找到RT Structure文件，正在转换为mask...")
                convert_rtstruct_to_masks(rs_files[0], ct_path, nii_output_dir)
            
            # 处理剂量文件
            if rd_files:
                print("找到剂量文件，正在转换...")
                rtdose_path = os.path.join(nii_output_dir, 'rtdose.nii.gz')
                convert_rtdose_to_nifti(rd_files[0], rtdose_path)
            
            # 处理计划文件
            if rp_files:
                print("找到计划文件，正在处理...")
                process_rp_file(rp_files[0], nii_output_dir)
            
            print("转换完成!")
        
    except Exception as e:
        print(f"处理目录时出错: {str(e)}")

def main():
    # 基础目录配置 - Windows路径
    base_dir = r"C:\Users\薛景硕\Desktop\BREAST"
    nii_output_base = os.path.join(base_dir, "BREAST_nii")  # 在BREAST目录下创建输出目录
    
    # 创建主输出目录
    os.makedirs(nii_output_base, exist_ok=True)
    
    # 处理NO RELAPSE目录
    no_relapse_dir = os.path.join(base_dir, "NO RELAPSE")
    if os.path.exists(no_relapse_dir):
        for patient_folder in os.listdir(no_relapse_dir):
            if patient_folder.startswith('.'):
                continue
            patient_dir = os.path.join(no_relapse_dir, patient_folder)
            if os.path.isdir(patient_dir):
                convert_dicom_to_nifti(patient_dir, nii_output_base)
    
    # 处理RELAPSE目录
    relapse_dir = os.path.join(base_dir, "RELAPSE")
    if os.path.exists(relapse_dir):
        for patient_folder in os.listdir(relapse_dir):
            if patient_folder.startswith('.'):
                continue
            patient_dir = os.path.join(relapse_dir, patient_folder)
            if os.path.isdir(patient_dir):
                convert_dicom_to_nifti(patient_dir, nii_output_base)

if __name__ == "__main__":
    # 确保所需库已安装
    required_packages = ['pydicom', 'numpy', 'nibabel']
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            print(f"请先安装{package}: pip install {package}")
            exit(1)
    
    main()