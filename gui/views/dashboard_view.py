from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QFrame,
    QGridLayout,
)
from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QFont, QColor


class MetricCard(QFrame):
    def __init__(self, title, color="#0d6efd", parent=None):
        super().__init__(parent)
        self.setStyleSheet(
            f"background-color: white; border: 1px solid #dee2e6; border-radius: 8px; border-left: 5px solid {color};"
        )
        layout = QVBoxLayout(self)

        lbl_title = QLabel(title)
        lbl_title.setStyleSheet("color: gray; font-weight: bold; border: none;")
        layout.addWidget(lbl_title)

        self.lbl_value = QLabel("0")
        self.lbl_value.setFont(QFont("Arial", 24, QFont.Bold))
        self.lbl_value.setStyleSheet("border: none;")
        layout.addWidget(self.lbl_value)

    def set_value(self, val):
        self.lbl_value.setText(str(val))


class DashboardView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.db = None
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(20, 20, 20, 20)

        # --- Header ---
        header = QLabel("Server Status (Real-time)")
        header.setFont(QFont("Arial", 16, QFont.Bold))
        self.layout.addWidget(header)

        # --- Row 1: Key Metrics ---
        grid = QGridLayout()
        self.card_conns = MetricCard("Active Connections", "#198754")
        self.card_mem = MetricCard("Memory (MB)", "#0dcaf0")
        self.card_ops = MetricCard("Ops / Sec", "#ffc107")
        self.card_uptime = MetricCard("Uptime (Hours)", "#6c757d")

        grid.addWidget(self.card_conns, 0, 0)
        grid.addWidget(self.card_mem, 0, 1)
        grid.addWidget(self.card_ops, 0, 2)
        grid.addWidget(self.card_uptime, 0, 3)
        self.layout.addLayout(grid)

        # --- Row 2: Capacity Bars ---
        self.layout.addSpacing(20)

        # Connection Capacity
        self.conn_lbl = QLabel("Connection Pool Usage:")
        self.layout.addWidget(self.conn_lbl)
        self.conn_bar = QProgressBar()
        self.conn_bar.setStyleSheet(
            "QProgressBar::chunk { background-color: #198754; }"
        )
        self.layout.addWidget(self.conn_bar)

        self.layout.addSpacing(10)

        # Network Info
        self.info_lbl = QLabel("Waiting for data...")
        self.info_lbl.setStyleSheet("color: gray; font-family: Consolas;")
        self.layout.addWidget(self.info_lbl)

        self.layout.addStretch()

        # --- Timer ---
        self.timer = QTimer()
        self.timer.timeout.connect(self.refresh_stats)

        self.last_ops_total = 0
        self.last_check_time = 0

    def set_db(self, db):
        self.db = db
        # --- CRITICAL FIX: Explicit check against None ---
        if self.db is not None:
            self.timer.start(2000)  # Refresh every 2s
            self.refresh_stats()
        else:
            self.timer.stop()

    def refresh_stats(self):
        # --- CRITICAL FIX: Explicit check against None ---
        if self.db is None:
            return

        try:
            status = self.db.command("serverStatus")

            # 1. Connections
            conns = status.get("connections", {})
            curr = conns.get("current", 0)
            avail = conns.get("available", 1)
            total = curr + avail
            self.card_conns.set_value(curr)
            self.conn_bar.setMaximum(total)
            self.conn_bar.setValue(curr)
            self.conn_lbl.setText(f"Connection Pool: {curr} / {total}")

            # 2. Memory
            mem = status.get("mem", {})
            resident = mem.get("resident", 0)
            self.card_mem.set_value(resident)

            # 3. Ops Per Sec (Rough Calc)
            opcounters = status.get("opcounters", {})
            total_ops = sum(opcounters.values())

            if self.last_ops_total > 0:
                diff = total_ops - self.last_ops_total
                self.card_ops.set_value(int(diff / 2))

            self.last_ops_total = total_ops

            # 4. Uptime
            uptime = status.get("uptime", 0)
            hours = int(uptime / 3600)
            self.card_uptime.set_value(hours)

            # 5. Info
            version = status.get("version", "Unknown")
            process = status.get("process", "mongod")
            host = status.get("host", "Unknown")
            self.info_lbl.setText(
                f"Process: {process} | Version: {version} | Host: {host}"
            )

        except Exception as e:
            self.info_lbl.setText(f"Error fetching stats: {e}")
            self.timer.stop()
