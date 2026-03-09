import os
import asyncio
import logging

from PyQt6.QtWidgets import (
    QDialog, 
    QVBoxLayout, 
    QLabel, 
    QWidget, 
    QDialogButtonBox, 
    QSpacerItem, 
    QSizePolicy,
    QHBoxLayout
)
from PyQt6.QtGui import QIcon, QCursor
from PyQt6.QtCore import Qt

from utils.dc.admin.reminder import CalendarData
from config import Config
from utils.logger import LoggerMixin

class ReminderAlertModal(QDialog, LoggerMixin):
    
    log: logging.Logger
    
    def __init__(self, 
        data: CalendarData, 
        parent = None
        ):
        
        super().__init__(parent)
        
        self.data = data
        
        self._result = None

        self.__init_modal()
        
    def __init_modal(self):    
        
        self.setWindowTitle("Reminder")
        self.setMinimumSize(300, 200)

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        icon_label = QLabel(self)
        icon = self.icon("alert-octagon.svg")
        
        pixmap = icon.pixmap(48, 48)

        if pixmap.isNull():
            
            icon_label.setText("⚠️")
            
        else:
            
            icon_label.setPixmap(pixmap)

        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.main_layout.addWidget(icon_label)

        note_label = QLabel(f"<b>{self.data.note}</b>", self)
        note_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.main_layout.addWidget(note_label)

        date_label = QLabel(self.data.date.strftime(Config.time.timeformat), self)
        date_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.main_layout.addWidget(date_label)

        self.main_layout.addSpacerItem(QSpacerItem(0, 20, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))

        self.button_container = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.button_container.setObjectName("ConfirmModalButtonBox")
        self.button_container.setFixedHeight(60)

        self.save_button = self.button_container.button(QDialogButtonBox.StandardButton.Ok)
        self.save_button.setText("Stop")
        self.save_button.setFixedHeight(35)
        self.save_button.setFixedWidth(90)
        self.save_button.setObjectName("ConfirmModalButton")
        self.save_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.save_button.clicked.connect(lambda: self._on_button_clicked(0))

        cancel_button = self.button_container.button(QDialogButtonBox.StandardButton.Cancel)
        cancel_button.setText("Ok")
        cancel_button.setFixedHeight(35)
        cancel_button.setFixedWidth(90)
        cancel_button.setObjectName("ConfirmModalButton")
        cancel_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        cancel_button.clicked.connect(lambda: self._on_button_clicked(1))

        button_widget = QWidget()
        
        button_layout = QHBoxLayout(button_widget)
        button_layout.addStretch()
        button_layout.addWidget(self.button_container)
        button_layout.addStretch()
        button_layout.setContentsMargins(0, 0, 0, 0)
        button_layout.setSpacing(10)

        self.main_layout.addWidget(button_widget)

    @staticmethod
    def icon(name: str) -> QIcon:
        
        return QIcon(os.path.join(Config.icon.icon_dir, name))
    
    def _on_button_clicked(self, result: int):
        
        self._result = result
        
        self.accept()

    def result_value(self):
        
        return self._result
    
    def exec_async(self) -> asyncio.Future:
        
        self._future = asyncio.get_event_loop().create_future()
        
        self.log.info("Starting asynchronous modal execution, future created and modal opened")
        
        self.accepted.connect(self._on_accepted)
        self.rejected.connect(self._on_rejected)
        
        self.open()
        
        return self._future

    def _on_accepted(self):
        
        if self._future and not self._future.done():
            
            self.log.info("Modal accepted by the user; setting future result to True")
            
            self._future.set_result(True)
            
        else:
            
            self.log.warning("Accepted signal received, but future is already done or missing")
        
        self._disconnect_signals()
        
        self.log.info("Disconnected accepted and rejected signals after acceptance")

    def _on_rejected(self):
        
        if self._future and not self._future.done():
            
            self.log.info("Modal rejected by the user; setting future result to False")
            
            self._future.set_result(False)
            
        else:
            
            self.log.warning("Rejected signal received, but future is already done or missing")
        
        self._disconnect_signals()
        
        self.log.info("Disconnected accepted and rejected signals after rejection")

    def _disconnect_signals(self):
        
        try:
            
            self.accepted.disconnect(self._on_accepted)
            self.rejected.disconnect(self._on_rejected)
            
            self.log.debug("Successfully disconnected modal signals")
            
        except TypeError:
            
            self.log.warning("Attempted to disconnect signals that were not connected")

    def closeEvent(self, event):
        
        if self._future and not self._future.done():
            
            self.log.info("Modal closed without explicit accept/reject; setting future result to False")
            
            self._future.set_result(False)
        
        self._disconnect_signals()
        
        self.log.info("Modal closed signals disconnected and closing event propagated")
        
        super().closeEvent(event)