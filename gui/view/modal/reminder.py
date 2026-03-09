import asyncio
from datetime import datetime
import logging

from PyQt6.QtWidgets import (
    QVBoxLayout, 
    QDialog, 
    QLabel, 
    QTextEdit, 
    QDialogButtonBox, 
    QHBoxLayout, 
    QTimeEdit,
    QWidget
)
from PyQt6.QtCore import QDateTime, Qt, pyqtSignal
from PyQt6.QtGui import QCursor

from utils.logger import LoggerMixin
from utils.dc.admin.reminder import CalendarData
from utils.handlers.math import UtilityCalculator
from config import Config

class ReminderModal(QDialog, LoggerMixin):
    
    log: logging.Logger
    
    finished_signal = pyqtSignal()
    
    def __init__(self, parent = None):
        
        super().__init__(parent)
        
        self.calendar_date = None
        
        self.utility_calculator: UtilityCalculator | None = None
        
        self.setWindowTitle("Note and reminder")
        
        self.setModal(True)
        
        self.setMinimumWidth(500)
        
        self.__init_modal()
        
        self.adjustSize()
        
    def __init_modal(self):
        
        self.setObjectName("ConfirmModal")

        self.note_edit = QTextEdit()
        self.note_edit.setObjectName("TranslateInputField")
        self.note_edit.textChanged.connect(self.__on_fields_changed)
        
        self.layout = QVBoxLayout(self) 
        self.layout.addWidget(QLabel("Jegyzet:"))
        self.layout.addWidget(self.note_edit)
        self.layout.addWidget(QLabel("Reminder time:"))

        self.time_edit = QTimeEdit()
        self.time_edit.setObjectName("time_edit")
        self.time_edit.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.time_edit.setMinimumHeight(30)
        self.time_edit.timeChanged.connect(self.__on_fields_changed)
        
        self.layout.addWidget(self.time_edit) 

        self.button_container = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        self.button_container.setObjectName("ConfirmModalButtonBox")
        self.button_container.setFixedHeight(60)

        self.save_button = self.button_container.button(QDialogButtonBox.StandardButton.Save)
        self.save_button.setFixedHeight(35)
        self.save_button.setFixedWidth(90)
        self.save_button.setObjectName("ConfirmModalButton")
        self.save_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.save_button.setEnabled(False)  

        cancel_button = self.button_container.button(QDialogButtonBox.StandardButton.Cancel)
        cancel_button.setFixedHeight(35)
        cancel_button.setFixedWidth(90)
        cancel_button.setObjectName("ConfirmModalButton")
        cancel_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

        self.button_container.accepted.connect(self.accept)
        self.button_container.rejected.connect(self.reject)

        button_widget = QWidget()
        button_layout = QHBoxLayout(button_widget)
        button_layout.addStretch()
        button_layout.addWidget(self.button_container)
        button_layout.addStretch()
        button_layout.setContentsMargins(0, 0, 0, 0)
        button_layout.setSpacing(10)

        self.layout.addWidget(button_widget)

    def __on_fields_changed(self):
        
        note_text = self.note_edit.toPlainText().strip()

        if self.calendar_date is None:
            
            self.save_button.setEnabled(False)
            
            return
        
        if self.utility_calculator is not None:
            
            selected_time = QDateTime(self.calendar_date, self.time_edit.time()).toPyDateTime()
        
            parsed_time = self.utility_calculator.parse_datetime_safe(selected_time)    
        
            now = datetime.now(Config.time.timezone_utc)

            is_valid = bool(note_text) and parsed_time > now
            
            self.save_button.setEnabled(is_valid)

    def get_modal_data(self) -> CalendarData:
        
        qdate = self.calendar_date 
        qtime = self.time_edit.time()         

        qdatetime = QDateTime(qdate, qtime)
        datetime = qdatetime.toPyDateTime()
        
        data = CalendarData(
            calendar_cache_id = None,
            id = None,
            note = self.note_edit.toPlainText().strip(),
            date = datetime,
            used = False 
        )
        
        self.note_edit.clear()
        self.time_edit.clear()
        
        self.log.debug("Save data: %s" % data)

        return data
    
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
        
        self.log.info("Modal closed; signals disconnected and closing event propagated")
        
        super().closeEvent(event)