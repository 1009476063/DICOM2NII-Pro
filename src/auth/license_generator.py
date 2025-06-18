#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文件名: license_generator.py
功能描述: IGPS 批量授权码生成工具
创建日期: 2025-06-18
作者: TanX
版本: v2.0.0

本脚本用于生成 Image Group Processing System (IGPS) 所需的内置授权码文件。
它会调用核心的授权管理器来生成1000个与软件应用密钥绑定的唯一授权码。
"""

import sys
from pathlib import Path
from datetime import datetime

# 将项目根目录添加到Python路径，以便能够导入src中的模块
# 这使得脚本可以在项目根目录中通过 `python src/auth/license_generator.py` 直接运行
try:
    # 尝试确定项目根目录
    project_root = Path(__file__).resolve().parent.parent.parent
    sys.path.append(str(project_root))
    from src.auth.license_manager import IGPSLicenseManager
except (ImportError, IndexError):
    print("错误：无法导入 IGPSLicenseManager。")
    print("请确保从项目根目录运行此脚本, e.g., 'python src/auth/license_generator.py'")
    sys.exit(1)


def generate_keys_file(output_path: Path, count: int = 1000):
    """
    生成授权码并保存到文件。

    Args:
        output_path (Path): 输出文件的路径。
        count (int): 要生成的授权码数量。
    """
    print("正在初始化授权管理器...")
    # 临时的管理器实例，仅用于调用生成和导出逻辑
    manager = IGPSLicenseManager()
    
    print(f"正在生成 {count} 个授权码...")
    licenses = manager._generate_builtin_licenses(count)
    
    print(f"正在将授权码写入到: {output_path}")
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(f"# Image Group Processing System (IGPS) - 内置授权码\n")
            f.write(f"# 生成时间: {datetime.now().isoformat()}\n")
            f.write(f"# 总数量: {len(licenses)}个\n\n")
            
            for i, license_code in enumerate(licenses, 1):
                f.write(f"{i:04d}: {license_code}\n")
        
        print(f"授权码文件生成成功！路径: {output_path}")

    except IOError as e:
        print(f"错误：无法写入文件 {output_path}。原因: {e}")
        sys.exit(1)


if __name__ == '__main__':
    # 将生成的授权码文件保存在项目根目录下的 'generated' 文件夹中
    default_output_dir = Path(__file__).resolve().parent.parent.parent / "generated"
    output_file = default_output_dir / "igps_builtin_licenses.txt"
    
    print("=========================================")
    print("== IGPS 批量授权码生成工具 ==")
    print("=========================================")
    
    # 检查 'export_builtin_licenses' 方法是否存在且可调用
    if hasattr(IGPSLicenseManager, 'export_builtin_licenses') and callable(getattr(IGPSLicenseManager, 'export_builtin_licenses')):
        print(f"检测到 'export_builtin_licenses' 方法，正在使用该方法导出...")
        manager = IGPSLicenseManager()
        success = manager.export_builtin_licenses(str(output_file))
        if success:
            print(f"授权码文件通过 export_builtin_licenses 导出成功！路径: {output_file}")
        else:
            print("使用 'export_builtin_licenses' 方法导出失败。")
    else:
        print("警告: 未找到 'export_builtin_licenses' 方法，将使用备用方法生成。")
        generate_keys_file(output_file, count=1000) 