#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文件名: settings.py
功能描述: DICOM2NII Pro 配置管理系统
创建日期: 2025-01-23
作者: Claude AI Assistant
版本: v0.1.0-dev

提供应用程序配置管理，包括默认设置、用户设置和运行时配置。
"""

import os
import json
import yaml
from pathlib import Path
from typing import Dict, Any, Optional, Union
from dataclasses import dataclass, asdict, field
from ..core.exceptions import ConfigurationError


@dataclass
class ConversionSettings:
    """转换设置配置类"""
    
    # 输出格式设置
    output_format: str = "nii.gz"
    compression_level: int = 6
    data_type: str = "float32"
    
    # 图像处理设置
    orientation: str = "LPS"  # 图像方向标准
    matrix_size: Optional[tuple] = None  # 目标矩阵大小
    voxel_size: Optional[tuple] = None   # 目标体素大小
    
    # 预处理设置
    normalize_orientation: bool = True
    apply_rescale: bool = True
    remove_sensitive_info: bool = True
    
    # 质量控制设置
    validate_dicom: bool = True
    check_completeness: bool = True
    verify_output: bool = True
    
    # 性能设置
    max_memory_gb: float = 8.0
    use_parallel_processing: bool = True
    num_threads: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConversionSettings':
        """从字典创建配置"""
        return cls(**data)


@dataclass 
class UISettings:
    """用户界面设置"""
    
    # 主题设置
    theme: str = "light"  # light, dark, auto
    language: str = "zh-CN"  # zh-CN, en-US
    
    # 窗口设置
    window_width: int = 1200
    window_height: int = 800
    remember_geometry: bool = True
    
    # 界面行为
    show_progress_details: bool = True
    auto_clear_completed: bool = False
    confirm_before_exit: bool = True
    
    # 文件浏览设置
    default_input_dir: str = ""
    default_output_dir: str = ""
    remember_last_dirs: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UISettings':
        """从字典创建配置"""
        return cls(**data)


@dataclass
class LoggingSettings:
    """日志设置"""
    
    # 日志级别
    level: str = "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL
    
    # 文件日志设置
    log_to_file: bool = True
    log_file_path: str = "logs/app.log"
    max_file_size_mb: int = 10
    backup_count: int = 5
    
    # 控制台日志设置
    log_to_console: bool = True
    console_level: str = "INFO"
    
    # 日志格式
    file_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s"
    console_format: str = "%(levelname)s - %(message)s"
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LoggingSettings':
        """从字典创建配置"""
        return cls(**data)


@dataclass
class AuthSettings:
    """授权设置"""
    
    # 授权模式
    require_license: bool = True
    trial_conversions: int = 3
    
    # 授权文件
    license_file: str = "license.key"
    machine_id_file: str = ".machine_id"
    
    # 授权验证
    check_interval_hours: int = 24
    offline_grace_period_days: int = 7
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AuthSettings':
        """从字典创建配置"""
        return cls(**data)


class Settings:
    """应用程序设置管理器"""
    
    def __init__(self, config_dir: Optional[Path] = None):
        """
        初始化设置管理器
        
        Args:
            config_dir: 配置文件目录，默认为程序目录下的config
        """
        if config_dir is None:
            config_dir = Path(__file__).parent.parent.parent / "config"
        
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(exist_ok=True)
        
        # 配置文件路径
        self.config_file = self.config_dir / "settings.yaml"
        self.user_config_file = self.config_dir / "user_settings.yaml"
        
        # 初始化默认设置
        self.conversion = ConversionSettings()
        self.ui = UISettings()
        self.logging = LoggingSettings()
        self.auth = AuthSettings()
        
        # 加载配置
        self.load_config()
    
    def load_config(self) -> None:
        """加载配置文件"""
        try:
            # 加载默认配置
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config_data = yaml.safe_load(f)
                    self._load_from_dict(config_data)
            
            # 加载用户配置（覆盖默认配置）
            if self.user_config_file.exists():
                with open(self.user_config_file, 'r', encoding='utf-8') as f:
                    user_config_data = yaml.safe_load(f)
                    self._load_from_dict(user_config_data)
                    
        except Exception as e:
            raise ConfigurationError("config_load", f"配置文件加载失败: {e}")
    
    def save_config(self, save_user_config: bool = True) -> None:
        """
        保存配置文件
        
        Args:
            save_user_config: 是否保存用户配置文件
        """
        try:
            config_data = self.to_dict()
            
            if save_user_config:
                # 保存用户配置
                with open(self.user_config_file, 'w', encoding='utf-8') as f:
                    yaml.dump(config_data, f, default_flow_style=False, 
                             allow_unicode=True, indent=2)
            else:
                # 保存默认配置
                with open(self.config_file, 'w', encoding='utf-8') as f:
                    yaml.dump(config_data, f, default_flow_style=False,
                             allow_unicode=True, indent=2)
                    
        except Exception as e:
            raise ConfigurationError("config_save", f"配置文件保存失败: {e}")
    
    def _load_from_dict(self, config_data: Dict[str, Any]) -> None:
        """从字典加载配置"""
        if 'conversion' in config_data:
            self.conversion = ConversionSettings.from_dict(config_data['conversion'])
        
        if 'ui' in config_data:
            self.ui = UISettings.from_dict(config_data['ui'])
        
        if 'logging' in config_data:
            self.logging = LoggingSettings.from_dict(config_data['logging'])
        
        if 'auth' in config_data:
            self.auth = AuthSettings.from_dict(config_data['auth'])
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'conversion': self.conversion.to_dict(),
            'ui': self.ui.to_dict(),
            'logging': self.logging.to_dict(),
            'auth': self.auth.to_dict()
        }
    
    def reset_to_defaults(self) -> None:
        """重置为默认设置"""
        self.conversion = ConversionSettings()
        self.ui = UISettings()
        self.logging = LoggingSettings()
        self.auth = AuthSettings()
    
    def get_setting(self, key: str, default: Any = None) -> Any:
        """
        获取设置值
        
        Args:
            key: 设置键，支持点号分隔的嵌套键
            default: 默认值
            
        Returns:
            设置值
        """
        try:
            keys = key.split('.')
            obj = self
            
            for k in keys:
                obj = getattr(obj, k)
            
            return obj
        except AttributeError:
            return default
    
    def set_setting(self, key: str, value: Any) -> None:
        """
        设置配置值
        
        Args:
            key: 设置键，支持点号分隔的嵌套键
            value: 设置值
        """
        try:
            keys = key.split('.')
            obj = self
            
            # 导航到最后一个属性的父对象
            for k in keys[:-1]:
                obj = getattr(obj, k)
            
            # 设置最后一个属性
            setattr(obj, keys[-1], value)
        except AttributeError:
            raise ConfigurationError(key, f"无效的配置键: {key}")


# 全局设置实例
settings = Settings() 