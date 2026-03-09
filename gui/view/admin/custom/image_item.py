import logging
import typing as t
import os

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QPushButton,
    QLabel,
    QSizePolicy
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QPixmap, QIcon

from utils.logger import LoggerMixin
from config import Config

if t.TYPE_CHECKING:
    
    from ..works.add_work import AdminAddWorkContent
    from ..works.edit_work import AdminEditWorkContent

class ImageItemWidget(QWidget,LoggerMixin):
    
    log: logging.Logger
    
    def __init__(self, 
        image: t.Union[str, bytes],
        parent: t.Union['AdminAddWorkContent', 'AdminEditWorkContent'],
        image_id: int | None = None
        ):
        
        super().__init__(parent)
        
        assert parent is not None, "ImageItemWidget requires a parent widget"
        
        self.file_path: t.Optional[str] = None
        
        self.image_id: t.Optional[int] = None
        
        self.parent_widget = parent

        layout = QVBoxLayout(self)
        
        layout.setContentsMargins(5, 5, 5, 5)
        
        # layout.setSpacing(5)
        
        pixmap = QPixmap()

        if isinstance(image, str):
            
            self.file_path = image
            
            success: bool = pixmap.load(image)
            
            if success is False:
                
                self.log.warning("Invalid image: %s", image)
                
                return
            
        elif isinstance(image, bytes):
            
            if image_id is not None:
                
                self.image_id = image_id
    
            success: bool = pixmap.loadFromData(image)
            
            if success is False:
                
                self.log.warning("Invalid image bytes")
                
                return

        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding
        )
        
        self.image_label.setPixmap(
            pixmap.scaled(
                400, 400,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
        )
        
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.delete_button = QPushButton()
        self.delete_button.setObjectName("TrashButton")
        self.delete_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.delete_button.setIcon(ImageItemWidget.icon("trash.svg"))
        self.delete_button.setFixedHeight(35)
        self.delete_button.setFixedWidth(150)
        self.delete_button.setIconSize(QSize(20, 20))
        self.delete_button.setToolTip("Delete")
        
        self.delete_button.clicked.connect(self._handle_delete)

        layout.addWidget(self.image_label)
        
        layout.addWidget(
            self.delete_button, 
            alignment = Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignBottom
        )

    @staticmethod
    def icon(name: str) -> QIcon:
  
        return QIcon(os.path.join(Config.icon.icon_dir, name))

    def _handle_delete(self):
        
        if self.file_path is not None:
            
            self.parent_widget._handle_delete_image(self.file_path)
            
        elif self.image_id is not None:
            
            self.parent_widget._handle_delete_image(self.image_id)
