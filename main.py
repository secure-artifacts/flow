# -*- coding: utf-8 -*-
import sys
import os
import traceback

# Force PyInstaller static analysis to bundle third-party packages
import PIL
import bs4
import gdown
import requests

def get_workspace_dir():
    if getattr(sys, 'frozen', False):
        exe_dir = os.path.dirname(sys.executable)
        if exe_dir.endswith("Contents/MacOS"):
            return os.path.dirname(os.path.dirname(os.path.dirname(exe_dir)))
        return exe_dir
    return os.path.dirname(os.path.abspath(__file__))

def log_error(err_str):
    try:
        ws = get_workspace_dir()
        log_path = os.path.join(ws, "error.log")
        with open(log_path, "a", encoding="utf-8") as f:
            f.write("=" * 50 + "\n")
            f.write(err_str + "\n\n")
    except Exception:
        pass

def handle_exception(exc_type, exc_value, exc_traceback):
    err_str = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    log_error(err_str)
    try:
        from PyQt6.QtWidgets import QApplication, QMessageBox
        if not QApplication.instance():
            _app = QApplication(sys.argv)
        QMessageBox.critical(
            None,
            "程序运行异常 (Error)",
            f"应用发生异常：\n\n{exc_value}\n\n详细日志已保存至 error.log"
        )
    except Exception:
        pass

sys.excepthook = handle_exception

def qt_message_handler(mode, context, message):
    if "Point size <= 0" in message:
        return
    if sys.stderr is not None:
        try:
            sys.stderr.write(f"{message}\n")
        except Exception:
            pass

def main():
    try:
        from PyQt6.QtWidgets import QApplication
        from PyQt6.QtCore import qInstallMessageHandler
        from views.main_window import MainWindow

        qInstallMessageHandler(qt_message_handler)
        app = QApplication(sys.argv)
        
        workspace_dir = get_workspace_dir()
        window = MainWindow(workspace_dir)
        window.show()
        
        sys.exit(app.exec())
    except Exception as e:
        handle_exception(type(e), e, e.__traceback__)

if __name__ == "__main__":
    main()
