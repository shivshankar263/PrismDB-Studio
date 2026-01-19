import json
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QTextEdit, 
    QPushButton, QSplitter, QLabel, QTableWidget, QTableWidgetItem, QMessageBox,
    QHeaderView, QComboBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor
from bson import json_util, ObjectId

class AggregationView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.collection = None
        self.layout = QVBoxLayout(self)
        
        # --- Toolbar ---
        toolbar = QHBoxLayout()
        self.stage_combo = QComboBox()
        self.stage_combo.addItems(["$match", "$group", "$project", "$sort", "$limit", "$skip", "$lookup", "$unwind", "$count"])
        
        add_btn = QPushButton("+ Add Stage")
        add_btn.clicked.connect(self.add_stage)
        
        self.run_btn = QPushButton("Run Pipeline")
        self.run_btn.setStyleSheet("background-color: #0d6efd; color: white; font-weight: bold;")
        self.run_btn.clicked.connect(self.run_pipeline)
        
        clear_btn = QPushButton("Clear All")
        clear_btn.clicked.connect(self.clear_stages)
        
        toolbar.addWidget(QLabel("Stage:"))
        toolbar.addWidget(self.stage_combo)
        toolbar.addWidget(add_btn)
        toolbar.addStretch()
        toolbar.addWidget(clear_btn)
        toolbar.addWidget(self.run_btn)
        self.layout.addLayout(toolbar)
        
        # --- Main Splitter ---
        splitter = QSplitter(Qt.Horizontal)
        
        # Left: Stages List
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0,0,0,0)
        left_layout.addWidget(QLabel("<b>Pipeline Stages</b>"))
        self.stage_list = QListWidget()
        self.stage_list.currentRowChanged.connect(self.load_stage_json)
        
        # Remove Stage Button
        del_stage_btn = QPushButton("Remove Selected Stage")
        del_stage_btn.setStyleSheet("color: red;")
        del_stage_btn.clicked.connect(self.remove_stage)
        
        left_layout.addWidget(self.stage_list)
        left_layout.addWidget(del_stage_btn)
        splitter.addWidget(left_widget)
        
        # Center: JSON Editor
        center_widget = QWidget()
        center_layout = QVBoxLayout(center_widget)
        center_layout.setContentsMargins(0,0,0,0)
        center_layout.addWidget(QLabel("<b>Stage JSON</b>"))
        self.json_edit = QTextEdit()
        self.json_edit.setFont(QFont("Consolas", 10))
        self.json_edit.textChanged.connect(self.save_current_stage)
        center_layout.addWidget(self.json_edit)
        splitter.addWidget(center_widget)
        
        # Right: Preview Result
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0,0,0,0)
        right_layout.addWidget(QLabel("<b>Result Preview (First 20)</b>"))
        self.result_table = QTableWidget()
        right_layout.addWidget(self.result_table)
        splitter.addWidget(right_widget)
        
        splitter.setSizes([200, 300, 500])
        self.layout.addWidget(splitter)
        
        # Data
        self.pipeline_data = [] # List of dicts: {'type': '$match', 'json': '{}'}

    def set_collection(self, collection):
        self.collection = collection
        self.clear_stages()

    def add_stage(self):
        stage_type = self.stage_combo.currentText()
        
        # Default Templates
        default_json = "{}"
        if stage_type == "$match": default_json = '{\n  "status": "active"\n}'
        elif stage_type == "$group": default_json = '{\n  "_id": "$field",\n  "count": { "$sum": 1 }\n}'
        elif stage_type == "$project": default_json = '{\n  "name": 1,\n  "_id": 0\n}'
        elif stage_type == "$sort": default_json = '{\n  "created_at": -1\n}'
        elif stage_type == "$limit": default_json = '20' 
        
        self.pipeline_data.append({'type': stage_type, 'json': default_json})
        self.stage_list.addItem(f"{len(self.pipeline_data)}. {stage_type}")
        self.stage_list.setCurrentRow(len(self.pipeline_data) - 1)

    def remove_stage(self):
        row = self.stage_list.currentRow()
        if row >= 0:
            self.pipeline_data.pop(row)
            self.stage_list.takeItem(row)
            if self.pipeline_data:
                self.stage_list.setCurrentRow(max(0, row-1))
            else:
                self.json_edit.clear()

    def clear_stages(self):
        self.pipeline_data = []
        self.stage_list.clear()
        self.json_edit.clear()
        self.result_table.clear()
        self.result_table.setRowCount(0)

    def load_stage_json(self, row):
        if row >= 0 and row < len(self.pipeline_data):
            self.json_edit.blockSignals(True)
            self.json_edit.setText(self.pipeline_data[row]['json'])
            self.json_edit.blockSignals(False)

    def save_current_stage(self):
        row = self.stage_list.currentRow()
        if row >= 0:
            self.pipeline_data[row]['json'] = self.json_edit.toPlainText()

    def run_pipeline(self):
        if self.collection is None: return
        
        # Build Pipeline
        pipeline = []
        try:
            for item in self.pipeline_data:
                stage_key = item['type']
                stage_content_str = item['json']
                
                # Parse JSON
                try:
                    content = json.loads(stage_content_str, object_hook=json_util.object_hook)
                except json.JSONDecodeError:
                    # Allow simple integers for $limit/$skip
                    if stage_key in ["$limit", "$skip", "$count"] and stage_content_str.strip().isdigit():
                         content = int(stage_content_str.strip())
                    else:
                        raise Exception(f"Invalid JSON in {stage_key}")
                
                pipeline.append({stage_key: content})
                
            # Run
            results = list(self.collection.aggregate(pipeline + [{"$limit": 20}])) 
            self.render_table(results)
            
        except Exception as e:
            QMessageBox.critical(self, "Pipeline Error", str(e))

    def render_table(self, docs):
        self.result_table.clear()
        if not docs:
            self.result_table.setRowCount(0)
            return

        headers = []
        for d in docs:
            for k in d.keys():
                if k not in headers: headers.append(k)
        
        self.result_table.setColumnCount(len(headers))
        self.result_table.setHorizontalHeaderLabels(headers)
        self.result_table.setRowCount(len(docs))
        
        for r, d in enumerate(docs):
            for c, h in enumerate(headers):
                val = d.get(h, "")
                if isinstance(val, (dict, list)): val = json_util.dumps(val)
                self.result_table.setItem(r, c, QTableWidgetItem(str(val)))