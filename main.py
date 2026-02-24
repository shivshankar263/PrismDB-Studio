import sys
import os
import multiprocessing
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon # <--- NEW IMPORT
from PySide6.QtCore import QSettings

# Ensure the root directory is in sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from gui.main_window import MainWindow
from utils.theme_manager import apply_theme

if __name__ == "__main__":
    multiprocessing.freeze_support()
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    # --- FIX: Set Application Icon (Taskbar & Window) ---
    # Construct absolute path to assets
    base_dir = os.path.dirname(os.path.abspath(__file__))
    icon_path = os.path.join(base_dir, "assets", "favicon.png")
    
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))
    # ----------------------------------------------------
    
    # Load Theme
    settings = QSettings("PrismDB", "Studio")
    current_theme = settings.value("theme", "Light")
    apply_theme(app, current_theme)
    
    win = MainWindow()
    win.show()
    sys.exit(app.exec())