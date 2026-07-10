# -*- coding: utf-8 -*-
import os
import re
import subprocess
import sys
from pathlib import Path
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QTextEdit, QTableWidget, QTableWidgetItem, 
                             QHeaderView, QTabWidget, QListWidget, QListWidgetItem, 
                             QMessageBox, QSplitter, QLineEdit, QAbstractItemView, 
                             QToolTip, QComboBox)
from PyQt6.QtCore import Qt, pyqtSlot, QUrl
from PyQt6.QtGui import QDesktopServices, QGuiApplication, QCursor, QPixmap
from models.project_model import ProjectModel
from services.text_processor import TextProcessor
from services.downloader import DownloadThread

class ProjectDetailWidget(QWidget):
    """Widget displaying detail and editing options for a selected project."""
    
    project_saved_signal = pyqtSlot() # To trigger sidebar reload if names change (not needed in v1, but good to have)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.project_path = None
        self.project_model = None
        self.download_thread = None
        self.template_manager = None
        self.init_ui()

    def set_template_manager(self, tm):
        self.template_manager = tm

    def init_ui(self):
        # Base styling for warm theme
        self.setStyleSheet("""
            QWidget#detail_root {
                background-color: #FAF6F0;
            }
            QLabel#lbl_proj_title {
                font-size: 16px;
                font-weight: bold;
                color: #5D4037;
            }
            QLabel {
                font-size: 13px;
                color: #5D4037;
                font-weight: bold;
            }
            QPushButton {
                background-color: #E0A96D;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #D2904C;
            }
            QPushButton:pressed {
                background-color: #B87635;
            }
            QPushButton#btn_delete_segment {
                background-color: #E57373;
            }
            QPushButton#btn_delete_segment:hover {
                background-color: #EF5350;
            }
            QPushButton#btn_open_folder {
                background-color: #D7CCC8;
                color: #5D4037;
            }
            QPushButton#btn_open_folder:hover {
                background-color: #BCAAA4;
            }
            QTextEdit {
                background-color: white;
                border: 1px solid #D7CCC8;
                border-radius: 4px;
                color: #3E2723;
                font-family: Consolas, sans-serif;
                font-size: 13px;
            }
            QTableWidget {
                background-color: white;
                border: 1px solid #D7CCC8;
                border-radius: 4px;
                gridline-color: #EFEBE9;
                selection-background-color: #FFE0B2;
                selection-color: #5D4037;
            }
            QHeaderView::section {
                background-color: #D7CCC8;
                color: #5D4037;
                padding: 4px;
                font-weight: bold;
                border: 1px solid #EFEBE9;
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
        
        self.setObjectName("detail_root")
        
        # We start in a "No Selection" state
        self.layout_stack = QVBoxLayout(self)
        
        self.no_selection_widget = QLabel("请在左侧选择一个工程项目以查看详情...")
        self.no_selection_widget.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.no_selection_widget.setStyleSheet("font-size: 16px; color: #8D6E63; font-style: italic;")
        self.layout_stack.addWidget(self.no_selection_widget)
        
        # Create the main content widget (initially hidden)
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        
        # Header Row
        header_layout = QHBoxLayout()
        self.lbl_proj_title = QLabel("项目名称:")
        self.lbl_proj_title.setObjectName("lbl_proj_title")
        header_layout.addWidget(self.lbl_proj_title)
        
        header_layout.addStretch()
        
        self.btn_open_folder = QPushButton("📂 在文件夹中显示")
        self.btn_open_folder.setObjectName("btn_open_folder")
        self.btn_open_folder.clicked.connect(self.open_project_folder)
        header_layout.addWidget(self.btn_open_folder)
        
        self.content_layout.addLayout(header_layout)
        
        # Tabs
        self.tabs = QTabWidget()
        self.init_text_tab()
        self.init_media_tab()
        self.content_layout.addWidget(self.tabs)
        
        self.layout_stack.addWidget(self.content_widget)
        self.content_widget.setVisible(False)

    def init_text_tab(self):
        tab_widget = QWidget()
        tab_layout = QVBoxLayout(tab_widget)
        tab_layout.setContentsMargins(10, 10, 10, 10)
        tab_layout.setSpacing(10)
        
        # 1. Top Selectors Layout
        selectors_layout = QHBoxLayout()
        selectors_layout.setSpacing(10)
        
        selectors_layout.addWidget(QLabel("选择提示词模板:"))
        self.combo_templates = QComboBox()
        self.combo_templates.currentIndexChanged.connect(self.on_template_changed)
        selectors_layout.addWidget(self.combo_templates, stretch=1)
        
        selectors_layout.addWidget(QLabel("选择运镜预设:"))
        self.combo_motions = QComboBox()
        self.combo_motions.currentIndexChanged.connect(self.on_motion_changed)
        selectors_layout.addWidget(self.combo_motions, stretch=1)
        
        tab_layout.addLayout(selectors_layout)
        
        # 2. Main Splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left pane: Chinese & Spanish texts
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        left_layout.addWidget(QLabel("中文原文 (Chinese Source):"))
        self.txt_chinese = QTextEdit()
        left_layout.addWidget(self.txt_chinese)
        
        left_layout.addWidget(QLabel("西班牙语原文 (Spanish Source):"))
        self.txt_spanish = QTextEdit()
        left_layout.addWidget(self.txt_spanish)
        
        self.btn_segment = QPushButton("✨ 自动清洗并智能切分西文")
        self.btn_segment.clicked.connect(self.run_segmentation)
        left_layout.addWidget(self.btn_segment)
        
        left_widget.setLayout(left_layout)
        splitter.addWidget(left_widget)
        
        # Right pane: Segment Table
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        
        right_layout.addWidget(QLabel("切分段落与提示词工作台 (Segments & Prompts):"))
        
        self.table_segments = QTableWidget()
        self.table_segments.setColumnCount(6)
        self.table_segments.setHorizontalHeaderLabels([
            "序号", "分句文案 (双击可修改)", "字数", "时长 (秒)", "生成的提示词 (双击可复制)", "操作"
        ])
        self.table_segments.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table_segments.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
        self.table_segments.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self.table_segments.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Interactive)
        self.table_segments.cellChanged.connect(self.on_cell_changed)
        
        right_layout.addWidget(self.table_segments)
        
        # Table edit buttons
        table_buttons_layout = QHBoxLayout()
        self.btn_add_segment = QPushButton("＋ 添加行")
        self.btn_add_segment.clicked.connect(self.add_segment_row)
        table_buttons_layout.addWidget(self.btn_add_segment)
        
        self.btn_delete_segment = QPushButton("－ 删除选中行")
        self.btn_delete_segment.setObjectName("btn_delete_segment")
        self.btn_delete_segment.clicked.connect(self.delete_selected_segment)
        table_buttons_layout.addWidget(self.btn_delete_segment)
        
        table_buttons_layout.addStretch()
        
        self.btn_save_project = QPushButton("💾 保存修改")
        self.btn_save_project.clicked.connect(self.save_project_data)
        table_buttons_layout.addWidget(self.btn_save_project)
        
        right_layout.addLayout(table_buttons_layout)
        right_widget.setLayout(right_layout)
        splitter.addWidget(right_widget)
        
        # Collapse the left widget (Chinese & Spanish text inputs) by default.
        splitter.setSizes([0, 900])
        tab_layout.addWidget(splitter, stretch=1)
        
        tab_widget.setLayout(tab_layout)
        self.tabs.addTab(tab_widget, "📝 文案、切分与提示词")

    def init_media_tab(self):
        """Initializes the media management tab."""
        tab_widget = QWidget()
        layout = QVBoxLayout(tab_widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)
        
        # 1. Google Drive URL Downloader block
        dl_layout = QHBoxLayout()
        dl_layout.addWidget(QLabel("谷歌云盘链接 (Google Drive URL):"))
        
        self.txt_gdrive_url = QTextEdit()
        self.txt_gdrive_url.setMaximumHeight(60)
        self.txt_gdrive_url.setPlaceholderText("可包含多个谷歌云盘链接，每行一个...")
        dl_layout.addWidget(self.txt_gdrive_url)
        
        self.btn_download = QPushButton("📥 下载全部资源")
        self.btn_download.clicked.connect(self.start_download)
        dl_layout.addWidget(self.btn_download)
        
        layout.addLayout(dl_layout)
        
        # 2. Download status
        self.lbl_download_status = QLabel("下载状态: 未开始")
        self.lbl_download_status.setStyleSheet("color: #795548; font-style: italic;")
        layout.addWidget(self.lbl_download_status)
        
        # 3. Split-screen List and Image Preview
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left side: List
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.addWidget(QLabel("下载的本地素材列表 (Double-click to open):"))
        
        self.list_media = QListWidget()
        self.list_media.doubleClicked.connect(self.open_media_file)
        self.list_media.currentItemChanged.connect(self.on_media_selection_changed)
        left_layout.addWidget(self.list_media)
        
        left_widget.setLayout(left_layout)
        splitter.addWidget(left_widget)
        
        # Right side: Preview
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.addWidget(QLabel("图片素材预览 (Preview):"))
        
        self.lbl_preview = QLabel("选择左侧素材以预览...")
        self.lbl_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_preview.setStyleSheet("""
            QLabel {
                background-color: #EFEBE9;
                border: 1px solid #D7CCC8;
                border-radius: 4px;
                color: #8D6E63;
                font-weight: normal;
            }
        """)
        self.lbl_preview.setMinimumWidth(300)
        right_layout.addWidget(self.lbl_preview, stretch=1)
        
        right_widget.setLayout(right_layout)
        splitter.addWidget(right_widget)
        
        splitter.setSizes([350, 450])
        layout.addWidget(splitter, stretch=1)
        
        tab_widget.setLayout(layout)
        self.tabs.addTab(tab_widget, "📁 资源下载与管理")

    def reset_to_no_selection(self):
        """Resets the detail widget to the 'No Selection' state."""
        self.project_path = None
        self.project_model = None
        self.content_widget.setVisible(False)
        self.no_selection_widget.setVisible(True)

    def set_project(self, project_path):
        """Loads and binds project data."""
        self.project_path = Path(project_path)
        self.project_model = ProjectModel(self.project_path)
        
        # Switch visible UI
        self.no_selection_widget.setVisible(False)
        self.content_widget.setVisible(True)
        
        # Update labels and fields
        self.lbl_proj_title.setText(f"项目名称: {self.project_model.project_id} (序号: {self.project_model.index:02d})")
        self.txt_chinese.setPlainText(self.project_model.chinese_text)
        self.txt_spanish.setPlainText(self.project_model.spanish_text)
        self.txt_gdrive_url.setPlainText(self.project_model.google_drive_url)
        
        # Populate table segments
        self.populate_segments_table()
        
        # Refresh media list
        self.refresh_media_list()
        
        # Refresh templates dropdowns & prompts table
        self.refresh_template_comboboxes()
        
        # Check if this project has an active background download running in MainWindow
        main_win = self.window()
        if hasattr(main_win, "active_downloads") and self.project_model.project_id in main_win.active_downloads:
            self.lbl_download_status.setText("下载状态: 正在后台自动下载中...")
            self.btn_download.setEnabled(False)
        else:
            self.lbl_download_status.setText("下载状态: 未开始")
            self.btn_download.setEnabled(True)

    def populate_segments_table(self):
        """Fills QTableWidget with stored Spanish segments and generated prompts."""
        self.table_segments.blockSignals(True)
        self.table_segments.clearContents()
        
        if not self.project_model:
            self.table_segments.setRowCount(0)
            self.table_segments.blockSignals(False)
            return
            
        segments = self.project_model.spanish_segments
        self.table_segments.setRowCount(len(segments))
        
        # Get active template & motion
        tpl_id = self.combo_templates.currentData()
        motion_id = self.combo_motions.currentData()
        
        tpl = self.template_manager.get_template(tpl_id) if self.template_manager else None
        motion = self.template_manager.get_motion(motion_id) if self.template_manager else None
        
        template_content = tpl["content"] if tpl else "{spanish_text}"
        motion_content = motion["content"] if motion else ""
        
        for idx, seg in enumerate(segments):
            # 0. Index
            self.table_segments.setItem(idx, 0, QTableWidgetItem(str(idx + 1)))
            self.table_segments.item(idx, 0).setFlags(Qt.ItemFlag.ItemIsEnabled)
            
            # 1. Spanish segment text (editable)
            text = seg.get("text", "")
            self.table_segments.setItem(idx, 1, QTableWidgetItem(text))
            
            # Calculate length and duration dynamically
            length = len(text)
            
            # Determine duration label
            if length <= 100:
                duration_label = "6s"
            elif length <= 140:
                duration_label = "8s"
            elif length <= 180:
                duration_label = "10s"
            else:
                duration_label = "超时 (>10s)"
                
            # 2. Length (read-only)
            self.table_segments.setItem(idx, 2, QTableWidgetItem(str(length)))
            self.table_segments.item(idx, 2).setFlags(Qt.ItemFlag.ItemIsEnabled)
            
            # 3. Duration (read-only)
            duration_item = QTableWidgetItem(duration_label)
            duration_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
            if length > 180:
                duration_item.setForeground(Qt.GlobalColor.red)
            self.table_segments.setItem(idx, 3, duration_item)
            
            # 4. Generated final prompt (read-only)
            final_prompt = template_content.replace("{spanish_text}", text)
            final_prompt = final_prompt.replace("{camera_motion}", motion_content)
            final_prompt = re.sub(r' +', ' ', final_prompt).strip()
            
            prompt_item = QTableWidgetItem(final_prompt)
            prompt_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            self.table_segments.setItem(idx, 4, prompt_item)
            
            # 5. Dual action buttons
            btn_widget = QWidget()
            btn_layout = QHBoxLayout(btn_widget)
            btn_layout.setContentsMargins(2, 2, 2, 2)
            btn_layout.setSpacing(4)
            
            btn_copy_text = QPushButton("📋 复制文案")
            btn_copy_prompt = QPushButton("🤖 复制提示词")
            
            btn_copy_text.setStyleSheet("padding: 2px 6px; font-size: 11px; font-weight: normal;")
            btn_copy_prompt.setStyleSheet("padding: 2px 6px; font-size: 11px; font-weight: bold; background-color: #E0A96D; color: white;")
            
            btn_copy_text.clicked.connect(self.copy_segment_text)
            btn_copy_prompt.clicked.connect(self.copy_segment_prompt)
            
            btn_layout.addWidget(btn_copy_text)
            btn_layout.addWidget(btn_copy_prompt)
            btn_widget.setLayout(btn_layout)
            
            self.table_segments.setCellWidget(idx, 5, btn_widget)
            
        self.table_segments.blockSignals(False)

    def on_cell_changed(self, row, column):
        """Saves edited segment text, updates character count, duration and prompt columns in the UI."""
        if column != 1:
            return
            
        text_item = self.table_segments.item(row, 1)
        new_text = text_item.text().strip() if text_item else ""
        
        # Calculate length and duration
        length = len(new_text)
        
        if length <= 100:
            duration_label = "6s"
            duration_val = 6
        elif length <= 140:
            duration_label = "8s"
            duration_val = 8
        elif length <= 180:
            duration_label = "10s"
            duration_val = 10
        else:
            duration_label = "超时 (>10s)"
            duration_val = 10
            
        self.table_segments.blockSignals(True)
        
        # 1. Update length cell
        self.table_segments.setItem(row, 2, QTableWidgetItem(str(length)))
        self.table_segments.item(row, 2).setFlags(Qt.ItemFlag.ItemIsEnabled)
        
        # 2. Update duration cell
        dur_item = QTableWidgetItem(duration_label)
        dur_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
        if length > 180:
            dur_item.setForeground(Qt.GlobalColor.red)
        self.table_segments.setItem(row, 3, dur_item)
        
        # 3. Update generated final prompt cell
        tpl_id = self.combo_templates.currentData()
        motion_id = self.combo_motions.currentData()
        tpl = self.template_manager.get_template(tpl_id) if self.template_manager else None
        motion = self.template_manager.get_motion(motion_id) if self.template_manager else None
        template_content = tpl["content"] if tpl else "{spanish_text}"
        motion_content = motion["content"] if motion else ""
        
        final_prompt = template_content.replace("{spanish_text}", new_text)
        final_prompt = final_prompt.replace("{camera_motion}", motion_content)
        final_prompt = re.sub(r' +', ' ', final_prompt).strip()
        
        prompt_item = QTableWidgetItem(final_prompt)
        prompt_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
        self.table_segments.setItem(row, 4, prompt_item)
        
        self.table_segments.blockSignals(False)
        
        # 4. Update in-memory model
        if self.project_model and row < len(self.project_model.spanish_segments):
            self.project_model.spanish_segments[row]["text"] = new_text
            self.project_model.spanish_segments[row]["length"] = length
            self.project_model.spanish_segments[row]["duration"] = duration_val

    def add_segment_row(self):
        """Adds a blank row to the segments table."""
        self.table_segments.blockSignals(True)
        row_idx = self.table_segments.rowCount()
        self.table_segments.insertRow(row_idx)
        
        self.table_segments.setItem(row_idx, 0, QTableWidgetItem(str(row_idx + 1)))
        self.table_segments.item(row_idx, 0).setFlags(Qt.ItemFlag.ItemIsEnabled)
        self.table_segments.setItem(row_idx, 1, QTableWidgetItem(""))
        self.table_segments.setItem(row_idx, 2, QTableWidgetItem("0"))
        self.table_segments.item(row_idx, 2).setFlags(Qt.ItemFlag.ItemIsEnabled)
        self.table_segments.setItem(row_idx, 3, QTableWidgetItem("6s"))
        
        self.table_segments.setItem(row_idx, 4, QTableWidgetItem(""))
        self.table_segments.item(row_idx, 4).setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
        
        # Add copy buttons in Col 5
        btn_widget = QWidget()
        btn_layout = QHBoxLayout(btn_widget)
        btn_layout.setContentsMargins(2, 2, 2, 2)
        btn_layout.setSpacing(4)
        
        btn_copy_text = QPushButton("📋 复制文案")
        btn_copy_prompt = QPushButton("🤖 复制提示词")
        
        btn_copy_text.setStyleSheet("padding: 2px 6px; font-size: 11px; font-weight: normal;")
        btn_copy_prompt.setStyleSheet("padding: 2px 6px; font-size: 11px; font-weight: bold; background-color: #E0A96D; color: white;")
        
        btn_copy_text.clicked.connect(self.copy_segment_text)
        btn_copy_prompt.clicked.connect(self.copy_segment_prompt)
        
        btn_layout.addWidget(btn_copy_text)
        btn_layout.addWidget(btn_copy_prompt)
        btn_widget.setLayout(btn_layout)
        
        self.table_segments.setCellWidget(row_idx, 5, btn_widget)
        
        self.table_segments.blockSignals(False)

    def copy_segment_text(self):
        """Copies the text of the row containing the clicked button to clipboard."""
        button = self.sender()
        if not button:
            return
            
        target_row = -1
        for row in range(self.table_segments.rowCount()):
            widget = self.table_segments.cellWidget(row, 5)
            if widget and button in widget.findChildren(QPushButton):
                target_row = row
                break
                
        if target_row != -1:
            text_item = self.table_segments.item(target_row, 1)
            if text_item:
                text = text_item.text().strip()
                if text:
                    clipboard = QGuiApplication.clipboard()
                    clipboard.setText(text)
                    QToolTip.showText(QCursor.pos(), "已复制分句西文！", self)

    def copy_segment_prompt(self):
        """Copies generated prompt from corresponding row to clipboard."""
        button = self.sender()
        if not button:
            return
            
        target_row = -1
        for row in range(self.table_segments.rowCount()):
            widget = self.table_segments.cellWidget(row, 5)
            if widget and button in widget.findChildren(QPushButton):
                target_row = row
                break
                
        if target_row != -1:
            prompt_item = self.table_segments.item(target_row, 4)
            if prompt_item:
                prompt_text = prompt_item.text().strip()
                if prompt_text:
                    clipboard = QGuiApplication.clipboard()
                    clipboard.setText(prompt_text)
                    QToolTip.showText(QCursor.pos(), "已复制完整提示词！", self)

    def delete_selected_segment(self):
        """Deletes selected row in segments table."""
        selected_rows = self.table_segments.selectedRanges()
        if not selected_rows:
            return
            
        # Delete from bottom to top to avoid offset errors
        rows_to_delete = []
        for r in selected_rows:
            for i in range(r.topRow(), r.bottomRow() + 1):
                rows_to_delete.append(i)
        
        rows_to_delete = sorted(list(set(rows_to_delete)), reverse=True)
        for r in rows_to_delete:
            self.table_segments.removeRow(r)
            
        # Recalculate IDs
        self.table_segments.blockSignals(True)
        for idx in range(self.table_segments.rowCount()):
            self.table_segments.setItem(idx, 0, QTableWidgetItem(str(idx + 1)))
            self.table_segments.item(idx, 0).setFlags(Qt.ItemFlag.ItemIsEnabled)
        self.table_segments.blockSignals(False)

    def run_segmentation(self):
        """Cleans and segments the Spanish text."""
        if not self.project_model:
            return
            
        text = self.txt_spanish.toPlainText()
        if not text.strip():
            QMessageBox.warning(self, "提示", "西班牙语文案为空，请先输入。")
            return
            
        # Perform segmentation
        segments = TextProcessor.segment_spanish_text(text)
        self.project_model.spanish_segments = segments
        self.populate_segments_table()
        QMessageBox.information(self, "成功", "已完成西文的表情清理与智能切分！")

    def save_project_data(self):
        """Saves text changes and segments back to metadata.json."""
        if not self.project_model:
            return
            
        # 1. Update basic texts
        self.project_model.chinese_text = self.txt_chinese.toPlainText()
        self.project_model.spanish_text = self.txt_spanish.toPlainText()
        self.project_model.google_drive_url = self.txt_gdrive_url.toPlainText().strip()
        
        # 2. Update segments from table
        segments = []
        for row in range(self.table_segments.rowCount()):
            text_item = self.table_segments.item(row, 1)
            duration_item = self.table_segments.item(row, 3)
            
            text = text_item.text().strip() if text_item else ""
            dur_str = duration_item.text().strip().replace("s", "") if duration_item else "6"
            try:
                duration = int(dur_str)
            except ValueError:
                duration = 6
                
            segments.append({
                "text": text,
                "length": len(text),
                "duration": duration
            })
            
        self.project_model.spanish_segments = segments
        
        # 3. Save to disk
        if self.project_model.save():
            QMessageBox.information(self, "成功", "工程文案与配置保存成功！")
        else:
            QMessageBox.critical(self, "错误", "工程保存失败，请检查写入权限。")

    def open_project_folder(self):
        """Opens project folder in system file explorer."""
        if self.project_path and self.project_path.exists():
            QDesktopServices.openUrl(QUrl(self.project_path.as_uri()))

    def start_download(self):
        """Starts background download of Google Drive link by delegating to MainWindow."""
        url = self.txt_gdrive_url.toPlainText().strip()
        if not url:
            QMessageBox.warning(self, "错误", "谷歌云盘链接为空，无法下载。")
            return
            
        main_win = self.window()
        if hasattr(main_win, "active_downloads") and self.project_model.project_id in main_win.active_downloads:
            QMessageBox.warning(self, "提示", "该项目的下载任务已在后台运行中，请等待完成。")
            return
            
        if hasattr(main_win, "start_background_download"):
            self.btn_download.setEnabled(False)
            self.lbl_download_status.setText("下载状态: 初始化中...")
            main_win.start_background_download(self.project_model.project_id, url, self.project_path)
        else:
            # Fallback if window is not initialized
            downloads_dir = self.project_path / "downloads"
            self.btn_download.setEnabled(False)
            self.lbl_download_status.setText("下载状态: 初始化中...")
            self.download_thread = DownloadThread(url, downloads_dir)
            self.download_thread.status_signal.connect(self.on_download_status_updated)
            self.download_thread.finished_signal.connect(self.on_download_finished)
            self.download_thread.start()

    def on_download_status_updated(self, msg):
        self.lbl_download_status.setText(f"下载状态: {msg}")

    def on_download_finished(self, success, msg):
        self.btn_download.setEnabled(True)
        if success:
            self.lbl_download_status.setText("下载状态: 下载完成！")
            QMessageBox.information(self, "下载完成", msg)
        else:
            self.lbl_download_status.setText(f"下载状态: 下载失败 - {msg}")
            QMessageBox.critical(self, "下载失败", msg)
            
        # Refresh local files list
        self.refresh_media_list()
        
        # Update metadata.json list
        if self.project_model:
            self.project_model.update_media_files()

    def refresh_media_list(self):
        """Populates list_media with files inside project_dir/downloads."""
        self.list_media.clear()
        if not self.project_path:
            return
            
        downloads_dir = self.project_path / "downloads"
        if downloads_dir.exists():
            for item in downloads_dir.iterdir():
                if item.is_file():
                    # Display filename and file size in KB
                    size_kb = item.stat().st_size / 1024
                    list_item = QListWidgetItem(f"{item.name} ({size_kb:.1f} KB)")
                    list_item.setData(Qt.ItemDataRole.UserRole, item.name)
                    self.list_media.addItem(list_item)

    def open_media_file(self, qmodelindex):
        """Double click handler to open the media file with default system player/viewer."""
        current_item = self.list_media.currentItem()
        if not current_item:
            return
        filename = current_item.data(Qt.ItemDataRole.UserRole)
        if not filename:
            return
        file_path = self.project_path / "downloads" / filename
        
        if file_path.exists():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(file_path.resolve())))

    def on_media_selection_changed(self, current, previous):
        """Displays a preview of the selected image on the right side."""
        if not current:
            self.lbl_preview.clear()
            self.lbl_preview.setText("选择左侧素材以预览...")
            return
            
        filename = current.data(Qt.ItemDataRole.UserRole)
        if not filename:
            self.lbl_preview.clear()
            self.lbl_preview.setText("无有效文件名")
            return
            
        file_path = self.project_path / "downloads" / filename
        
        if file_path.exists():
            pixmap = QPixmap()
            # 1. Use Pillow to load image (handles JPEG/PNG/WEBP/GIF with 100% reliability, bypassing Qt C++ plugins)
            try:
                from PIL import Image
                from PyQt6.QtGui import QImage
                
                pil_img = Image.open(file_path)
                # Convert to RGBA format for safe rendering in Qt
                pil_img_rgba = pil_img.convert("RGBA")
                width, height = pil_img_rgba.size
                
                # Convert PIL image bytes directly to QImage
                raw_data = pil_img_rgba.tobytes("raw", "RGBA")
                # QImage requires a reference to the bytes data to stay alive, or we copy it using .copy()
                qimg = QImage(raw_data, width, height, QImage.Format.Format_RGBA8888).copy()
                
                pixmap = QPixmap.fromImage(qimg)
            except Exception as e:
                print(f"Pillow load failed: {e}. Trying fallback direct loading...")
                # 2. Fallback to direct loading
                try:
                    with open(file_path, "rb") as f:
                        img_data = f.read()
                    pixmap = QPixmap()
                    pixmap.loadFromData(img_data)
                except Exception as fallback_err:
                    print(f"Fallback direct loading failed: {fallback_err}")
                    pixmap = QPixmap()
                
            if not pixmap.isNull():
                # Prevent negative or zero scaling size
                w = max(100, self.lbl_preview.width() - 12)
                h = max(100, self.lbl_preview.height() - 12)
                
                # Scale the image to fit the label, keeping aspect ratio
                scaled_pixmap = pixmap.scaled(
                    w, h,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                self.lbl_preview.setPixmap(scaled_pixmap)
            else:
                self.lbl_preview.clear()
                self.lbl_preview.setText("无法预览此文件格式")
        else:
            self.lbl_preview.clear()
            self.lbl_preview.setText("文件不存在")

    def refresh_template_comboboxes(self):
        """Loads prompt templates and motions lists into dropdown selectors."""
        if not self.template_manager:
            return
            
        self.combo_templates.blockSignals(True)
        self.combo_motions.blockSignals(True)
        
        self.combo_templates.clear()
        self.combo_motions.clear()
        
        self.combo_templates.addItem("-- 请选择提示词模板 --", "")
        self.combo_motions.addItem("-- 请选择运镜预设 --", "")
        
        for t in self.template_manager.templates:
            self.combo_templates.addItem(t["name"], t["id"])
        for m in self.template_manager.motions:
            self.combo_motions.addItem(m["name"], m["id"])
            
        if self.project_model:
            tpl_idx = self.combo_templates.findData(self.project_model.selected_template_id)
            if tpl_idx >= 0:
                self.combo_templates.setCurrentIndex(tpl_idx)
            else:
                self.combo_templates.setCurrentIndex(0)
                
            motion_idx = self.combo_motions.findData(self.project_model.selected_motion_id)
            if motion_idx >= 0:
                self.combo_motions.setCurrentIndex(motion_idx)
            else:
                self.combo_motions.setCurrentIndex(0)
                
        self.combo_templates.blockSignals(False)
        self.combo_motions.blockSignals(False)
        
        self.populate_segments_table()

    def on_template_changed(self):
        if not self.project_model:
            return
        tpl_id = self.combo_templates.currentData()
        self.project_model.selected_template_id = tpl_id if tpl_id else ""
        self.project_model.save()
        self.populate_segments_table()

    def on_motion_changed(self):
        if not self.project_model:
            return
        motion_id = self.combo_motions.currentData()
        self.project_model.selected_motion_id = motion_id if motion_id else ""
        self.project_model.save()
        self.populate_segments_table()
