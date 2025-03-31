from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel
from dashboard import DashboardWindow
from database import Database


class AuthWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Authentication")
        self.setGeometry(200, 200, 300, 100)
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Authentication stub - proceeding to dashboard"))
        self.setLayout(layout)
        # Simulate login success
        self.db = Database(email="user@example.com")
        self.dashboard = DashboardWindow(self.db, "user@example.com")
        self.dashboard.show()
        self.hide()