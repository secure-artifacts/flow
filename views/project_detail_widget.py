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
                             QToolTip, QComboBox, QFrame, QDialog)
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
        self.copied_rows = set()
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
        
        # Inner splitter for Table and Property Panel
        self.table_splitter = QSplitter(Qt.Orientation.Horizontal)
        
        self.table_segments = QTableWidget()
        self.table_segments.setColumnCount(6)
        self.table_segments.setHorizontalHeaderLabels([
            "序号", "分句文案 (双击可修改)", "字数", "时长 (秒)", "生成的提示词 (双击可复制)", "操作"
        ])
        self.table_segments.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table_segments.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table_segments.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table_segments.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
        self.table_segments.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self.table_segments.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Interactive)
        self.table_segments.cellChanged.connect(self.on_cell_changed)
        self.table_segments.cellDoubleClicked.connect(self.on_cell_double_clicked)
        self.table_segments.currentItemChanged.connect(self.on_table_selection_changed)
        
        self.table_splitter.addWidget(self.table_segments)
        
        # Property Panel Widget
        self.property_panel = QWidget()
        self.init_property_panel()
        self.table_splitter.addWidget(self.property_panel)
        
        # Set default proportions
        self.table_splitter.setSizes([680, 220])
        from PyQt6.QtWidgets import QSizePolicy
        self.table_splitter.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        right_layout.addWidget(self.table_splitter, 1)
        
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
        
        self.btn_export_batch = QPushButton("📋 导出批量生成 JSON")
        self.btn_export_batch.setStyleSheet("background-color: #8B5CF6; color: white; font-weight: bold;")
        self.btn_export_batch.clicked.connect(self.export_batch_json)
        table_buttons_layout.addWidget(self.btn_export_batch)
        
        self.btn_import_report = QPushButton("📥 导入报告并归位视频")
        self.btn_import_report.setStyleSheet("background-color: #10B981; color: white; font-weight: bold;")
        self.btn_import_report.clicked.connect(self.import_execution_report)
        table_buttons_layout.addWidget(self.btn_import_report)
        
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
        self.copied_rows = set()
        
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
        
        # Auto-associate single downloaded image if applicable
        single_img = self.get_project_single_image()
        if single_img:
            for seg in segments:
                if not seg.get("image_name"):
                    seg["image_name"] = single_img
        
        # Get active template & motion
        tpl_id = self.combo_templates.currentData()
        motion_id = self.combo_motions.currentData()
        
        tpl = self.template_manager.get_template(tpl_id) if self.template_manager else None
        motion = self.template_manager.get_motion(motion_id) if self.template_manager else None
        
        template_content = tpl["content"] if tpl else "{spanish_text}"
        motion_content = motion["content"] if motion else ""
        
        for idx, seg in enumerate(segments):
            # 0. Index
            has_image = bool(seg.get("image_name"))
            idx_text = f"{idx + 1} 📷" if has_image else str(idx + 1)
            self.table_segments.setItem(idx, 0, QTableWidgetItem(idx_text))
            self.table_segments.item(idx, 0).setFlags(Qt.ItemFlag.ItemIsEnabled)
            
            # 1. Spanish segment text (editable)
            text = seg.get("text", "")
            self.table_segments.setItem(idx, 1, QTableWidgetItem(text))
            
            # Calculate length and duration dynamically
            length = len(text)
            
            # Determine duration label
            if length <= 50:
                duration_label = "4s"
            elif length <= 100:
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
            
            # 5. Single action button (Copy Prompt)
            btn_widget = QWidget()
            btn_layout = QHBoxLayout(btn_widget)
            btn_layout.setContentsMargins(2, 2, 2, 2)
            btn_layout.setSpacing(4)
            
            btn_copy_prompt = QPushButton("🤖 复制提示词")
            btn_copy_prompt.setStyleSheet("padding: 2px 6px; font-size: 11px; font-weight: bold; background-color: #E0A96D; color: white;")
            btn_copy_prompt.clicked.connect(self.copy_segment_prompt)
            
            btn_layout.addWidget(btn_copy_prompt)
            btn_widget.setLayout(btn_layout)
            
            self.table_segments.setCellWidget(idx, 5, btn_widget)
            
        # Apply colors for copied rows
        if hasattr(self, 'copied_rows'):
            for r in self.copied_rows:
                if r < len(segments):
                    self.change_row_color(r, copied=True)
            
        self.table_segments.blockSignals(False)

    def on_cell_changed(self, row, column):
        """Saves edited segment text, updates character count, duration and prompt columns in the UI."""
        if column != 1:
            return
            
        text_item = self.table_segments.item(row, 1)
        new_text = text_item.text().strip() if text_item else ""
        
        # Calculate length and duration
        length = len(new_text)
        
        if length <= 50:
            duration_label = "4s"
            duration_val = 4
        elif length <= 100:
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
        
        # Add copy button in Col 5
        btn_widget = QWidget()
        btn_layout = QHBoxLayout(btn_widget)
        btn_layout.setContentsMargins(2, 2, 2, 2)
        btn_layout.setSpacing(4)
        
        btn_copy_prompt = QPushButton("🤖 复制提示词")
        btn_copy_prompt.setStyleSheet("padding: 2px 6px; font-size: 11px; font-weight: bold; background-color: #E0A96D; color: white;")
        btn_copy_prompt.clicked.connect(self.copy_segment_prompt)
        
        btn_layout.addWidget(btn_copy_prompt)
        btn_widget.setLayout(btn_layout)
        
        self.table_segments.setCellWidget(row_idx, 5, btn_widget)
        
        self.table_segments.blockSignals(False)
        
        if self.project_model:
            single_img = self.get_project_single_image()
            self.project_model.spanish_segments.append({
                "text": "",
                "length": 0,
                "duration": 6,
                "image_name": single_img if single_img else "",
                "mode": "VIDEO_FRAMES"
            })



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
            # Highlight this row programmatically and update property panel
            self.table_segments.selectRow(target_row)
            item = self.table_segments.item(target_row, 0)
            if item:
                self.table_segments.setCurrentItem(item)
                
            prompt_item = self.table_segments.item(target_row, 4)
            if prompt_item:
                prompt_text = prompt_item.text().strip()
                if prompt_text:
                    clipboard = QGuiApplication.clipboard()
                    clipboard.setText(prompt_text)
                    QToolTip.showText(QCursor.pos(), "已复制完整提示词！", self)
                    self.change_row_color(target_row, copied=True)

    def on_cell_double_clicked(self, row, column):
        """Handle double-clicks on the table segments."""
        if column == 3: # Double clicked on "秒数" (Duration) column
            self.change_row_color(row, copied=False)
            return
            
        if column == 4: # Double clicked on "生成的提示词" column
            prompt_item = self.table_segments.item(row, 4)
            if not prompt_item:
                return
                
            prompt_text = prompt_item.text().strip()
            if not prompt_text:
                return
                
            from PyQt6.QtWidgets import QDialog, QVBoxLayout, QTextEdit, QPushButton, QHBoxLayout
            dialog = QDialog(self)
            dialog.setWindowTitle(f"完整提示词 (第 {row + 1} 句)")
            dialog.resize(600, 400)
            
            layout = QVBoxLayout(dialog)
            
            text_edit = QTextEdit()
            text_edit.setPlainText(prompt_text)
            text_edit.setReadOnly(True)
            layout.addWidget(text_edit)
            
            btn_layout = QHBoxLayout()
            btn_layout.addStretch()
            
            btn_copy = QPushButton("📋 复制全部提示词")
            btn_copy.clicked.connect(lambda: self.copy_text_to_clipboard(prompt_text, dialog, row))
            btn_layout.addWidget(btn_copy)
            
            btn_close = QPushButton("关闭")
            btn_close.clicked.connect(dialog.accept)
            btn_layout.addWidget(btn_close)
            
            layout.addLayout(btn_layout)
            
            dialog.setStyleSheet(self.styleSheet())
            dialog.exec()

    def copy_text_to_clipboard(self, text, dialog, row):
        """Utility method to copy text and show tooltip inside dialog context."""
        clipboard = QGuiApplication.clipboard()
        clipboard.setText(text)
        QToolTip.showText(QCursor.pos(), "已复制完整提示词！", dialog)
        self.change_row_color(row, copied=True)

    def change_row_color(self, row, copied=True):
        """Change the background color of a specific row to indicate status."""
        from PyQt6.QtGui import QColor
        if copied:
            bg_color = QColor("#D4EDDA") # Light green
            text_color = QColor("#155724") # Dark green
            if hasattr(self, 'copied_rows'):
                self.copied_rows.add(row)
        else:
            bg_color = QColor()
            text_color = QColor()
            if hasattr(self, 'copied_rows') and row in self.copied_rows:
                self.copied_rows.discard(row)

        for col in range(5):
            item = self.table_segments.item(row, col)
            if item:
                if copied:
                    item.setBackground(bg_color)
                    item.setForeground(text_color)
                else:
                    item.setData(Qt.ItemDataRole.BackgroundRole, None)
                    item.setData(Qt.ItemDataRole.ForegroundRole, None)

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
            if self.project_model and r < len(self.project_model.spanish_segments):
                self.project_model.spanish_segments.pop(r)
            if hasattr(self, 'copied_rows'):
                # Remove this index, and shift all indices greater than r down by 1
                new_copied = set()
                for idx in self.copied_rows:
                    if idx < r:
                        new_copied.add(idx)
                    elif idx > r:
                        new_copied.add(idx - 1)
                self.copied_rows = new_copied
            
        # Recalculate IDs
        self.table_segments.blockSignals(True)
        for idx in range(self.table_segments.rowCount()):
            # Recalculate with 📷 emoji if it has an image
            has_image = False
            if self.project_model and idx < len(self.project_model.spanish_segments):
                has_image = bool(self.project_model.spanish_segments[idx].get("image_name"))
            idx_text = f"{idx + 1} 📷" if has_image else str(idx + 1)
            self.table_segments.setItem(idx, 0, QTableWidgetItem(idx_text))
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
        
        # 2. Update segments from table in-place to preserve other properties (image_name, mode)
        for row in range(self.table_segments.rowCount()):
            text_item = self.table_segments.item(row, 1)
            duration_item = self.table_segments.item(row, 3)
            
            text = text_item.text().strip() if text_item else ""
            dur_str = duration_item.text().strip().replace("s", "") if duration_item else "6"
            try:
                duration = int(dur_str)
            except ValueError:
                duration = 6
                
            if row < len(self.project_model.spanish_segments):
                self.project_model.spanish_segments[row]["text"] = text
                self.project_model.spanish_segments[row]["length"] = len(text)
                self.project_model.spanish_segments[row]["duration"] = duration
            else:
                self.project_model.spanish_segments.append({
                    "text": text,
                    "length": len(text),
                    "duration": duration,
                    "image_name": "",
                    "mode": "VIDEO_FRAMES"
                })
                
        # Truncate model segments to match table row count if needed
        if len(self.project_model.spanish_segments) > self.table_segments.rowCount():
            self.project_model.spanish_segments = self.project_model.spanish_segments[:self.table_segments.rowCount()]
        
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
            if success:
                self.populate_segments_table()

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
                    
        # Refresh combo_prop_image dropdown in property panel
        if hasattr(self, "combo_prop_image"):
            self.refresh_prop_image_combo_items()

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

    def init_property_panel(self):
        panel_layout = QVBoxLayout(self.property_panel)
        panel_layout.setContentsMargins(10, 0, 10, 0)
        panel_layout.setSpacing(10)
        
        # Title
        lbl_title = QLabel("⚙️ 片段属性配置")
        lbl_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #5D4037;")
        panel_layout.addWidget(lbl_title)
        
        # Separator line
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        line.setStyleSheet("color: #D7CCC8;")
        panel_layout.addWidget(line)
        
        # Selected Segment Info
        self.lbl_prop_index = QLabel("当前句：无选择")
        self.lbl_prop_index.setStyleSheet("color: #8D6E63; font-weight: bold;")
        panel_layout.addWidget(self.lbl_prop_index)
        
        self.txt_prop_text = QTextEdit()
        self.txt_prop_text.setReadOnly(True)
        self.txt_prop_text.setMaximumHeight(80)
        self.txt_prop_text.setStyleSheet("""
            QTextEdit {
                background-color: #F5F5F5;
                color: #5D4037;
                border: 1px solid #E0D7D3;
                font-size: 12px;
            }
        """)
        panel_layout.addWidget(self.txt_prop_text)
        
        # Image selector
        panel_layout.addWidget(QLabel("📸 关联图片素材:"))
        self.combo_prop_image = QComboBox()
        self.combo_prop_image.currentIndexChanged.connect(self.on_prop_image_changed)
        panel_layout.addWidget(self.combo_prop_image)
        
        # Image preview
        self.lbl_prop_preview = QLabel("无图片预览")
        self.lbl_prop_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_prop_preview.setMinimumHeight(120)
        self.lbl_prop_preview.setMaximumHeight(160)
        self.lbl_prop_preview.setStyleSheet("""
            QLabel {
                background-color: #EFEBE9;
                border: 1px solid #D7CCC8;
                border-radius: 4px;
                color: #8D6E63;
                font-size: 11px;
                font-weight: normal;
            }
        """)
        panel_layout.addWidget(self.lbl_prop_preview)
        
        # Mode selector
        panel_layout.addWidget(QLabel("⚙️ 生成模式:"))
        self.combo_prop_mode = QComboBox()
        self.combo_prop_mode.addItem("帧模式 (First Frame)", "VIDEO_FRAMES")
        self.combo_prop_mode.addItem("素材模式 (Reference)", "VIDEO_REFERENCES")
        self.combo_prop_mode.currentIndexChanged.connect(self.on_prop_mode_changed)
        panel_layout.addWidget(self.combo_prop_mode)
        
        panel_layout.addStretch()
        
        # Disable properties by default until a row is selected
        self.property_panel.setEnabled(False)

    def get_project_single_image(self):
        """Returns the filename of the single image in downloads directory, or None if 0 or >1 images."""
        if not self.project_path:
            return None
        downloads_dir = self.project_path / "downloads"
        if not downloads_dir.exists():
            return None
        img_extensions = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"}
        try:
            images = [item.name for item in downloads_dir.iterdir() if item.is_file() and item.suffix.lower() in img_extensions]
            if len(images) == 1:
                return images[0]
        except Exception:
            pass
        return None

    def on_table_selection_changed(self, current, previous):
        if not self.project_model or current is None:
            self.current_prop_row = -1
            self.lbl_prop_index.setText("当前句：无选择")
            self.txt_prop_text.clear()
            self.combo_prop_image.blockSignals(True)
            self.combo_prop_image.setCurrentIndex(0)
            self.combo_prop_image.blockSignals(False)
            self.lbl_prop_preview.clear()
            self.lbl_prop_preview.setText("无图片预览")
            self.combo_prop_mode.blockSignals(True)
            self.combo_prop_mode.setCurrentIndex(0)
            self.combo_prop_mode.blockSignals(False)
            self.property_panel.setEnabled(False)
            return
            
        row = current.row()
        if row < 0 or row >= len(self.project_model.spanish_segments):
            self.current_prop_row = -1
            self.property_panel.setEnabled(False)
            return
            
        self.current_prop_row = row
        self.property_panel.setEnabled(True)
        
        # Block signals to prevent infinite update loop
        self.combo_prop_image.blockSignals(True)
        self.combo_prop_mode.blockSignals(True)
        
        # Populate selected segment data
        seg = self.project_model.spanish_segments[row]
        self.lbl_prop_index.setText(f"当前句：第 {row + 1} 句")
        self.txt_prop_text.setPlainText(seg.get("text", ""))
        
        # Load images list into combo_prop_image
        self.refresh_prop_image_combo_items()
        
        # Select current image
        image_name = seg.get("image_name", "")
        img_idx = self.combo_prop_image.findData(image_name)
        if img_idx >= 0:
            self.combo_prop_image.setCurrentIndex(img_idx)
        else:
            self.combo_prop_image.setCurrentIndex(0)
            
        # Select current mode
        mode = seg.get("mode", "VIDEO_FRAMES")
        mode_idx = self.combo_prop_mode.findData(mode)
        if mode_idx >= 0:
            self.combo_prop_mode.setCurrentIndex(mode_idx)
        else:
            self.combo_prop_mode.setCurrentIndex(0)
            
        # Update preview
        self.update_prop_image_preview(image_name)
        
        self.combo_prop_image.blockSignals(False)
        self.combo_prop_mode.blockSignals(False)

    def refresh_prop_image_combo_items(self):
        self.combo_prop_image.blockSignals(True)
        current_data = self.combo_prop_image.currentData()
        
        self.combo_prop_image.clear()
        self.combo_prop_image.addItem("-- 无图片 --", "")
        
        if self.project_path:
            downloads_dir = self.project_path / "downloads"
            if downloads_dir.exists():
                # Supported image extensions
                img_extensions = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"}
                for item in sorted(downloads_dir.iterdir()):
                    if item.is_file() and item.suffix.lower() in img_extensions:
                        # Add item with a small icon preview!
                        icon = self.get_small_image_icon(item)
                        self.combo_prop_image.addItem(icon, item.name, item.name)
                        
        # Restore index if it was previously set
        if current_data:
            idx = self.combo_prop_image.findData(current_data)
            if idx >= 0:
                self.combo_prop_image.setCurrentIndex(idx)
        self.combo_prop_image.blockSignals(False)

    def get_small_image_icon(self, file_path):
        from PyQt6.QtGui import QIcon, QImage, QPixmap
        try:
            from PIL import Image
            # Use PIL to read image and scale it to a small thumbnail, e.g. 24x24 px
            pil_img = Image.open(file_path)
            pil_img.thumbnail((24, 24))
            pil_img_rgba = pil_img.convert("RGBA")
            width, height = pil_img_rgba.size
            raw_data = pil_img_rgba.tobytes("raw", "RGBA")
            qimg = QImage(raw_data, width, height, QImage.Format.Format_RGBA8888).copy()
            pixmap = QPixmap.fromImage(qimg)
            return QIcon(pixmap)
        except Exception:
            return QIcon()

    def update_prop_image_preview(self, image_name):
        if not image_name:
            self.lbl_prop_preview.clear()
            self.lbl_prop_preview.setText("无图片")
            return
            
        file_path = self.project_path / "downloads" / image_name
        if not file_path.exists():
            self.lbl_prop_preview.clear()
            self.lbl_prop_preview.setText("图片不存在")
            return
            
        try:
            from PIL import Image
            from PyQt6.QtGui import QImage, QPixmap
            pil_img = Image.open(file_path)
            pil_img.thumbnail((220, 150))
            pil_img_rgba = pil_img.convert("RGBA")
            width, height = pil_img_rgba.size
            raw_data = pil_img_rgba.tobytes("raw", "RGBA")
            qimg = QImage(raw_data, width, height, QImage.Format.Format_RGBA8888).copy()
            pixmap = QPixmap.fromImage(qimg)
            self.lbl_prop_preview.setPixmap(pixmap)
        except Exception as e:
            print(f"Error loading preview: {e}")
            self.lbl_prop_preview.clear()
            self.lbl_prop_preview.setText("预览失败")

    def on_prop_image_changed(self):
        row = getattr(self, "current_prop_row", -1)
        if row < 0 or not self.project_model or row >= len(self.project_model.spanish_segments):
            return
            
        image_name = self.combo_prop_image.currentData()
        self.project_model.spanish_segments[row]["image_name"] = image_name if image_name else ""
        
        # Update large preview
        self.update_prop_image_preview(image_name)
        
        # Refresh the index cell text to display the camera emoji if selected
        self.refresh_table_row_index_label(row)

    def on_prop_mode_changed(self):
        row = getattr(self, "current_prop_row", -1)
        if row < 0 or not self.project_model or row >= len(self.project_model.spanish_segments):
            return
            
        mode = self.combo_prop_mode.currentData()
        self.project_model.spanish_segments[row]["mode"] = mode if mode else "VIDEO_FRAMES"

    def refresh_table_row_index_label(self, row):
        if not self.project_model or row < 0 or row >= len(self.project_model.spanish_segments):
            return
        seg = self.project_model.spanish_segments[row]
        has_image = bool(seg.get("image_name"))
        index_label = f"{row + 1} 📷" if has_image else f"{row + 1}"
        
        self.table_segments.blockSignals(True)
        item = self.table_segments.item(row, 0)
        if item:
            item.setText(index_label)
        self.table_segments.blockSignals(False)

    def export_batch_json(self):
        """Generates task list JSON and opens batch copy dialog partitioned by points budget <= 50."""
        if not self.project_model:
            QMessageBox.warning(self, "提示", "请先打开一个工程项目。")
            return
            
        segments = self.project_model.spanish_segments
        if not segments:
            QMessageBox.warning(self, "提示", "当前项目没有西文分句，无法生成任务。")
            return
            
        # Get active template & motion
        tpl_id = self.combo_templates.currentData()
        motion_id = self.combo_motions.currentData()
        tpl = self.template_manager.get_template(tpl_id) if self.template_manager else None
        motion = self.template_manager.get_motion(motion_id) if self.template_manager else None
        template_content = tpl["content"] if tpl else "{spanish_text}"
        motion_content = motion["content"] if motion else ""
        
        all_tasks = []
        for idx, seg in enumerate(segments):
            text = seg.get("text", "")
            # Generate final prompt
            final_prompt = template_content.replace("{spanish_text}", text)
            final_prompt = final_prompt.replace("{camera_motion}", motion_content)
            final_prompt = re.sub(r' +', ' ', final_prompt).strip()
            
            image_name = seg.get("image_name", "")
            mode = seg.get("mode", "VIDEO_FRAMES")
            duration = seg.get("duration", 6)
            
            local_image_path = ""
            if image_name:
                local_image_path = str((self.project_path / "downloads" / image_name).resolve())
                
            # Formulate output download_path under 'downloads/videos' folder
            videos_dir = self.project_path / "downloads" / "videos"
            download_name = f"{idx+1:02d}.mp4"
            download_path = str((videos_dir / download_name).resolve())
            
            all_tasks.append({
                "prompt": final_prompt,
                "mode": mode,
                "image_name": image_name,
                "local_image_path": local_image_path,
                "duration": duration,
                "download_path": download_path,
                "_raw_duration": duration,
                "_original_index": idx
            })
            
        # Partition tasks using First Fit Decreasing (FFD) to maximize points utilization per batch
        batches = []
        points_map = {10: 15, 8: 12, 6: 10, 4: 7}
        
        # Sort tasks descending by points
        sorted_tasks = sorted(all_tasks, key=lambda t: points_map.get(t["_raw_duration"], 7), reverse=True)
        
        for task in sorted_tasks:
            pts = points_map.get(task["_raw_duration"], 7)
            # Find the first batch that can fit this task
            placed = False
            for batch in batches:
                # Calculate current points in this batch
                batch_points = sum(points_map.get(t["_raw_duration"], 7) for t in batch)
                if batch_points + pts <= 50:
                    batch.append(task)
                    placed = True
                    break
            if not placed:
                # Create a new batch
                batches.append([task])
                
        # Sort tasks within each batch by their original chronological index for clear display
        for batch in batches:
            batch.sort(key=lambda t: t["_original_index"])
            
        # Open the batch copy dialog
        dialog = BatchExportDialog(self, batches)
        dialog.exec()

    def import_execution_report(self):
        """Reads status report from clipboard and relocates downloaded videos to their target paths."""
        if not self.project_model:
            QMessageBox.warning(self, "提示", "请先打开一个工程项目。")
            return
            
        clipboard = QGuiApplication.clipboard()
        report_text = clipboard.text().strip()
        if not report_text:
            QMessageBox.warning(self, "提示", "剪贴板为空，请先从浏览器插件复制运行报告。")
            return
            
        import json
        import re
        
        # Try to extract JSON list or object block from clipboard text
        match = re.search(r'(\[.*\]|\{.*\})', report_text, re.DOTALL)
        json_candidate = match.group(1) if match else report_text
        
        try:
            report_data = json.loads(json_candidate)
            if isinstance(report_data, dict):
                report_data = [report_data]
            elif not isinstance(report_data, list):
                raise ValueError("解析的数据既不是 JSON 数组也不是 JSON 对象")
        except Exception as e:
            preview = report_text[:80] + "..." if len(report_text) > 80 else report_text
            QMessageBox.critical(
                self, "解析失败", 
                f"解析剪贴板 JSON 失败: {e}\n\n"
                f"当前剪贴板文本预览：\n{preview}\n\n"
                f"请确保您已点击 Chrome 插件的“复制报告”按钮，或剪贴板中是合法的 JSON 格式报告。"
            )
            return
            
        from pathlib import Path
        import shutil
        
        success_count = 0
        fail_count = 0
        not_found_paths = []
        
        chrome_downloads = Path.home() / "Downloads"
        
        for item in report_data:
            target_path_str = item.get("download_path")
            status = item.get("status")
            
            if not target_path_str or status != "success":
                continue
                
            target_path = Path(target_path_str)
            filename = target_path.name
            
            possible_sources = [
                chrome_downloads / "Flow" / self.project_model.project_id / filename,
                chrome_downloads / "Flow" / f"{self.project_model.project_id}-flow" / filename,
                chrome_downloads / "Flow" / filename,
                chrome_downloads / filename,
            ]
            
            source_file = None
            for p in possible_sources:
                if p.exists() and p.is_file():
                    source_file = p
                    break
                    
            if not source_file:
                flow_dir = chrome_downloads / "Flow"
                if flow_dir.exists():
                    found_files = list(flow_dir.glob(f"**/{filename}"))
                    if found_files:
                        source_file = found_files[0]
                        
            if not source_file:
                found_files = list(chrome_downloads.glob(f"**/{filename}"))
                if found_files:
                    source_file = found_files[0]
                    
            if source_file:
                try:
                    target_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(source_file), str(target_path))
                    success_count += 1
                except Exception as err:
                    print(f"Error moving file {source_file} to {target_path}: {err}")
                    fail_count += 1
            else:
                not_found_paths.append(filename)
                
        self.refresh_media_list()
        
        if self.project_model:
            self.project_model.update_media_files()
            
        msg = f"已成功移入并归档 {success_count} 个视频文件！\n"
        if fail_count > 0:
            msg += f"移动失败 {fail_count} 个文件。\n"
        if not_found_paths:
            msg += f"\n未在下载目录中找到以下 {len(not_found_paths)} 个视频（请确认浏览器下载已完成）：\n"
            msg += "\n".join(f"- {name}" for name in not_found_paths[:5])
            if len(not_found_paths) > 5:
                msg += f"\n... 以及其他 {len(not_found_paths) - 5} 个文件"
                
        if success_count > 0:
            QMessageBox.information(self, "归档结果", msg)
        else:
            QMessageBox.warning(self, "未找到文件", msg)


