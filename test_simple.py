#!/usr/bin/env python3
"""
简化的转换器测试脚本
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_basic_functionality():
    """测试基本功能"""
    print("🚀 开始DICOM2NII Pro 转换器测试")
    
    try:
        # 测试模块导入
        from src.core.converters.mri_converter import MRIConverter
        from src.core.converters.mammography_converter import MammographyConverter  
        from src.core.converters.radiotherapy_converter import RadiotherapyConverter
        from src.core.converters import list_supported_modalities
        
        print("✅ 所有转换器模块导入成功")
        
        # 测试支持的模态
        modalities = list_supported_modalities()
        print(f"✅ 支持的模态: {modalities}")
        
        # 测试配置
        from src.config.settings import settings
        print(f"✅ 配置系统正常: 输出格式={settings.conversion.output_format}")
        
        print("🎉 所有基础测试通过！")
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False

if __name__ == "__main__":
    success = test_basic_functionality()
    sys.exit(0 if success else 1) 