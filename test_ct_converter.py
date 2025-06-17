#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文件名: test_ct_converter.py
功能描述: CT转换器测试脚本
创建日期: 2025-01-23
作者: Claude AI Assistant
版本: v0.1.0-dev

用于测试CT转换器功能的脚本，使用提供的头部CT测试数据。
"""

import sys
import logging
from pathlib import Path

# 添加src目录到Python路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

try:
    from src.core.converters.ct_converter import CTConverter
    from src.config.settings import ConversionSettings
except ImportError as e:
    print(f"导入模块失败: {e}")
    print("请确保已安装所需依赖: pip install -r requirements.txt")
    sys.exit(1)


def setup_test_logging():
    """设置测试日志"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )


def progress_callback(progress_info):
    """进度回调函数"""
    print(f"进度: {progress_info.current_step} - {progress_info.progress:.1%} "
          f"({progress_info.processed_files}/{progress_info.total_files})")
    if progress_info.current_file:
        print(f"  当前文件: {progress_info.current_file}")


def test_ct_converter():
    """测试CT转换器"""
    
    # 设置日志
    setup_test_logging()
    logger = logging.getLogger(__name__)
    
    print("🏥 DICOM2NII Pro - CT转换器测试")
    print("=" * 50)
    
    # 测试数据路径
    test_data_dir = Path("../dic2nii")
    ct_data_dirs = [
        test_data_dir / "1023-0007-Baseline-head-CT",
        test_data_dir / "1009-0021-Baseline-head-CT", 
        test_data_dir / "1016-0018-0"
    ]
    
    # 查找可用的测试数据
    available_data = []
    for data_dir in ct_data_dirs:
        if data_dir.exists():
            available_data.append(data_dir)
            print(f"✅ 找到测试数据: {data_dir}")
        else:
            print(f"❌ 测试数据不存在: {data_dir}")
    
    if not available_data:
        print("❌ 未找到任何测试数据，请检查dic2nii目录")
        return False
    
    # 使用第一个可用的测试数据
    input_path = available_data[0]
    output_path = Path("output") / f"{input_path.name}_converted.nii.gz"
    
    print(f"\n📂 输入路径: {input_path}")
    print(f"📄 输出路径: {output_path}")
    
    # 确保输出目录存在
    output_path.parent.mkdir(exist_ok=True)
    
    try:
        # 创建转换配置
        config = ConversionSettings(
            output_format="nii.gz",
            data_type="float32",
            validate_dicom=True,
            verify_output=True
        )
        
        print(f"\n⚙️  转换配置:")
        print(f"  输出格式: {config.output_format}")
        print(f"  数据类型: {config.data_type}")
        print(f"  验证DICOM: {config.validate_dicom}")
        print(f"  验证输出: {config.verify_output}")
        
        # 创建转换器
        print(f"\n🔧 创建CT转换器...")
        converter = CTConverter(input_path, output_path, config)
        converter.set_progress_callback(progress_callback)
        
        print(f"支持的模态: {converter.get_supported_modalities()}")
        
        # 执行转换
        print(f"\n🚀 开始转换...")
        result = converter.convert()
        
        # 显示结果
        print(f"\n📊 转换结果:")
        print(f"  成功: {'✅' if result.success else '❌'}")
        print(f"  输入路径: {result.input_path}")
        print(f"  输出路径: {result.output_path}")
        print(f"  处理时间: {result.processing_time:.2f}秒" if result.processing_time else "  处理时间: 未知")
        print(f"  文件数量: {result.file_count}")
        
        if result.success:
            print(f"  输出文件大小: {result.output_path.stat().st_size / 1024 / 1024:.2f} MB")
            
            # 显示元数据
            if result.metadata:
                print(f"\n📋 图像信息:")
                print(f"  模态: {result.metadata.get('modality', 'Unknown')}")
                print(f"  尺寸: {result.metadata.get('rows', '?')}x{result.metadata.get('columns', '?')}x{result.metadata.get('number_of_slices', '?')}")
                print(f"  像素间距: {result.metadata.get('pixel_spacing', 'Unknown')}")
                print(f"  层厚: {result.metadata.get('slice_thickness', 'Unknown')} mm")
                print(f"  制造商: {result.metadata.get('manufacturer', 'Unknown')}")
                
                if 'rescale_slope' in result.metadata:
                    print(f"  Rescale斜率: {result.metadata['rescale_slope']}")
                    print(f"  Rescale截距: {result.metadata['rescale_intercept']}")
        else:
            print(f"  错误代码: {result.error_code}")
            print(f"  错误信息: {result.error_message}")
        
        return result.success
        
    except Exception as e:
        logger.error(f"测试过程中发生异常: {e}", exc_info=True)
        return False


def main():
    """主函数"""
    try:
        success = test_ct_converter()
        
        print(f"\n{'='*50}")
        if success:
            print("🎉 CT转换器测试成功完成！")
            return 0
        else:
            print("❌ CT转换器测试失败")
            return 1
            
    except KeyboardInterrupt:
        print(f"\n⚠️  用户中断测试")
        return 130
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main()) 