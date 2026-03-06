from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QCheckBox, QDialogButtonBox, QLineEdit, QDateEdit, QGroupBox
from PySide6.QtGui import QIntValidator
from PySide6.QtCore import QDate

class ExportDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Export Settings")
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Select Format:"))
        self.combo = QComboBox()
        self.combo.addItems(["json", "sql", "postgresql", "csv", "bson"])
        self.combo.currentIndexChanged.connect(self.update_ui_state)
        layout.addWidget(self.combo)

        # New: Encoding Selection
        layout.addWidget(QLabel("File Encoding:"))
        self.encoding_combo = QComboBox()
        self.encoding_combo.addItems(["utf-8", "ascii"])
        layout.addWidget(self.encoding_combo)

        # New: PostgreSQL Version Selection
        self.pg_ver_label = QLabel("PostgreSQL Version:")
        layout.addWidget(self.pg_ver_label)
        self.pg_ver_combo = QComboBox()
        self.pg_ver_combo.addItems(["18", "17", "16", "15", "14"])
        layout.addWidget(self.pg_ver_combo)

        # New: Export Limit Selection
        layout.addWidget(QLabel("Row Limit (0 for all):"))
        self.limit_input = QLineEdit()
        self.limit_input.setText("0")
        self.limit_input.setValidator(QIntValidator(0, 999999999))
        self.limit_input.setToolTip("Maximum number of documents to export per collection")
        layout.addWidget(self.limit_input)

        # New: Date Range Filter (By ObjectId Generation Time)
        date_group = QGroupBox("Date Range Filter (Optional, relies on _id)")
        date_layout = QVBoxLayout()
        
        self.enable_date_check = QCheckBox("Enable Date Filter")
        date_layout.addWidget(self.enable_date_check)
        
        hbox = QHBoxLayout()
        self.from_date = QDateEdit()
        self.from_date.setCalendarPopup(True)
        self.from_date.setDate(QDate.currentDate().addDays(-30))
        self.from_date.setEnabled(False)
        
        self.to_date = QDateEdit()
        self.to_date.setCalendarPopup(True)
        self.to_date.setDate(QDate.currentDate())
        self.to_date.setEnabled(False)
        
        hbox.addWidget(QLabel("From:"))
        hbox.addWidget(self.from_date)
        hbox.addWidget(QLabel("To:"))
        hbox.addWidget(self.to_date)
        
        date_layout.addLayout(hbox)
        date_group.setLayout(date_layout)
        layout.addWidget(date_group)
        
        self.enable_date_check.toggled.connect(self.toggle_dates)

        # New: Single File Checkbox
        self.single_file_check = QCheckBox("Export as Single SQL File")
        self.single_file_check.setChecked(True) # Default to true for SQL
        layout.addWidget(self.single_file_check)

        self.meta_check = QCheckBox("Export Metadata (_id, __v)")
        self.meta_check.setChecked(False) 
        layout.addWidget(self.meta_check)

        self.pk_check = QCheckBox("Add Primary Key (id)")
        self.pk_check.setChecked(False)
        self.pk_check.setToolTip("Adds an auto-incrementing 'id' column")
        layout.addWidget(self.pk_check)

        self.json_check = QCheckBox("Store nested objects as JSON")
        self.json_check.setChecked(False)
        self.json_check.setToolTip("Serializes dict/list fields to JSON strings")
        layout.addWidget(self.json_check)

        self.flatten_check = QCheckBox("Flatten Nested JSON to Columns")
        self.flatten_check.setChecked(False)
        self.flatten_check.setToolTip("Converts nested dict properties into separate top-level columns (e.g., gnssInfo_speed)")
        layout.addWidget(self.flatten_check)

        self.normalize_check = QCheckBox("Normalize Names & Types (SQL/PostgreSQL)")
        self.normalize_check.setChecked(False)
        self.normalize_check.setToolTip("Exports a second normalized file with standard types")
        layout.addWidget(self.normalize_check)

        # New: Naming Convention Selection
        self.naming_label = QLabel("Naming Convention:")
        self.naming_combo = QComboBox()
        self.naming_combo.addItems(["snake_case", "camelCase"])
        self.naming_label.setVisible(False)
        self.naming_combo.setVisible(False)
        
        naming_layout = QHBoxLayout()
        naming_layout.addWidget(self.naming_label)
        naming_layout.addWidget(self.naming_combo)
        layout.addLayout(naming_layout)

        self.normalize_check.toggled.connect(self.toggle_naming_options)

        self.buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)

        self.update_ui_state() # Init state

    def toggle_dates(self, checked):
        self.from_date.setEnabled(checked)
        self.to_date.setEnabled(checked)

    def toggle_naming_options(self, checked):
        self.naming_label.setVisible(checked)
        self.naming_combo.setVisible(checked)

    def update_ui_state(self):
        fmt = self.combo.currentText()
        is_sql = fmt in ["sql", "postgresql"]
        is_pg = fmt == "postgresql"

        self.single_file_check.setEnabled(is_sql)
        if not is_sql:
            self.single_file_check.setChecked(False)
        
        self.pk_check.setEnabled(is_sql)
        self.json_check.setEnabled(is_sql)
        self.flatten_check.setEnabled(is_sql)
        self.normalize_check.setEnabled(is_sql)
        if not is_sql:
            self.pk_check.setChecked(False)
            self.json_check.setChecked(False)
            self.flatten_check.setChecked(False)
            self.normalize_check.setChecked(False)

        # Toggle mutual exclusion between Store JSON and Flatten JSON

        # PostgreSQL specifics
        self.pg_ver_label.setVisible(is_pg)
        self.pg_ver_combo.setVisible(is_pg)

        # Toggle dependent visibility
        if not is_sql:
            self.naming_label.setVisible(False)
            self.naming_combo.setVisible(False)
        else:
            self.naming_label.setVisible(self.normalize_check.isChecked())
            self.naming_combo.setVisible(self.normalize_check.isChecked())

    def get_settings(self):
        try:
            limit = int(self.limit_input.text())
        except ValueError:
            limit = 0

        date_range = None
        if self.enable_date_check.isChecked():
            from_dt = self.from_date.date().toPython()
            to_dt = self.to_date.date().toPython()
            date_range = (from_dt, to_dt)

        return (
            self.combo.currentText(), 
            self.meta_check.isChecked(), 
            self.single_file_check.isChecked(),
            self.pk_check.isChecked(),
            self.json_check.isChecked(),
            self.flatten_check.isChecked(),
            self.normalize_check.isChecked(),
            self.naming_combo.currentText() if self.normalize_check.isChecked() else None,
            self.pg_ver_combo.currentText() if self.combo.currentText() == "postgresql" else None,
            self.encoding_combo.currentText(),
            limit,
            date_range
        )