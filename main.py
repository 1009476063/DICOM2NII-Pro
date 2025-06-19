#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文件名: main.py
功能描述: IGPS - Image Group Processing System 主程序入口
创建日期: 2025-06-18 (重构)
作者: TanX
版本: v2.0.0

这是IGPS的主程序入口点，负责:
1. 初始化应用程序环境
2. 加载配置文件
3. 启动基于PyQt6的GUI界面
4. 处理命令行参数
5. 授权验证
"""

import sys
import os
from pathlib import Path
import argparse
import logging
import pprint
from typing import Optional

# 添加src目录到Python路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Core logic imports (placed at top level)
from src import __version__, __author__
from src.core.processing_controller import ProcessingController
from src.auth.license_manager import IGPSLicenseManager
from src.core.conversion_config import (
    BaseConversionConfig, CTConversionConfig, MRIConversionConfig,
    MammographyConversionConfig, UltrasoundConversionConfig
)

# 定义全局变量，以便在try/except块之外访问
GUI_AVAILABLE = False

# 导入GUI模块 (PyQt6)
try:
    from PyQt6.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QTabWidget, QLabel, QListWidget, QStackedWidget, QSplitter,
        QPushButton, QFileDialog, QTextEdit, QStatusBar, QListWidgetItem,
        QGroupBox, QCheckBox, QLineEdit, QComboBox, QProgressBar, QMessageBox,
        QMenu, QStyle
    )
    from PyQt6.QtGui import QAction, QIcon, QDesktopServices
    from PyQt6.QtCore import Qt, QUrl, pyqtSignal
    GUI_AVAILABLE = True

    # Import custom widgets
    from src.gui.settings_tab import SettingsTab
except ImportError as e:
    # Set GUI_AVAILABLE to False if any GUI import fails
    GUI_AVAILABLE = False
    print(f"GUI模块导入失败: {e}")


# ===================================================================
#  GUI Class Definitions
#  All classes that depend on PyQt6 must be defined inside this
#  'if' block to avoid NameError when PyQt6 is not installed.
# ===================================================================
if GUI_AVAILABLE:
    class ClickableLabel(QLabel):
        """A QLabel that emits a 'clicked' signal when clicked."""
        def __init__(self, url: str, text: str = "", parent=None):
            super().__init__(text, parent)
            self.url = QUrl(url)
            self.setOpenExternalLinks(False)
            self.setCursor(Qt.CursorShape.PointingHandCursor)

        def mouseReleaseEvent(self, event):
            if event.button() == Qt.MouseButton.LeftButton:
                QDesktopServices.openUrl(self.url)
            super().mouseReleaseEvent(event)

    class CTSettingsWidget(QWidget):
        """CT图像预处理设置面板"""
        def __init__(self, parent=None):
            super().__init__(parent)
            main_layout = QVBoxLayout(self)
            main_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

            # --- 核心转换选项 ---
            core_group = QGroupBox("核心转换选项")
            core_layout = QVBoxLayout()
            
            self.convert_rtstruct_check = QCheckBox("转换RTSTRUCT轮廓为NIfTI掩码")
            self.convert_rtstruct_check.setChecked(True)
            self.convert_rtstruct_check.setToolTip("如果找到RTSTRUCT文件，将其中的轮廓转换为对应的nii.gz掩码文件。")
            core_layout.addWidget(self.convert_rtstruct_check)

            self.convert_rtdose_check = QCheckBox("转换并对齐RTDOSE至CT空间")
            self.convert_rtdose_check.setToolTip("如果找到RTDOSE文件，将其转换为nii.gz并重采样以匹配CT图像空间。")
            core_layout.addWidget(self.convert_rtdose_check)
            
            self.convert_rtplan_check = QCheckBox("匿名化并保存RTPLAN文件")
            self.convert_rtplan_check.setToolTip("如果找到RTPLAN文件，将其匿名化后另存为.dcm文件。")
            core_layout.addWidget(self.convert_rtplan_check)
            
            core_group.setLayout(core_layout)
            main_layout.addWidget(core_group)

            # --- 影像组学预处理 ---
            radiomics_group = QGroupBox("影像组学预处理")
            radiomics_layout = QVBoxLayout()
            
            self.resample_check = QCheckBox("图像重采样 (插值)")
            self.resample_check.setToolTip("将图像插值到指定的体素大小。")
            radiomics_layout.addWidget(self.resample_check)
            
            resample_options_widget = QWidget()
            resample_options_layout = QHBoxLayout(resample_options_widget)
            resample_options_layout.setContentsMargins(20, 0, 0, 0) # Indent
            
            resample_options_layout.addWidget(QLabel("新体素大小 (mm):"))
            self.voxel_x = QLineEdit("1.0")
            self.voxel_y = QLineEdit("1.0")
            self.voxel_z = QLineEdit("1.5")
            for editor in [self.voxel_x, self.voxel_y, self.voxel_z]:
                editor.setFixedWidth(50)
            resample_options_layout.addWidget(self.voxel_x)
            resample_options_layout.addWidget(self.voxel_y)
            resample_options_layout.addWidget(self.voxel_z)
            resample_options_layout.addStretch()
            
            radiomics_layout.addWidget(resample_options_widget)
            
            # --- 插值方法 ---
            interpolator_layout = QHBoxLayout()
            interpolator_layout.setContentsMargins(20, 0, 0, 0) # Indent
            interpolator_layout.addWidget(QLabel("插值方法:"))
            self.interpolator_combo = QComboBox()
            self.interpolator_combo.addItems(["sitkLinear", "sitkNearestNeighbor", "sitkBSpline"])
            interpolator_layout.addWidget(self.interpolator_combo)
            interpolator_layout.addStretch()
            radiomics_layout.addLayout(interpolator_layout)

            # Enable/disable logic
            resample_options_widget.setEnabled(False)
            self.interpolator_combo.setEnabled(False)
            self.resample_check.toggled.connect(resample_options_widget.setEnabled)
            self.resample_check.toggled.connect(self.interpolator_combo.setEnabled)

            # --- 强度离散化 ---
            discretization_group = QGroupBox("强度离散化 (Intensity Discretization)")
            discretization_group.setCheckable(True)
            discretization_group.setChecked(False)
            discretization_layout = QVBoxLayout(discretization_group)

            self.discretization_type_combo = QComboBox()
            self.discretization_type_combo.addItems(["固定斌宽 (Fixed Bin Width)", "固定斌数量 (Fixed Bin Count)"])
            
            self.discretization_value_edit = QLineEdit("25")
            self.discretization_value_edit.setToolTip("对于固定斌宽，这是HU单位的宽度；对于固定斌数量，这是整数个数。")

            discretization_options_layout = QHBoxLayout()
            discretization_options_layout.addWidget(self.discretization_type_combo)
            discretization_options_layout.addWidget(self.discretization_value_edit)
            discretization_layout.addLayout(discretization_options_layout)
            
            radiomics_layout.addWidget(discretization_group)
            
            radiomics_group.setLayout(radiomics_layout)
            main_layout.addWidget(radiomics_group)

            # --- DICOM元数据覆盖 ---
            override_group = QGroupBox("DICOM 元数据覆盖 (高级)")
            override_layout = QVBoxLayout()
            
            self.override_spacing_check = QCheckBox("手动指定像素间距 (Spacing)")
            override_layout.addWidget(self.override_spacing_check)
            
            spacing_widget = QWidget()
            spacing_layout = QHBoxLayout(spacing_widget)
            spacing_layout.setContentsMargins(20, 0, 0, 0)
            spacing_layout.addWidget(QLabel("Spacing (x, y):"))
            self.spacing_x = QLineEdit()
            self.spacing_y = QLineEdit()
            self.spacing_x.setPlaceholderText("e.g., 0.97")
            self.spacing_y.setPlaceholderText("e.g., 0.97")
            spacing_layout.addWidget(self.spacing_x)
            spacing_layout.addWidget(self.spacing_y)
            spacing_layout.addStretch()
            override_layout.addWidget(spacing_widget)

            self.override_orientation_check = QCheckBox("手动指定图像方位 (Orientation)")
            override_layout.addWidget(self.override_orientation_check)

            orientation_widget = QWidget()
            orientation_layout = QHBoxLayout(orientation_widget)
            orientation_layout.setContentsMargins(20, 0, 0, 0)
            orientation_layout.addWidget(QLabel("Orientation:"))
            self.orientation_combo = QComboBox()
            self.orientation_combo.addItems(["LPS", "RAS", "RAI", "LAI", "RPI", "LPI", "ASL"])
            orientation_layout.addWidget(self.orientation_combo)
            orientation_layout.addStretch()
            override_layout.addWidget(orientation_widget)
            
            # Enable/disable logic
            spacing_widget.setEnabled(False)
            orientation_widget.setEnabled(False)
            self.override_spacing_check.toggled.connect(spacing_widget.setEnabled)
            self.override_orientation_check.toggled.connect(orientation_widget.setEnabled)

            override_group.setLayout(override_layout)
            main_layout.addWidget(override_group)

    class MRISettingsWidget(QWidget):
        """MRI图像预处理设置面板"""
        def __init__(self, parent=None):
            super().__init__(parent)
            main_layout = QVBoxLayout(self)
            main_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

            # --- MRI专用预处理 ---
            mri_group = QGroupBox("MRI 专用预处理")
            mri_layout = QVBoxLayout()
            
            self.n4_correction_check = QCheckBox("启用N4偏置场校正 (N4 Bias Field Correction)")
            self.n4_correction_check.setToolTip("使用SimpleITK的N4算法校正MRI图像中的低频强度不均匀性。")
            self.n4_correction_check.setChecked(True)
            mri_layout.addWidget(self.n4_correction_check)

            self.skull_stripping_check = QCheckBox("应用颅骨剥离 (适用于脑部MRI)")
            self.skull_stripping_check.setToolTip("尝试自动检测并移除颅骨，仅保留脑组织。")
            self.skull_stripping_check.setChecked(False)
            mri_layout.addWidget(self.skull_stripping_check)
            
            mri_group.setLayout(mri_layout)
            main_layout.addWidget(mri_group)
            
            # --- 强度归一化 ---
            norm_group = QGroupBox("强度归一化")
            norm_layout = QVBoxLayout()
            
            norm_layout.addWidget(QLabel("选择一种强度归一化方法:"))
            
            self.norm_combo = QComboBox()
            self.norm_combo.addItems([
                "无 (None)",
                "Z-Score 标准化 (每个图像独立)",
                "白条纹法 (WhiteStripe)",
                "直方图匹配 (Histogram Matching)"
            ])
            self.norm_combo.setToolTip("对图像强度值进行标准化，以消除不同扫描之间的差异。")
            norm_layout.addWidget(self.norm_combo)

            norm_group.setLayout(norm_layout)
            main_layout.addWidget(norm_group)

            # --- 强度离散化 (for MRI) ---
            self.mri_discretization_group = QGroupBox("强度离散化 (Intensity Discretization)")
            self.mri_discretization_group.setCheckable(True)
            self.mri_discretization_group.setChecked(False)
            mri_discretization_layout = QVBoxLayout(self.mri_discretization_group)

            self.mri_dis_type_combo = QComboBox()
            self.mri_dis_type_combo.addItems(["固定斌宽 (Fixed Bin Width)", "固定斌数量 (Fixed Bin Count)"])
            
            self.mri_dis_value_edit = QLineEdit("0.5")
            self.mri_dis_value_edit.setToolTip("对于固定斌宽，这是归一化后的强度单位；对于固定斌数量，这是整数个数。")

            mri_dis_options_layout = QHBoxLayout()
            mri_dis_options_layout.addWidget(self.mri_dis_type_combo)
            mri_dis_options_layout.addWidget(self.mri_dis_value_edit)
            mri_dis_options_layout.addStretch()
            mri_discretization_layout.addLayout(mri_dis_options_layout)
            
            main_layout.addWidget(self.mri_discretization_group)

    class MammographySettingsWidget(QWidget):
        """钼靶图像预处理设置面板"""
        def __init__(self, parent=None):
            super().__init__(parent)
            main_layout = QVBoxLayout(self)
            main_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

            # --- 钼靶专用处理 ---
            mammo_group = QGroupBox("乳腺钼靶专用处理")
            mammo_layout = QVBoxLayout()
            
            self.orientation_check = QCheckBox("自动修正图像方位 (推荐)")
            self.orientation_check.setToolTip("根据DICOM头中的方位信息 (如 LMLO, RCC)，自动旋转图像至标准方向。")
            self.orientation_check.setChecked(True)
            mammo_layout.addWidget(self.orientation_check)

            self.anonymize_check = QCheckBox("移除图像边缘的敏感文本信息")
            self.anonymize_check.setToolTip("通过将图像顶部和底部10%的区域涂黑，来移除可能存在的患者信息。")
            self.anonymize_check.setChecked(False)
            mammo_layout.addWidget(self.anonymize_check)
            
            mammo_group.setLayout(mammo_layout)
            main_layout.addWidget(mammo_group)

    class UltrasoundSettingsWidget(QWidget):
        """超声图像预处理设置面板"""
        def __init__(self, parent=None):
            super().__init__(parent)
            layout = QVBoxLayout(self)
            layout.addWidget(QLabel("超声 (Ultrasound) 预处理设置"))
            # 未来在这里添加具体的超声设置控件

    class PreprocessingTab(QWidget):
        """图像预处理功能总面板"""
        trial_used = pyqtSignal() # Signal to indicate a trial has been consumed

        def __init__(self, license_manager: IGPSLicenseManager, parent=None):
            super().__init__(parent)
            self.controller = ProcessingController(license_manager=license_manager)
            main_layout = QVBoxLayout(self)

            # 1. 输入输出设置
            io_group = self._create_io_group()
            main_layout.addWidget(io_group)

            # --- 创建一个新的主分割器，用于左右布局 ---
            main_splitter = QSplitter(Qt.Orientation.Horizontal)

            # --- 左侧面板：影像类型选择和参数设置 ---
            left_panel = QWidget()
            left_layout = QVBoxLayout(left_panel)
            left_layout.setContentsMargins(0,0,0,0)

            # 核心设置区域 (类型选择 + 参数面板)
            settings_splitter = QSplitter(Qt.Orientation.Horizontal)
            
            self.modality_list = QListWidget()
            self.modality_list.addItems(["CT", "MRI", "钼靶 (Mammography)", "超声 (Ultrasound)"])
            self.modality_list.setMaximumWidth(200)
            
            self.ct_settings = CTSettingsWidget()
            self.mri_settings = MRISettingsWidget()
            self.mammo_settings = MammographySettingsWidget()
            self.us_settings = UltrasoundSettingsWidget()

            self.settings_stack = QStackedWidget()
            self.settings_stack.addWidget(self.ct_settings)
            self.settings_stack.addWidget(self.mri_settings)
            self.settings_stack.addWidget(self.mammo_settings)
            self.settings_stack.addWidget(self.us_settings)
            
            settings_splitter.addWidget(self.modality_list)
            settings_splitter.addWidget(self.settings_stack)
            settings_splitter.setSizes([150, 450]) # 调整左侧内部比例

            left_layout.addWidget(settings_splitter)
            
            # --- 右侧面板：控制与日志 ---
            right_panel = self._create_log_group()
            
            # --- 将左右面板添加到主分割器 ---
            main_splitter.addWidget(left_panel)
            main_splitter.addWidget(right_panel)
            main_splitter.setSizes([600, 300]) # 设置初始比例为 2:1

            main_layout.addWidget(main_splitter)

            # 连接信号和槽
            self.modality_list.currentRowChanged.connect(self.settings_stack.setCurrentIndex)
            self.modality_list.setCurrentRow(0)

        def _create_io_group(self):
            io_group = QGroupBox("输入与输出")
            io_layout = QVBoxLayout()

            input_layout = QHBoxLayout()
            self.input_dir_line = QLineEdit()
            self.input_dir_line.setPlaceholderText("请选择包含DICOM文件的根目录...")
            self.input_dir_line.setReadOnly(True)
            input_btn = QPushButton("浏览...")
            input_btn.clicked.connect(self._select_input_dir)
            input_layout.addWidget(QLabel("输入目录:"))
            input_layout.addWidget(self.input_dir_line)
            input_layout.addWidget(input_btn)
            
            output_layout = QHBoxLayout()
            self.output_dir_line = QLineEdit()
            self.output_dir_line.setPlaceholderText("请选择保存NIfTI文件的目录...")
            self.output_dir_line.setReadOnly(True)
            output_btn = QPushButton("浏览...")
            output_btn.clicked.connect(self._select_output_dir)
            output_layout.addWidget(QLabel("输出目录:"))
            output_layout.addWidget(self.output_dir_line)
            output_layout.addWidget(output_btn)
            
            io_layout.addLayout(input_layout)
            io_layout.addLayout(output_layout)
            io_group.setLayout(io_layout)
            return io_group

        def _create_log_group(self):
            log_group = QGroupBox("控制与日志")
            log_layout = QVBoxLayout()

            self.start_button = QPushButton("🚀 开始预处理")
            self.start_button.clicked.connect(self._start_preprocessing)
            log_layout.addWidget(self.start_button)
            
            self.progress_bar = QProgressBar()
            self.progress_bar.setVisible(False)
            log_layout.addWidget(self.progress_bar)

            self.log_display = QTextEdit()
            self.log_display.setReadOnly(True)
            log_layout.addWidget(self.log_display)
            
            log_group.setLayout(log_layout)
            return log_group

        def _select_input_dir(self):
            dir_path = QFileDialog.getExistingDirectory(self, "选择输入目录")
            if dir_path:
                self.input_dir_line.setText(dir_path)

        def _select_output_dir(self):
            dir_path = QFileDialog.getExistingDirectory(self, "选择输出目录")
            if dir_path:
                self.output_dir_line.setText(dir_path)

        def _update_progress(self, percentage, message):
            self.progress_bar.setValue(percentage)
            self.log_display.append(f"[{percentage}%] {message}")
            
        def _on_processing_finished(self):
            self.log_display.append("\n--- 任务完成 ---")
            self.start_button.setEnabled(True)
            self.progress_bar.setVisible(False)

        def _on_processing_error(self, error_info):
            """处理来自工作线程的错误信号"""
            self.log_display.append(f"\n--- 发生错误 ---")
            self.log_display.append(f"错误类型: {error_info.__class__.__name__}")
            self.log_display.append(f"错误信息: {error_info}")
            self.log_display.append(f"Traceback:\n{error_info.__traceback__}")
            self.start_button.setEnabled(True)
            self.progress_bar.setVisible(False)

        def _collect_settings(self) -> Optional[BaseConversionConfig]:
            """Gathers settings from the UI and creates a config object."""
            input_dir = self.input_dir_line.text()
            output_dir = self.output_dir_line.text()

            if not os.path.isdir(input_dir) or not os.path.isdir(output_dir):
                QMessageBox.critical(self, "路径错误", "请输入有效的输入和输出目录。")
                return None

            modality_item = self.modality_list.currentItem()
            if not modality_item:
                QMessageBox.critical(self, "选择错误", "请先在左侧列表中选择一种影像类型。")
                return None
            modality = modality_item.text().split(" ")[0]

            current_widget = self.settings_stack.currentWidget()
            s = current_widget # Abbreviation for easier access

            try:
                if modality == "CT":
                    # Ensure the widget is the correct one before accessing attributes
                    if not isinstance(s, CTSettingsWidget): return None
                    return CTConversionConfig(
                        input_dir=input_dir, output_dir=output_dir,
                        convert_rtstruct=s.convert_rtstruct_check.isChecked(),
                        convert_rtdose=s.convert_rtdose_check.isChecked(),
                        anonymize_rtplan=s.convert_rtplan_check.isChecked(),
                        resample=s.resample_check.isChecked(),
                        new_voxel_size=(float(s.voxel_x.text()), float(s.voxel_y.text()), float(s.voxel_z.text())),
                        interpolator=s.interpolator_combo.currentText(),
                        discretize=s.discretization_group.isChecked(),
                        discretization_type="FixedBinWidth" if s.discretization_type_combo.currentIndex() == 0 else "FixedBinCount",
                        discretization_value=float(s.discretization_value_edit.text()),
                        override_spacing=s.override_spacing_check.isChecked(),
                        new_spacing=(float(s.spacing_x.text()), float(s.spacing_y.text())) if s.override_spacing_check.isChecked() and s.spacing_x.text() and s.spacing_y.text() else None,
                        override_orientation=s.override_orientation_check.isChecked(),
                        new_orientation=s.orientation_combo.currentText()
                    )
                elif modality == "MRI":
                    if not isinstance(s, MRISettingsWidget): return None
                    return MRIConversionConfig(
                        input_dir=input_dir, output_dir=output_dir,
                        n4_bias_correction=s.n4_correction_check.isChecked(),
                        normalization_method=s.norm_combo.currentText().split(" ")[0],
                        skull_stripping=s.skull_stripping_check.isChecked(),
                        discretize=s.mri_discretization_group.isChecked(),
                        discretization_type="FixedBinWidth" if s.mri_dis_type_combo.currentIndex() == 0 else "FixedBinCount",
                        discretization_value=float(s.mri_dis_value_edit.text())
                    )
                elif modality == "钼靶":
                    if not isinstance(s, MammographySettingsWidget): return None
                    return MammographyConversionConfig(
                        input_dir=input_dir, output_dir=output_dir,
                        correct_orientation=s.orientation_check.isChecked(),
                        remove_edge_info=s.anonymize_check.isChecked()
                    )
                elif modality == "超声":
                    if not isinstance(s, UltrasoundSettingsWidget): return None
                    return UltrasoundConversionConfig(
                        input_dir=input_dir, output_dir=output_dir
                    )
                else:
                    QMessageBox.warning(self, "未实现", f"尚未支持 '{modality}' 类型的处理。")
                    return None
            except ValueError as e:
                QMessageBox.critical(self, "输入错误", f"预处理参数值无效，请检查输入是否为数字。\n错误: {e}")
                return None
            except Exception as e:
                QMessageBox.critical(self, "未知错误", f"收集设置时发生意外错误: {e}")
                return None

        def _start_preprocessing(self):
            """启动预处理流程"""
            # ===================================================================
            #  授权检查
            # ===================================================================
            license_manager = self.controller.get_license_manager()
            if not license_manager.is_licensed():
                if license_manager.can_use_trial():
                    remaining = license_manager.get_remaining_trials()
                    msg = QMessageBox()
                    msg.setIcon(QMessageBox.Icon.Warning)
                    msg.setText(f"您当前未激活软件，将使用试用次数。")
                    # The count is decremented *after* use, so show the current value
                    msg.setInformativeText(f"剩余试用次数: {remaining} 次。\n\n是否继续？")
                    msg.setWindowTitle("试用提醒")
                    msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                    ret = msg.exec()
                    
                    if ret == QMessageBox.StandardButton.Yes:
                        license_manager.use_trial() # Consume one trial
                        self.trial_used.emit() # Notify UI to update
                    else:
                        self.log_display.append("用户取消了操作。")
                        return
                else:
                    QMessageBox.critical(self, "试用结束", 
                                         "您的试用次数已用尽。请前往'设置'页面激活软件以继续使用。")
                    return
            # ===================================================================

            config = self._collect_settings()
            if not config:
                self.log_display.append("配置无效或用户取消，处理中止。")
                return

            self.log_display.append(f"▶️ 开始处理 '{config.modality}' 任务...")
            self.log_display.append(f"   - 输入: {config.input_dir}")
            self.log_display.append(f"   - 输出: {config.output_dir}")
            pp = pprint.PrettyPrinter(indent=4)
            self.log_display.append("   - 参数:\n" + pp.pformat(config))

            self.start_button.setEnabled(False)
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(0)
            
            signals = self.controller.run_preprocessing(config)
            signals.progress.connect(self._update_progress)
            signals.finished.connect(self._on_processing_finished)
            signals.error.connect(self._on_processing_error)

    class IGPSMainWindow(QMainWindow):
        """IGPS主程序窗口 (基于PyQt6)"""
        def __init__(self):
            super().__init__()
            self.setWindowTitle(f"Image Group Processing System - v{__version__}")
            self.setGeometry(100, 100, 1200, 800)
            self.license_manager = IGPSLicenseManager()

            self._create_menu()
            self._create_central_widget()
            self._create_status_bar()
            self.show()
            
            # Connect signals to slots for UI updates
            self.settings_tab.license_activated.connect(self.update_status_bar)
            self.settings_tab.license_activated.connect(self.settings_tab.update_status_display)
            self.preprocessing_tab.trial_used.connect(self.update_status_bar)
            self.preprocessing_tab.trial_used.connect(self.settings_tab.update_status_display)

            self.update_status_bar()

        def _create_menu(self):
            menu_bar = self.menuBar()
            file_menu = menu_bar.addMenu("&文件")
            exit_action = QAction("&退出", self)
            exit_action.triggered.connect(self.close)
            file_menu.addAction(exit_action)
            help_menu = menu_bar.addMenu("帮助")
            
            docs_action = QAction("查看文档", self)
            # Placeholder: Connect this to showing a help dialog/file
            help_menu.addAction(docs_action)

            about_action = QAction("关于 IGPS", self)
            # Placeholder: Connect this to an about box
            help_menu.addAction(about_action)

        def _create_central_widget(self):
            """创建主窗口中心控件"""
            self.tabs = QTabWidget()

            # 1. 图像预处理
            self.preprocessing_tab = PreprocessingTab(self.license_manager, self)
            self.tabs.addTab(self.preprocessing_tab, "图像预处理")

            # 2. 特征提取
            self.feature_extraction_tab = QWidget()
            self.tabs.addTab(self.feature_extraction_tab, "特征提取")

            # 3. 特征选择
            self.feature_selection_tab = QWidget()
            self.tabs.addTab(self.feature_selection_tab, "特征选择")
            
            # 4. 模型构建
            self.model_building_tab = QWidget()
            self.tabs.addTab(self.model_building_tab, "模型构建")

            # 5. 设置
            self.settings_tab = SettingsTab(self.license_manager, self)
            self.tabs.addTab(self.settings_tab, "设置")

            self.setCentralWidget(self.tabs)
            
            # 连接帮助菜单动作到设置页面的槽
            # A more robust way to find the menu
            for menu in self.menuBar().findChildren(QMenu):
                if menu.title() == "帮助":
                    actions = menu.actions()
                    if len(actions) > 0:
                        actions[0].triggered.connect(self.settings_tab.show_help_dialog)
                    if len(actions) > 1:
                        actions[1].triggered.connect(self.settings_tab.show_about_dialog)
                    break

        def _create_status_bar(self):
            """创建并布局状态栏"""
            self.status_bar = QStatusBar()
            self.setStatusBar(self.status_bar)
            
            # --- Main container widget for the status bar ---
            status_widget = QWidget()
            status_layout = QHBoxLayout(status_widget)
            status_layout.setContentsMargins(10, 0, 10, 0) # left, top, right, bottom

            # --- 1. License Status (Left) ---
            self.license_status_label = QLabel("授权状态未知")
            status_layout.addWidget(self.license_status_label)
            
            status_layout.addStretch(1)

            # --- 2. Copyright (Center) ---
            copyright_label = QLabel("© 2025 TanX. All Rights Reserved.")
            copyright_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            status_layout.addWidget(copyright_label)

            status_layout.addStretch(1)

            # --- 3. External Links (Right) ---
            links_layout = QHBoxLayout()
            
            # Create icon objects using paths relative to the main script
            app_dir = Path(__file__).parent
            github_icon = QIcon(str(app_dir / "resources" / "github-mark.png"))
            home_icon = QIcon(str(app_dir / "resources" / "home.png"))
            blog_icon = QIcon(str(app_dir / "resources" / "blogger.png"))

            # GitHub Icon
            github_label = ClickableLabel("https://github.com/1009476063/IGPS", "")
            github_label.setPixmap(github_icon.pixmap(16, 16))
            github_label.setToolTip("查看项目GitHub仓库")
            links_layout.addWidget(github_label)

            # Home Icon
            home_label = ClickableLabel("https://alist.1661688.xyz", "")
            home_label.setPixmap(home_icon.pixmap(16, 16))
            home_label.setToolTip("访问作者主页")
            links_layout.addWidget(home_label)

            # Blog Icon
            blog_label = ClickableLabel("https://blog.1661688.xyz", "")
            blog_label.setPixmap(blog_icon.pixmap(16, 16))
            blog_label.setToolTip("访问作者博客")
            links_layout.addWidget(blog_label)

            status_layout.addLayout(links_layout)
            
            self.status_bar.addWidget(status_widget, 1)

        def update_status_bar(self):
            """根据授权状态更新状态栏显示"""
            info = self.license_manager.get_license_info()
            if info:
                status_text = f"<font color='green'><b>授权成功</b> (剩余 {info.days_remaining} 天)</font>"
            else:
                remaining_trials = self.license_manager.get_remaining_trials()
                if remaining_trials > 0:
                    status_text = f"<font color='orange'><b>试用模式</b> (剩余 {remaining_trials} 次)</font>"
                else:
                    status_text = f"<font color='red'><b>授权已失效</b></font>"
            self.license_status_label.setText(status_text)


# ===================================================================
#  Core Logic (Non-GUI)
# ===================================================================
# Dummy classes for when GUI is not available, to allow core logic to run
if not GUI_AVAILABLE:
    class QWidget: pass
    class QObject: pass
    class QMainWindow: pass
    class PreprocessingTab(QWidget): pass
    # Add any other required base classes

def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="IGPS - Image Group Processing System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  python main.py                    # 启动GUI界面
  python main.py --version          # 显示版本信息
  python main.py --license          # 许可证管理
        """
    )
    
    parser.add_argument(
        "--version", 
        action="version", 
        version=f"IGPS {__version__} by {__author__}"
    )
    
    parser.add_argument(
        "--license",
        action="store_true",
        help="进入命令行许可证管理模式"
    )
    
    parser.add_argument("--hwid", action="store_true", help="显示本机硬件ID")
    parser.add_argument("--export", type=str, help="导出内置授权码到指定文件")
    args = parser.parse_args()

    return args

