# MICS - Medical Imaging Image Conversion System

专业的医学影像DICOM到NIfTI格式转换软件

## 🏥 项目简介

MICS (Medical Imaging Image Conversion System) 是一个专业的医学影像格式转换软件，支持将DICOM格式转换为NIfTI格式。软件具有现代化的图形界面，支持多种医学影像模态，提供批量处理和智能序列识别功能。

**作者**: TanX  
**版本**: v1.0.0  
**开发日期**: 2025-06-01  
**GitHub**: https://github.com/TanX-009/MICS

## ✨ 主要特性

- 🔄 **多模态支持**：CT、MRI、乳腺摄影(MG)、放疗数据(RT)、超声(US)等
- 🧠 **智能识别**：自动识别DICOM序列类型和模态
- ⚡ **批量处理**：支持大量文件的高效并行转换
- 🎨 **现代界面**：基于Tkinter的直观易用图形界面
- 🔒 **离线授权**：基于硬件指纹的安全授权系统
- 🎯 **专业处理**：支持放疗结构(RTSTRUCT)、计划(RTPLAN)、剂量(RTDOSE)数据
- 🔧 **灵活配置**：丰富的转换参数和输出格式选项
- 📊 **进度监控**：实时显示转换进度和详细状态信息

## 🚀 快速开始

### 环境要求
- Python 3.9+
- 支持的操作系统：Windows 10+, macOS 10.15+, Linux Ubuntu 18.04+

### 安装依赖
```bash
pip install -r requirements.txt
```

### 运行软件

#### GUI模式
```bash
python main.py
```

#### 命令行模式
```bash
python main.py --cli --input /path/to/dicom --output /path/to/output
```

#### 许可证管理
```bash
python main.py --license
```

## 🏗️ 架构设计

### 核心组件
- **转换引擎**: 支持CT、MRI、乳腺摄影、放疗等多种模态
- **批量处理器**: 智能目录扫描和任务管理
- **授权系统**: 离线硬件指纹验证
- **GUI界面**: 现代化用户体验设计

### 技术栈
- **后端**: Python 3.9+, pydicom, nibabel, SimpleITK
- **前端**: Tkinter, ttk
- **数据处理**: NumPy, SciPy
- **授权加密**: cryptography

## 📁 项目结构

```
MICS/
├── src/                      # 源代码
│   ├── core/                 # 核心功能模块
│   │   ├── converters/       # 转换器(CT/MRI/MG/RT)
│   │   ├── conversion_manager.py  # 转换管理器
│   │   ├── batch_processor.py     # 批量处理器
│   │   └── exceptions.py          # 异常定义
│   ├── auth/                # 授权系统
│   │   ├── license_manager.py     # 许可证管理
│   │   └── license_generator.py   # 许可证生成
│   ├── gui/                 # 用户界面
│   │   ├── main_window.py         # 主窗口
│   │   └── components/            # UI组件
│   └── config/              # 配置管理
├── tests/                   # 测试代码
├── docs/                    # 文档
├── main.py                  # 主程序入口
├── requirements.txt         # 依赖列表
└── README.md               # 项目说明
```

## 🧪 测试

### 运行单元测试
```bash
# 测试转换器
python test_all_converters.py

# 测试授权系统
python test_license_system.py

# 测试批量处理
python test_batch_conversion.py
```

## 📊 支持的医学影像模态

| 模态 | 格式 | 状态 | 特殊处理 |
|------|------|------|----------|
| CT | DICOM | ✅ | 层排序、方向修正 |
| MRI | DICOM | ✅ | 序列检测(T1/T2/DWI/DCE) |
| 乳腺摄影 | DICOM | ✅ | 视图检测(MLO/CC)、去标识 |
| 放疗结构 | RTSTRUCT | ✅ | ROI提取、颜色管理 |
| 放疗计划 | RTPLAN | ✅ | 计划信息提取 |
| 放疗剂量 | RTDOSE | ✅ | 剂量分布转换 |
| 超声 | DICOM | 🔄 | 开发中 |

## 🔐 授权系统

MICS使用基于硬件指纹的离线授权系统：

### 许可证类型
- **试用版**: 30天有效期，支持基础转换功能
- **标准版**: 支持高级设置和商业使用
- **专业版**: 支持插件扩展
- **企业版**: 包含优先技术支持和定制功能

### 许可证管理
```bash
# 查看当前许可证状态
python main.py --license

# 生成硬件指纹
python -c "from src.auth.license_manager import HardwareFingerprint; print(HardwareFingerprint.get_machine_id())"
```

## 📈 开发进度

- [x] **第一阶段**: 项目架构设计和规划 ✅
- [x] **第二阶段**: 核心转换器实现 ✅
- [x] **第三阶段**: 批量处理和任务管理 ✅
- [x] **第四阶段**: GUI界面开发 ✅
- [x] **第五阶段**: 授权系统实现 ✅
- [ ] **第六阶段**: 测试和优化 🔄
- [ ] **第七阶段**: 打包和发布 📋

## 🤝 贡献指南

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 打开 Pull Request

## 📞 技术支持

- **GitHub Issues**: https://github.com/TanX-009/MICS/issues
- **开发者**: TanX
- **邮箱**: [待补充]

## 📄 许可证

Copyright © 2025 MICS Development Team. All rights reserved.

本软件为专有软件，受版权法保护。未经许可，不得复制、分发或修改。

---

**项目启动时间**: 2025年6月1日  
**当前版本**: v1.0.0  
**最后更新**: 2025年6月18日 