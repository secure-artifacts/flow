# -*- coding: utf-8 -*-
import sys
import os
from PyQt6.QtWidgets import QApplication
from views.main_window import MainWindow

def main():
    # Create the application
    app = QApplication(sys.argv)
    
    # Identify the current folder as workspace
    workspace_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Create and show main window
    window = MainWindow(workspace_dir)
    window.show()
    
    # Execute the app
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
