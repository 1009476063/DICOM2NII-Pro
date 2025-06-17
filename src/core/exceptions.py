#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文件名: exceptions.py
功能描述: DICOM2NII Pro 异常处理系统
创建日期: 2025-01-23
作者: Claude AI Assistant
版本: v0.1.0-dev

定义了项目中使用的所有自定义异常类，提供详细的错误信息和错误代码。
"""

from typing import Dict, Any, Optional


class DICOM2NIIError(Exception):
    """DICOM2NII Pro 基础异常类"""
    
    def __init__(self, message: str, error_code: str = "UNKNOWN", 
                 details: Optional[Dict[str, Any]] = None):
        """
        初始化异常
        
        Args:
            message: 错误描述信息
            error_code: 错误代码
            details: 详细错误信息字典
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}
    
    def __str__(self) -> str:
        """返回格式化的错误信息"""
        base_msg = f"[{self.error_code}] {self.message}"
        if self.details:
            details_str = ", ".join([f"{k}={v}" for k, v in self.details.items()])
            return f"{base_msg} (详情: {details_str})"
        return base_msg


class DicomReadError(DICOM2NIIError):
    """DICOM文件读取错误"""
    
    def __init__(self, file_path: str, message: str = "DICOM文件读取失败"):
        super().__init__(
            message=message,
            error_code="DICOM_READ_ERROR",
            details={"file_path": file_path}
        )


class DicomValidationError(DICOM2NIIError):
    """DICOM文件验证错误"""
    
    def __init__(self, validation_type: str, message: str = "DICOM文件验证失败"):
        super().__init__(
            message=message,
            error_code="DICOM_VALIDATION_ERROR",
            details={"validation_type": validation_type}
        )


class ConversionError(DICOM2NIIError):
    """转换过程错误"""
    
    def __init__(self, converter_type: str, message: str = "文件转换失败"):
        super().__init__(
            message=message,
            error_code="CONVERSION_ERROR", 
            details={"converter_type": converter_type}
        )


class ProcessingError(DICOM2NIIError):
    """图像处理错误"""
    
    def __init__(self, processing_step: str, message: str = "图像处理失败"):
        super().__init__(
            message=message,
            error_code="PROCESSING_ERROR",
            details={"processing_step": processing_step}
        )


class ConfigurationError(DICOM2NIIError):
    """配置错误"""
    
    def __init__(self, config_key: str, message: str = "配置参数错误"):
        super().__init__(
            message=message,
            error_code="CONFIG_ERROR",
            details={"config_key": config_key}
        )


class AuthenticationError(DICOM2NIIError):
    """授权验证错误"""
    
    def __init__(self, auth_type: str, message: str = "授权验证失败"):
        super().__init__(
            message=message,
            error_code="AUTH_ERROR",
            details={"auth_type": auth_type}
        )


class FileSystemError(DICOM2NIIError):
    """文件系统错误"""
    
    def __init__(self, operation: str, path: str, message: str = "文件系统操作失败"):
        super().__init__(
            message=message,
            error_code="FILESYSTEM_ERROR",
            details={"operation": operation, "path": path}
        )


class UnsupportedModalityError(DICOM2NIIError):
    """不支持的影像模态错误"""
    
    def __init__(self, modality: str, message: str = "不支持的影像模态"):
        super().__init__(
            message=message,
            error_code="UNSUPPORTED_MODALITY",
            details={"modality": modality}
        )


class MemoryError(DICOM2NIIError):
    """内存不足错误"""
    
    def __init__(self, required_memory: str, message: str = "内存不足"):
        super().__init__(
            message=message,
            error_code="MEMORY_ERROR",
            details={"required_memory": required_memory}
        )


# 错误代码映射
ERROR_CODE_MAP = {
    "DICOM_READ_ERROR": "DICOM文件读取失败",
    "DICOM_VALIDATION_ERROR": "DICOM文件验证失败", 
    "CONVERSION_ERROR": "文件转换失败",
    "PROCESSING_ERROR": "图像处理失败",
    "CONFIG_ERROR": "配置参数错误",
    "AUTH_ERROR": "授权验证失败",
    "FILESYSTEM_ERROR": "文件系统操作失败",
    "UNSUPPORTED_MODALITY": "不支持的影像模态",
    "MEMORY_ERROR": "内存不足",
    "UNKNOWN": "未知错误"
}


def get_error_description(error_code: str) -> str:
    """
    根据错误代码获取错误描述
    
    Args:
        error_code: 错误代码
        
    Returns:
        错误描述信息
    """
    return ERROR_CODE_MAP.get(error_code, ERROR_CODE_MAP["UNKNOWN"]) 