import json
import os
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QListWidget,
    QPushButton,
    QMessageBox,
    QFileDialog,
    QTabWidget,
    QTextEdit,
    QProgressBar,
    QLabel,
    QMenu,
    QSplitter,
    QStyle,
    QListWidgetItem,
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QAction, QCursor, QKeySequence, QShortcut, QPixmap, QIcon
from multiprocessing import Process, Queue
from pymongo.errors import CollectionInvalid, OperationFailure

from core.db_manager import DBManager
from core.workers import worker_import_task, worker_export_task, worker_scan_schema
from gui.widgets.conn_bar import ConnectionBar
from gui.views.data_view import DataView
from gui.views.erd_view import ErdView
from gui.views.agg_view import AggregationView
from gui.views.dashboard_view import DashboardView
from gui.dialogs.export_dialog import ExportDialog
from gui.dialogs.create_coll_dialog import CreateCollectionDialog
from gui.dialogs.index_manager import IndexManagerDialog
from gui.dialogs.schema_dialog import SchemaDialog
from utils.query_manager import QueryManager


class DatabaseTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.client = None
        self.db = None
        self.process = None
        self.queue = None
        self.timer = QTimer()
        self.timer.timeout.connect(self.check_process_queue)
        self.init_ui()
        self.setup_shortcuts()

    def init_ui(self):
        # 1. Connection Bar
        self.conn_bar = ConnectionBar(
            on_connect=self.connect_mongo, on_disconnect=self.disconnect_mongo
        )
        self.layout.addWidget(self.conn_bar)

        # 2. Splitter
        self.splitter = QSplitter(Qt.Horizontal)

        # --- LEFT SIDEBAR ---
        sidebar_widget = QWidget()
        sidebar_layout = QVBoxLayout(sidebar_widget)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)

        # Logo
        current_dir = os.path.dirname(os.path.abspath(__file__))
        logo_path = os.path.abspath(os.path.join(current_dir, "../../assets/logo.png"))
        if os.path.exists(logo_path):
            logo_lbl = QLabel()
            pixmap = QPixmap(logo_path)
            scaled_pixmap = pixmap.scaledToWidth(200, Qt.SmoothTransformation)
            logo_lbl.setPixmap(scaled_pixmap)
            logo_lbl.setAlignment(Qt.AlignCenter)
            logo_lbl.setContentsMargins(0, 10, 0, 10)
            sidebar_layout.addWidget(logo_lbl)

        # Sidebar Tabs (Collections / Queries)
        self.side_tabs = QTabWidget()

        # --- Tab 1: Collections ---
        coll_widget = QWidget()
        coll_layout = QVBoxLayout(coll_widget)
        coll_layout.setContentsMargins(0, 0, 0, 0)

        # Collections Header (Add/Refresh)
        header_layout = QHBoxLayout()
        header_layout.addWidget(QLabel("<b>Collections</b>"))

        add_coll_btn = QPushButton("+")
        add_coll_btn.setToolTip("Create New Collection")
        add_coll_btn.setFixedWidth(30)
        add_coll_btn.clicked.connect(self.action_create_collection)
        header_layout.addWidget(add_coll_btn)

        refresh_btn = QPushButton("R")
        refresh_btn.setToolTip("Refresh List")
        refresh_btn.setFixedWidth(30)
        refresh_btn.clicked.connect(self.refresh_colls)
        header_layout.addWidget(refresh_btn)

        coll_layout.addLayout(header_layout)

        self.coll_list = QListWidget()
        self.coll_list.itemClicked.connect(self.select_collection)
        self.coll_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.coll_list.customContextMenuRequested.connect(self.show_coll_menu)
        coll_layout.addWidget(self.coll_list)

        self.side_tabs.addTab(coll_widget, "Collections")

        # --- Tab 2: Queries (Bookmarks/History) ---
        query_widget = QWidget()
        query_layout = QVBoxLayout(query_widget)

        query_layout.addWidget(QLabel("<b>Bookmarks</b>"))
        self.bookmark_list = QListWidget()
        self.bookmark_list.itemClicked.connect(self.load_saved_query)
        query_layout.addWidget(self.bookmark_list)

        query_layout.addWidget(QLabel("<b>Recent History</b>"))
        self.history_list = QListWidget()
        self.history_list.itemClicked.connect(self.load_saved_query)
        
        # Enable Right-Click Context Menu for History
        self.history_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.history_list.customContextMenuRequested.connect(self.show_history_menu)
        
        query_layout.addWidget(self.history_list)

        self.side_tabs.addTab(query_widget, "Queries")

        sidebar_layout.addWidget(self.side_tabs)
        self.splitter.addWidget(sidebar_widget)
        # -----------------------

        # --- RIGHT WORK AREA ---
        work_widget = QWidget()
        work_layout = QVBoxLayout(work_widget)
        work_layout.setContentsMargins(0, 0, 0, 0)

        self.tabs = QTabWidget()

        # Initialize Views
        self.dashboard_view = DashboardView()
        self.data_view = DataView()
        self.data_view.request_navigation.connect(self.navigate_to_collection)
        self.data_view.query_executed.connect(
            self.refresh_query_sidebar
        )  # Update history on run

        self.agg_view = AggregationView()
        self.erd_view = ErdView()

        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setStyleSheet("background: #212529; color: #00ff00;")

        # Add Tabs
        self.tabs.addTab(self.data_view, "Data Explorer")
        self.tabs.addTab(self.dashboard_view, "Dashboard")
        self.tabs.addTab(self.agg_view, "Aggregation Builder")
        self.tabs.addTab(self.erd_view, "Schema / ERD")
        self.tabs.addTab(self.log_view, "System Logs")

        work_layout.addWidget(self.tabs)

        self.progress = QProgressBar()
        self.progress.setVisible(False)
        work_layout.addWidget(self.progress)

        self.splitter.addWidget(work_widget)
        self.splitter.setSizes([250, 800])
        self.layout.addWidget(self.splitter)

        # Initial Sidebar Load
        self.refresh_query_sidebar()

    # --- ACTIONS & LOGIC ---

    def action_create_collection(self):
        if self.db is None:
            return QMessageBox.warning(self, "Error", "Connect to DB first.")
        dlg = CreateCollectionDialog(self)
        if dlg.exec():
            data = dlg.get_data()
            name = data.pop("name")
            try:
                self.db.create_collection(name, **data)
                self.log_view.append(
                    f"SUCCESS: Created collection '{name}' with options {data}"
                )
                QMessageBox.information(
                    self, "Success", f"Collection '{name}' created."
                )
                self.refresh_colls()
            except CollectionInvalid:
                QMessageBox.warning(
                    self, "Error", f"Collection '{name}' already exists."
                )
            except OperationFailure as e:
                QMessageBox.critical(
                    self, "Error", f"MongoDB Error: {e.details.get('errmsg', str(e))}"
                )
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))

    def action_drop_collection(self, coll_name):
        if self.db is None:
            return
        confirm = QMessageBox.question(
            self,
            "Drop Collection",
            f"Are you sure you want to DROP '{coll_name}'?\n\nThis action cannot be undone!",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if confirm == QMessageBox.Yes:
            try:
                self.db.drop_collection(coll_name)
                self.log_view.append(f"SUCCESS: Dropped collection '{coll_name}'")
                if (
                    self.data_view.collection is not None
                    and self.data_view.collection.name == coll_name
                ):
                    self.data_view.set_collection(None)
                    self.data_view.table.clear()
                    self.agg_view.set_collection(None)
                self.refresh_colls()
                QMessageBox.information(
                    self, "Dropped", f"Collection '{coll_name}' has been dropped."
                )
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to drop collection: {e}")

    def action_manage_indexes(self, coll_name):
        if self.db is None:
            return
        try:
            coll = self.db[coll_name]
            dlg = IndexManagerDialog(coll, self)
            dlg.exec()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def action_manage_schema(self, coll_name):
        if self.db is None:
            return
        try:
            coll = self.db[coll_name]
            dlg = SchemaDialog(coll, self)
            dlg.exec()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def show_coll_menu(self, pos):
        item = self.coll_list.itemAt(pos)
        menu = QMenu(self)

        base_dir = os.path.dirname(os.path.abspath(__file__))
        icons_dir = os.path.abspath(os.path.join(base_dir, "../../assets/icons"))

        icon_add = QIcon(os.path.join(icons_dir, "plus.svg"))
        icon_refresh = QIcon(os.path.join(icons_dir, "refresh.svg"))
        icon_delete = self.style().standardIcon(QStyle.SP_TrashIcon)
        icon_export = self.style().standardIcon(QStyle.SP_DialogSaveButton)
        icon_gear = self.style().standardIcon(QStyle.SP_FileDialogDetailedView)

        if item:
            coll_name = item.text()

            idx_action = QAction(f"Manage Indexes...", self)
            idx_action.setIcon(icon_gear)
            idx_action.triggered.connect(lambda: self.action_manage_indexes(coll_name))
            menu.addAction(idx_action)

            schema_action = QAction(f"Manage Schema...", self)
            schema_action.triggered.connect(
                lambda: self.action_manage_schema(coll_name)
            )
            menu.addAction(schema_action)

            menu.addSeparator()

            export_action = QAction(f"Export '{coll_name}'...", self)
            export_action.setIcon(icon_export)
            export_action.triggered.connect(
                lambda: self.trigger_single_export(coll_name)
            )
            menu.addAction(export_action)

            drop_action = QAction(f"Drop Collection", self)
            drop_action.setIcon(icon_delete)
            drop_action.triggered.connect(
                lambda: self.action_drop_collection(coll_name)
            )
            menu.addAction(drop_action)

            menu.addSeparator()

        create_action = QAction("Create New Collection...", self)
        create_action.setIcon(icon_add)
        create_action.triggered.connect(self.action_create_collection)
        menu.addAction(create_action)

        refresh_action = QAction("Refresh List", self)
        refresh_action.setIcon(icon_refresh)
        refresh_action.triggered.connect(self.refresh_colls)
        menu.addAction(refresh_action)

        menu.exec_(QCursor.pos())

    def navigate_to_collection(self, target_coll_name, query):
        # Find item in collection list
        items = self.coll_list.findItems(target_coll_name, Qt.MatchExactly)
        if items:
            self.coll_list.setCurrentItem(items[0])
            coll = self.db[target_coll_name]
            self.data_view.set_collection(coll)
            self.agg_view.set_collection(coll)

            # --- FIX: Use search_widget instead of query_input ---
            self.data_view.search_widget.set_raw_query(query)
            # -----------------------------------------------------

            self.data_view.reset_and_load()
            self.tabs.setCurrentIndex(1)
        else:
            QMessageBox.warning(
                self, "Error", f"Collection '{target_coll_name}' not found."
            )

    def refresh_query_sidebar(self, _=None):
        data = QueryManager.load()

        self.bookmark_list.clear()
        for b in data["bookmarks"]:
            item = QListWidgetItem(f"★ {b['name']}")
            item.setToolTip(b["query"])
            item.setData(Qt.UserRole, b["query"])
            self.bookmark_list.addItem(item)

        self.history_list.clear()
        for h in data["history"]:
            item = QListWidgetItem(h)
            item.setToolTip(h)
            item.setData(Qt.UserRole, h)
            self.history_list.addItem(item)

    def load_saved_query(self, item):
        query_str = item.data(Qt.UserRole)
        import json
        from bson import json_util

        try:
            query_dict = json.loads(query_str, object_hook=json_util.object_hook)
            self.data_view.search_widget.set_raw_query(query_dict)
        except Exception as e:
            pass

        self.tabs.setCurrentIndex(1)  # Switch to Data Explorer
        # self.data_view.reset_and_load() # Uncomment to auto-run

    def setup_shortcuts(self):
        self.sc_refresh = QShortcut(QKeySequence("F5"), self)
        self.sc_refresh.activated.connect(self.refresh_action)
        self.sc_run = QShortcut(QKeySequence("Ctrl+Return"), self)
        self.sc_run.activated.connect(self.refresh_action)
        self.sc_next = QShortcut(QKeySequence("Ctrl+Right"), self)
        self.sc_next.activated.connect(self.data_view.next_page)
        self.sc_prev = QShortcut(QKeySequence("Ctrl+Left"), self)
        self.sc_prev.activated.connect(self.data_view.prev_page)
        self.sc_export = QShortcut(QKeySequence("Ctrl+E"), self)
        self.sc_export.activated.connect(self.trigger_bulk_export)
        self.sc_import = QShortcut(QKeySequence("Ctrl+O"), self)
        self.sc_import.activated.connect(self.trigger_import)
        self.sc_focus = QShortcut(QKeySequence("Ctrl+L"), self)
        self.sc_focus.activated.connect(self.conn_bar.uri_input.setFocus)

    def refresh_action(self):
        idx = self.tabs.currentIndex()
        if idx == 0:
            self.dashboard_view.refresh_stats()
        elif idx == 1:
            self.data_view.reset_and_load()
        elif idx == 2:
            self.agg_view.run_pipeline()
        elif idx == 3:
            self.trigger_erd_scan()

    def connect_mongo(self, uri):
        if not uri:
            return False
        client, db, error = DBManager.connect(uri)
        if error:
            QMessageBox.critical(self, "Connection Error", error)
            return False
        self.client = client
        self.db = db
        self.log_view.append(f"Connected to: {self.db.name}")
        self.refresh_colls()

        # Start Dashboard
        self.dashboard_view.set_db(self.db)

        QMessageBox.information(
            self, "Connected", f"Successfully connected to database: {self.db.name}"
        )
        return True

    def disconnect_mongo(self):
        if self.client:
            self.client.close()
        self.client = None
        self.db = None

        self.dashboard_view.set_db(None)

        self.coll_list.clear()
        self.data_view.table.clear()
        self.data_view.table.setRowCount(0)
        self.erd_view.scene.clear()
        self.log_view.append("Disconnected.")

    def safe_close(self):
        if self.client is not None:
            reply = QMessageBox.question(
                self,
                "Disconnect?",
                f"Database '{self.db.name}' is connected.\nDisconnect and close?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if reply == QMessageBox.Yes:
                self.disconnect_mongo()
                return True
            else:
                return False
        return True

    def refresh_colls(self):
        if self.db is None:
            return
        try:
            self.coll_list.clear()
            colls = sorted(self.db.list_collection_names())
            visible = [c for c in colls if not c.startswith("system.")]
            icon = self.style().standardIcon(QStyle.SP_FileIcon)
            for name in visible:
                item = QListWidgetItem(icon, name)
                self.coll_list.addItem(item)
        except Exception as e:
            self.log_view.append(f"Error listing collections: {e}")

    def select_collection(self, item):
        if self.db is None:
            return
        coll = self.db[item.text()]
        self.data_view.set_collection(coll)
        self.agg_view.set_collection(coll)

    def trigger_single_export(self, coll_name):
        if self.db is None:
            return
        dlg = ExportDialog(self)
        dlg.setWindowTitle(f"Export Collection: {coll_name}")
        if dlg.exec():
            fmt, meta = dlg.get_settings()
            folder = QFileDialog.getExistingDirectory(self, "Select Folder")
            if folder:
                self.start_process(
                    worker_export_task,
                    self.conn_bar.uri_input.text(),
                    folder,
                    fmt,
                    meta,
                    [coll_name],
                )

    def trigger_bulk_export(self):
        if self.db is None:
            return QMessageBox.warning(self, "Error", "Connect to DB first.")
        dlg = ExportDialog(self)
        if dlg.exec():
            fmt, meta = dlg.get_settings()
            folder = QFileDialog.getExistingDirectory(self, "Select Folder")
            if folder:
                self.start_process(
                    worker_export_task,
                    self.conn_bar.uri_input.text(),
                    folder,
                    fmt,
                    meta,
                    None,
                )

    def trigger_import(self):
        if self.db is None:
            return QMessageBox.warning(self, "Error", "Connect to DB first.")
        files, _ = QFileDialog.getOpenFileNames(
            self, "Select Files", "", "Data (*.json *.bson)"
        )
        if files:
            self.start_process(
                worker_import_task, self.conn_bar.uri_input.text(), files
            )

    def trigger_erd_scan(self):
        if self.db is None:
            return QMessageBox.warning(self, "Error", "Connect to DB first.")
        self.start_process(worker_scan_schema, self.conn_bar.uri_input.text())

    def export_erd_image(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Image", "erd_diagram.png", "PNG Image (*.png)"
        )
        if path:
            img = self.erd_view.get_image()
            img.save(path)
            QMessageBox.information(self, "Saved", f"ERD saved to {path}")

    def start_process(self, target_func, *args):
        if self.process is not None:
            return QMessageBox.warning(self, "Busy", "Background task running.")
        # Switch to Logs Tab (index 4)
        self.tabs.setCurrentIndex(4)
        self.progress.setVisible(True)
        self.progress.setValue(0)
        self.queue = Queue()
        self.process = Process(target=target_func, args=args + (self.queue,))
        self.process.start()
        self.timer.start(100)

    def check_process_queue(self):
        if self.queue is None:
            return
        while self.queue and not self.queue.empty():
            try:
                msg = self.queue.get_nowait()
                msg_type, content = msg[0], msg[1]
                if msg_type == "progress":
                    self.log_view.append(f"PROCESSING: {content}")
                    if len(msg) > 2:
                        self.progress.setValue(msg[2])
                elif msg_type == "log":
                    self.log_view.append(f"LOG: {content}")
                elif msg_type == "finished":
                    self.cleanup_process()
                    QMessageBox.information(self, "Task Complete", content)
                    return
                elif msg_type == "error":
                    self.cleanup_process()
                    QMessageBox.critical(self, "Error", content)
                    return
                elif msg_type == "schema_result":
                    self.erd_view.render_schema(json.loads(content))
                    self.tabs.setCurrentIndex(3)
            except Exception:
                break

    def cleanup_process(self):
        self.timer.stop()
        if self.process and self.process.is_alive():
            self.process.terminate()
            self.process.join()
        self.process = None
        self.queue = None
        self.progress.setVisible(False)

    def show_history_menu(self, pos):
        menu = QMenu(self)

        clear_action = QAction("Clear History", self)
        clear_action.setIcon(self.style().standardIcon(QStyle.SP_TrashIcon))
        clear_action.triggered.connect(self.action_clear_history)
        menu.addAction(clear_action)

        menu.exec_(QCursor.pos())

    # --- NEW: Clear History Action ---
    def action_clear_history(self):
        reply = QMessageBox.question(
            self,
            "Clear History",
            "Are you sure you want to clear all history?\nBookmarks will NOT be deleted.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )

        if reply == QMessageBox.Yes:
            QueryManager.clear_history()
            self.refresh_query_sidebar()
            QMessageBox.information(self, "Success", "Search history cleared.")
