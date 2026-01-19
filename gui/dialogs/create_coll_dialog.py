import json
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QLineEdit, QCheckBox, 
    QSpinBox, QDialogButtonBox, QTabWidget, QWidget, QFormLayout, QTextEdit, QMessageBox
)
from PySide6.QtGui import QFont

class CreateCollectionDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Create New Collection")
        self.resize(500, 550)
        
        self.layout = QVBoxLayout(self)
        
        # --- Basic Info ---
        form = QFormLayout()
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("e.g., users_v2")
        form.addRow("Collection Name:", self.name_input)
        self.layout.addLayout(form)
        
        # --- Advanced Options Tabs ---
        self.tabs = QTabWidget()
        
        # Tab 1: Configuration (Capped)
        self.config_tab = QWidget()
        config_layout = QVBoxLayout(self.config_tab)
        
        self.capped_check = QCheckBox("Capped Collection (Fixed Size)")
        self.capped_check.toggled.connect(self.toggle_capped_options)
        
        self.size_spin = QSpinBox()
        self.size_spin.setRange(0, 2147483647) # 2GB limit for spinbox visual, mongo goes higher
        self.size_spin.setSuffix(" bytes")
        self.size_spin.setValue(1024 * 1024) # 1MB Default
        self.size_spin.setEnabled(False)
        
        self.max_docs_spin = QSpinBox()
        self.max_docs_spin.setRange(0, 2147483647)
        self.max_docs_spin.setSuffix(" docs")
        self.max_docs_spin.setEnabled(False)
        
        config_form = QFormLayout()
        config_form.addRow(self.capped_check)
        config_form.addRow("Max Size (bytes):", self.size_spin)
        config_form.addRow("Max Documents:", self.max_docs_spin)
        
        # Description
        desc_lbl = QLabel("Capped collections overwrite old data when they reach the size limit.\nGreat for logs and high-speed buffers.")
        desc_lbl.setStyleSheet("color: gray; font-size: 11px;")
        config_layout.addLayout(config_form)
        config_layout.addWidget(desc_lbl)
        config_layout.addStretch()
        
        # Tab 2: Validation (Schema)
        self.valid_tab = QWidget()
        valid_layout = QVBoxLayout(self.valid_tab)
        
        valid_layout.addWidget(QLabel("Validation Rules (JSON Schema):"))
        self.validator_edit = QTextEdit()
        self.validator_edit.setFont(QFont("Consolas", 10))
        self.validator_edit.setPlaceholderText('{\n  "$jsonSchema": {\n    "required": ["name", "email"],\n    "properties": { ... }\n  }\n}')
        valid_layout.addWidget(self.validator_edit)
        
        self.tabs.addTab(self.config_tab, "Configuration")
        self.tabs.addTab(self.valid_tab, "Validator")
        
        self.layout.addWidget(self.tabs)

        # --- Buttons ---
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.validate_and_accept)
        buttons.rejected.connect(self.reject)
        self.layout.addWidget(buttons)
        
        self.collection_data = {}

    def toggle_capped_options(self, checked):
        self.size_spin.setEnabled(checked)
        self.max_docs_spin.setEnabled(checked)

    def validate_and_accept(self):
        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Error", "Collection name is required.")
            return

        options = {'name': name}
        
        # Handle Capped
        if self.capped_check.isChecked():
            options['capped'] = True
            options['size'] = self.size_spin.value()
            if self.max_docs_spin.value() > 0:
                options['max'] = self.max_docs_spin.value()
        
        # Handle Validator
        validator_txt = self.validator_edit.toPlainText().strip()
        if validator_txt:
            try:
                options['validator'] = json.loads(validator_txt)
            except json.JSONDecodeError as e:
                QMessageBox.warning(self, "Invalid JSON", f"Validator JSON is invalid:\n{e}")
                return

        self.collection_data = options
        self.accept()

    def get_data(self):
        return self.collection_data