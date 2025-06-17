"""
DICOM转换器模块

包含所有DICOM到NIfTI的转换器实现
"""

from .base import BaseDICOMConverter
from .ct_converter import CTConverter
from .mri_converter import MRIConverter
from .mammography_converter import MammographyConverter
from .radiotherapy_converter import RadiotherapyConverter

__all__ = [
    'BaseDICOMConverter',
    'CTConverter',
    'MRIConverter', 
    'MammographyConverter',
    'RadiotherapyConverter',
]

# 转换器注册表
CONVERTER_REGISTRY = {
    'CT': CTConverter,
    'MRI': MRIConverter,
    'MR': MRIConverter,  # MRI的别名
    'MG': MammographyConverter,
    'MAMMOGRAPHY': MammographyConverter,
    'RT': RadiotherapyConverter,
    'RTSTRUCT': RadiotherapyConverter,
    'RTPLAN': RadiotherapyConverter,
    'RTDOSE': RadiotherapyConverter,
}

def get_converter(modality: str, progress_callback=None):
    """
    根据模态获取相应的转换器
    
    Args:
        modality: 图像模态（CT/MRI/MG/RT等）
        progress_callback: 进度回调函数
        
    Returns:
        对应的转换器实例
        
    Raises:
        ValueError: 不支持的模态类型
    """
    modality_upper = modality.upper()
    
    if modality_upper in CONVERTER_REGISTRY:
        converter_class = CONVERTER_REGISTRY[modality_upper]
        return converter_class(progress_callback)
    else:
        raise ValueError(f"不支持的模态类型: {modality}")

def list_supported_modalities():
    """
    获取支持的模态类型列表
    
    Returns:
        支持的模态类型列表
    """
    return list(CONVERTER_REGISTRY.keys())
