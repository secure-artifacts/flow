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

    log_path = os.path.join(workspace_dir, "crash_log.txt")

    try:
        # Write startup marker so we know the exe at least started
        with open(log_path, "w", encoding="utf-8") as f:
            f.write(f"flow starting...\n")
            f.write(f"Python: {sys.version}\n")
            f.write(f"Frozen: {getattr(sys, 'frozen', False)}\n")
            f.write(f"Exe: {sys.executable}\n")
            f.write(f"Workspace: {workspace_dir}\n")
            f.write(f"MEIPASS: {getattr(sys, '_MEIPASS', 'N/A')}\n\n")

        # For PyInstaller --onefile: Qt DLLs and plugins are extracted to _MEIPASS
        # but Windows and Qt don't know to look there. Must set paths explicitly
        # BEFORE importing PyQt6, otherwise loading .pyd files triggers a hard crash
        # because they can't find Qt6Core.dll, Qt6Gui.dll, etc.
        if getattr(sys, 'frozen', False):
            meipass = sys._MEIPASS

            # 1. Register Qt6 DLL directory so Windows can find Qt6Core.dll etc.
            qt_bin = os.path.join(meipass, "PyQt6", "Qt6", "bin")
            if os.path.isdir(qt_bin):
                os.add_dll_directory(qt_bin)
                os.environ["PATH"] = qt_bin + os.pathsep + os.environ.get("PATH", "")

            # Also add _MEIPASS itself (some DLLs may be placed at root level)
            os.add_dll_directory(meipass)

            # 2. Set Qt plugin path so Qt can find platform/style plugins
            qt_plugins = os.path.join(meipass, "PyQt6", "Qt6", "plugins")
            if os.path.isdir(qt_plugins):
                os.environ["QT_PLUGIN_PATH"] = qt_plugins
            elif os.path.isdir(os.path.join(meipass, "plugins")):
                os.environ["QT_PLUGIN_PATH"] = os.path.join(meipass, "plugins")

            with open(log_path, "a", encoding="utf-8") as f:
                f.write(f"QT_PLUGIN_PATH: {os.environ.get('QT_PLUGIN_PATH', 'NOT SET')}\n")
                f.write(f"Qt6 bin dir: {qt_bin} (exists: {os.path.isdir(qt_bin)})\n")
                if os.path.isdir(qt_bin):
                    f.write(f"Qt6 bin contents: {os.listdir(qt_bin)[:20]}\n")
                f.write("\n")

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

        # If we get here, delete the startup log (app launched successfully)
        if os.path.exists(log_path):
            os.remove(log_path)
        
        # Execute the app
        sys.exit(app.exec())
    except BaseException as e:
        # Append crash info to log
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"CRASH:\n{traceback.format_exc()}\n")
        raise

if __name__ == "__main__":
    main()
