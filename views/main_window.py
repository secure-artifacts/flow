# -*- coding: utf-8 -*-
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QLineEdit, QPushButton, QListWidget, 
                             QListWidgetItem, QSplitter, QFileDialog, QMessageBox)
from PyQt6.QtCore import Qt, QSize
from models.storage_manager import StorageManager
from views.import_dialog import ImportDialog
from views.project_detail_widget import ProjectDetailWidget
from pathlib import Path

class MainWindow(QMainWindow):
    """Main window of the Project Manager application."""
    
    def __init__(self, workspace_dir):
        super().__init__()
        self.workspace_dir = Path(workspace_dir)
        self.storage_manager = StorageManager(self.workspace_dir)
        self.active_downloads = {}
        
        # Initialize TemplateManager
        from models.template_manager import TemplateManager
        self.template_manager = TemplateManager(self.workspace_dir)
        
        self.init_ui()
        # Bind template manager to detail panel
        self.detail_widget.set_template_manager(self.template_manager)
        self.load_initial_state()

    def init_ui(self):
        self.setWindowTitle("项目管理器 (Project Manager)")
        self.resize(1200, 800)
        self.setMinimumSize(1000, 600)
        
        # Warm and premium style theme
        self.setStyleSheet("""
            QMainWindow {
                background-color: #F5EBE6;
                font-family: "Segoe UI", "PingFang SC", sans-serif;
            }
            QWidget#central_widget {
                background-color: #F5EBE6;
            }
            QLabel {
                font-size: 13px;
                color: #5D4037;
                font-weight: bold;
            }
            QLineEdit {
                background-color: white;
                border: 1px solid #D7CCC8;
                border-radius: 4px;
                padding: 6px;
                color: #5D4037;
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
            QPushButton#btn_import {
                background-color: #E0A96D;
                font-size: 14px;
                padding: 8px 18px;
            }
            QPushButton#btn_import:hover {
                background-color: #D2904C;
            }
            QPushButton#btn_template_config {
                background-color: #D7CCC8;
                color: #5D4037;
                font-size: 13px;
                padding: 6px 14px;
            }
            QPushButton#btn_template_config:hover {
                background-color: #BCAAA4;
            }
            QListWidget {
                background-color: white;
                border: 1px solid #D7CCC8;
                border-radius: 4px;
                color: #5D4037;
                font-size: 13px;
                padding: 4px;
            }
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #EFEBE9;
                border-radius: 4px;
            }
            QListWidget::item:hover {
                background-color: #F5F5F5;
                color: #5D4037;
            }
            QListWidget::item:selected {
                background-color: #FFE0B2;
                color: #5D4037;
                font-weight: bold;
            }
        """)

        central_widget = QWidget()
        central_widget.setObjectName("central_widget")
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(12)
        
        # 1. Top Bar (Storage path & Import)
        top_layout = QHBoxLayout()
        top_layout.setSpacing(8)
        
        top_layout.addWidget(QLabel("存储路径 (Storage Path):"))
        
        self.txt_base_path = QLineEdit()
        self.txt_base_path.setReadOnly(True)
        self.txt_base_path.setPlaceholderText("请选择项目数据存放的总目录...")
        top_layout.addWidget(self.txt_base_path, stretch=1)
        
        self.btn_select_path = QPushButton("选择路径")
        self.btn_select_path.clicked.connect(self.select_base_path)
        top_layout.addWidget(self.btn_select_path)
        
        top_layout.addSpacing(20)
        
        self.btn_import = QPushButton("＋ 新建导入 (Import)")
        self.btn_import.setObjectName("btn_import")
        self.btn_import.clicked.connect(self.open_import_dialog)
        top_layout.addWidget(self.btn_import)
        
        top_layout.addSpacing(8)
        
        self.btn_template_config = QPushButton("⚙️ 模板配置")
        self.btn_template_config.setObjectName("btn_template_config")
        self.btn_template_config.clicked.connect(self.open_template_config_dialog)
        top_layout.addWidget(self.btn_template_config)
        
        main_layout.addLayout(top_layout)
        
        # 2. Main Area (Splitter: Sidebar and Details)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left Panel (Sidebar Container)
        sidebar_widget = QWidget()
        sidebar_layout = QVBoxLayout(sidebar_widget)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(6)
        
        sidebar_layout.addWidget(QLabel("项目列表 (Projects):"))
        self.list_projects = QListWidget()
        self.list_projects.itemClicked.connect(self.on_project_clicked)
        sidebar_layout.addWidget(self.list_projects)
        
        # Add delete button under the list
        self.btn_delete_project = QPushButton("🗑️ 删除选中项目")
        self.btn_delete_project.setObjectName("btn_delete_project")
        self.btn_delete_project.setStyleSheet("""
            QPushButton#btn_delete_project {
                background-color: #E57373;
                color: white;
            }
            QPushButton#btn_delete_project:hover {
                background-color: #EF5350;
            }
            QPushButton#btn_delete_project:pressed {
                background-color: #E53935;
            }
        """)
        self.btn_delete_project.clicked.connect(self.delete_selected_project)
        sidebar_layout.addWidget(self.btn_delete_project)
        
        sidebar_widget.setLayout(sidebar_layout)
        splitter.addWidget(sidebar_widget)
        
        # Right Panel (Detail Widget)
        self.detail_widget = ProjectDetailWidget()
        splitter.addWidget(self.detail_widget)
        
        # Set splitter proportions (approx 25% sidebar, 75% details)
        splitter.setSizes([300, 900])
        main_layout.addWidget(splitter, stretch=1)

    def load_initial_state(self):
        """Displays saved base path if it exists and loads projects list."""
        base_path = self.storage_manager.get_base_path()
        if base_path:
            self.txt_base_path.setText(str(base_path))
            self.reload_projects_list()
        else:
            self.txt_base_path.setText("")
            QMessageBox.information(self, "欢迎", "首次使用，请先点击 ［选择路径］ 设置数据存放的总目录！")

    def select_base_path(self):
        """Opens a folder selection dialog to set the base path."""
        dir_path = QFileDialog.getExistingDirectory(self, "选择总存储路径", str(self.workspace_dir))
        if dir_path:
            if self.storage_manager.set_base_path(dir_path):
                self.txt_base_path.setText(dir_path)
                self.reload_projects_list()
                QMessageBox.information(self, "成功", "总存储路径设置成功！")
            else:
                QMessageBox.critical(self, "错误", "无法使用该存储路径，请检查权限。")

    def reload_projects_list(self):
        """Fetches current projects and populates sidebar list widget."""
        self.list_projects.clear()
        
        projects = self.storage_manager.list_projects()
        for p in projects:
            # Format list item label: {index} {col1} - {col7}
            label = f"●  {p['index_str']}   {p['col1']}"
            if p['col7']:
                label += f" - {p['col7']}"
                
            item = QListWidgetItem(label)
            # Store the absolute path in UserRole for easy lookup
            item.setData(Qt.ItemDataRole.UserRole, p['path'])
            self.list_projects.addItem(item)

    def open_import_dialog(self):
        """Opens the clipboard import dialog."""
        if not self.storage_manager.get_base_path():
            QMessageBox.warning(self, "错误", "请先设置总存储路径后再导入项目！")
            return
            
        dialog = ImportDialog(self.storage_manager, self)
        if dialog.exec() == ImportDialog.DialogCode.Accepted:
            self.reload_projects_list()

    def on_project_clicked(self, item):
        """Triggers detail load when sidebar item is clicked."""
        path = item.data(Qt.ItemDataRole.UserRole)
        if path:
            self.detail_widget.set_project(path)

    def start_background_download(self, project_id, url, project_dir):
        """Starts an asynchronous background download of Google Drive link for a project."""
        if not url:
            return
            
        if project_id in self.active_downloads:
            return
            
        from services.downloader import DownloadThread
        downloads_dir = Path(project_dir) / "downloads"
        
        thread = DownloadThread(url, downloads_dir)
        self.active_downloads[project_id] = thread
        
        thread.status_signal.connect(
            lambda msg, pid=project_id: self.on_background_download_status(msg, pid)
        )
        thread.finished_signal.connect(
            lambda success, msg, pid=project_id: self.on_background_download_finished(success, msg, pid)
        )
        
        thread.start()

    def on_background_download_status(self, msg, project_id):
        """Dispatches status updates to detail widget if showing this project."""
        if self.detail_widget.project_model and self.detail_widget.project_model.project_id == project_id:
            self.detail_widget.on_download_status_updated(msg)

    def on_background_download_finished(self, success, msg, project_id):
        """Cleans up thread and updates project metadata and detail view."""
        self.active_downloads.pop(project_id, None)
        
        # Scan and update metadata files in project directory
        proj_path = self.storage_manager.resolve_path(project_id)
        if proj_path.exists():
            from models.project_model import ProjectModel
            try:
                proj = ProjectModel(proj_path)
                proj.update_media_files()
            except Exception as e:
                print(f"Error updating project files: {e}")
                
        # Notify detail widget if current project matches
        if self.detail_widget.project_model and self.detail_widget.project_model.project_id == project_id:
            self.detail_widget.on_download_finished(success, msg)

    def delete_selected_project(self):
        """Permanently deletes the selected project folder and files."""
        current_item = self.list_projects.currentItem()
        if not current_item:
            QMessageBox.warning(self, "提示", "请先在列表中选择要删除的项目！")
            return
            
        project_path_str = current_item.data(Qt.ItemDataRole.UserRole)
        project_path = Path(project_path_str)
        project_id = project_path.name
        
        # Confirmation Dialog
        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要永久删除项目【{project_id}】吗？\n\n这将会永久删除该项目的文件夹及所有已下载的素材资源，此操作无法撤销！",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # 1. Stop any active download thread first
            if project_id in self.active_downloads:
                thread = self.active_downloads.pop(project_id)
                if thread.isRunning():
                    thread.terminate()
                    thread.wait()
            
            # 2. Delete the directory recursively
            import shutil
            try:
                if project_path.exists() and project_path.is_dir():
                    shutil.rmtree(project_path)
                
                # Delete corresponding subtitle file in "字幕" folder
                subtitles_dir = project_path.parent / "字幕"
                subtitle_file_path = subtitles_dir / f"{project_id}.txt"
                if subtitle_file_path.exists():
                    subtitle_file_path.unlink()
                
                # 3. If the deleted project is currently displayed, reset the detail view
                if self.detail_widget.project_model and self.detail_widget.project_model.project_id == project_id:
                    self.detail_widget.reset_to_no_selection()
                    
                # 4. Reload the sidebar
                self.reload_projects_list()
                QMessageBox.information(self, "成功", f"项目【{project_id}】已成功删除！")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"删除项目文件夹失败: {str(e)}")

    def open_template_config_dialog(self):
        """Opens the templates and motions configuration dialog."""
        from views.template_config_dialog import TemplateConfigDialog
        dialog = TemplateConfigDialog(self.template_manager, self)
        if dialog.exec() == TemplateConfigDialog.DialogCode.Accepted:
            # Refresh project details dropdowns if a project is loaded
            if self.detail_widget.project_model:
                self.detail_widget.refresh_template_comboboxes()
