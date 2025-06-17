import os
import glob
from dcmrtstruct2nii import dcmrtstruct2nii, list_rt_structs
import pydicom
import dicom2nifti
import SimpleITK as sitk

dir_ = r'D:\Downloads\c\d'
save_dir = r'D:\Downloads\c\save'
ID_list = os.listdir(dir_)

for ID in ID_list:
    print(ID)
    os.makedirs(os.path.join(save_dir, ID), exist_ok=True)

    RD_path_list = glob.glob(os.path.join(dir_, ID, 'RD*.dcm'))
    RS_path_list = glob.glob(os.path.join(dir_, ID, 'RS*.dcm'))
    RP_path_list = glob.glob(os.path.join(dir_, ID, 'RP*.dcm'))

    if len(RS_path_list) > 0:
        print('Image and mask!')
        dcmrtstruct2nii(RS_path_list[0], os.path.join(dir_, ID), os.path.join(save_dir, ID))
        os.rename(os.path.join(save_dir, ID, 'image.nii.gz'), os.path.join(save_dir, ID, 'CT.nii.gz'))
    else:
        print('Only image!')
        dicom2nifti.dicom_series_to_nifti(os.path.join(dir_, ID),
                                          os.path.join(save_dir, ID, 'CT.nii.gz'),
                                          reorient_nifti=True)

    if len(RP_path_list) > 0:
        print('RP!')
        os.makedirs(os.path.join(save_dir, ID), exist_ok=True)
        dcm = pydicom.dcmread(RP_path_list[0])
        dcm.AccessionNumber = ''
        dcm.ContentDate = ''
        dcm.ContentTime = ''
        dcm.InstanceCreationDate = ''
        dcm.InstanceNumber = ''
        dcm.Manufacturer = ''
        dcm.ManufacturerModelName = ''
        dcm.PatientBirthDate = ''
        dcm.PatientID = ''
        dcm.PatientName = ''
        dcm.OperatorsName = ''
        dcm.PatientSex = ''
        dcm.ReferringPhysicianName = ''
        dcm.SOPClassUID = ''
        dcm.SOPInstanceUID = ''
        dcm.SeriesDescription = ''
        dcm.SeriesInstanceUID = ''
        dcm.SeriesNumber = ''
        dcm.SoftwareVersions = ''
        dcm.SpecificCharacterSet = ''
        dcm.StationName = ''
        dcm.StudyDate = ''
        dcm.StudyDescription = ''
        dcm.StudyID = ''
        dcm.StudyInstanceUID = ''
        dcm.StudyTime = ''
        dcm.InstanceCreationTime = ''
        dcm.SOPClassUID = ''
        dcm.SOPInstanceUID = ''
        dcm.FrameOfReferenceUID = ''
        dcm.ApprovalStatus = ''
        dcm.ReviewDate = ''
        dcm.ReviewTime = ''
        dcm.ReviewerName = ''
        dcm.RTPlanDate = ''
        dcm.RTPlanDescription = ''
        dcm.RTPlanGeometry = ''
        dcm.RTPlanLabel = ''
        dcm.RTPlanName = ''
        dcm.RTPlanTime = ''
        dcm.private_creators = ''
        dcm.StudyID = ''
        dcm.StudyID = ''
        dcm.StudyID = ''
        dcm.BrachyTreatmentTechnique = ''
        pydicom.dcmwrite(os.path.join(save_dir, ID, 'RP.dcm'), dcm)

    if len(RD_path_list) > 0 and os.path.exists(os.path.join(save_dir, ID, 'CT.nii.gz')):
        print('RD!')
        os.makedirs(os.path.join(save_dir, ID), exist_ok=True)
        rtdose = sitk.ReadImage(RD_path_list[0])
        CT_nii = sitk.ReadImage(os.path.join(save_dir, ID, 'CT.nii.gz'))
        rtdose_dcm = pydicom.dcmread(RD_path_list[0])
        DoseGridScaling = rtdose_dcm.DoseGridScaling

        rtdose_array = sitk.GetArrayFromImage(rtdose) * DoseGridScaling
        rtdose_Spacing = rtdose.GetSpacing()
        rtdose_origin = rtdose.GetOrigin()
        rtdose_direction = rtdose.GetDirection()
        rtdose = sitk.GetImageFromArray(rtdose_array)
        rtdose.SetSpacing(rtdose_Spacing)
        rtdose.SetOrigin(rtdose_origin)
        rtdose.SetDirection(rtdose_direction)

        target_Size = CT_nii.GetSize()  # 目标图像大小  [x,y,z]
        target_Spacing = CT_nii.GetSpacing()  # 目标的体素块尺寸    [x,y,z]
        target_origin = CT_nii.GetOrigin()  # 目标的起点 [x,y,z]
        target_direction = CT_nii.GetDirection()

        resampler = sitk.ResampleImageFilter()
        resampler.SetReferenceImage(rtdose)  # 需要重新采样的目标图像
        # 设置目标图像的信息
        resampler.SetSize(target_Size)  # 目标图像大小
        resampler.SetOutputOrigin(target_origin)
        resampler.SetOutputDirection(target_direction)
        resampler.SetOutputSpacing(target_Spacing)
        # 根据需要重采样图像的情况设置不同的dype
        resampler.SetOutputPixelType(sitk.sitkFloat32)  # 线性插值用于PET/CT/MRI之类的，保存float32
        resampler.SetTransform(sitk.Transform(3, sitk.sitkIdentity))
        # resampler.SetInterpolator(sitk.sitkLinear)
        resampler.SetInterpolator(sitk.sitkNearestNeighbor)
        itk_img_resampled = resampler.Execute(rtdose)

        sitk.WriteImage(itk_img_resampled, os.path.join(save_dir, ID, 'rtdose.nii.gz'))

    if os.path.exists(os.path.join(dir_, ID, 'CECT')) and len(RS_path_list) > 0:
        print('CECT Image and mask!')
        dcmrtstruct2nii(RS_path_list[0], os.path.join(dir_, ID, 'CECT'), os.path.join(save_dir, ID))
        os.rename(os.path.join(save_dir, ID, 'image.nii.gz'), os.path.join(save_dir, ID, 'CECT.nii.gz'))
    elif os.path.exists(os.path.join(dir_, ID, 'CECT')):
        print('CBCT Only image!')
        dicom2nifti.dicom_series_to_nifti(os.path.join(dir_, ID, 'CECT'),
                                          os.path.join(save_dir, ID, 'CECT.nii.gz'),
                                          reorient_nifti=True)