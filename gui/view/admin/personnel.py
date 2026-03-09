import logging

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel
)

from utils.logger import LoggerMixin

class PersonnelContent(QWidget, LoggerMixin):
    
    log: logging.Logger
    
    def __init__(self):
        
        super().__init__()
        
        layout = QVBoxLayout(self)
        
        layout.addWidget(QLabel("This feature is currently unavailable!"))

        self.setLayout(layout)