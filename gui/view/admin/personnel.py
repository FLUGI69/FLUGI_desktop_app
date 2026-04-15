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
        
        layout.addWidget(QLabel("Ez a funkció jelenleg még nem elérhető!"))

        self.setLayout(layout)