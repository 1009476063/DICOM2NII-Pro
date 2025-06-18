# Image Group Processing System (IGPS) v2.0.0

**Image Group Processing System (IGPS)** is a one-stop research platform for medical image analysis, tailored for radiomics studies. It provides an intuitive graphical user interface for batch processing of medical images (DICOM format), including conversion to NIfTI, extensive preprocessing, and preparation for feature extraction.

![App Screenshot](https://raw.githubusercontent.com/your-username/your-repo/main/docs/screenshot.png) 
*(Note: You should update this screenshot link after pushing to GitHub)*

---

## ✨ Core Features

- **Multi-Modality Support**: Process CT, MRI, Mammography, and Ultrasound images.
- **DICOM to NIfTI Conversion**: Robust conversion of DICOM series into NIfTI format (`.nii.gz`), preserving patient-centric folder structures.
- **Advanced Radiomics Preprocessing**:
  - **Image Resampling**: Interpolate images to a specified voxel size with a choice of interpolators (Linear, Nearest Neighbor, B-Spline).
  - **Intensity Normalization (MRI)**: Includes Z-Score, and placeholders for WhiteStripe and Histogram Matching.
  - **Bias Field Correction (MRI)**: Integrated N4 bias field correction to handle intensity non-uniformity.
  - **Intensity Discretization**: Apply Fixed Bin Width or Fixed Bin Count discretization.
  - **Skull Stripping (Brain MRI)**: Automated (basic) skull stripping to isolate brain tissue.
- **RT-DICOM Support**: Convert RTSTRUCT, RTDOSE, and RTPLAN files associated with CT scans.
- **Intuitive GUI**: A user-friendly interface built with PyQt6, featuring dedicated tabs for each stage of the radiomics workflow.
- **License Management**:
  - **Trial Period**: New users can use the software's core features **3 times** before activation is required.
  - **Offline Activation**: Activate the software using a license key in the "Settings" tab.
  - **Hardware Lock**: Licenses are tied to a specific machine using a hardware fingerprint.

## 🚀 Getting Started

### Prerequisites
- Python 3.8+
- Dependencies listed in `requirements.txt`.

### Installation
1. Clone the repository:
   ```bash
   git clone <your-repo-url>
   ```
2. Navigate to the project directory:
   ```bash
   cd Image-Group-Processing-System
   ```
3. Install the required packages:
   ```bash
   pip install -r requirements.txt
   ```

### Running the Application
To start the graphical user interface, run:
```bash
python main.py
```

## 🖥️ User Interface Guide

The application is organized into several tabs:

### 1. 图像预处理 (Image Preprocessing)

This is the main tab for converting and preprocessing your DICOM data.

1.  **Input/Output**: Select your main DICOM directory (containing subdirectories for each patient) and an output directory for the NIfTI files.
2.  **Modality Selection**: Choose the imaging modality (e.g., CT, MRI) on the left.
3.  **Parameter Tuning**: Set the desired preprocessing parameters in the panel on the right. Options will change based on the selected modality.
4.  **Start Processing**: Click the "开始处理" button to begin the batch conversion.
5.  **Log**: Monitor the progress in the log window at the bottom.

### 2. 设置 (Settings)

This tab allows you to manage the software's license and access help resources.

- **授权管理 (License Management)**:
  - **授权码 (License Key)**: Enter your 16-digit license key here.
  - **激活授权 (Activate License)**: Click to validate and activate your key.
  - **Status**: Shows your current license status (e.g., Trial, Activated, Expired).
- **软件与授权信息 (Software & License Info)**:
  - **本机硬件ID (Hardware ID)**: Your machine's unique ID. This is required to generate a valid license key.
  - **授权有效期至 (License Expiry)**: Shows the expiration date of your active license.
- **帮助与支持 (Help & Support)**:
  - **查看帮助文档 (View Help Docs)**: Opens the user guide.
  - **关于软件 (About Software)**: Shows version and copyright information.

## 🔑 License System

- **Trial Mode**: Without a license, you can use the core processing functions 3 times. A notification will appear before each trial use.
- **Activation**:
  1. Obtain a license key from the software provider. You will need to provide your **Hardware ID** found in the Settings tab.
  2. Go to the **Settings** tab.
  3. Enter the key in the "授权码" field and click "激活授权".
  4. The status will update to "授权成功" upon successful activation. Each key is valid for 3 months.

---
This project was developed by **TanX** with assistance from AI.
For support, please contact `your-email@example.com`.

## 🏥 项目简介

IGPS (Image Group Processing System) 是一款专业的、一站式影像组学分析软件，旨在为临床医生和研究人员提供从影像数据到临床预测模型的全流程解决方案。软件覆盖了影像组学研究的四大核心环节：图像预处理、特征提取、特征选择与模型构建。

**作者**: TanX  
**版本**: v2.0.0 (开发中)
**开发日期**: 2025-06-18
**GitHub**: https://github.com/TanX-009/IGPS (占位符)

## 🚀 快速开始

### 环境要求
- Python 3.9+
- 支持的操作系统：Windows 10+, macOS 10.15+, Linux Ubuntu 18.04+

### 安装依赖
```bash
pip install -r requirements.txt
```

### 运行软件
```bash
python main.py
```

## 🏗️ 架构设计

### 核心功能模块
1.  **图像预处理 (Image Preprocessing)**: DICOM转换、图像重采样、强度归一化、N4偏置场校正等。
2.  **特征提取 (Feature Extraction)**: 基于`pyradiomics`提取一阶、形态、纹理等多种特征。
3.  **特征选择 (Feature Selection)**: 提供Filter、Wrapper、Embedded等多种筛选方法。
4.  **模型构建 (Model Building)**: 支持逻辑回归、支持向量机(SVM)、随机森林、XGBoost等模型的训练与验证。

### 技术栈
- **核心算法**: pydicom, SimpleITK, nibabel, pyradiomics, scikit-learn
- **用户界面**: PyQt6
- **数据处理**: NumPy, pandas
- **授权加密**: cryptography

## 📁 项目结构 (规划中)

```
Image-Group-Processing-System/
├── src/                      # 源代码
│   ├── preprocessing/      # 图像预处理模块
│   ├── feature_extraction/ # 特征提取模块
│   ├── feature_selection/  # 特征选择模块
│   ├── model_building/     # 模型构建模块
│   ├── licensing/          # 授权系统
│   ├── ui/                 # UI界面代码
│   ├── config/             # 配置管理
│   └── core/               # 核心共享组件
├── tests/                    # 测试代码
├── resources/                # 资源文件 (图标, 样式)
├── docs/                     # 文档
├── main.py                   # 主程序入口
├── requirements.txt          # 依赖列表
└── README.md                 # 项目说明
```

## 📈 开发路线图

- [x] **第一阶段**: 项目重构与新架构规划 ✅
- [ ] **第二阶段**: 深化图像预处理模块 🔄
- [ ] **第三阶段**: 开发特征提取模块 📋
- [ ] **第四阶段**: 开发特征选择模块 📋
- [ ] **第五阶段**: 开发模型构建模块 📋
- [ ] **第六阶段**: 整合与测试 📋
- [ ] **第七阶段**: 打包和发布 📋

## 🤝 贡献指南

1.  Fork 本仓库
2.  创建特性分支 (`git checkout -b feature/AmazingFeature`)
3.  提交更改 (`git commit -m 'Add some AmazingFeature'`)
4.  推送到分支 (`git push origin feature/AmazingFeature`)
5.  打开 Pull Request

## 📞 技术支持

- **GitHub Issues**: https://github.com/TanX-009/IGPS/issues (占位符)
- **开发者**: TanX
- **邮箱**: [待补充]

## 📄 许可证

Copyright © 2025 IGPS Development Team. All rights reserved.

本软件为专有软件，受版权法保护。未经许可，不得复制、分发或修改。

---

**项目启动时间**: 2025年6月1日  
**重构启动时间**: 2025年6月18日
**当前版本**: v2.0.0 (开发中)
**最后更新**: 2025年6月18日 