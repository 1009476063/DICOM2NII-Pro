#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文件名: test_license_system.py
功能描述: MICS授权系统测试工具
创建日期: 2025-06-01
作者: TanX
版本: v1.0.0

测试授权系统的各项功能
"""

import logging
from pathlib import Path
from src.auth.license_manager import LicenseManager, HardwareFingerprint
from src.auth.license_generator import LicenseGenerator

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)


def test_hardware_fingerprint():
    """测试硬件指纹功能"""
    print("🔍 测试硬件指纹功能")
    print("=" * 50)
    
    # 获取硬件ID
    hardware_id = HardwareFingerprint.get_machine_id()
    print(f"当前硬件ID: {hardware_id}")
    
    # 验证硬件ID
    is_valid = HardwareFingerprint.validate_hardware_id(hardware_id)
    print(f"硬件ID验证: {'✅ 通过' if is_valid else '❌ 失败'}")
    
    return hardware_id


def test_license_generator():
    """测试许可证生成器"""
    print("\n🏭 测试许可证生成器")
    print("=" * 50)
    
    generator = LicenseGenerator()
    hardware_id = HardwareFingerprint.get_machine_id()
    
    # 生成试用许可证
    print("生成试用许可证...")
    trial_license = generator.create_trial_license(
        hardware_id=hardware_id,
        user_name="测试用户",
        organization="测试组织",
        days=30
    )
    print(f"试用许可证长度: {len(trial_license)} 字符")
    
    # 验证许可证数据
    is_valid = generator.validate_license_data(trial_license)
    print(f"许可证验证: {'✅ 通过' if is_valid else '❌ 失败'}")
    
    # 生成标准许可证
    print("\n生成标准许可证...")
    standard_license = generator.create_standard_license(
        hardware_id=hardware_id,
        user_name="TanX",
        organization="MICS Solutions",
        expire_date="2026-06-01"
    )
    print(f"标准许可证长度: {len(standard_license)} 字符")
    
    return trial_license, standard_license


def test_license_manager(trial_license: str, standard_license: str):
    """测试许可证管理器"""
    print("\n📋 测试许可证管理器")
    print("=" * 50)
    
    # 创建临时许可证管理器
    manager = LicenseManager("MICS-Test")
    
    # 导出硬件信息
    hardware_info = manager.export_hardware_info()
    print("硬件信息:")
    for key, value in hardware_info.items():
        print(f"  {key}: {value}")
    
    print("\n安装试用许可证...")
    success, message = manager.install_license(trial_license)
    print(f"安装结果: {'✅ ' if success else '❌ '}{message}")
    
    if success:
        # 验证许可证
        is_valid, status = manager.validate_license()
        print(f"许可证状态: {'✅ ' if is_valid else '❌ '}{status}")
        
        # 获取许可证信息
        license_info = manager.get_license_info()
        if license_info:
            print(f"许可证类型: {license_info.license_type}")
            print(f"用户名: {license_info.user_name}")
            print(f"组织: {license_info.organization}")
            print(f"剩余天数: {license_info.days_remaining}")
            print(f"最大转换次数: {license_info.max_conversions}")
            
            # 测试功能权限
            print("\n功能权限检查:")
            for feature, enabled in license_info.features.items():
                status = "✅ 启用" if enabled else "❌ 禁用"
                print(f"  {feature}: {status}")
    
    print("\n安装标准许可证...")
    success, message = manager.install_license(standard_license)
    print(f"安装结果: {'✅ ' if success else '❌ '}{message}")
    
    if success:
        license_info = manager.get_license_info()
        if license_info:
            print(f"新许可证类型: {license_info.license_type}")
            print(f"剩余天数: {license_info.days_remaining}")


def test_license_decorator():
    """测试许可证装饰器"""
    print("\n🎯 测试许可证装饰器")
    print("=" * 50)
    
    from src.auth.license_manager import require_license
    
    @require_license()
    def basic_function():
        return "基础功能执行成功"
    
    @require_license("advanced_settings")
    def advanced_function():
        return "高级功能执行成功"
    
    @require_license("plugin_support")
    def plugin_function():
        return "插件功能执行成功"
    
    # 测试基础功能
    try:
        result = basic_function()
        print(f"基础功能: ✅ {result}")
    except PermissionError as e:
        print(f"基础功能: ❌ {e}")
    
    # 测试高级功能
    try:
        result = advanced_function()
        print(f"高级功能: ✅ {result}")
    except PermissionError as e:
        print(f"高级功能: ❌ {e}")
    
    # 测试插件功能
    try:
        result = plugin_function()
        print(f"插件功能: ✅ {result}")
    except PermissionError as e:
        print(f"插件功能: ❌ {e}")


def test_license_file_operations():
    """测试许可证文件操作"""
    print("\n💾 测试许可证文件操作")
    print("=" * 50)
    
    manager = LicenseManager("MICS-FileTest")
    
    # 生成试用许可证
    generator = LicenseGenerator()
    hardware_id = HardwareFingerprint.get_machine_id()
    
    trial_license = generator.create_trial_license(
        hardware_id=hardware_id,
        user_name="文件测试用户",
        organization="文件测试组织"
    )
    
    # 安装许可证
    success, message = manager.install_license(trial_license)
    print(f"许可证安装: {'✅' if success else '❌'} {message}")
    
    # 重新加载许可证
    manager2 = LicenseManager("MICS-FileTest")
    license_info = manager2.get_license_info()
    
    if license_info:
        print("✅ 许可证文件保存和加载成功")
        print(f"   用户名: {license_info.user_name}")
        print(f"   组织: {license_info.organization}")
    else:
        print("❌ 许可证文件保存或加载失败")
    
    # 清理测试文件
    try:
        manager2.remove_license()
        print("✅ 测试许可证文件已清理")
    except Exception as e:
        print(f"❌ 清理测试文件失败: {e}")


def main():
    """主测试函数"""
    print("🚀 MICS授权系统完整测试")
    print("=" * 80)
    
    try:
        # 1. 测试硬件指纹
        hardware_id = test_hardware_fingerprint()
        
        # 2. 测试许可证生成器
        trial_license, standard_license = test_license_generator()
        
        # 3. 测试许可证管理器
        test_license_manager(trial_license, standard_license)
        
        # 4. 测试许可证装饰器
        test_license_decorator()
        
        # 5. 测试文件操作
        test_license_file_operations()
        
        print("\n🎉 所有授权系统测试完成!")
        print("=" * 80)
        
        # 显示硬件信息供许可证生成使用
        print(f"\n📋 硬件信息（用于许可证申请）:")
        print(f"硬件ID: {hardware_id}")
        
    except Exception as e:
        print(f"\n❌ 测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main() 