def setup_environment():
    """设置应用程序环境"""
    app_dir = Path(__file__).parent
    directories = [app_dir / "logs", app_dir / "config", app_dir / "temp", app_dir / "output", app_dir / "generated"]
    for directory in directories:
        directory.mkdir(exist_ok=True)
    return app_dir

def setup_logging(verbose=False, debug=False):
    """设置日志系统"""
    log_level = logging.DEBUG if debug else (logging.INFO if verbose else logging.WARNING)
    logging.basicConfig(level=log_level, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger = logging.getLogger(__name__)
    logger.info(f"IGPS {__version__} 启动")
    return logger

def run_gui_mode():
    """以GUI模式运行"""
    if not GUI_AVAILABLE:
        print("错误: PyQt6 未安装或加载失败，无法启动GUI。")
        print("请运行 'pip install PyQt6' 来安装。")
        return

    app = QApplication(sys.argv)
    
    # 在启动主窗口前进行一次授权检查
    license_manager = IGPSLicenseManager()
    if not license_manager.is_licensed() and not license_manager.can_use_trial():
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Icon.Warning)
        msg_box.setWindowTitle("授权提醒")
        msg_box.setText("您的授权已过期或试用次数已用尽。")
        msg_box.setInformativeText("请在启动后前往'设置'页面激活软件。在激活之前，核心功能将被禁用。")
        msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg_box.exec()
        
    main_window = IGPSMainWindow()
    sys.exit(app.exec())

