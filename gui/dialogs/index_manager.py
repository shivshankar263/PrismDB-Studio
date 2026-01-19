from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem, 
    QPushButton, QLabel, QHeaderView, QMessageBox, QInputDialog, QComboBox, QCheckBox, QDialogButtonBox
)
from PySide6.QtCore import Qt

class CreateIndexDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Create New Index")
        self.layout = QVBoxLayout(self)
        
        self.layout.addWidget(QLabel("Field Name (e.g., email or address.zip):"))
        self.field_input = QInputDialog() 
        self.field_input.setInputMode(QInputDialog.TextInput)
        self.field_input.setLabelText("Field:")
        
        # Since QInputDialog is complex to embed, let's build a simple form
        # Re-doing layout for simple form
        while self.layout.count():
            item = self.layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()

        self.layout.addWidget(QLabel("Field Name:"))
        self.field_edit = QComboBox()
        self.field_edit.setEditable(True) 
        self.layout.addWidget(self.field_edit)
        
        self.layout.addWidget(QLabel("Order:"))
        self.order_combo = QComboBox()
        self.order_combo.addItems(["Ascending (1)", "Descending (-1)"])
        self.layout.addWidget(self.order_combo)
        
        self.unique_check = QCheckBox("Unique (Prevent Duplicates)")
        self.layout.addWidget(self.unique_check)
        
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        self.layout.addWidget(buttons)

    def get_data(self):
        field = self.field_edit.currentText().strip()
        direction = 1 if self.order_combo.currentIndex() == 0 else -1
        unique = self.unique_check.isChecked()
        return field, direction, unique

class IndexManagerDialog(QDialog):
    def __init__(self, collection, parent=None):
        super().__init__(parent)
        self.collection = collection
        self.setWindowTitle(f"Index Manager: {collection.name}")
        self.resize(600, 400)
        self.layout = QVBoxLayout(self)
        
        # Toolbar
        toolbar = QHBoxLayout()
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self.load_indexes)
        
        self.add_btn = QPushButton("+ Create Index")
        self.add_btn.setStyleSheet("color: green; font-weight: bold;")
        self.add_btn.clicked.connect(self.create_index)
        
        self.drop_btn = QPushButton("- Drop Selected")
        self.drop_btn.setStyleSheet("color: red;")
        self.drop_btn.clicked.connect(self.drop_index)
        
        toolbar.addWidget(self.refresh_btn)
        toolbar.addStretch()
        toolbar.addWidget(self.add_btn)
        toolbar.addWidget(self.drop_btn)
        self.layout.addLayout(toolbar)
        
        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Name", "Key(s)", "Unique", "Size"])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.layout.addWidget(self.table)
        
        self.load_indexes()

    def load_indexes(self):
        self.table.setRowCount(0)
        try:
            indexes = list(self.collection.list_indexes())
            self.table.setRowCount(len(indexes))
            
            for r, idx in enumerate(indexes):
                # Name
                self.table.setItem(r, 0, QTableWidgetItem(str(idx.get('name'))))
                
                # Key (Convert dict to string like "email: 1")
                key_dict = idx.get('key', {})
                key_str = ", ".join([f"{k}: {v}" for k, v in key_dict.items()])
                self.table.setItem(r, 1, QTableWidgetItem(key_str))
                
                # Unique
                is_unique = str(idx.get('unique', False))
                self.table.setItem(r, 2, QTableWidgetItem(is_unique))
                
                # Size (Not always available in basic list_indexes, requires stats)
                self.table.setItem(r, 3, QTableWidgetItem("-"))
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load indexes: {e}")

    def create_index(self):
        dlg = CreateIndexDialog(self)
        # Pre-fill some fields based on one document to help user
        try:
            sample = self.collection.find_one()
            if sample:
                dlg.field_edit.addItems(list(sample.keys()))
        except: pass
        
        if dlg.exec():
            field, direction, unique = dlg.get_data()
            if not field: return
            
            try:
                self.collection.create_index([(field, direction)], unique=unique)
                QMessageBox.information(self, "Success", f"Index on '{field}' created.")
                self.load_indexes()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to create index: {e}")

    def drop_index(self):
        row = self.table.currentRow()
        if row < 0: return QMessageBox.warning(self, "Select Index", "Please select an index to drop.")
        
        index_name = self.table.item(row, 0).text()
        if index_name == "_id_":
            return QMessageBox.warning(self, "Restricted", "Cannot drop the default _id_ index.")
            
        reply = QMessageBox.question(self, "Confirm Drop", f"Delete index '{index_name}'?", QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            try:
                self.collection.drop_index(index_name)
                self.load_indexes()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to drop index: {e}")