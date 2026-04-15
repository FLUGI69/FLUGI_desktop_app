import logging

from PyQt6.QtWidgets import QMainWindow, QLabel, QProgressBar, QVBoxLayout, QHBoxLayout, QWidget, QPushButton
from PyQt6.QtCore import Qt, QPoint
from PyQt6.QtGui import QMouseEvent

from utils.logger import LoggerMixin

class LauncherWindow(QMainWindow, LoggerMixin):
    
    log: logging.Logger
    
    def __init__(self):
        
        super().__init__()

        self.setWindowFlag(Qt.WindowType.FramelessWindowHint)
        
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        self._drag_pos: QPoint | None = None

        self.__init_window()
        
    def __init_window(self):

        self.setWindowTitle("Example Company Kft - Launcher")
        self.setFixedSize(600, 150) 

        central_widget = QWidget()
        central_widget.setObjectName("LauncherCentral")
        central_widget.setStyleSheet("""
            #LauncherCentral {
                background: qlineargradient(
                    x1:0, y1:0, x2:0, y2:1,
                    stop:0 #4a4a4a,
                    stop:1 #363636
                );
                border: 1px solid #505050;
                border-radius: 12px;
            }
            #LauncherCentral QLabel {
                color: white;
                font-size: 14px;
                font-weight: bold;
                padding: 4px;
                background: transparent;
                border: none;
            }
            #LauncherCentral QProgressBar {
                background-color: #4a4a4a;
                border: 1px solid #2a2a2a;
                border-radius: 8px;
                text-align: center;
                color: white;
                min-height: 20px;
            }
            #LauncherCentral QProgressBar::chunk {
                background-color: #4285f4;
                border-radius: 8px;
            }
        """)
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Title bar
        title_bar = QWidget()
        title_bar.setStyleSheet("background: transparent; border: none;")
        title_layout = QHBoxLayout(title_bar)
        title_layout.setContentsMargins(12, 4, 4, 0)
        title_layout.setSpacing(0)

        title_label = QLabel("Example Company Ltd.")
        title_label.setStyleSheet("font-size: 11px; color: #b0b0b0; background: transparent; border: none;")
        title_layout.addWidget(title_label)
        title_layout.addStretch()

        btn_close = QPushButton("✕")
        btn_close.setFixedSize(30, 30)
        btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_close.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                border-radius: 6px;
                color: #b0b0b0;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #c42b1c;
                color: #ffffff;
            }
            QPushButton:pressed {
                background: #a02015;
                color: #ffffff;
            }
        """)
        btn_close.clicked.connect(self.close)
        title_layout.addWidget(btn_close)

        main_layout.addWidget(title_bar)

        # Content
        content_layout = QVBoxLayout()
        content_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        content_layout.setContentsMargins(20, 0, 20, 16)

        self.label = QLabel("Verzió ellenőrzése...")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        content_layout.addWidget(self.label)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        content_layout.addWidget(self.progress)

        main_layout.addLayout(content_layout)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
        
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
       
        if self._drag_pos is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
       
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
       
        self._drag_pos = None
        
        super().mouseReleaseEvent(event)