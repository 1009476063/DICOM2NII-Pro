#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文件名: license_manager.py
功能描述: 离线授权系统核心模块
创建日期: 2025-01-23
作者: Claude AI Assistant
版本: v0.1.0-dev

实现基于硬件指纹的离线授权验证系统
"""

import os
import json
import hashlib
import platform
import uuid
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
import logging

try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    import base64
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False


@dataclass
class LicenseInfo:
    """授权信息数据类"""
    license_key: str
    hardware_id: str
    expire_date: str
    user_name: str
    organization: str
    license_type: str  # trial, standard, professional, enterprise
    max_conversions: int = -1  # -1表示无限制
    features: Dict[str, bool] = None
    
    def __post_init__(self):
        if self.features is None:
            self.features = {}
    
    @property
    def is_expired(self) -> bool:
        """检查授权是否过期"""
        try:
            expire_dt = datetime.strptime(self.expire_date, "%Y-%m-%d")
            return datetime.now() > expire_dt
        except ValueError:
            return True
    
    @property
    def days_remaining(self) -> int:
        """剩余天数"""
        try:
            expire_dt = datetime.strptime(self.expire_date, "%Y-%m-%d")
            remaining = (expire_dt - datetime.now()).days
            return max(0, remaining)
        except ValueError:
            return 0


class HardwareFingerprint:
    """硬件指纹生成器"""
    
    @staticmethod
    def get_machine_id() -> str:
        """获取机器唯一标识"""
        # 获取各种硬件信息
        machine_info = []
        
        # CPU信息
        try:
            if platform.system() == "Windows":
                import subprocess
                result = subprocess.run(
                    ["wmic", "cpu", "get", "ProcessorId", "/value"],
                    capture_output=True, text=True
                )
                for line in result.stdout.split('\n'):
                    if line.startswith('ProcessorId='):
                        machine_info.append(line.split('=')[1].strip())
                        break
            else:
                # Linux/Mac - 使用/proc/cpuinfo或其他方法
                try:
                    with open('/proc/cpuinfo', 'r') as f:
                        for line in f:
                            if 'serial' in line.lower():
                                machine_info.append(line.split(':')[1].strip())
                                break
                except FileNotFoundError:
                    pass
        except Exception:
            pass
        
        # MAC地址
        try:
            mac = hex(uuid.getnode())[2:].upper()
            machine_info.append(mac)
        except Exception:
            pass
        
        # 主板序列号
        try:
            if platform.system() == "Windows":
                import subprocess
                result = subprocess.run(
                    ["wmic", "baseboard", "get", "SerialNumber", "/value"],
                    capture_output=True, text=True
                )
                for line in result.stdout.split('\n'):
                    if line.startswith('SerialNumber='):
                        machine_info.append(line.split('=')[1].strip())
                        break
        except Exception:
            pass
        
        # 如果没有获取到硬件信息，使用备用方案
        if not machine_info:
            machine_info = [
                platform.node(),  # 计算机名
                platform.platform(),  # 平台信息
                str(uuid.uuid4())  # 随机UUID作为最后备用
            ]
        
        # 生成硬件指纹
        combined = '|'.join(machine_info)
        return hashlib.sha256(combined.encode()).hexdigest()[:16]
    
    @staticmethod
    def validate_hardware_id(stored_id: str) -> bool:
        """验证硬件ID是否匹配"""
        current_id = HardwareFingerprint.get_machine_id()
        return stored_id == current_id


class LicenseManager:
    """授权管理器"""
    
    def __init__(self, app_name: str = "MICS"):
        """
        初始化授权管理器
        
        Args:
            app_name: 应用程序名称
        """
        self.app_name = app_name
        self.logger = logging.getLogger(__name__)
        
        # 授权文件路径
        if platform.system() == "Windows":
            self.license_dir = Path.home() / "AppData" / "Local" / app_name
        else:
            self.license_dir = Path.home() / f".{app_name.lower()}"
        
        self.license_file = self.license_dir / "license.dat"
        self.config_file = self.license_dir / "config.json"
        
        # 确保目录存在
        self.license_dir.mkdir(parents=True, exist_ok=True)
        
        # 加密密钥
        self.encryption_key = None
        if CRYPTO_AVAILABLE:
            self._init_encryption()
        
        # 当前授权信息
        self.current_license: Optional[LicenseInfo] = None
        self.load_license()
    
    def _init_encryption(self):
        """初始化加密"""
        if not CRYPTO_AVAILABLE:
            return
        
        # 基于硬件指纹生成加密密钥
        hardware_id = HardwareFingerprint.get_machine_id()
        password = f"{self.app_name}_{hardware_id}".encode()
        salt = b'MICS_SALT_2025'
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password))
        self.encryption_key = Fernet(key)
    
    def _encrypt_data(self, data: str) -> str:
        """加密数据"""
        if not CRYPTO_AVAILABLE or not self.encryption_key:
            # 如果没有加密库，使用简单的编码
            return base64.b64encode(data.encode()).decode()
        
        return self.encryption_key.encrypt(data.encode()).decode()
    
    def _decrypt_data(self, encrypted_data: str) -> str:
        """解密数据"""
        if not CRYPTO_AVAILABLE or not self.encryption_key:
            # 如果没有加密库，使用简单的解码
            try:
                return base64.b64decode(encrypted_data.encode()).decode()
            except Exception:
                raise ValueError("授权文件损坏")
        
        try:
            return self.encryption_key.decrypt(encrypted_data.encode()).decode()
        except Exception:
            raise ValueError("授权文件损坏或被篡改")
    
    def generate_trial_license(self, days: int = 30) -> LicenseInfo:
        """
        生成试用授权
        
        Args:
            days: 试用天数
            
        Returns:
            试用授权信息
        """
        hardware_id = HardwareFingerprint.get_machine_id()
        expire_date = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d")
        
        license_info = LicenseInfo(
            license_key=f"TRIAL-{hardware_id[:8]}-{datetime.now().strftime('%Y%m%d')}",
            hardware_id=hardware_id,
            expire_date=expire_date,
            user_name="Trial User",
            organization="Trial Organization",
            license_type="trial",
            max_conversions=100,  # 试用版限制100次转换
            features={
                "basic_conversion": True,
                "batch_processing": True,
                "advanced_settings": False,
                "plugin_support": False,
                "commercial_use": False
            }
        )
        
        return license_info
    
    def install_license(self, license_data: str) -> Tuple[bool, str]:
        """
        安装授权
        
        Args:
            license_data: 授权数据字符串
            
        Returns:
            (是否成功, 消息)
        """
        try:
            # 解析授权数据
            license_info = self._parse_license_data(license_data)
            
            # 验证硬件指纹
            if not HardwareFingerprint.validate_hardware_id(license_info.hardware_id):
                return False, "授权与当前硬件不匹配"
            
            # 验证授权是否过期
            if license_info.is_expired:
                return False, f"授权已过期（过期日期：{license_info.expire_date}）"
            
            # 保存授权
            self.save_license(license_info)
            self.current_license = license_info
            
            return True, f"授权安装成功，有效期至：{license_info.expire_date}"
            
        except Exception as e:
            return False, f"授权安装失败：{str(e)}"
    
    def _parse_license_data(self, license_data: str) -> LicenseInfo:
        """解析授权数据"""
        try:
            # 这里应该包含更复杂的验证逻辑
            # 简化版本：假设license_data是JSON格式
            if license_data.startswith('{'):
                data = json.loads(license_data)
            else:
                # 假设是base64编码的JSON
                decoded = base64.b64decode(license_data).decode()
                data = json.loads(decoded)
            
            # 过滤掉LicenseInfo类不需要的字段
            valid_fields = {
                'license_key', 'hardware_id', 'expire_date', 'user_name',
                'organization', 'license_type', 'max_conversions', 'features'
            }
            filtered_data = {k: v for k, v in data.items() if k in valid_fields}
            
            return LicenseInfo(**filtered_data)
            
        except Exception as e:
            raise ValueError(f"无效的授权数据格式：{e}")
    
    def save_license(self, license_info: LicenseInfo):
        """保存授权信息"""
        try:
            # 序列化授权信息
            license_dict = asdict(license_info)
            license_json = json.dumps(license_dict, ensure_ascii=False, indent=2)
            
            # 加密并保存
            encrypted_data = self._encrypt_data(license_json)
            
            with open(self.license_file, 'w', encoding='utf-8') as f:
                f.write(encrypted_data)
            
            self.logger.info("授权信息保存成功")
            
        except Exception as e:
            self.logger.error(f"保存授权信息失败：{e}")
            raise
    
    def load_license(self) -> Optional[LicenseInfo]:
        """加载授权信息"""
        try:
            if not self.license_file.exists():
                return None
            
            with open(self.license_file, 'r', encoding='utf-8') as f:
                encrypted_data = f.read().strip()
            
            # 解密数据
            license_json = self._decrypt_data(encrypted_data)
            license_dict = json.loads(license_json)
            
            license_info = LicenseInfo(**license_dict)
            
            # 验证硬件指纹
            if not HardwareFingerprint.validate_hardware_id(license_info.hardware_id):
                self.logger.warning("硬件指纹不匹配，授权可能被非法复制")
                return None
            
            self.current_license = license_info
            return license_info
            
        except Exception as e:
            self.logger.warning(f"加载授权信息失败：{e}")
            return None
    
    def validate_license(self) -> Tuple[bool, str]:
        """
        验证当前授权
        
        Returns:
            (是否有效, 状态消息)
        """
        if not self.current_license:
            return False, "未找到有效授权"
        
        # 检查过期时间
        if self.current_license.is_expired:
            return False, f"授权已过期（过期日期：{self.current_license.expire_date}）"
        
        # 检查硬件指纹
        if not HardwareFingerprint.validate_hardware_id(self.current_license.hardware_id):
            return False, "硬件指纹不匹配"
        
        return True, f"授权有效，剩余 {self.current_license.days_remaining} 天"
    
    def check_feature(self, feature_name: str) -> bool:
        """
        检查功能授权
        
        Args:
            feature_name: 功能名称
            
        Returns:
            是否有权限使用该功能
        """
        if not self.current_license:
            return False
        
        return self.current_license.features.get(feature_name, False)
    
    def get_license_info(self) -> Optional[LicenseInfo]:
        """获取当前授权信息"""
        return self.current_license
    
    def remove_license(self):
        """移除授权"""
        try:
            if self.license_file.exists():
                self.license_file.unlink()
            self.current_license = None
            self.logger.info("授权已移除")
        except Exception as e:
            self.logger.error(f"移除授权失败：{e}")
    
    def get_hardware_id(self) -> str:
        """获取当前硬件ID"""
        return HardwareFingerprint.get_machine_id()
    
    def export_hardware_info(self) -> Dict[str, Any]:
        """导出硬件信息用于生成授权"""
        return {
            "hardware_id": self.get_hardware_id(),
            "platform": platform.platform(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "node": platform.node(),
            "timestamp": datetime.now().isoformat()
        }


# 全局授权管理器实例
license_manager = LicenseManager("MICS")


def require_license(feature: str = None):
    """
    授权装饰器
    
    Args:
        feature: 需要的功能权限
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            # 验证基本授权
            is_valid, message = license_manager.validate_license()
            if not is_valid:
                raise PermissionError(f"授权验证失败：{message}")
            
            # 验证功能权限
            if feature and not license_manager.check_feature(feature):
                raise PermissionError(f"无权限使用功能：{feature}")
            
            return func(*args, **kwargs)
        return wrapper
    return decorator 