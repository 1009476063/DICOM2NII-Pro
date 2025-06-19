#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文件名: image_processing.py
功能描述: 提供通用的医学影像处理函数
创建日期: 2025-06-19
作者: TanX
"""
import SimpleITK as sitk
import numpy as np

def correct_image_orientation(image: sitk.Image) -> sitk.Image:
    """
    Corrects the orientation of a medical image to a standard anatomical orientation (LPS).
    This is a placeholder and often requires modality-specific logic.
    For demonstration, we ensure the direction cosine matrix is standard.
    """
    # A simple approach: set direction to identity matrix, assuming data is stored in LPS
    # A more robust implementation would analyze DICOM tags (0020,0037) Image Orientation (Patient)
    # and (0020,0032) Image Position (Patient) to derive the correct transform.
    original_direction = image.GetDirection()
    h_flip = np.abs(np.linalg.det(np.array(original_direction).reshape(3,3))) < 0
    if h_flip:
        flipper = sitk.FlipImageFilter()
        flipper.SetFlipAxes([True, False, False])
        image = flipper.Execute(image)
        
    image.SetDirection((1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0))
    return image

def remove_edge_artifacts(image: sitk.Image, lower_threshold: float = 0.95, upper_threshold: float = 1.0) -> sitk.Image:
    """
    Attempts to remove high-intensity artifacts at the image edges, common in mammography.
    It creates a mask of the high-intensity areas and multiplies it with the original image.
    
    Args:
        image (sitk.Image): The input image.
        lower_threshold (float): The lower bound of intensity percentile to be considered an artifact.
        upper_threshold (float): The upper bound of intensity percentile.

    Returns:
        sitk.Image: The image with edge artifacts removed.
    """
    img_array = sitk.GetArrayViewFromImage(image)
    
    # Determine the intensity range for artifacts
    max_intensity = np.max(img_array)
    lower_bound = max_intensity * lower_threshold
    
    # Create a mask where artifacts are present (intensity is high)
    artifact_mask = (img_array >= lower_bound)
    
    # Use morphological operations to clean up the mask and identify large connected components
    label_image = sitk.GetImageFromArray(artifact_mask.astype(np.uint8))
    connected_components = sitk.ConnectedComponent(label_image)
    
    # Remove small objects from the mask
    relabel_image = sitk.RelabelComponent(connected_components, minimumObjectSize=100)
    
    final_mask = sitk.GetArrayViewFromImage(relabel_image) > 0
    
    # Invert the mask: we want to keep the areas that are NOT artifacts
    final_mask_inverted = np.logical_not(final_mask)
    
    # Apply the mask
    cleaned_array = img_array * final_mask_inverted
    
    cleaned_image = sitk.GetImageFromArray(cleaned_array)
    cleaned_image.CopyInformation(image) # Preserve metadata
    
    return cleaned_image

def normalize_intensity(image: sitk.Image, method: str) -> sitk.Image:
    """
    Normalizes the intensity of an MRI image.
    """
    if method == "None":
        return image
    
    if method == "Z-Score":
        stats = sitk.StatisticsImageFilter()
        stats.Execute(image)
        mean = stats.GetMean()
        std_dev = stats.GetStdDev()
        
        if std_dev > 0:
            return sitk.ShiftScale(image, -mean, 1.0/std_dev)
        else:
            return image
            
    # Placeholders for more advanced methods
    elif method == "WhiteStripe":
        # TODO: Implement WhiteStripe normalization
        print("WhiteStripe normalization is not yet implemented.")
        return image
    elif method == "HistogramMatching":
        # TODO: Implement Histogram Matching
        print("Histogram Matching is not yet implemented.")
        return image
        
    return image

def discretize_intensity(image: sitk.Image, method: str, value: float) -> sitk.Image:
    """
    Discretizes the intensity of an image.
    """
    if method == "FixedBinWidth":
        # Bin width is provided by 'value'
        return sitk.BinomialBlur(image, int(value))
    elif method == "FixedBinCount":
        # Number of bins is provided by 'value'
        discretizer = sitk.DiscretizeImageFilter()
        discretizer.SetNumberOfBins(int(value))
        return discretizer.Execute(image)
    
    return image 