#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文件名: main.py
功能描述: MICS - Medical Imaging Image Conversion System 主程序入口
创建日期: 2025-06-01
作者: TanX
版本: v1.0.0

这是MICS的主程序入口点，负责:
1. 初始化应用程序环境
2. 加载配置文件
3. 启动GUI界面
4. 处理命令行参数
5. 授权验证
"""

import sys
import os
from pathlib import Path
import argparse
import logging

# 添加src目录到Python路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

# 导入核心模块 (暂时用占位符，将在后续开发中实现)
# from gui.main_window import MainWindow
# from config.settings import Settings
# from logging.logger import setup_logger

__version__ = "1.0.0"
__author__ = "TanX"
__copyright__ = "Copyright 2025, MICS - Medical Imaging Image Conversion System"
__github__ = "https://github.com/TanX-009/MICS"

def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="MICS - Medical Imaging Image Conversion System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  python main.py                    # 启动GUI界面
  python main.py --cli input.dcm    # 命令行模式转换
  python main.py --version          # 显示版本信息
  python main.py --license          # 许可证管理
        """
    )
    
    parser.add_argument(
        "--version", 
        action="version", 
        version=f"MICS {__version__} by {__author__}"
    )
    
    parser.add_argument(
        "--cli",
        action="store_true",
        help="使用命令行界面模式"
    )
    
    parser.add_argument(
        "--input", "-i",
        type=str,
        help="输入DICOM文件或目录路径"
    )
    
    parser.add_argument(
        "--output", "-o",
        type=str,
        help="输出NIfTI文件路径"
    )
    
    parser.add_argument(
        "--config", "-c",
        type=str,
        help="配置文件路径"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="显示详细输出信息"
    )
    
    parser.add_argument(
        "--debug",
        action="store_true",
        help="启用调试模式"
    )
    
    parser.add_argument(
        "--license",
        action="store_true",
        help="许可证管理和验证"
    )
    
    return parser.parse_args()

def setup_environment():
    """设置应用程序环境"""
    # 创建必要的目录
    app_dir = Path(__file__).parent
    
    # 确保必要目录存在
    directories = [
        app_dir / "logs",
        app_dir / "config",
        app_dir / "temp",
        app_dir / "output"
    ]
    
    for directory in directories:
        directory.mkdir(exist_ok=True)
    
    return app_dir

def setup_logging(verbose=False, debug=False):
    """设置日志系统"""
    log_level = logging.DEBUG if debug else (logging.INFO if verbose else logging.WARNING)
    
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(Path(__file__).parent / "logs" / "app.log"),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    logger = logging.getLogger(__name__)
    logger.info(f"MICS {__version__} 启动")
    
    return logger

def run_gui_mode():
    """运行GUI模式"""
    print("🎨 启动GUI模式...")
    print("⚠️  GUI界面正在开发中，敬请期待!")
    
    # TODO: 实现GUI启动逻辑
    # app = QApplication(sys.argv)
    # window = MainWindow()
    # window.show()
    # return app.exec()
    
    return 0

def run_cli_mode(args):
    """运行命令行模式"""
    print("💻 启动命令行模式...")
    
    if not args.input:
        print("❌ 错误: 命令行模式需要指定输入文件 (--input)")
        return 1
    
    if not args.output:
        print("❌ 错误: 命令行模式需要指定输出文件 (--output)")
        return 1
    
    print(f"📂 输入: {args.input}")
    print(f"📄 输出: {args.output}")
    print("⚠️  命令行转换功能正在开发中，敬请期待!")
    
    # TODO: 实现命令行转换逻辑
    # converter = DicomConverter(args.input, args.output)
    # result = converter.convert()
    # return 0 if result else 1
    
    return 0

def run_license_mode():
    """运行许可证管理模式"""
    print("🔐 启动许可证管理模式...")
    
    try:
        from auth.license_manager import license_manager
        from auth.license_generator import LicenseGenerator
        
        # 显示当前许可证状态
        is_valid, message = license_manager.validate_license()
        print(f"许可证状态: {'✅' if is_valid else '❌'} {message}")
        
        license_info = license_manager.get_license_info()
        if license_info:
            print(f"\n当前许可证信息:")
            print(f"  类型: {license_info.license_type}")
            print(f"  用户: {license_info.user_name}")
            print(f"  组织: {license_info.organization}")
            print(f"  剩余天数: {license_info.days_remaining}")
        
        # 显示硬件信息
        hardware_info = license_manager.export_hardware_info()
        print(f"\n硬件信息:")
        print(f"  硬件ID: {hardware_info['hardware_id']}")
        print(f"  系统: {hardware_info['platform']}")
        
        # 简单的许可证管理菜单
        while True:
            print("\n📋 许可证管理选项:")
            print("1. 生成试用许可证")
            print("2. 安装许可证")
            print("3. 导出硬件信息")
            print("4. 移除许可证")
            print("0. 退出")
            
            choice = input("\n请选择操作 (0-4): ").strip()
            
            if choice == "0":
                break
            elif choice == "1":
                # 生成试用许可证
                generator = LicenseGenerator()
                trial_license = generator.create_trial_license(
                    hardware_info['hardware_id'],
                    user_name=input("请输入用户名: ").strip() or "Trial User",
                    organization=input("请输入组织名: ").strip() or "Trial Organization"
                )
                success, msg = license_manager.install_license(trial_license)
                print(f"{'✅' if success else '❌'} {msg}")
                
            elif choice == "2":
                # 安装许可证
                license_data = input("请输入许可证数据: ").strip()
                if license_data:
                    success, msg = license_manager.install_license(license_data)
                    print(f"{'✅' if success else '❌'} {msg}")
                    
            elif choice == "3":
                # 导出硬件信息
                import json
                print("\n硬件信息 (用于许可证申请):")
                print(json.dumps(hardware_info, indent=2, ensure_ascii=False))
                
            elif choice == "4":
                # 移除许可证
                confirm = input("确认移除当前许可证? (y/N): ").strip().lower()
                if confirm == 'y':
                    license_manager.remove_license()
                    print("✅ 许可证已移除")
        
        return 0
        
    except ImportError as e:
        print(f"❌ 许可证模块导入失败: {e}")
        return 1
    except Exception as e:
        print(f"❌ 许可证管理异常: {e}")
        return 1

def main():
    """主函数"""
    try:
        # 解析命令行参数
        args = parse_arguments()
        
        # 设置环境
        app_dir = setup_environment()
        
        # 设置日志
        logger = setup_logging(args.verbose, args.debug)
        
        # 显示启动信息
        print("=" * 60)
        print("🏥 MICS - Medical Imaging Image Conversion System")
        print(f"📊 版本: {__version__} | 作者: {__author__}")
        print(f"📁 工作目录: {app_dir}")
        print(f"🔗 GitHub: {__github__}")
        print("=" * 60)
        
        # 根据参数选择运行模式
        if args.license:
            return run_license_mode()
        elif args.cli:
            return run_cli_mode(args)
        else:
            return run_gui_mode()
            
    except KeyboardInterrupt:
        print("\n⚠️  用户中断操作")
        return 130
    except Exception as e:
        print(f"❌ 程序异常: {e}")
        logging.exception("程序异常")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 