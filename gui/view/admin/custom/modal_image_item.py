import logging

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QSizePolicy
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap

from config import Config
from utils.logger import LoggerMixin

class ImageItemWidget(QWidget,LoggerMixin):
    
    log: logging.Logger
    
    def __init__(self, 
        image: bytes,
        parent = None
        ):
        
        super().__init__(parent)
        
        layout = QVBoxLayout(self)
        
        layout.setContentsMargins(5, 5, 5, 5)
        
        pixmap = QPixmap()
        
        success: bool = pixmap.loadFromData(image)
        
        if success is False:
            
            self.log.warning("Invalid image bytes")
            
            return
            
        image_label = QLabel()
        image_label.setStyleSheet(Config.styleSheets.label)
        image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        image_label.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding
        )
        
        image_label.setPixmap(
            pixmap.scaled(
                550, 550,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
        )
        
        image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(image_label)