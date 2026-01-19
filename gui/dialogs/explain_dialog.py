import json
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QTextEdit, QDialogButtonBox, QFrame
)
from PySide6.QtGui import QFont, QColor
from bson import json_util

class ExplainDialog(QDialog):
    def __init__(self, explain_data, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Query Performance Analysis (Explain Plan)")
        self.resize(700, 600)
        layout = QVBoxLayout(self)

        # --- 1. Summary Dashboard ---
        stats = self._extract_stats(explain_data)
        
        summary_frame = QFrame()
        summary_frame.setStyleSheet("background-color: #f8f9fa; border: 1px solid #dee2e6; border-radius: 5px;")
        vbox = QVBoxLayout(summary_frame)
        
        # Title
        title = QLabel(f"Query Strategy: <b>{stats['stage']}</b>")
        title.setFont(QFont("Arial", 12))
        vbox.addWidget(title)
        
        # Metrics
        metrics = QLabel(
            f"Documents Returned: <b>{stats['nReturned']}</b><br>"
            f"Documents Scanned: <b>{stats['totalDocsExamined']}</b><br>"
            f"Execution Time: <b>{stats['executionTimeMillis']} ms</b>"
        )
        vbox.addWidget(metrics)
        
        # Health Check / Advice
        health_color = "green"
        health_msg = "Query looks healthy."
        
        # Logic: If scanned 100x more docs than returned, it's inefficient
        if stats['nReturned'] > 0:
            ratio = stats['totalDocsExamined'] / stats['nReturned']
            if ratio > 100:
                health_color = "orange"
                health_msg = "Warning: Database is scanning many documents to find results. Consider an Index."
            if ratio > 1000:
                health_color = "red"
                health_msg = "CRITICAL: Highly inefficient query! Full Collection Scan detected?"
        elif stats['totalDocsExamined'] > 1000:
             health_color = "red"
             health_msg = "CRITICAL: Scanned over 1000 docs but returned NONE."

        health_lbl = QLabel(health_msg)
        health_lbl.setStyleSheet(f"color: {health_color}; font-weight: bold; font-size: 13px;")
        vbox.addWidget(health_lbl)
        
        layout.addWidget(summary_frame)

        # --- 2. Raw JSON View ---
        layout.addWidget(QLabel("Raw JSON Output:"))
        self.text_area = QTextEdit()
        self.text_area.setFont(QFont("Consolas", 10))
        self.text_area.setReadOnly(True)
        self.text_area.setText(json.dumps(explain_data, indent=4, default=json_util.default))
        layout.addWidget(self.text_area)

        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self.accept)
        layout.addWidget(buttons)

    def _extract_stats(self, data):
        """Safely extract execution stats regardless of mongo version structure"""
        # Default fallback
        result = {
            'nReturned': 0,
            'totalDocsExamined': 0,
            'executionTimeMillis': 0,
            'stage': 'UNKNOWN'
        }
        
        try:
            # Structure usually: executionStats -> nReturned
            exec_stats = data.get('executionStats', {})
            result['nReturned'] = exec_stats.get('nReturned', 0)
            result['totalDocsExamined'] = exec_stats.get('totalDocsExamined', 0)
            result['executionTimeMillis'] = exec_stats.get('executionTimeMillis', 0)
            
            # Find winning plan stage (COLLSCAN vs IXSCAN)
            plan = data.get('queryPlanner', {}).get('winningPlan', {})
            result['stage'] = plan.get('stage', 'UNKNOWN')
            
            # Sometimes stage is nested in inputStage
            if result['stage'] == 'FETCH' and 'inputStage' in plan:
                result['stage'] += f" -> {plan['inputStage'].get('stage', '')}"
                
        except Exception:
            pass
            
        return result