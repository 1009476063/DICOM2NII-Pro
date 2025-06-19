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
from typing import Dict, Any, Optional, Tuple, List
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
import logging
import secrets
import base64

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


class IGPSLicenseManager:
    """IGPS授权管理器"""

    # 这是本软件唯一的应用密钥，确保授权码的专有性。
    # 警告：请勿泄露或修改此密钥，否则所有已生成的授权码将失效。
    APP_SECRET = "IGPS_TANX_RADIOMICS_PLATFORM_SECRET_KEY_2025"
    
    def __init__(self, config_dir: str = None):
        """初始化授权管理器"""
        self.config_dir = config_dir or os.path.join(os.getcwd(), "config")
        self.license_file = os.path.join(self.config_dir, "license.json")
        self.trial_file = os.path.join(self.config_dir, "trial.json")
        
        # 确保配置目录存在
        os.makedirs(self.config_dir, exist_ok=True)
        
        # 不再在内存中保存所有许可，而是按需验证
        # self.builtin_licenses = self._generate_builtin_licenses()
        
        # 初始化状态
        self._load_license_data()
        self._load_trial_data()
        
    def _generate_builtin_licenses(self, count=1000) -> List[str]:
        """生成指定数量的内置授权码，仅用于生成脚本。"""
        licenses = []
        base_seed = "IGPS-PRO-2025-USER"
        
        for i in range(count):
            # 创建基于应用密钥、索引和基础种子的授权码
            data = f"{self.APP_SECRET}-{base_seed}-{i:04d}"
            hash_obj = hashlib.sha256(data.encode())
            license_hash = hash_obj.hexdigest()[:16].upper()
            
            # 格式化为 XXXX-XXXX-XXXX-XXXX 格式
            formatted_license = f"{license_hash[:4]}-{license_hash[4:8]}-{license_hash[8:12]}-{license_hash[12:16]}"
            licenses.append(formatted_license)
            
        return licenses
        
    def _load_license_data(self):
        """加载授权数据"""
        self.license_data = {}
        if os.path.exists(self.license_file):
            try:
                with open(self.license_file, 'r', encoding='utf-8') as f:
                    self.license_data = json.load(f)
            except Exception as e:
                print(f"加载授权数据失败: {e}")
                
    def _save_license_data(self):
        """保存授权数据"""
        try:
            with open(self.license_file, 'w', encoding='utf-8') as f:
                json.dump(self.license_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存授权数据失败: {e}")
            
    def _load_trial_data(self):
        """加载试用数据"""
        self.trial_data = {"used_count": 0, "first_use": None}
        if os.path.exists(self.trial_file):
            try:
                with open(self.trial_file, 'r', encoding='utf-8') as f:
                    self.trial_data = json.load(f)
            except Exception as e:
                print(f"加载试用数据失败: {e}")
                
    def _save_trial_data(self):
        """保存试用数据"""
        try:
            with open(self.trial_file, 'w', encoding='utf-8') as f:
                json.dump(self.trial_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存试用数据失败: {e}")
            
    def get_hardware_fingerprint(self) -> str:
        """获取硬件指纹"""
        try:
            # 收集系统信息
            system_info = {
                'platform': platform.system(),
                'processor': platform.processor(),
                'machine': platform.machine(),
                'node': platform.node()
            }
            
            # 尝试获取更多硬件信息
            try:
                mac_address = ':'.join(['{:02x}'.format((uuid.getnode() >> i) & 0xff) 
                                      for i in range(0, 8*6, 8)][::-1])
                system_info['mac'] = mac_address
            except:
                pass
                
            # 创建指纹
            info_str = json.dumps(system_info, sort_keys=True)
            fingerprint = hashlib.sha256(info_str.encode()).hexdigest()[:16]
            return fingerprint
            
        except Exception as e:
            print(f"获取硬件指纹失败: {e}")
            return "default_fingerprint"
            
    def verify_builtin_license(self, license_code: str) -> bool:
        """
        验证一个授权码是否是理论上有效的内置授权码。
        这只检查码的格式和来源，不检查其是否已被激活。
        """
        if not self.validate_license_format(license_code):
            return False

        base_seed = "IGPS-PRO-2025-USER"
        # 此处我们假设内置授权码的数量上限为1000，与生成器保持一致
        for i in range(1000):
            # 使用与生成时完全相同的算法来验证
            data = f"{self.APP_SECRET}-{base_seed}-{i:04d}"
            hash_obj = hashlib.sha256(data.encode())
            license_hash = hash_obj.hexdigest()[:16].upper()
            
            expected_license = f"{license_hash[:4]}-{license_hash[4:8]}-{license_hash[8:12]}-{license_hash[12:16]}"
            
            if secrets.compare_digest(expected_license, license_code):
                # 只要找到一个匹配的，就证明这个码是合法的
                return True
        
        # 遍历完所有可能性都未找到，则为非法码
        return False

    def activate_license(self, license_code: str, user_name: str, organization: str) -> Tuple[bool, str]:
        """
        激活一个全新的授权码。
        """
        # 1. 验证是否为本软件的合法授权码
        if not self.verify_builtin_license(license_code):
            return False, "授权码无效或不属于本软件。"

        # 2. 检查授权码是否已经被激活
        if license_code in self.license_data:
            return False, "此授权码已被激活，请勿重复使用。"

        # 3. 如果未激活，则创建新的授权记录
        hardware_id = self.get_hardware_fingerprint()
        activation_date = datetime.now()
        # 有效期设置为90天
        expire_date = activation_date + timedelta(days=90)

        new_license_info = LicenseInfo(
            license_key=license_code,
            hardware_id=hardware_id,
            expire_date=expire_date.strftime("%Y-%m-%d"),
            user_name=user_name,
            organization=organization,
            license_type='standard', # 默认为标准版
        )

        self.license_data[license_code] = asdict(new_license_info)
        self._save_license_data()

        return True, "软件激活成功！"
        
    def is_licensed(self) -> bool:
        """检查当前环境是否有一个有效的、已激活的许可证"""
        hardware_id = self.get_hardware_fingerprint()

        for code, info_dict in self.license_data.items():
            current_info = info_dict.copy()
            # 兼容旧版可能存在的字段
            current_info.pop('activation_date', None)
            if 'expiry_date' in current_info:
                current_info['expire_date'] = current_info.pop('expiry_date')

            try:
                info = LicenseInfo(**current_info)
                if info.hardware_id == hardware_id and not info.is_expired:
                    # 找到一个与当前硬件匹配且未过期的授权
                    return True
            except TypeError:
                continue  # Skip malformed entries
        
        return False
        
    def get_license_info(self) -> Optional[LicenseInfo]:
        """获取当前环境下已激活的有效授权信息"""
        hardware_id = self.get_hardware_fingerprint()
        for code, info_dict in self.license_data.items():
            current_info = info_dict.copy()
            # 兼容旧版可能存在的字段
            current_info.pop('activation_date', None)
            if 'expiry_date' in current_info:
                current_info['expire_date'] = current_info.pop('expiry_date')

            try:
                info = LicenseInfo(**current_info)
                if info.hardware_id == hardware_id and not info.is_expired:
                    return info
            except TypeError:
                continue
        return None

    def can_use_trial(self) -> bool:
        """检查是否可以使用试用"""
        return self.trial_data["used_count"] < 3
        
    def use_trial(self) -> bool:
        """使用一次试用"""
        if not self.can_use_trial():
            return False
            
        current_time = datetime.now()
        
        if self.trial_data["first_use"] is None:
            self.trial_data["first_use"] = current_time.isoformat()
            
        self.trial_data["used_count"] += 1
        self._save_trial_data()
        return True
        
    def get_remaining_trials(self) -> int:
        """获取剩余试用次数"""
        return max(0, 3 - self.trial_data["used_count"])
        
    def reset_trial(self) -> bool:
        """重置试用次数（仅用于开发测试）"""
        self.trial_data = {"used_count": 0, "first_use": None}
        self._save_trial_data()
        return True
        
    def revoke_license(self, license_code: str) -> bool:
        """撤销授权"""
        if license_code in self.license_data:
            self.license_data[license_code]['status'] = 'revoked'
            self._save_license_data()
            return True
        return False
        
    def list_active_licenses(self) -> List[Dict]:
        """列出所有活跃的授权"""
        active_licenses = []
        current_time = datetime.now()
        
        for license_code, license_info in self.license_data.items():
            if license_info.get('status') == 'active':
                try:
                    expiry_date = datetime.fromisoformat(license_info['expiry_date'])
                    is_expired = current_time > expiry_date
                    days_remaining = (expiry_date - current_time).days if not is_expired else 0
                    
                    active_licenses.append({
                        'license_code': license_code,
                        'activation_date': license_info['activation_date'],
                        'expiry_date': license_info['expiry_date'],
                        'hardware_fingerprint': license_info.get('hardware_fingerprint', 'Unknown'),
                        'is_expired': is_expired,
                        'days_remaining': days_remaining
                    })
                except:
                    continue
                    
        return active_licenses
        
    def export_builtin_licenses(self, output_file: str) -> bool:
        """导出内置授权码到文件"""
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write("# MICS 授权码列表\n")
                f.write("# 每个授权码有效期：3个月\n")
                f.write("# 每个授权码只能在一台设备上使用\n")
                f.write("# 生成时间：" + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + "\n")
                f.write("# 总数量：1000个\n\n")
                
                for i, license_code in enumerate(self._generate_builtin_licenses(), 1):
                    f.write(f"{i:04d}: {license_code}\n")
                    
            return True
        except Exception as e:
            print(f"导出授权码失败: {e}")
            return False
            
    def validate_license_format(self, license_code: str) -> bool:
        """验证授权码格式"""
        if not license_code:
            return False
            
        # 移除空格和转换为大写
        license_code = license_code.replace(" ", "").upper()
        
        # 检查格式 XXXX-XXXX-XXXX-XXXX
        if len(license_code) != 19:  # 16个字符 + 3个破折号
            return False
            
        parts = license_code.split('-')
        if len(parts) != 4:
            return False
            
        for part in parts:
            if len(part) != 4 or not all(c in '0123456789ABCDEF' for c in part):
                return False
                
        return True


# 全局授权管理器实例
license_manager = IGPSLicenseManager()


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