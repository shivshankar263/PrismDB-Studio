import gridfs
import os
import mimetypes
from datetime import datetime
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTableWidget,
    QTableWidgetItem,
    QPushButton,
    QLabel,
    QSplitter,
    QHeaderView,
    QFileDialog,
    QMessageBox,
    QTextEdit,
    QScrollArea,
    QAbstractItemView,
    QMenu,
    QStyle,
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QPixmap, QImage, QFont, QAction, QCursor


class GridFSView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.db = None
        self.fs = None
        self.layout = QVBoxLayout(self)

        # --- Toolbar ---
        toolbar = QHBoxLayout()

        self.upload_btn = QPushButton("+ Upload File")
        self.upload_btn.setStyleSheet("color: green; font-weight: bold;")
        self.upload_btn.clicked.connect(self.upload_file)

        self.download_btn = QPushButton("Download")
        self.download_btn.clicked.connect(self.download_file)

        self.delete_btn = QPushButton("Delete")
        self.delete_btn.setStyleSheet("color: red;")
        self.delete_btn.clicked.connect(self.delete_file)

        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self.refresh_files)

        toolbar.addWidget(self.upload_btn)
        toolbar.addWidget(self.download_btn)
        toolbar.addWidget(self.delete_btn)
        toolbar.addStretch()
        toolbar.addWidget(self.refresh_btn)
        self.layout.addLayout(toolbar)

        # --- Splitter (List vs Preview) ---
        splitter = QSplitter(Qt.Horizontal)

        # File List
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(
            ["Filename", "Size", "Type", "Upload Date", "ID"]
        )
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)

        self.table.itemSelectionChanged.connect(self.preview_file)
        # --- DEBUG: Click Event ---
        self.table.cellClicked.connect(self.debug_selection)

        # Enable Context Menu
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_context_menu)

        splitter.addWidget(self.table)

        # Preview Pane
        self.preview_widget = QWidget()
        preview_layout = QVBoxLayout(self.preview_widget)
        preview_layout.addWidget(QLabel("<b>Preview</b>"))

        self.preview_area = QScrollArea()
        self.preview_area.setWidgetResizable(True)
        self.preview_content = QLabel("Select a file to preview")
        self.preview_content.setAlignment(Qt.AlignCenter)
        self.preview_area.setWidget(self.preview_content)

        self.text_preview = QTextEdit()
        self.text_preview.setReadOnly(True)
        self.text_preview.setVisible(False)

        preview_layout.addWidget(self.preview_area)
        preview_layout.addWidget(self.text_preview)

        splitter.addWidget(self.preview_widget)
        splitter.setSizes([500, 300])

        self.layout.addWidget(splitter)

    # --- DEBUG FUNCTION ---
    def debug_selection(self, row, col):
        # print(f"DEBUG: Clicked Row {row}, Col {col}")
        item = self.table.item(row, 4)  # ID Column
        if item:
            file_id = item.data(Qt.UserRole)
            # print(f"DEBUG: ID stored in item: {file_id}")
            # print(f"DEBUG: Current Row via API: {self.table.currentRow()}")
            selected = self.table.selectedItems()
            # print(f"DEBUG: Selected items count: {len(selected)}")
        else:
            print("DEBUG: Item at column 4 is None!")

    def set_db(self, db):
        self.db = db
        if self.db is not None:
            try:
                # Default bucket 'fs'
                self.fs = gridfs.GridFS(self.db)
                self.refresh_files()
            except Exception as e:
                self.preview_content.setText(f"Error init GridFS: {e}")
        else:
            self.fs = None
            self.table.setRowCount(0)

    def refresh_files(self):
        if self.fs is None:
            return
        self.table.setRowCount(0)
        self.preview_content.setText("Select a file")
        self.text_preview.setVisible(False)
        self.preview_area.setVisible(True)

        try:
            # GridFS find() returns a cursor, we list it to iterate
            files = list(self.fs.find().sort("uploadDate", -1))
            self.table.setRowCount(len(files))

            for r, f in enumerate(files):
                # Filename
                fn = str(getattr(f, "filename", "Untitled"))
                self.table.setItem(r, 0, QTableWidgetItem(fn))

                # Size
                size_str = self.format_size(f.length)
                self.table.setItem(r, 1, QTableWidgetItem(size_str))

                # Type - FIX: Fallback to extension if unknown
                mime = getattr(f, "contentType", None)
                if not mime or mime == "unknown":
                    mime, _ = mimetypes.guess_type(fn)
                    mime = mime or "unknown"

                self.table.setItem(r, 2, QTableWidgetItem(str(mime)))

                # Date
                date_val = getattr(f, "uploadDate", datetime.now())
                date_str = date_val.strftime("%Y-%m-%d %H:%M")
                self.table.setItem(r, 3, QTableWidgetItem(date_str))

                # ID (Hidden mainly, but shown for ref)
                id_item = QTableWidgetItem(str(f._id))
                id_item.setData(Qt.UserRole, f._id)  # Store real ObjectId
                self.table.setItem(r, 4, id_item)  # FIX: Use id_item variable

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to list files: {e}")

    def upload_file(self):
        if self.fs is None:
            return
        path, _ = QFileDialog.getOpenFileName(self, "Upload File")
        if path:
            filename = os.path.basename(path)
            try:
                # Detect MIME type
                mime_type, _ = mimetypes.guess_type(path)
                if mime_type is None:
                    mime_type = "application/octet-stream"

                with open(path, "rb") as f:
                    self.fs.put(f, filename=filename, contentType=mime_type)
                QMessageBox.information(self, "Success", f"Uploaded '{filename}'")
                self.refresh_files()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Upload failed: {e}")

    def download_file(self):
        if self.fs is None:
            return

        # print("DEBUG: Download requested")
        file_id = self.get_selected_id()
        # print(f"DEBUG: File ID for download: {file_id}")

        if not file_id:
            QMessageBox.warning(self, "Selection", "Please select a file to download.")
            return

        try:
            # Get filename for default
            grid_out = self.fs.get(file_id)
            filename = getattr(grid_out, "filename", "downloaded_file")

            path, _ = QFileDialog.getSaveFileName(self, "Save File", filename)
            if path:
                with open(path, "wb") as f:
                    f.write(grid_out.read())
                QMessageBox.information(self, "Success", f"Saved to {path}")
        except Exception as e:
            # print(f"DEBUG: Download Error: {e}")
            QMessageBox.critical(self, "Error", f"Download failed: {e}")

    def delete_file(self):
        if self.fs is None:
            return
        file_id = self.get_selected_id()
        if not file_id:
            QMessageBox.warning(self, "Selection", "Please select a file to delete.")
            return

        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            "Permanently delete this file?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            try:
                self.fs.delete(file_id)
                self.refresh_files()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Delete failed: {e}")

    def preview_file(self):
        if self.fs is None:
            return
        file_id = self.get_selected_id()
        # print(f"DEBUG: Previewing ID: {file_id}")
        if not file_id:
            return

        try:
            grid_out = self.fs.get(file_id)
            # Try to get contentType from metadata or guess from filename
            mime = getattr(grid_out, "contentType", "")
            filename = getattr(grid_out, "filename", "").lower()

            if not mime or mime == "unknown":
                mime, _ = mimetypes.guess_type(filename)
                mime = str(mime or "").lower()
            else:
                mime = str(mime).lower()

            # print(f"DEBUG: Preview MIME: {mime}, Filename: {filename}")

            # Reset views
            self.preview_area.setVisible(True)
            self.text_preview.setVisible(False)

            # Image Preview
            if "image" in mime or filename.endswith(
                (".png", ".jpg", ".jpeg", ".gif", ".bmp", ".ico", ".svg", ".webp")
            ):
                data = grid_out.read()
                pixmap = QPixmap()
                pixmap.loadFromData(data)
                if not pixmap.isNull():
                    # Scale if too big
                    if pixmap.width() > 400:
                        pixmap = pixmap.scaledToWidth(400, Qt.SmoothTransformation)
                    self.preview_content.setPixmap(pixmap)
                else:
                    self.preview_content.setText("Invalid Image Data")

            # PDF Preview (Text Placeholder)
            elif "pdf" in mime or filename.endswith(".pdf"):
                self.preview_content.setText("PDF Document\n(Download to view content)")

            # Text Preview (Max 10KB)
            elif (
                "text" in mime
                or "json" in mime
                or filename.endswith(
                    (
                        ".txt",
                        ".json",
                        ".xml",
                        ".py",
                        ".js",
                        ".md",
                        ".csv",
                        ".html",
                        ".css",
                    )
                )
            ):
                self.preview_area.setVisible(False)
                self.text_preview.setVisible(True)

                # Read partial
                raw = grid_out.read(10000)
                try:
                    text = raw.decode("utf-8")
                    self.text_preview.setText(text)
                except:
                    self.text_preview.setText("Binary or Non-UTF8 content.")

            else:
                self.preview_content.setText(
                    f"No preview for {mime}\n(Download to view)"
                )

        except Exception as e:
            # print(f"DEBUG: Preview Exception: {e}")
            self.preview_content.setText(f"Preview Error: {e}")

    def show_context_menu(self, pos):
        index = self.table.indexAt(pos)
        if not index.isValid():
            return

        menu = QMenu(self)

        dl_action = QAction("Download", self)
        dl_action.setIcon(self.style().standardIcon(QStyle.SP_DialogSaveButton))
        dl_action.triggered.connect(self.download_file)
        menu.addAction(dl_action)

        del_action = QAction("Delete", self)
        del_action.setIcon(self.style().standardIcon(QStyle.SP_TrashIcon))
        del_action.triggered.connect(self.delete_file)
        menu.addAction(del_action)

        menu.exec_(QCursor.pos())

    def get_selected_id(self):
        # Method 1: Check selected items (Most robust for row selection)
        selected_items = self.table.selectedItems()
        if selected_items:
            # We just need the row from any selected item
            row = selected_items[0].row()
            # print(f"DEBUG: Selected items found at row {row}")
            item = self.table.item(row, 4)
            if item:
                return item.data(Qt.UserRole)

        # Method 2: Check current row (Fallback)
        row = self.table.currentRow()
        if row >= 0:
            # print(f"DEBUG: Fallback current row {row}")
            item = self.table.item(row, 4)
            if item:
                return item.data(Qt.UserRole)

        # print("DEBUG: No selection found")
        return None

    def format_size(self, size):
        for unit in ["B", "KB", "MB", "GB"]:
            if size < 1024:
                return f"{size:.2f} {unit}"
            size /= 1024
        return f"{size:.2f} TB"
