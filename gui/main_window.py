import sys
from PySide6.QtWidgets import QMainWindow, QTabWidget, QMessageBox
from PySide6.QtGui import QKeySequence, QShortcut
from config.settings import APP_TITLE, WINDOW_SIZE
from gui.tabs.db_tab import DatabaseTab

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_TITLE)
        self.resize(*WINDOW_SIZE)
        
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.tabCloseRequested.connect(self.close_tab)
        self.setCentralWidget(self.tab_widget)
        
        self.create_menubar()
        self.setup_global_shortcuts() 
        
        self.add_new_tab()

    def create_menubar(self):
        menu = self.menuBar()
        
        file_menu = menu.addMenu("File")
        # Updated Visual Hints
        file_menu.addAction("New Connection Tab\tCtrl+N", self.add_new_tab)
        file_menu.addAction("Close Current Tab\tCtrl+W", lambda: self.close_tab(self.tab_widget.currentIndex()))
        file_menu.addSeparator()
        file_menu.addAction("Exit\tCtrl+Q", self.close)
        
        tools_menu = menu.addMenu("Tools")
        tools_menu.addAction("Import to Current DB...", self.action_import_current)
        tools_menu.addAction("Export All from Current DB...", self.action_export_current)

        help_menu = menu.addMenu("Help")
        help_menu.addAction("About", self.show_about)

    def setup_global_shortcuts(self):
        # 1. New Tab (Ctrl + N)
        QShortcut(QKeySequence("Ctrl+N"), self).activated.connect(self.add_new_tab)
        
        # 2. Close Tab (Ctrl + W)
        QShortcut(QKeySequence("Ctrl+W"), self).activated.connect(
            lambda: self.close_tab(self.tab_widget.currentIndex())
        )
        
        # 3. Switch Tabs (Ctrl + Tab / Ctrl + Shift + Tab)
        QShortcut(QKeySequence("Ctrl+Tab"), self).activated.connect(self.next_tab)
        QShortcut(QKeySequence("Ctrl+Shift+Tab"), self).activated.connect(self.prev_tab)
        
        # 4. Quit (Ctrl + Q)
        QShortcut(QKeySequence("Ctrl+Q"), self).activated.connect(self.close)

    def add_new_tab(self):
        new_tab = DatabaseTab(self)
        idx = self.tab_widget.addTab(new_tab, "New Connection")
        self.tab_widget.setCurrentIndex(idx)

    def close_tab(self, index):
        if index < 0: return 
        
        if self.tab_widget.count() > 1:
            widget = self.tab_widget.widget(index)
            widget.disconnect_mongo() 
            self.tab_widget.removeTab(index)
        else:
            widget = self.tab_widget.widget(0)
            widget.disconnect_mongo()
            widget.conn_bar.set_disconnected_state()
            self.tab_widget.setTabText(0, "New Connection")

    def next_tab(self):
        idx = self.tab_widget.currentIndex()
        if idx < self.tab_widget.count() - 1:
            self.tab_widget.setCurrentIndex(idx + 1)
        else:
            self.tab_widget.setCurrentIndex(0) # Loop back to start

    def prev_tab(self):
        idx = self.tab_widget.currentIndex()
        if idx > 0:
            self.tab_widget.setCurrentIndex(idx - 1)
        else:
            self.tab_widget.setCurrentIndex(self.tab_widget.count() - 1) # Loop to end

    def action_import_current(self):
        current_widget = self.tab_widget.currentWidget()
        if isinstance(current_widget, DatabaseTab):
            current_widget.trigger_import()

    def action_export_current(self):
        current_widget = self.tab_widget.currentWidget()
        if isinstance(current_widget, DatabaseTab):
            current_widget.trigger_bulk_export()

    def show_about(self):
        msg = (
            f"{APP_TITLE}\n\n"
            "Global Shortcuts:\n"
            "  Ctrl+N : New Tab\n"
            "  Ctrl+W : Close Tab\n"
            "  Ctrl+Tab : Next Tab\n"
            "  Ctrl+Q : Exit\n\n"
            "Tab Shortcuts:\n"
            "  F5 / Ctrl+Enter : Run Query\n"
            "  Ctrl+Left/Right : Pagination\n"
            "  Ctrl+E : Export\n"
            "  Ctrl+O : Import\n"
            "  Ctrl+L : Focus Address Bar"
        )
        QMessageBox.about(self, "About", msg)