def run_license_mode():
    """运行许可证管理模式 (交互式)"""
    print("🔑 许可证管理模式...")
    if not GUI_AVAILABLE:
        print("无法启动许可证模式，因为GUI模块未能成功导入。")
        return

    try:
        manager = IGPSLicenseManager()
        
        while True:
            print("\n--- 授权管理 ---")
            info = manager.get_license_info()
            if info:
                print(f"状态: 已授权")
                print(f"授权到期: {info['expire_date']}")
            else:
                trials_left = manager.get_remaining_trials()
                if trials_left > 0:
                    print(f"状态: 未授权 (剩余 {trials_left} 次试用)")
                else:
                    print("状态: 未授权 (试用已结束)")

            print("\n请选择操作:")
            print("1. 激活新授权码")
            print("2. 查看硬件ID")
            print("0. 退出")

            choice = input("> ")
            if choice == '1':
                key = input("请输入16位授权码: ")
                success, msg = manager.activate_license(key)
                print(f"激活结果: {msg}")
            elif choice == '2':
                hwid = manager.get_hardware_id()
                print(f"您的硬件ID是: {hwid}")
            elif choice == '0':
                break
            else:
                print("无效输入。")

    except Exception as e:
        print(f"无法加载授权模块: {e}")

def main():
    """主函数入口"""
    args = parse_arguments()
    setup_environment()
    setup_logging()
    
    if args.license:
        run_license_mode()
    else:
        run_gui_mode()

if __name__ == "__main__":
    main() 