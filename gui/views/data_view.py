import json
import re
import math
import csv
import io
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QLabel,
    QMenu,
    QDialog,
    QListWidget,
    QListWidgetItem,
    QDialogButtonBox,
    QMessageBox,
    QAbstractItemView,
    QCompleter,
    QApplication,
    QTextEdit,
    QStyle,
    QComboBox,
    QFrame,
    QHeaderView,
)
from PySide6.QtCore import Qt, QStringListModel, Signal
from PySide6.QtGui import QAction, QCursor, QFont, QColor, QBrush
from bson import json_util, ObjectId
from gui.dialogs.explain_dialog import ExplainDialog
from PySide6.QtWidgets import QInputDialog
from utils.query_manager import QueryManager


# --- 1. SIMPLE SEARCH WIDGET (UPDATED) ---
class SimpleSearchWidget(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(
            ".QFrame { background-color: white; border: 1px solid #ced4da; border-radius: 4px; }"
        )
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(5)

        self.field_combo = QComboBox()
        self.field_combo.setEditable(True)
        self.field_combo.setPlaceholderText("Field (e.g. status)")
        self.field_combo.setInsertPolicy(QComboBox.NoInsert)
        self.field_combo.completer().setCompletionMode(QCompleter.PopupCompletion)
        self.field_combo.setStyleSheet("border: none; padding: 4px;")

        lbl = QLabel(":")
        lbl.setStyleSheet("font-weight: bold; color: gray; border: none;")

        self.value_input = QLineEdit()
        self.value_input.setPlaceholderText("Value")
        self.value_input.setStyleSheet("border: none; padding: 4px;")

        self.layout.addWidget(self.field_combo, 1)
        self.layout.addWidget(lbl)
        self.layout.addWidget(self.value_input, 2)

    def set_fields(self, fields):
        current = self.field_combo.currentText()
        self.field_combo.clear()
        self.field_combo.addItems(sorted(fields))
        self.field_combo.setEditText(current)

    def get_query(self):
        field = self.field_combo.currentText().strip()
        val_txt = self.value_input.text().strip()

        if not field or not val_txt:
            return {}

        value = val_txt

        # 1. Force String via Quotes (e.g. "123")
        if (val_txt.startswith('"') and val_txt.endswith('"')) or (
            val_txt.startswith("'") and val_txt.endswith("'")
        ):
            value = val_txt[1:-1]

        # 2. ObjectId
        elif ObjectId.is_valid(val_txt):
            value = ObjectId(val_txt)

        # 3. Boolean
        elif val_txt.lower() == "true":
            value = True
        elif val_txt.lower() == "false":
            value = False

        # 4. Number (Int/Float) - WITH LEADING ZERO FIX
        elif val_txt.replace(".", "", 1).isdigit():
            # If it starts with '0' but isn't just "0" or "0.xx", treat as String (e.g. "0161...")
            if val_txt.startswith("0") and "." not in val_txt and len(val_txt) > 1:
                value = val_txt  # Keep as string
            elif "." in val_txt:
                value = float(val_txt)
            else:
                value = int(val_txt)

        # 5. JSON Object/Array
        elif val_txt.startswith("{") or val_txt.startswith("["):
            try:
                value = json.loads(val_txt, object_hook=json_util.object_hook)
            except:
                pass

        return {field: value}

    def set_raw_query(self, query_dict):
        if not query_dict:
            return
        try:
            k = list(query_dict.keys())[0]
            v = query_dict[k]
            self.field_combo.setEditText(k)
            self.value_input.setText(str(v))
        except:
            pass


# --- 2. FILTER DIALOG (Unchanged) ---
class FilterDialog(QDialog):
    def __init__(self, field_name, unique_values, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Filter: {field_name}")
        self.resize(350, 500)
        layout = QVBoxLayout(self)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(f"Search values in {field_name}...")
        self.search_input.textChanged.connect(self.filter_list_items)
        layout.addWidget(self.search_input)
        self.list_widget = QListWidget()
        for val in unique_values:
            display_val = str(val) if val is not None else "(Empty)"
            item = QListWidgetItem(display_val)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Unchecked)
            item.setData(Qt.UserRole, val)
            self.list_widget.addItem(item)
        layout.addWidget(self.list_widget)
        btn_row = QHBoxLayout()
        sel_all = QPushButton("Select All")
        sel_all.clicked.connect(self.select_all)
        sel_none = QPushButton("Clear Selection")
        sel_none.clicked.connect(self.select_none)
        btn_row.addWidget(sel_all)
        btn_row.addWidget(sel_none)
        layout.addLayout(btn_row)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def filter_list_items(self, text):
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            item.setHidden(text.lower() not in item.text().lower())

    def select_all(self):
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if not item.isHidden():
                item.setCheckState(Qt.Checked)

    def select_none(self):
        for i in range(self.list_widget.count()):
            self.list_widget.item(i).setCheckState(Qt.Unchecked)

    def get_selected_values(self):
        selected = []
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if item.checkState() == Qt.Checked:
                selected.append(item.data(Qt.UserRole))
        return selected


# --- 3. JSON EDITOR DIALOG (Unchanged) ---
class JsonEditorDialog(QDialog):
    def __init__(self, initial_data=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("JSON Document Editor")
        self.resize(600, 600)
        self.layout = QVBoxLayout(self)
        self.editor = QTextEdit()
        self.editor.setFont(QFont("Consolas", 10))
        if initial_data:
            text = json.dumps(initial_data, indent=4, default=json_util.default)
        else:
            text = "{\n    \n}"
        self.editor.setText(text)
        self.layout.addWidget(self.editor)
        self.info_lbl = QLabel(
            "Edit valid JSON below. ObjectId and Date formats are supported."
        )
        self.info_lbl.setStyleSheet("color: gray; font-style: italic;")
        self.layout.addWidget(self.info_lbl)
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.validate_and_accept)
        buttons.rejected.connect(self.reject)
        self.layout.addWidget(buttons)
        self.final_data = None

    def validate_and_accept(self):
        try:
            raw_text = self.editor.toPlainText()
            self.final_data = json.loads(raw_text, object_hook=json_util.object_hook)
            self.accept()
        except Exception as e:
            QMessageBox.warning(self, "Invalid JSON", f"Error parsing JSON:\n{e}")

    def get_data(self):
        return self.final_data


# --- 4. MAIN DATA VIEW ---
class DataView(QWidget):
    request_navigation = Signal(str, dict)
    query_executed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.collection = None
        self.page = 0
        self.page_size = 50
        self.current_sort = None
        self.active_filters = {}
        self.current_headers = []
        self.schema_keys = set()

        # Search Bar
        search_bar = QHBoxLayout()

        self.search_widget = SimpleSearchWidget()

        self.star_btn = QPushButton("★")
        self.star_btn.setToolTip("Bookmark this Query")
        self.star_btn.setFixedWidth(30)
        self.star_btn.setStyleSheet(
            "color: #ffc107; font-weight: bold; font-size: 14px;"
        )
        self.star_btn.clicked.connect(self.action_bookmark_query)

        run_btn = QPushButton("Search")
        run_btn.clicked.connect(self.reset_and_load)

        self.explain_btn = QPushButton("Explain")
        self.explain_btn.setToolTip("Analyze Query Performance")
        self.explain_btn.setStyleSheet("background-color: #6c757d; color: white;")
        self.explain_btn.clicked.connect(self.action_explain_query)

        self.paste_btn = QPushButton("Paste")
        self.paste_btn.setToolTip("Import JSON/CSV from Clipboard")
        self.paste_btn.setStyleSheet("background-color: #ffc107; color: black;")
        self.paste_btn.clicked.connect(self.action_paste_import)

        self.add_btn = QPushButton("+ Add")
        self.add_btn.setStyleSheet("color: green; font-weight: bold;")
        self.add_btn.clicked.connect(self.action_add_document)

        self.clear_filter_btn = QPushButton("Clear")
        self.clear_filter_btn.clicked.connect(self.clear_all_filters)

        search_bar.addWidget(self.search_widget, 1)
        search_bar.addWidget(self.star_btn)
        search_bar.addWidget(run_btn)
        search_bar.addWidget(self.explain_btn)
        search_bar.addWidget(self.paste_btn)
        search_bar.addWidget(self.add_btn)
        search_bar.addWidget(self.clear_filter_btn)
        self.layout.addLayout(search_bar)

        # Table
        self.table = QTableWidget()
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.handle_context_menu)
        self.table.horizontalHeader().setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.horizontalHeader().customContextMenuRequested.connect(
            self.show_header_menu
        )
        self.table.cellDoubleClicked.connect(self.check_foreign_key_click)
        self.layout.addWidget(self.table)

        # Pagination
        nav = QHBoxLayout()
        self.prev_b = QPushButton("< Prev")
        self.prev_b.clicked.connect(self.prev_page)
        self.next_b = QPushButton("Next >")
        self.next_b.clicked.connect(self.next_page)
        self.page_lbl = QLabel("Page 1")
        nav.addWidget(self.prev_b)
        nav.addWidget(self.page_lbl)
        nav.addWidget(self.next_b)
        nav.addStretch()
        self.layout.addLayout(nav)

    def set_collection(self, collection):
        self.collection = collection
        self.clear_all_filters()
        self.scan_schema_keys()

    # --- ACTIONS ---
    def action_bookmark_query(self):
        query_dict = self.search_widget.get_query()
        if not query_dict:
            return
        query_str = json.dumps(query_dict, default=json_util.default)
        name, ok = QInputDialog.getText(
            self, "Bookmark Query", "Enter a name for this bookmark:"
        )
        if ok and name:
            QueryManager.add_bookmark(name, query_str)
            QMessageBox.information(self, "Saved", "Query bookmarked!")
            self.query_executed.emit(query_str)

    def action_add_document(self):
        if self.collection is None:
            return
        dlg = JsonEditorDialog(parent=self)
        if dlg.exec():
            new_doc = dlg.get_data()
            if new_doc:
                try:
                    self.collection.insert_one(new_doc)
                    QMessageBox.information(
                        self, "Success", "Document inserted successfully."
                    )
                    self.load_data()
                except Exception as e:
                    QMessageBox.critical(self, "Error", f"Insert failed: {e}")

    def action_edit_document(self, doc_id):
        if self.collection is None or doc_id is None:
            return
        doc = self.collection.find_one({"_id": doc_id})
        if not doc:
            QMessageBox.warning(
                self, "Error", "Document not found (might have been deleted)."
            )
            return
        dlg = JsonEditorDialog(initial_data=doc, parent=self)
        if dlg.exec():
            updated_doc = dlg.get_data()
            if updated_doc:
                try:
                    if "_id" in updated_doc and updated_doc["_id"] != doc_id:
                        QMessageBox.warning(
                            self,
                            "Warning",
                            "Changing _id is not supported in Edit mode.",
                        )
                        updated_doc["_id"] = doc_id
                    self.collection.replace_one({"_id": doc_id}, updated_doc)
                    QMessageBox.information(self, "Success", "Document updated.")
                    self.load_data()
                except Exception as e:
                    QMessageBox.critical(self, "Error", f"Update failed: {e}")

    def action_delete_document(self, doc_id):
        if self.collection is None or doc_id is None:
            return
        reply = QMessageBox.question(
            self,
            "Delete Document",
            f"Are you sure you want to delete document with _id:\n{doc_id}?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            try:
                self.collection.delete_one({"_id": doc_id})
                self.load_data()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Delete failed: {e}")

    def action_explain_query(self):
        if self.collection is None:
            return
        final_query = self.search_widget.get_query()
        for field, values in self.active_filters.items():
            if values:
                final_query[field] = {"$in": values}

        try:
            cursor = self.collection.find(final_query)
            if self.current_sort:
                cursor.sort(self.current_sort[0], self.current_sort[1])
            explanation = cursor.explain("executionStats")
            dlg = ExplainDialog(explanation, self)
            dlg.exec()
        except Exception as e:
            QMessageBox.critical(self, "Explain Error", str(e))

    def action_paste_import(self):
        if self.collection is None:
            return
        clipboard = QApplication.clipboard()
        text = clipboard.text().strip()
        if not text:
            return QMessageBox.warning(self, "Empty", "Clipboard is empty.")

        parsed_docs = []
        fmt = "unknown"
        try:
            data = json.loads(text, object_hook=json_util.object_hook)
            if isinstance(data, list):
                parsed_docs = data
            elif isinstance(data, dict):
                parsed_docs = [data]
            fmt = "JSON"
        except json.JSONDecodeError:
            try:
                f = io.StringIO(text)
                reader = csv.DictReader(f)
                if reader.fieldnames:
                    parsed_docs = list(reader)
                    for d in parsed_docs:
                        for k, v in d.items():
                            if v.isdigit():
                                d[k] = int(v)
                            elif v.lower() == "true":
                                d[k] = True
                            elif v.lower() == "false":
                                d[k] = False
                    fmt = "CSV"
            except Exception:
                pass

        if not parsed_docs:
            return QMessageBox.warning(
                self,
                "Parse Error",
                "Could not detect valid JSON or CSV data in clipboard.",
            )

        reply = QMessageBox.question(
            self,
            "Import from Clipboard",
            f"Detected {len(parsed_docs)} documents ({fmt}).\nProceed with import?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            try:
                self.collection.insert_many(parsed_docs)
                QMessageBox.information(
                    self,
                    "Success",
                    f"Successfully imported {len(parsed_docs)} documents.",
                )
                self.load_data()
            except Exception as e:
                msg = str(e)
                if "DocumentValidationFailure" in msg:
                    msg = "Data violates Schema Validation rules."
                QMessageBox.critical(self, "Import Failed", msg)

    # --- UI HANDLERS ---
    def handle_context_menu(self, pos):
        index = self.table.indexAt(pos)
        if not index.isValid():
            return
        row = index.row()
        item = self.table.item(row, 0)
        doc_id = item.data(Qt.UserRole)

        menu = QMenu(self)
        edit_act = QAction("Edit Document", self)
        edit_act.triggered.connect(lambda: self.action_edit_document(doc_id))
        menu.addAction(edit_act)

        del_act = QAction("Delete Document", self)
        del_act.setIcon(self.style().standardIcon(QStyle.SP_TrashIcon))
        del_act.triggered.connect(lambda: self.action_delete_document(doc_id))
        menu.addAction(del_act)

        menu.addSeparator()

        copy_act = QAction("Copy Cell Value", self)
        copy_act.triggered.connect(lambda: self.copy_to_clipboard(index))
        menu.addAction(copy_act)
        menu.exec_(QCursor.pos())

    def show_header_menu(self, pos):
        header = self.table.horizontalHeader()
        col_idx = header.logicalIndexAt(pos)
        if col_idx < 0:
            return
        field_name = self.current_headers[col_idx]

        menu = QMenu(self)
        action_asc = QAction(f"Sort Ascending ({field_name})", self)
        action_asc.triggered.connect(lambda: self.apply_sort(field_name, 1))
        menu.addAction(action_asc)

        action_desc = QAction(f"Sort Descending ({field_name})", self)
        action_desc.triggered.connect(lambda: self.apply_sort(field_name, -1))
        menu.addAction(action_desc)

        menu.addSeparator()

        action_filter = QAction(f"Filter by Value...", self)
        action_filter.triggered.connect(lambda: self.open_filter_dialog(field_name))
        menu.addAction(action_filter)

        menu.exec_(QCursor.pos())

    def apply_sort(self, field, direction):
        self.current_sort = (field, direction)
        self.page = 0
        self.load_data()

    def open_filter_dialog(self, field_name):
        try:
            QApplication.setOverrideCursor(Qt.WaitCursor)
            unique_vals = self.collection.distinct(field_name)
            QApplication.restoreOverrideCursor()
            unique_vals = sorted([v for v in unique_vals if v is not None], key=str)[
                :2000
            ]
            dlg = FilterDialog(field_name, unique_vals, self)
            if field_name in self.active_filters:
                current_selection = self.active_filters[field_name]
                for i in range(dlg.list_widget.count()):
                    item = dlg.list_widget.item(i)
                    if item.data(Qt.UserRole) in current_selection:
                        item.setCheckState(Qt.Checked)
            if dlg.exec():
                selected = dlg.get_selected_values()
                if selected:
                    self.active_filters[field_name] = selected
                else:
                    if field_name in self.active_filters:
                        del self.active_filters[field_name]
                self.page = 0
                self.load_data()
        except Exception as e:
            QApplication.restoreOverrideCursor()
            QMessageBox.warning(self, "Error", f"Could not fetch unique values: {e}")

    def check_foreign_key_click(self, row, col):
        header = self.current_headers[col]
        item = self.table.item(row, col)
        if not item:
            return
        val = item.text().strip('"').strip("'")
        is_fk = header.lower().endswith("id") and header != "_id"

        if is_fk:
            base_name = re.sub(r"_?id$", "", header, flags=re.IGNORECASE)
            guesses = [base_name + "s", base_name + "es", base_name]
            db = self.collection.database
            target_coll = None
            existing_colls = db.list_collection_names()
            for g in guesses:
                match = next(
                    (c for c in existing_colls if c.lower() == g.lower()), None
                )
                if match:
                    target_coll = match
                    break

            if target_coll:
                query_val = val
                if ObjectId.is_valid(val):
                    query_val = ObjectId(val)
                reply = QMessageBox.question(
                    self,
                    "Navigate",
                    f"Found potential link to '{target_coll}'.\nGo to document {val}?",
                    QMessageBox.Yes | QMessageBox.No,
                )
                if reply == QMessageBox.Yes:
                    self.request_navigation.emit(target_coll, {"_id": query_val})
            else:
                QMessageBox.information(
                    self,
                    "No Link",
                    f"Could not find a collection matching '{base_name}'.",
                )

    def copy_to_clipboard(self, index):
        item = self.table.item(index.row(), index.column())
        if item:
            clipboard = QApplication.clipboard()
            clipboard.setText(item.text())

    def load_data(self):
        if self.collection is None:
            return
        self.table.clear()
        self.table.setRowCount(0)
        self.table.setColumnCount(0)

        final_query = self.search_widget.get_query()
        if final_query:
            query_str = json.dumps(final_query, default=json_util.default)
            QueryManager.add_to_history(query_str)
            self.query_executed.emit(query_str)

        for field, values in self.active_filters.items():
            if values:
                final_query[field] = {"$in": values}

        try:
            total_docs = self.collection.count_documents(final_query)
            max_page = math.ceil(total_docs / self.page_size)
            if max_page == 0:
                max_page = 1
            self.prev_b.setEnabled(self.page > 0)
            self.next_b.setEnabled(self.page < max_page - 1)
            self.page_lbl.setText(f"Page {self.page + 1} / {max_page}")

            cursor = self.collection.find(final_query)
            if self.current_sort:
                cursor.sort(self.current_sort[0], self.current_sort[1])
            else:
                cursor.sort("_id", -1)
            cursor.skip(self.page * self.page_size).limit(self.page_size)
            docs = list(cursor)

            if not docs:
                self.table.setRowCount(0)
                self.prev_b.setEnabled(False)
                self.next_b.setEnabled(False)
                self.page_lbl.setText("No Results")
                return

            self.current_headers = []
            visible_values = set()
            for d in docs:
                for k, v in d.items():
                    if k not in self.current_headers:
                        self.current_headers.append(k)
                    if isinstance(v, (str, int, float, bool)):
                        visible_values.add(v)
            for f in self.active_filters.keys():
                if f not in self.current_headers:
                    self.current_headers.append(f)

            self.search_widget.set_fields(list(self.schema_keys))
            self.table.setColumnCount(len(self.current_headers))
            self.table.setHorizontalHeaderLabels(self.current_headers)
            self.table.setRowCount(len(docs))

            start_index = self.page * self.page_size + 1
            for r, d in enumerate(docs):
                self.table.setVerticalHeaderItem(
                    r, QTableWidgetItem(str(start_index + r))
                )
                doc_id = d.get("_id")
                for c, h in enumerate(self.current_headers):
                    val = d.get(h, "")
                    if isinstance(val, (dict, list)):
                        val = json_util.dumps(val)
                    if isinstance(val, ObjectId):
                        val = str(val)
                    item = QTableWidgetItem(str(val))
                    item.setToolTip(str(val))
                    if c == 0:
                        item.setData(Qt.UserRole, doc_id)

                    if h.lower().endswith("id") and h != "_id":
                        item.setForeground(QBrush(QColor("#0d6efd")))
                        font = QFont()
                        font.setUnderline(True)
                        item.setFont(font)
                        item.setToolTip(f"Double-click to find in related collection")

                    self.table.setItem(r, c, item)
        except Exception as e:
            print(f"Query Error: {e}, full error: {getattr(e, 'details', 'N/A')}")

    def scan_schema_keys(self):
        if self.collection is None:
            return
        try:
            pipeline = [{"$sample": {"size": 20}}]
            samples = list(self.collection.aggregate(pipeline))
            self.schema_keys = set()
            for doc in samples:
                self.schema_keys.update(doc.keys())
            self.search_widget.set_fields(list(self.schema_keys))
        except Exception as e:
            print(f"Schema scan warning: {e}")

    def clear_all_filters(self):
        self.page = 0
        self.active_filters = {}
        self.current_sort = None
        self.search_widget.value_input.clear()
        self.load_data()

    def reset_and_load(self):
        self.page = 0
        self.load_data()

    def next_page(self):
        self.page += 1
        self.load_data()

    def prev_page(self):
        if self.page > 0:
            self.page -= 1
            self.load_data()
