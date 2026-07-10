# -*- coding: utf-8 -*-
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QListWidget, QListWidgetItem, QLabel, QLineEdit, 
                             QTextEdit, QTabWidget, QWidget, QMessageBox, QSplitter)
from PyQt6.QtCore import Qt
import uuid

class TemplateConfigDialog(QDialog):
    """Dialog for managing prompt templates and camera motion presets."""
    
    def __init__(self, template_manager, parent=None):
        super().__init__(parent)
        self.tm = template_manager
        self.init_ui()
        self.load_data()

    def init_ui(self):
        self.setWindowTitle("模板与运镜配置 (Templates & Motions Config)")
        self.resize(850, 550)
        
        # Apply stylesheet matching the warm theme
        self.setStyleSheet("""
            QDialog {
                background-color: #FAF6F0;
                color: #5D4037;
                font-family: "Segoe UI", sans-serif;
            }
            QLabel {
                font-size: 13px;
                color: #5D4037;
                font-weight: bold;
            }
            QLineEdit, QTextEdit {
                background-color: white;
                border: 1px solid #D7CCC8;
                border-radius: 4px;
                padding: 6px;
                color: #3E2723;
                font-size: 13px;
            }
            QPushButton {
                background-color: #E0A96D;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 14px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #D2904C;
            }
            QPushButton:pressed {
                background-color: #B87635;
            }
            QPushButton#btn_delete {
                background-color: #E57373;
            }
            QPushButton#btn_delete:hover {
                background-color: #EF5350;
            }
            QListWidget {
                background-color: white;
                border: 1px solid #D7CCC8;
                border-radius: 4px;
                color: #5D4037;
            }
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #EFEBE9;
            }
            QListWidget::item:selected {
                background-color: #FFE0B2;
                color: #5D4037;
                font-weight: bold;
            }
            QTabWidget::pane {
                border: 1px solid #D7CCC8;
                background-color: #FAF6F0;
                border-radius: 4px;
            }
            QTabBar::tab {
                background-color: #EFEBE9;
                color: #795548;
                padding: 8px 16px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                font-weight: bold;
            }
            QTabBar::tab:selected {
                background-color: #FAF6F0;
                color: #5D4037;
                border: 1px solid #D7CCC8;
                border-bottom-color: #FAF6F0;
            }
        """)

        layout = QVBoxLayout(self)
        
        self.tabs = QTabWidget()
        
        # 1. Setup Prompt Templates Tab
        self.init_templates_tab()
        
        # 2. Setup Camera Motions Tab
        self.init_motions_tab()
        
        layout.addWidget(self.tabs)
        
        # Bottom Close Button
        btn_close_layout = QHBoxLayout()
        btn_close_layout.addStretch()
        self.btn_close = QPushButton("关闭")
        self.btn_close.clicked.connect(self.accept)
        btn_close_layout.addWidget(self.btn_close)
        layout.addLayout(btn_close_layout)

    def init_templates_tab(self):
        tab = QWidget()
        layout = QHBoxLayout(tab)
        
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left sidebar: List & New/Delete Buttons
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        left_layout.addWidget(QLabel("已保存的提示词模板:"))
        self.list_templates = QListWidget()
        self.list_templates.currentRowChanged.connect(self.on_template_selected)
        left_layout.addWidget(self.list_templates)
        
        btn_left_layout = QHBoxLayout()
        self.btn_new_tpl = QPushButton("＋ 新建")
        self.btn_new_tpl.clicked.connect(self.new_template)
        
        self.btn_delete_tpl = QPushButton("🗑️ 删除")
        self.btn_delete_tpl.setObjectName("btn_delete")
        self.btn_delete_tpl.clicked.connect(self.delete_template)
        
        btn_left_layout.addWidget(self.btn_new_tpl)
        btn_left_layout.addWidget(self.btn_delete_tpl)
        left_layout.addLayout(btn_left_layout)
        
        left_widget.setLayout(left_layout)
        splitter.addWidget(left_widget)
        
        # Right edit panel
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        
        right_layout.addWidget(QLabel("模板名称:"))
        self.txt_tpl_name = QLineEdit()
        right_layout.addWidget(self.txt_tpl_name)
        
        right_layout.addWidget(QLabel("模板内容 (必须包含 {spanish_text} 和 {camera_motion} 占位符):"))
        self.txt_tpl_content = QTextEdit()
        right_layout.addWidget(self.txt_tpl_content)
        
        save_layout = QHBoxLayout()
        save_layout.addStretch()
        self.btn_save_tpl = QPushButton("💾 保存模板")
        self.btn_save_tpl.clicked.connect(self.save_template)
        save_layout.addWidget(self.btn_save_tpl)
        right_layout.addLayout(save_layout)
        
        right_widget.setLayout(right_layout)
        splitter.addWidget(right_widget)
        
        splitter.setSizes([300, 550])
        layout.addWidget(splitter)
        self.tabs.addTab(tab, "📝 提示词模板")

    def init_motions_tab(self):
        tab = QWidget()
        layout = QHBoxLayout(tab)
        
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left sidebar
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        left_layout.addWidget(QLabel("已保存的运镜预设:"))
        self.list_motions = QListWidget()
        self.list_motions.currentRowChanged.connect(self.on_motion_selected)
        left_layout.addWidget(self.list_motions)
        
        btn_left_layout = QHBoxLayout()
        self.btn_new_motion = QPushButton("＋ 新建")
        self.btn_new_motion.clicked.connect(self.new_motion)
        
        self.btn_delete_motion = QPushButton("🗑️ 删除")
        self.btn_delete_motion.setObjectName("btn_delete")
        self.btn_delete_motion.clicked.connect(self.delete_motion)
        
        btn_left_layout.addWidget(self.btn_new_motion)
        btn_left_layout.addWidget(self.btn_delete_motion)
        left_layout.addLayout(btn_left_layout)
        
        left_widget.setLayout(left_layout)
        splitter.addWidget(left_widget)
        
        # Right edit panel
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        
        right_layout.addWidget(QLabel("运镜预设名称:"))
        self.txt_motion_name = QLineEdit()
        right_layout.addWidget(self.txt_motion_name)
        
        right_layout.addWidget(QLabel("运镜描述内容:"))
        self.txt_motion_content = QTextEdit()
        right_layout.addWidget(self.txt_motion_content)
        
        save_layout = QHBoxLayout()
        save_layout.addStretch()
        self.btn_save_motion = QPushButton("💾 保存预设")
        self.btn_save_motion.clicked.connect(self.save_motion)
        save_layout.addWidget(self.btn_save_motion)
        right_layout.addLayout(save_layout)
        
        right_widget.setLayout(right_layout)
        splitter.addWidget(right_widget)
        
        splitter.setSizes([300, 550])
        layout.addWidget(splitter)
        self.tabs.addTab(tab, "🎥 运镜预设")

    def load_data(self):
        """Loads items from template manager into widgets."""
        # Load templates
        self.list_templates.clear()
        for t in self.tm.templates:
            item = QListWidgetItem(t["name"])
            item.setData(Qt.ItemDataRole.UserRole, t["id"])
            self.list_templates.addItem(item)
            
        # Load motions
        self.list_motions.clear()
        for m in self.tm.motions:
            item = QListWidgetItem(m["name"])
            item.setData(Qt.ItemDataRole.UserRole, m["id"])
            self.list_motions.addItem(item)

        # Select first items by default
        if self.list_templates.count() > 0:
            self.list_templates.setCurrentRow(0)
        if self.list_motions.count() > 0:
            self.list_motions.setCurrentRow(0)

    # --- Template Handlers ---
    def on_template_selected(self, row):
        if row < 0:
            self.txt_tpl_name.clear()
            self.txt_tpl_content.clear()
            return
            
        item = self.list_templates.item(row)
        tpl_id = item.data(Qt.ItemDataRole.UserRole)
        tpl = self.tm.get_template(tpl_id)
        if tpl:
            self.txt_tpl_name.setText(tpl["name"])
            self.txt_tpl_content.setText(tpl["content"])

    def new_template(self):
        new_id = f"tpl_{uuid.uuid4().hex[:8]}"
        new_tpl = {
            "id": new_id,
            "name": "未命名提示词模板",
            "content": "这里是您的提示词模板，包含占位符 {spanish_text} 和 {camera_motion}。"
        }
        self.tm.templates.append(new_tpl)
        
        # Add to list
        item = QListWidgetItem(new_tpl["name"])
        item.setData(Qt.ItemDataRole.UserRole, new_id)
        self.list_templates.addItem(item)
        self.list_templates.setCurrentItem(item)
        self.txt_tpl_name.setFocus()

    def delete_template(self):
        row = self.list_templates.currentRow()
        if row < 0:
            return
            
        item = self.list_templates.item(row)
        tpl_id = item.data(Qt.ItemDataRole.UserRole)
        
        reply = QMessageBox.question(self, "确认删除", "确定要删除该提示词模板吗？",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.tm.templates = [t for t in self.tm.templates if t["id"] != tpl_id]
            self.tm.save_templates()
            self.list_templates.takeItem(row)

    def save_template(self):
        row = self.list_templates.currentRow()
        if row < 0:
            return
            
        name = self.txt_tpl_name.text().strip()
        content = self.txt_tpl_content.toPlainText().strip()
        
        if not name:
            QMessageBox.warning(self, "错误", "模板名称不能为空。")
            return
            
        if "{spanish_text}" not in content:
            QMessageBox.warning(self, "警告", "提示词模板内容必须包含 {spanish_text} 占位符。")
            return

        item = self.list_templates.item(row)
        tpl_id = item.data(Qt.ItemDataRole.UserRole)
        
        # Update model
        for t in self.tm.templates:
            if t["id"] == tpl_id:
                t["name"] = name
                t["content"] = content
                break
                
        # Save to file
        if self.tm.save_templates():
            # Update list display name
            item.setText(name)
            QMessageBox.information(self, "成功", "提示词模板保存成功！")
        else:
            QMessageBox.critical(self, "错误", "模板保存失败。")

    # --- Motion Handlers ---
    def on_motion_selected(self, row):
        if row < 0:
            self.txt_motion_name.clear()
            self.txt_motion_content.clear()
            return
            
        item = self.list_motions.item(row)
        motion_id = item.data(Qt.ItemDataRole.UserRole)
        motion = self.tm.get_motion(motion_id)
        if motion:
            self.txt_motion_name.setText(motion["name"])
            self.txt_motion_content.setText(motion["content"])

    def new_motion(self):
        new_id = f"motion_{uuid.uuid4().hex[:8]}"
        new_mot = {
            "id": new_id,
            "name": "未命名运镜预设",
            "content": "运镜细节描述文本"
        }
        self.tm.motions.append(new_mot)
        
        item = QListWidgetItem(new_mot["name"])
        item.setData(Qt.ItemDataRole.UserRole, new_id)
        self.list_motions.addItem(item)
        self.list_motions.setCurrentItem(item)
        self.txt_motion_name.setFocus()

    def delete_motion(self):
        row = self.list_motions.currentRow()
        if row < 0:
            return
            
        item = self.list_motions.item(row)
        motion_id = item.data(Qt.ItemDataRole.UserRole)
        
        reply = QMessageBox.question(self, "确认删除", "确定要删除该运镜预设吗？",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.tm.motions = [m for m in self.tm.motions if m["id"] != motion_id]
            self.tm.save_motions()
            self.list_motions.takeItem(row)

    def save_motion(self):
        row = self.list_motions.currentRow()
        if row < 0:
            return
            
        name = self.txt_motion_name.text().strip()
        content = self.txt_motion_content.toPlainText().strip()
        
        if not name:
            QMessageBox.warning(self, "错误", "预设名称不能为空。")
            return

        item = self.list_motions.item(row)
        motion_id = item.data(Qt.ItemDataRole.UserRole)
        
        for m in self.tm.motions:
            if m["id"] == motion_id:
                m["name"] = name
                m["content"] = content
                break
                
        if self.tm.save_motions():
            item.setText(name)
            QMessageBox.information(self, "成功", "运镜预设保存成功！")
        else:
            QMessageBox.critical(self, "错误", "运镜保存失败。")
