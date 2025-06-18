#!/usr/bin/env python3
"""
MICS 授权码生成器
生成1000个可用的授权码并保存到文本文件中
"""

import os
import sys
from datetime import datetime

# 添加src路径
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

def main():
    """主函数"""
    try:
        from src.auth.license_manager import MicsLicenseManager
        
        # 创建授权管理器
        print("🔑 正在初始化MICS授权管理器...")
        license_manager = MicsLicenseManager()
        
        # 生成授权码文件
        output_file = "MICS_授权码列表.txt"
        print(f"📄 正在生成授权码到文件: {output_file}")
        
        if license_manager.export_builtin_licenses(output_file):
            print(f"✅ 成功生成1000个授权码！")
            print(f"📁 文件位置: {os.path.abspath(output_file)}")
            print(f"📊 文件大小: {os.path.getsize(output_file)} 字节")
            
            # 显示前几个授权码作为示例
            print("\n🔍 前10个授权码预览:")
            with open(output_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                
            code_lines = [line for line in lines if line.strip() and not line.startswith('#')]
            for i, line in enumerate(code_lines[:10]):
                print(f"  {line.strip()}")
                
            print(f"\n💡 使用说明:")
            print(f"  • 每个授权码有效期：3个月")
            print(f"  • 每个授权码只能在一台设备上使用")
            print(f"  • 在软件的设置页面输入授权码进行验证")
            print(f"  • 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            
        else:
            print("❌ 生成授权码失败！")
            return 1
            
    except ImportError as e:
        print(f"❌ 导入授权模块失败: {e}")
        return 1
    except Exception as e:
        print(f"❌ 生成过程中发生错误: {e}")
        return 1
        
    return 0

if __name__ == "__main__":
    exit(main()) 