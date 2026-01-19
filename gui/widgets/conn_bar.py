from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLineEdit, QPushButton, 
    QLabel, QMessageBox, QSizePolicy
)
from config.settings import DEFAULT_URI

class ConnectionBar(QFrame):
    def __init__(self, parent=None, on_connect=None, on_disconnect=None):
        super().__init__(parent)
        self.setObjectName("ConnPanel")
        
        # FIX 1: Force height to match content (prevents stretching)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        
        self.layout = QHBoxLayout(self)
        
        # FIX 2: Reduce internal margins (Left, Top, Right, Bottom)
        # Reduced Top/Bottom from default ~11px to 2px
        self.layout.setContentsMargins(10, 2, 10, 2)
        
        self.on_connect_callback = on_connect
        self.on_disconnect_callback = on_disconnect
        self.is_connected = False
        
        self.uri_input = QLineEdit()
        self.uri_input.setPlaceholderText("mongodb://localhost:27017/my_database")
        self.uri_input.setText(DEFAULT_URI)
        
        self.conn_btn = QPushButton("Connect")
        self.conn_btn.setObjectName("Primary")
        self.conn_btn.clicked.connect(self.handle_click)
        
        self.layout.addWidget(QLabel("Connection URI:"))
        self.layout.addWidget(self.uri_input)
        self.layout.addWidget(self.conn_btn)

    def handle_click(self):
        if self.is_connected:
            # Handle Disconnect
            if self.on_disconnect_callback:
                self.on_disconnect_callback()
            self.set_disconnected_state()
        else:
            # Handle Connect
            uri = self.uri_input.text().strip()
            if not uri: return
            
            # Visual Feedback: "Connecting..."
            self.conn_btn.setText("Connecting...")
            self.conn_btn.setEnabled(False) 
            self.uri_input.setEnabled(False)
            
            # Allow UI to redraw briefly before blocking logic runs
            from PySide6.QtWidgets import QApplication
            QApplication.processEvents()
            
            if self.on_connect_callback:
                success = self.on_connect_callback(uri)
                if success:
                    self.set_connected_state()
                else:
                    self.set_disconnected_state()

    def set_connected_state(self):
        self.is_connected = True
        self.conn_btn.setText("Disconnect")
        self.conn_btn.setEnabled(True)
        self.conn_btn.setStyleSheet("background-color: #dc3545; color: white; border: none;") # Red color
        self.uri_input.setEnabled(False)

    def set_disconnected_state(self):
        self.is_connected = False
        self.conn_btn.setText("Connect")
        self.conn_btn.setEnabled(True)
        self.conn_btn.setStyleSheet("") # Reset to default style
        self.conn_btn.setObjectName("Primary")
        self.uri_input.setEnabled(True)