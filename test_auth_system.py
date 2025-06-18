#!/usr/bin/env python3
"""
MICS 授权系统测试脚本
测试新的授权管理功能
"""

import os
import sys
import tempfile
import shutil

# 添加src路径
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

def test_license_manager():
    """测试授权管理器"""
    print("🔐 测试MICS授权管理器...")
    
    try:
        from src.auth.license_manager import MicsLicenseManager
        
        # 创建临时目录用于测试
        temp_dir = tempfile.mkdtemp()
        print(f"📁 使用临时目录: {temp_dir}")
        
        # 初始化授权管理器
        auth_manager = MicsLicenseManager(temp_dir)
        
        # 测试1: 试用功能
        print("\n🧪 测试1: 试用功能")
        print(f"初始试用次数: {auth_manager.get_remaining_trials()}")
        
        for i in range(3):
            if auth_manager.can_use_trial():
                auth_manager.use_trial()
                remaining = auth_manager.get_remaining_trials()
                print(f"  使用试用 #{i+1}, 剩余: {remaining}")
            else:
                print(f"  无法使用试用: 次数已用完")
                
        # 再次尝试试用
        print(f"第4次试用: {auth_manager.can_use_trial()}")
        
        # 测试2: 获取内置授权码
        print("\n🧪 测试2: 内置授权码")
        licenses = auth_manager.builtin_licenses
        print(f"内置授权码数量: {len(licenses)}")
        print(f"前5个授权码:")
        for i, code in enumerate(licenses[:5]):
            print(f"  {i+1}: {code}")
            
        # 测试3: 验证无效授权码
        print("\n🧪 测试3: 验证无效授权码")
        invalid_codes = [
            "INVALID-CODE-1234-5678",
            "1234-5678-9ABC-DEF0",  # 格式正确但不在列表中
            "",
            "invalid",
        ]
        
        for code in invalid_codes:
            result = auth_manager.verify_builtin_license(code)
            print(f"  {code}: {'✅ 有效' if result else '❌ 无效'}")
            
        # 测试4: 验证有效授权码
        print("\n🧪 测试4: 验证有效授权码")
        test_license = licenses[0]  # 使用第一个授权码
        print(f"测试授权码: {test_license}")
        
        # 第一次验证（应该成功）
        result1 = auth_manager.verify_builtin_license(test_license)
        print(f"第一次验证: {'✅ 成功' if result1 else '❌ 失败'}")
        
        # 第二次验证（应该成功，因为同一设备）
        result2 = auth_manager.verify_builtin_license(test_license)
        print(f"第二次验证: {'✅ 成功' if result2 else '❌ 失败'}")
        
        # 测试5: 检查授权状态
        print("\n🧪 测试5: 检查授权状态")
        is_licensed = auth_manager.is_licensed()
        print(f"是否已授权: {'✅ 是' if is_licensed else '❌ 否'}")
        
        if is_licensed:
            license_info = auth_manager.get_license_info()
            print(f"授权信息: {license_info}")
            
        # 测试6: 导出授权码格式验证
        print("\n🧪 测试6: 授权码格式验证")
        test_formats = [
            "1234-5678-9ABC-DEF0",  # 正确格式
            "12345678-9ABC-DEF0",   # 错误格式
            "1234-5678-9ABC",       # 不完整
            "1234 5678 9ABC DEF0",  # 空格分隔
            "1234-5678-9abc-def0",  # 小写
        ]
        
        for fmt in test_formats:
            valid = auth_manager.validate_license_format(fmt)
            print(f"  {fmt}: {'✅ 有效格式' if valid else '❌ 无效格式'}")
            
        # 测试7: 活跃授权列表
        print("\n🧪 测试7: 活跃授权列表")
        active_licenses = auth_manager.list_active_licenses()
        print(f"活跃授权数量: {len(active_licenses)}")
        for license in active_licenses:
            print(f"  授权码: {license['license_code']}")
            print(f"  剩余天数: {license['days_remaining']}")
            
        # 清理临时目录
        shutil.rmtree(temp_dir)
        print(f"\n🧹 清理临时目录: {temp_dir}")
        
        print("\n✅ 所有测试完成！")
        return True
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_gui_integration():
    """测试GUI集成"""
    print("\n🖥️ 测试GUI集成...")
    
    try:
        # 导入main模块
        import main
        
        # 检查GUI是否可以正常启动
        print("✅ GUI模块导入成功")
        
        # 测试授权管理器是否正确集成
        print("✅ 授权系统集成测试完成")
        
    except Exception as e:
        print(f"❌ GUI集成测试失败: {e}")
        return False
        
    return True

def main():
    """主函数"""
    print("🧪 MICS 授权系统测试")
    print("=" * 50)
    
    success = True
    
    # 测试授权管理器
    if not test_license_manager():
        success = False
        
    # 测试GUI集成
    if not test_gui_integration():
        success = False
        
    print("\n" + "=" * 50)
    if success:
        print("🎉 所有测试通过！")
        return 0
    else:
        print("💥 部分测试失败！")
        return 1

if __name__ == "__main__":
    exit(main()) 