import json
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QLabel,
    QTextEdit,
    QDialogButtonBox,
    QMessageBox,
)
from PySide6.QtGui import QFont
from bson import json_util


class SchemaDialog(QDialog):
    def __init__(self, collection, parent=None):
        super().__init__(parent)
        self.collection = collection
        self.setWindowTitle(f"Schema Validation: {collection.name}")
        self.resize(600, 500)
        self.layout = QVBoxLayout(self)

        self.info = QLabel(
            "Define validation rules using MongoDB JSON Schema syntax.\nLeave empty to disable validation."
        )
        self.info.setStyleSheet("color: gray;")
        self.layout.addWidget(self.info)

        self.editor = QTextEdit()
        self.editor.setFont(QFont("Consolas", 10))
        self.layout.addWidget(self.editor)

        self.load_current_schema()

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.save_schema)
        buttons.rejected.connect(self.reject)
        self.layout.addWidget(buttons)

    def load_current_schema(self):
        try:
            # Fetch collection info to get current options
            info = self.collection.database.list_collections(
                filter={"name": self.collection.name}
            )
            data = list(info)
            if data:
                options = data[0].get("options", {})
                validator = options.get("validator", {})
                if validator:
                    text = json.dumps(validator, indent=4, default=json_util.default)
                    self.editor.setText(text)
                else:
                    self.editor.setText("{}")
        except Exception as e:
            self.editor.setText(f"// Error fetching schema: {e}")

    def save_schema(self):
        raw_text = self.editor.toPlainText().strip()
        if not raw_text:
            validator = {}
        else:
            try:
                validator = json.loads(raw_text, object_hook=json_util.object_hook)
            except json.JSONDecodeError as e:
                return QMessageBox.warning(
                    self, "Invalid JSON", f"Schema JSON is invalid:\n{e}"
                )

        try:
            # Use collMod to update validator
            cmd = {"collMod": self.collection.name, "validator": validator}

            # If disabling (empty dict), we might need validationLevel='off' or just empty
            if not validator:
                cmd["validationLevel"] = "off"
            else:
                cmd["validationLevel"] = "strict"
                cmd["validationAction"] = "error"

            self.collection.database.command(cmd)
            QMessageBox.information(
                self, "Success", "Validation rules updated successfully."
            )
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to update schema: {e}")