class BatchExportDialog(QDialog):
    def __init__(self, parent, batches):
        super().__init__(parent)
        self.setWindowTitle("分批复制生成任务 (每批最高50积分)")
        self.resize(550, 400)
        self.batches = batches  # List of lists of dicts
        self.copied_batches = set()
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(12)
        
        # Summary Label
        total_segments = sum(len(b) for b in self.batches)
        total_points = sum(self.get_batch_points(b) for b in self.batches)
        
        lbl_summary = QLabel(
            f"📊 <b>统计信息</b>：共 <b>{total_segments}</b> 个视频片段，"
            f"总需 <b>{total_points}</b> 积分。<br/>"
            f"每批次点数上限为 <b>50</b> 积分，已智能分拆为 <b>{len(self.batches)}</b> 个批次进行生成。"
        )
        lbl_summary.setStyleSheet("font-size: 13px; color: #5D4037;")
        layout.addWidget(lbl_summary)
        
        # Scrollable area of batches
        self.list_batches = QListWidget()
        self.list_batches.setStyleSheet("""
            QListWidget {
                border: 1px solid #D7CCC8;
                border-radius: 4px;
                background-color: #FAFAFA;
            }
        """)
        
        for idx, batch in enumerate(self.batches):
            item = QListWidgetItem(self.list_batches)
            
            # Create a widget for the item
            widget = QWidget()
            widget_layout = QHBoxLayout(widget)
            widget_layout.setContentsMargins(10, 8, 10, 8)
            
            points = self.get_batch_points(batch)
            indices_str = ", ".join(str(t["_original_index"] + 1) for t in batch)
            
            info_text = (
                f"<b>第 {idx + 1} 批</b> (序号: {indices_str})<br/>"
                f"📎 包含 {len(batch)} 个分句 | ⚡ 消耗 <b>{points}</b> 积分"
            )
            lbl_info = QLabel(info_text)
            lbl_info.setStyleSheet("font-size: 12px; color: #5D4037;")
            widget_layout.addWidget(lbl_info, stretch=1)
            
            # Copy Button
            btn_copy = QPushButton("📋 复制本批任务")
            btn_copy.setStyleSheet("""
                QPushButton {
                    background-color: #8B5CF6;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    padding: 6px 12px;
                    font-size: 11px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #7C3AED;
                }
            """)
            btn_copy.clicked.connect(self.make_copy_callback(idx, btn_copy))
            widget_layout.addWidget(btn_copy)
            
            widget.setLayout(widget_layout)
            item.setSizeHint(widget.sizeHint())
            self.list_batches.setItemWidget(item, widget)
            
        layout.addWidget(self.list_batches)
        
        # Close Button
        btn_close = QPushButton("关闭")
        btn_close.setStyleSheet("background-color: #E0A96D; color: white; padding: 6px; font-weight: bold; border-radius: 4px;")
        btn_close.clicked.connect(self.accept)
        layout.addWidget(btn_close)
        
    def get_batch_points(self, batch):
        points_map = {10: 15, 8: 12, 6: 10, 4: 7}
        total = 0
        for item in batch:
            dur = item.get("_raw_duration", 6)
            total += points_map.get(dur, 7)
        return total
        
    def make_copy_callback(self, batch_idx, button):
        return lambda: self.copy_batch(batch_idx, button)
        
    def copy_batch(self, batch_idx, button):
        import json
        batch_data = self.batches[batch_idx]
        
        # Strip internal temporary keys before copying to clipboard
        cleaned_batch = []
        for item in batch_data:
            c_item = {k: v for k, v in item.items() if not k.startswith("_")}
            cleaned_batch.append(c_item)
            
        try:
            json_str = json.dumps(cleaned_batch, indent=2, ensure_ascii=False)
            from PyQt6.QtGui import QGuiApplication
            clipboard = QGuiApplication.clipboard()
            clipboard.setText(json_str)
            
            # Visual feedback
            button.setText("✓ 已复制")
            button.setStyleSheet("""
                QPushButton {
                    background-color: #10B981;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    padding: 6px 12px;
                    font-size: 11px;
                    font-weight: bold;
                }
            """)
            self.copied_batches.add(batch_idx)
        except Exception as e:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "错误", f"复制批次失败: {e}")
