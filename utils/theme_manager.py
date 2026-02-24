import os
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

LIGHT_QSS = """
QMainWindow, QDialog, QMessageBox { background-color: #f8f9fa; color: #000000; }
QMenuBar { background-color: #ffffff; color: #000000; border-bottom: 1px solid #dee2e6; }
QMenu { background-color: #ffffff; color: #000000; border: 1px solid #dee2e6; }
QMenu::item:selected { background-color: #0d6efd; color: white; }
QFrame#ConnPanel { background-color: #ffffff; border: 1px solid #dee2e6; border-radius: 8px; }
QLineEdit { border: 1px solid #ced4da; border-radius: 4px; padding: 6px; background: white; color: black; }
QPushButton { padding: 8px 16px; border-radius: 4px; font-weight: bold; border: 1px solid #dee2e6; background: #f8f9fa; color: black; }
QPushButton:hover { background: #e2e6ea; }
QPushButton#Primary { background-color: #0d6efd; color: white; border: none; }
QPushButton#Primary:hover { background-color: #0b5ed7; }
QTableWidget, QTreeView, QListView { background-color: white; color: black; border: 1px solid #dee2e6; gridline-color: #dee2e6; }
QHeaderView::section { background-color: #f8f9fa; color: black; font-weight: bold; border: 1px solid #dee2e6; padding: 4px; }
QProgressBar { height: 15px; text-align: center; border-radius: 7px; background: #e9ecef; color: black; }
QProgressBar::chunk { background-color: #0d6efd; border-radius: 7px; }
QTextEdit { font-family: Consolas, monospace; background: white; color: black; border: 1px solid #ced4da; }
QTabBar::tab { background: #f8f9fa; color: black; border: 1px solid #dee2e6; padding: 8px; border-bottom-color: #dee2e6; }
QTabBar::tab:selected { background: white; border-bottom-color: white; font-weight: bold; }
QTabWidget::pane { border: 1px solid #dee2e6; }
QLabel { color: black; }
QCheckBox { color: black; }
QComboBox { background: white; color: black; border: 1px solid #ced4da; padding: 4px; }
"""

DARK_QSS = """
QMainWindow, QDialog, QMessageBox { background-color: #1e1e1e; color: #ffffff; }
QMenuBar { background-color: #2d2d2d; color: #ffffff; border-bottom: 1px solid #3c3c3c; }
QMenu { background-color: #2d2d2d; color: #ffffff; border: 1px solid #3c3c3c; }
QMenu::item:selected { background-color: #0d6efd; color: white; }
QFrame#ConnPanel { background-color: #252526; border: 1px solid #3c3c3c; border-radius: 8px; }
QLineEdit { border: 1px solid #3c3c3c; border-radius: 4px; padding: 6px; background: #333333; color: white; }
QPushButton { padding: 8px 16px; border-radius: 4px; font-weight: bold; border: 1px solid #3c3c3c; background: #333333; color: white; }
QPushButton:hover { background: #444444; }
QPushButton#Primary { background-color: #0d6efd; color: white; border: none; }
QPushButton#Primary:hover { background-color: #0b5ed7; }
QTableWidget, QTreeView, QListView { background-color: #1e1e1e; color: #ffffff; border: 1px solid #3c3c3c; gridline-color: #3c3c3c; }
QHeaderView::section { background-color: #2d2d2d; color: #ffffff; font-weight: bold; border: 1px solid #3c3c3c; padding: 4px; }
QProgressBar { height: 15px; text-align: center; border-radius: 7px; background: #333333; color: white; }
QProgressBar::chunk { background-color: #0d6efd; border-radius: 7px; }
QTextEdit { font-family: Consolas, monospace; background: #1e1e1e; color: #ffffff; border: 1px solid #3c3c3c; }
QTabBar::tab { background: #2d2d2d; color: #aaaaaa; border: 1px solid #3c3c3c; padding: 8px; border-bottom-color: #3c3c3c; }
QTabBar::tab:selected { background: #1e1e1e; color: #ffffff; border-bottom-color: #1e1e1e; font-weight: bold; }
QTabWidget::pane { border: 1px solid #3c3c3c; }
QLabel { color: #ffffff; }
QCheckBox { color: #ffffff; }
QComboBox { background: #333333; color: #ffffff; border: 1px solid #3c3c3c; padding: 4px; }
"""

def apply_theme(app: QApplication, theme_name: str):
    """
    Applies the specified theme to the entire application.
    """
    if theme_name == "System Default":
        if hasattr(app.styleHints(), 'colorScheme'):
            scheme = app.styleHints().colorScheme()
            if scheme == Qt.ColorScheme.Dark:
                app.setStyleSheet(DARK_QSS)
            else:
                app.setStyleSheet(LIGHT_QSS)
        else:
            app.setStyleSheet(LIGHT_QSS)
    elif theme_name == "Dark":
        app.setStyleSheet(DARK_QSS)
    else:
        app.setStyleSheet(LIGHT_QSS)
