"""Dialogue de création de to-do - stub."""
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel

class TodoDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Nouvelle To-do")
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Dialogue de to-do - En développement"))
