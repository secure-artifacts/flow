# -*- coding: utf-8 -*-
import sys
import os
import traceback

def main():
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

    try:
        from PyQt6.QtWidgets import QApplication
        from PyQt6.QtCore import qInstallMessageHandler
        from views.main_window import MainWindow

        def qt_message_handler(mode, context, message):
            if "Point size <= 0" in message:
                return
            sys.stderr.write(f"{message}\n")

        qInstallMessageHandler(qt_message_handler)
        # Create the application
        app = QApplication(sys.argv)
        
        # Create and show main window
        window = MainWindow(workspace_dir)
        window.show()
        
        # Execute the app
        sys.exit(app.exec())
    except Exception:
        # Write crash log next to the executable so users can report issues
        log_path = os.path.join(workspace_dir, "crash_log.txt")
        with open(log_path, "w", encoding="utf-8") as f:
            f.write(traceback.format_exc())
        raise

if __name__ == "__main__":
    main()
