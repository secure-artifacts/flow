# -*- coding: utf-8 -*-
from pathlib import Path
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QLabel, QTableWidget, QTableWidgetItem, QHeaderView, 
                             QMessageBox, QGroupBox, QAbstractItemView, QProgressBar,
                             QLineEdit, QFileDialog)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from services.video_checker import VideoChecker

class VideoCheckDialog(QDialog):
    """Dialog displaying video completeness inspection report with custom search directory selection and auto-relocation."""
    
    def __init__(self, report, project_model, project_path, parent=None):
        super().__init__(parent)
        self.report = report
        self.project_model = project_model
        self.project_path = project_path
        self.custom_search_dir = self.report.get("primary_search_dir", "")
        self.init_ui()
        self.populate_report()

    def init_ui(self):
        self.setWindowTitle("🔍 视频完整性核查与自动归位 (Video Completeness & Relocator)")
        self.resize(820, 600)
        
        self.setStyleSheet("""
            QDialog {
                background-color: #FAF6F0;
                color: #5D4037;
                font-family: "Segoe UI", "PingFang SC", sans-serif;
            }
            QGroupBox {
                font-weight: bold;
                font-size: 13px;
                border: 1px solid #D7CCC8;
                border-radius: 6px;
                margin-top: 6px;
                padding-top: 12px;
                background-color: white;
            }
            QLabel {
                font-size: 13px;
                color: #5D4037;
            }
            QLineEdit {
                background-color: white;
                border: 1px solid #D7CCC8;
                border-radius: 4px;
                padding: 5px 8px;
                font-size: 12px;
                color: #5D4037;
            }
            QTableWidget {
                background-color: white;
                border: 1px solid #EFEBE9;
                border-radius: 4px;
                font-size: 12px;
            }
            QHeaderView::section {
                background-color: #EFEBE9;
                color: #5D4037;
                font-weight: bold;
                padding: 5px;
                border: 1px solid #D7CCC8;
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
            QPushButton#btn_relocate {
                background-color: #10B981;
                font-size: 13px;
            }
            QPushButton#btn_relocate:hover {
                background-color: #059669;
            }
            QPushButton#btn_browse {
                background-color: #64748B;
                padding: 5px 12px;
                font-size: 12px;
            }
            QPushButton#btn_browse:hover {
                background-color: #475569;
            }
        """)
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(12)
        
        # 1. Custom Search Directory Bar
        group_search_dir = QGroupBox("📁 视频文件搜索目录设置 (Search Location)")
        dir_layout = QHBoxLayout(group_search_dir)
        dir_layout.setContentsMargins(12, 12, 12, 12)
        dir_layout.setSpacing(8)
        
        dir_layout.addWidget(QLabel("搜索位置:"))
        self.txt_search_dir = QLineEdit()
        self.txt_search_dir.setReadOnly(True)
        dir_layout.addWidget(self.txt_search_dir, stretch=1)
        
        btn_browse = QPushButton("📁 浏览/更改目录")
        btn_browse.setObjectName("btn_browse")
        btn_browse.clicked.connect(self.browse_search_directory)
        dir_layout.addWidget(btn_browse)
        
        main_layout.addWidget(group_search_dir)
        
        # 2. Summary Cards Section
        group_summary = QGroupBox("📊 视频完成度概览 (Overview)")
        sum_layout = QVBoxLayout(group_summary)
        sum_layout.setContentsMargins(12, 12, 12, 12)
        sum_layout.setSpacing(8)
        
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(15)
        
        self.lbl_total = QLabel("共 <b>0</b> 句段")
        self.lbl_found = QLabel("✅ 已就绪 <b>0</b> 视频")
        self.lbl_found.setStyleSheet("color: #10B981; font-weight: bold;")
        self.lbl_missing = QLabel("❌ 缺失 <b>0</b> 视频")
        self.lbl_missing.setStyleSheet("color: #EF4444; font-weight: bold;")
        self.lbl_rate = QLabel("完成度: <b>0.0%</b>")
        self.lbl_rate.setStyleSheet("color: #8B5CF6; font-size: 14px; font-weight: bold;")
        
        cards_layout.addWidget(self.lbl_total)
        cards_layout.addWidget(self.lbl_found)
        cards_layout.addWidget(self.lbl_missing)
        cards_layout.addStretch()
        cards_layout.addWidget(self.lbl_rate)
        
        sum_layout.addLayout(cards_layout)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedHeight(14)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #D7CCC8;
                border-radius: 7px;
                background-color: #EFEBE9;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #10B981;
                border-radius: 6px;
            }
        """)
        sum_layout.addWidget(self.progress_bar)
        
        main_layout.addWidget(group_summary)
        
        # 3. Detailed Table Section
        self.table_details = QTableWidget()
        self.table_details.setColumnCount(6)
        self.table_details.setHorizontalHeaderLabels([
            "序号", "分句文案", "期待视频文件名", "视频状态", "文件大小", "当前存放在"
        ])
        self.table_details.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table_details.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table_details.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        self.table_details.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        main_layout.addWidget(self.table_details, stretch=1)
        
        # 4. Bottom Action Buttons
        bottom_layout = QHBoxLayout()
        
        self.btn_relocate = QPushButton("📦 一键自动归位视频 (到项目 Downloads/Videos)")
        self.btn_relocate.setObjectName("btn_relocate")
        self.btn_relocate.clicked.connect(self.do_relocate)
        bottom_layout.addWidget(self.btn_relocate)
        
        bottom_layout.addStretch()
        
        btn_close = QPushButton("关闭")
        btn_close.clicked.connect(self.accept)
        bottom_layout.addWidget(btn_close)
        
        main_layout.addLayout(bottom_layout)

    def browse_search_directory(self):
        """Allows user to select a custom folder to scan for video files."""
        current_dir = self.txt_search_dir.text().strip() or str(Path.home() / "Downloads" / "Flow")
        chosen_dir = QFileDialog.getExistingDirectory(self, "选择视频搜索/存放目录", current_dir)
        if chosen_dir:
            self.custom_search_dir = chosen_dir
            self.txt_search_dir.setText(chosen_dir)
            self.refresh_report()

    def refresh_report(self):
        """Re-scans disk for videos using the selected custom_search_dir."""
        self.report = VideoChecker.check_project_videos(
            self.project_model, self.project_path, custom_search_dir=self.custom_search_dir
        )
        self.populate_report()

    def populate_report(self):
        search_dir_path = self.report.get("primary_search_dir", self.custom_search_dir)
        self.txt_search_dir.setText(search_dir_path)
        
        tot = self.report.get("total_segments", 0)
        found = self.report.get("found_count", 0)
        missing = self.report.get("missing_count", 0)
        rate = self.report.get("completion_rate", 0.0)
        
        self.lbl_total.setText(f"共 <b>{tot}</b> 个分句")
        self.lbl_found.setText(f"✅ 已就绪 <b>{found}</b> 个视频")
        self.lbl_missing.setText(f"❌ 缺失 <b>{missing}</b> 个视频")
        self.lbl_rate.setText(f"完成度: <b>{rate:.1f}%</b>")
        self.progress_bar.setValue(int(rate))
        
        details = self.report.get("segments_detail", [])
        self.table_details.setRowCount(len(details))
        
        for r, item in enumerate(details):
            # 0. Index
            self.table_details.setItem(r, 0, QTableWidgetItem(str(item["index"])))
            
            # 1. Text
            self.table_details.setItem(r, 1, QTableWidgetItem(item["text"]))
            
            # 2. Download name
            self.table_details.setItem(r, 2, QTableWidgetItem(item["download_name"]))
            
            # 3. Status
            if item["found"]:
                status_item = QTableWidgetItem("✅ 已就绪")
                status_item.setForeground(QColor("#10B981"))
            else:
                status_item = QTableWidgetItem("❌ 缺少视频")
                status_item.setForeground(QColor("#EF4444"))
            status_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
            self.table_details.setItem(r, 3, status_item)
            
            # 4. File size
            self.table_details.setItem(r, 4, QTableWidgetItem(item["file_size"]))
            
            # 5. Path
            path_str = str(item["source_path"]) if item["source_path"] else "未找到"
            if item.get("already_in_target"):
                path_str = "[项目内置文件夹] " + path_str
            self.table_details.setItem(r, 5, QTableWidgetItem(path_str))
            
            # Highlight row color
            bg = QColor("#D4EDDA") if item["found"] else QColor("#F8D7DA")
            for c in range(6):
                it = self.table_details.item(r, c)
                if it:
                    it.setBackground(bg)

    def do_relocate(self):
        res = VideoChecker.relocate_found_videos(self.report)
        moved = res["moved_count"]
        already = res["already_count"]
        errs = res["errors"]
        
        msg = ""
        if moved > 0:
            msg += f"✅ 成功归位移动了 {moved} 个视频到项目 `downloads/videos/` 文件夹中！\n"
        if already > 0:
            msg += f"ℹ️ 有 {already} 个视频本身就已在项目目录中。\n"
        if errs:
            msg += "\n以下文件移动发生异常：\n" + "\n".join(errs)
            
        if not msg:
            msg = "没有可供归位的视频文件。"
            
        QMessageBox.information(self, "归位完成", msg)
        self.refresh_report()
