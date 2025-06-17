#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文件名: license_generator.py
功能描述: MICS许可证生成器工具
创建日期: 2025-06-01
作者: TanX
版本: v1.0.0

用于生成和管理MICS软件的授权许可证
"""

import json
import base64
import hashlib
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from pathlib import Path
import secrets

from .license_manager import LicenseInfo


class LicenseGenerator:
    """许可证生成器"""
    
    def __init__(self, master_key: str = "MICS_MASTER_KEY_2025"):
        """
        初始化许可证生成器
        
        Args:
            master_key: 主密钥
        """
        self.master_key = master_key
        self.signature_key = hashlib.sha256(master_key.encode()).hexdigest()
    
    def generate_license_key(self, license_type: str, hardware_id: str) -> str:
        """
        生成许可证密钥
        
        Args:
            license_type: 许可证类型
            hardware_id: 硬件ID
            
        Returns:
            许可证密钥
        """
        # 生成基础密钥
        timestamp = datetime.now().strftime("%Y%m%d")
        random_part = secrets.token_hex(4).upper()
        
        # 组合密钥
        key_parts = [
            license_type[:4].upper(),
            hardware_id[:8].upper(),
            timestamp,
            random_part
        ]
        
        return "-".join(key_parts)
    
    def create_trial_license(self, hardware_id: str, 
                           user_name: str = "Trial User",
                           organization: str = "Trial Organization",
                           days: int = 30) -> str:
        """
        创建试用许可证
        
        Args:
            hardware_id: 硬件ID
            user_name: 用户名
            organization: 组织名
            days: 试用天数
            
        Returns:
            许可证数据字符串
        """
        expire_date = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d")
        license_key = self.generate_license_key("TRIAL", hardware_id)
        
        license_info = LicenseInfo(
            license_key=license_key,
            hardware_id=hardware_id,
            expire_date=expire_date,
            user_name=user_name,
            organization=organization,
            license_type="trial",
            max_conversions=100,
            features={
                "basic_conversion": True,
                "batch_processing": True,
                "advanced_settings": False,
                "plugin_support": False,
                "commercial_use": False
            }
        )
        
        return self._encode_license(license_info)
    
    def create_standard_license(self, hardware_id: str,
                              user_name: str,
                              organization: str,
                              expire_date: str) -> str:
        """
        创建标准许可证
        
        Args:
            hardware_id: 硬件ID
            user_name: 用户名
            organization: 组织名
            expire_date: 过期日期 (YYYY-MM-DD)
            
        Returns:
            许可证数据字符串
        """
        license_key = self.generate_license_key("STD", hardware_id)
        
        license_info = LicenseInfo(
            license_key=license_key,
            hardware_id=hardware_id,
            expire_date=expire_date,
            user_name=user_name,
            organization=organization,
            license_type="standard",
            max_conversions=-1,  # 无限制
            features={
                "basic_conversion": True,
                "batch_processing": True,
                "advanced_settings": True,
                "plugin_support": False,
                "commercial_use": True
            }
        )
        
        return self._encode_license(license_info)
    
    def create_professional_license(self, hardware_id: str,
                                   user_name: str,
                                   organization: str,
                                   expire_date: str) -> str:
        """
        创建专业许可证
        
        Args:
            hardware_id: 硬件ID
            user_name: 用户名
            organization: 组织名
            expire_date: 过期日期 (YYYY-MM-DD)
            
        Returns:
            许可证数据字符串
        """
        license_key = self.generate_license_key("PRO", hardware_id)
        
        license_info = LicenseInfo(
            license_key=license_key,
            hardware_id=hardware_id,
            expire_date=expire_date,
            user_name=user_name,
            organization=organization,
            license_type="professional",
            max_conversions=-1,
            features={
                "basic_conversion": True,
                "batch_processing": True,
                "advanced_settings": True,
                "plugin_support": True,
                "commercial_use": True
            }
        )
        
        return self._encode_license(license_info)
    
    def create_enterprise_license(self, hardware_id: str,
                                 user_name: str,
                                 organization: str,
                                 expire_date: str) -> str:
        """
        创建企业许可证
        
        Args:
            hardware_id: 硬件ID
            user_name: 用户名
            organization: 组织名
            expire_date: 过期日期 (YYYY-MM-DD)
            
        Returns:
            许可证数据字符串
        """
        license_key = self.generate_license_key("ENT", hardware_id)
        
        license_info = LicenseInfo(
            license_key=license_key,
            hardware_id=hardware_id,
            expire_date=expire_date,
            user_name=user_name,
            organization=organization,
            license_type="enterprise",
            max_conversions=-1,
            features={
                "basic_conversion": True,
                "batch_processing": True,
                "advanced_settings": True,
                "plugin_support": True,
                "commercial_use": True,
                "priority_support": True,
                "custom_features": True
            }
        )
        
        return self._encode_license(license_info)
    
    def _encode_license(self, license_info: LicenseInfo) -> str:
        """
        编码许可证信息
        
        Args:
            license_info: 许可证信息
            
        Returns:
            编码后的许可证字符串
        """
        # 转换为字典
        license_dict = {
            "license_key": license_info.license_key,
            "hardware_id": license_info.hardware_id,
            "expire_date": license_info.expire_date,
            "user_name": license_info.user_name,
            "organization": license_info.organization,
            "license_type": license_info.license_type,
            "max_conversions": license_info.max_conversions,
            "features": license_info.features
        }
        
        # 添加签名
        license_dict["signature"] = self._generate_signature(license_dict)
        license_dict["timestamp"] = datetime.now().isoformat()
        
        # JSON序列化并Base64编码
        license_json = json.dumps(license_dict, ensure_ascii=False)
        encoded = base64.b64encode(license_json.encode()).decode()
        
        return encoded
    
    def _generate_signature(self, license_dict: Dict[str, Any]) -> str:
        """
        生成许可证签名
        
        Args:
            license_dict: 许可证字典
            
        Returns:
            签名字符串
        """
        # 创建用于签名的字符串
        sign_data = f"{license_dict['license_key']}{license_dict['hardware_id']}{license_dict['expire_date']}{self.signature_key}"
        
        # 生成SHA256签名
        signature = hashlib.sha256(sign_data.encode()).hexdigest()[:16]
        
        return signature
    
    def validate_license_data(self, license_data: str) -> bool:
        """
        验证许可证数据
        
        Args:
            license_data: 许可证数据字符串
            
        Returns:
            是否有效
        """
        try:
            # 解码
            decoded = base64.b64decode(license_data).decode()
            license_dict = json.loads(decoded)
            
            # 验证签名
            stored_signature = license_dict.pop("signature", "")
            calculated_signature = self._generate_signature(license_dict)
            
            return stored_signature == calculated_signature
            
        except Exception:
            return False
    
    def save_license_file(self, license_data: str, output_file: Path):
        """
        保存许可证到文件
        
        Args:
            license_data: 许可证数据
            output_file: 输出文件路径
        """
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(license_data)


def main():
    """命令行工具主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="MICS许可证生成器")
    parser.add_argument("--type", choices=["trial", "standard", "professional", "enterprise"],
                       required=True, help="许可证类型")
    parser.add_argument("--hardware-id", required=True, help="硬件ID")
    parser.add_argument("--user-name", required=True, help="用户名")
    parser.add_argument("--organization", required=True, help="组织名")
    parser.add_argument("--expire-date", help="过期日期 (YYYY-MM-DD)")
    parser.add_argument("--days", type=int, default=30, help="试用天数（仅试用版）")
    parser.add_argument("--output", help="输出文件路径")
    
    args = parser.parse_args()
    
    generator = LicenseGenerator()
    
    # 生成许可证
    if args.type == "trial":
        license_data = generator.create_trial_license(
            args.hardware_id, args.user_name, args.organization, args.days
        )
    elif args.type == "standard":
        if not args.expire_date:
            print("标准许可证需要指定过期日期")
            return
        license_data = generator.create_standard_license(
            args.hardware_id, args.user_name, args.organization, args.expire_date
        )
    elif args.type == "professional":
        if not args.expire_date:
            print("专业许可证需要指定过期日期")
            return
        license_data = generator.create_professional_license(
            args.hardware_id, args.user_name, args.organization, args.expire_date
        )
    elif args.type == "enterprise":
        if not args.expire_date:
            print("企业许可证需要指定过期日期")
            return
        license_data = generator.create_enterprise_license(
            args.hardware_id, args.user_name, args.organization, args.expire_date
        )
    
    # 输出许可证
    if args.output:
        generator.save_license_file(license_data, Path(args.output))
        print(f"许可证已保存到: {args.output}")
    else:
        print("许可证数据:")
        print(license_data)


if __name__ == "__main__":
    main() 