# -*- coding: utf-8 -*-
import sys
import os
from PyQt6.QtWidgets import QApplication
from views.main_window import MainWindow

def main():
    # Create the application
    app = QApplication(sys.argv)
    
    # Identify the current folder as workspace (handles PyInstaller packaging)
    if getattr(sys, 'frozen', False):
        exe_dir = os.path.dirname(sys.executable)
        # On macOS, PyInstaller bundles the app inside Contents/MacOS/
        if exe_dir.endswith("Contents/MacOS"):
            workspace_dir = os.path.dirname(os.path.dirname(os.path.dirname(exe_dir)))
        else:
            workspace_dir = exe_dir
    else:
        workspace_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Create and show main window
    window = MainWindow(workspace_dir)
    window.show()
    
    # Execute the app
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
