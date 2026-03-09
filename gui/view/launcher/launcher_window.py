import logging

from PyQt6.QtWidgets import QMainWindow, QLabel, QProgressBar, QVBoxLayout, QWidget
from PyQt6.QtCore import Qt

from utils.logger import LoggerMixin

class LauncherWindow(QMainWindow, LoggerMixin):
    
    log: logging.Logger
    
    def __init__(self):
        
        super().__init__()

        self.__init_window()
        
    def __init_window(self):
        
        self.setStyleSheet(
            """
            QMainWindow {
                background: qradialgradient(
                    cx: 0.5, cy: 0.5,
                    fx: 0.5, fy: 0.5,
                    radius: 1,
                    stop: 0 #6e6e6e,
                    stop: 1 #3e3e3e
                );
                color: white;
            }
            QLabel {
                color: white;
                font-size: 14px;
                font-weight: bold;
                padding: 4px;
            }
            QProgressBar {
                background-color: #4a4a4a;
                border: 1px solid #2a2a2a;
                border-radius: 8px;
                text-align: center;
                color: white;
                min-height: 20px;
            }
            QProgressBar::chunk {
                background-color: #4285f4;
                border-radius: 8px;
            }
            """
        )

        self.setWindowTitle("Example Company Ltd. - Launcher")
        
        self.setFixedSize(600, 150) 

        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.label = QLabel("Checking version...")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        layout.addWidget(self.label)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        
        layout.addWidget(self.progress)

        central_widget = QWidget()
        central_widget.setLayout(layout)
        
        self.setCentralWidget(central_widget)