#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文件名: settings_tab.py
功能描述: "设置"选项卡的UI和逻辑
创建日期: 2025-06-18
作者: TanX
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QMessageBox, QTextBrowser, QDialog
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtCore import QUrl
import os
from pathlib import Path

# 假设 license_manager 在 src/auth 目录下
from ..auth.license_manager import IGPSLicenseManager
from .. import __version__ as app_version
from typing import Optional

class SettingsTab(QWidget):
    """设置页面"""
    license_activated = pyqtSignal()

    def __init__(self, license_manager: IGPSLicenseManager, parent=None):
        super().__init__(parent)
        self.license_manager = license_manager
        
        main_layout = QVBoxLayout(self)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # --- 授权管理 ---
        license_group = self._create_license_group()
        main_layout.addWidget(license_group)

        # --- 软件信息 ---
        info_group = self._create_info_group()
        main_layout.addWidget(info_group)
        
        # --- 帮助与支持 ---
        help_group = self._create_help_group()
        main_layout.addWidget(help_group)

        main_layout.addStretch()

        self.update_status_display()

    def _create_license_group(self):
        """创建授权管理控件组"""
        group = QGroupBox("授权管理")
        layout = QVBoxLayout()

        # 激活码输入
        activation_layout = QHBoxLayout()
        activation_layout.addWidget(QLabel("授权码:"))
        self.license_input = QLineEdit()
        self.license_input.setPlaceholderText("请输入16位授权码 (XXXX-XXXX-XXXX-XXXX)")
        activation_layout.addWidget(self.license_input)
        
        self.activate_button = QPushButton("激活授权")
        self.activate_button.clicked.connect(self.activate_license)
        activation_layout.addWidget(self.activate_button)
        
        layout.addLayout(activation_layout)
        
        # 状态显示
        self.status_label = QLabel()
        layout.addWidget(self.status_label)

        group.setLayout(layout)
        return group

    def _create_info_group(self):
        """创建软件信息控件组"""
        group = QGroupBox("软件与授权信息")
        layout = QVBoxLayout()

        # 硬件ID
        hw_layout = QHBoxLayout()
        hw_layout.addWidget(QLabel("本机硬件ID:"))
        self.hwid_label = QLabel(f"<code>{self.license_manager.get_hardware_fingerprint()}</code>")
        self.hwid_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        hw_layout.addWidget(self.hwid_label)
        hw_layout.addStretch()
        layout.addLayout(hw_layout)

        # 授权到期日
        expiry_layout = QHBoxLayout()
        expiry_layout.addWidget(QLabel("授权有效期至:"))
        self.expiry_label = QLabel("N/A")
        expiry_layout.addWidget(self.expiry_label)
        expiry_layout.addStretch()
        layout.addLayout(expiry_layout)
        
        # 软件版本
        version_layout = QHBoxLayout()
        version_layout.addWidget(QLabel("软件版本:"))
        self.version_label = QLabel(f"v{app_version}")
        version_layout.addWidget(self.version_label)
        version_layout.addStretch()
        layout.addLayout(version_layout)

        group.setLayout(layout)
        return group

    def _create_help_group(self):
        """创建帮助与支持控件组"""
        group = QGroupBox("帮助与支持")
        layout = QHBoxLayout()
        
        self.help_button = QPushButton("查看帮助文档")
        self.help_button.clicked.connect(self.show_help_dialog)
        layout.addWidget(self.help_button)
        
        self.about_button = QPushButton("关于软件")
        self.about_button.clicked.connect(self.show_about_dialog)
        layout.addWidget(self.about_button)

        layout.addStretch()
        group.setLayout(layout)
        return group

    def activate_license(self):
        """激活授权码"""
        license_key = self.license_input.text().strip()
        if not license_key:
            QMessageBox.warning(self, "输入错误", "请输入有效的授权码。")
            return
        
        # 假设user_name和organization暂时为空
        # 在真实场景中，可以弹出对话框要求用户输入
        success, message = self.license_manager.activate_license(license_key, "", "")
        
        if success:
            QMessageBox.information(self, "激活成功", message)
            self.license_input.clear()
            self.license_activated.emit()
        else:
            QMessageBox.critical(self, "激活失败", message)
            
        self.update_status_display()

    def update_status_display(self):
        """更新授权状态的UI显示"""
        if self.license_manager.is_licensed():
            info = self.license_manager.get_license_info()
            if info:
                status_text = f"<font color='green'><b>授权成功</b> (类型: {info.license_type})</font>"
                self.status_label.setText(status_text)
                self.expiry_label.setText(f"{info.expire_date} (剩余 {info.days_remaining} 天)")
                self.activate_button.setEnabled(False)
                self.license_input.setEnabled(False)
        else:
            remaining_trials = self.license_manager.get_remaining_trials()
            if remaining_trials > 0:
                status_text = f"<font color='orange'><b>未授权</b> (剩余试用次数: {remaining_trials})</font>"
                self.expiry_label.setText("N/A (试用模式)")
            else:
                status_text = f"<font color='red'><b>试用结束</b></font> (请激活软件以继续使用)"
                self.expiry_label.setText("N/A (试用已过期)")
            
            self.status_label.setText(status_text)
            self.activate_button.setEnabled(True)
            self.license_input.setEnabled(True)

    def show_help_dialog(self):
        """显示帮助文档对话框"""
        help_file_path = Path(__file__).parent.parent.parent / "HELP.md"
        
        help_dialog = QDialog(self)
        help_dialog.setWindowTitle("帮助文档")
        help_dialog.setMinimumSize(600, 500)
        
        layout = QVBoxLayout(help_dialog)
        text_browser = QTextBrowser()
        
        if help_file_path.exists():
            with open(help_file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            text_browser.setMarkdown(content)
        else:
            text_browser.setPlainText(f"帮助文件未找到: {help_file_path}")
            
        layout.addWidget(text_browser)
        help_dialog.exec()

    def show_about_dialog(self):
        """显示关于软件的对话框"""
        about_text = f"""
        <h2>Image Group Processing System (IGPS)</h2>
        <p>版本: {app_version}</p>
        <p>版权所有 © 2025 TanX。保留所有权利。</p>
        <p>本软件旨在提供一个高效、可靠的影像组学研究平台，集成了DICOM转换、图像预处理、特征提取与分析等功能。</p>
        <p>技术支持与联系: <a href='mailto:1009476063@qq.com'>1009476063@qq.com</a></p>
        """
        QMessageBox.about(self, "关于 IGPS", about_text) 