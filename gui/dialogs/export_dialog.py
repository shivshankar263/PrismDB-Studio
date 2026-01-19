from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QComboBox, QCheckBox, QDialogButtonBox

class ExportDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Export Settings")
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Select Format:"))
        self.combo = QComboBox()
        self.combo.addItems(["json", "sql", "csv", "bson"])
        layout.addWidget(self.combo)

        self.meta_check = QCheckBox("Export Metadata (_id, __v)")
        self.meta_check.setChecked(False) 
        layout.addWidget(self.meta_check)

        self.buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)

    def get_settings(self):
        return self.combo.currentText(), self.meta_check.isChecked()