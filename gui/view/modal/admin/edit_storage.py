import asyncio
import logging

from PyQt6.QtWidgets import (
    QDialog, 
    QVBoxLayout,
    QLabel, 
    QDialogButtonBox, 
    QWidget, 
    QHBoxLayout,
    QLineEdit
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QCursor

from utils.dc.admin.storage import StorageData
from utils.logger import LoggerMixin

class EditStorageModal(QDialog, LoggerMixin):
    
    log: logging.Logger

    def __init__(self, parent = None):
        
        super().__init__(parent)
        
        self._future = None
        
        self.setWindowTitle("Edit storage")
        
        self.setModal(True)
        
        self.setMinimumWidth(500)

        self.__init_modal()
        
        self.adjustSize()
            
    def __init_modal(self):
        
        self.setObjectName("EditStorageModal")
        
        self.label_name = QLabel("Name:")
        self.input_name = QLineEdit()
        self.input_name.setObjectName("input_unit")
        self.input_name.setFixedHeight(35)
        
        self.input_name_error = QLabel()
        self.input_name_error.setObjectName("error")
        self.input_name_error.setVisible(False)
        
        self.label_location = QLabel("Telephely:")
        self.input_location = QLineEdit()
        self.input_location.setObjectName("input_unit")
        self.input_location.setFixedHeight(35)
        
        self.input_location_error = QLabel()
        self.input_location_error.setObjectName("error")
        self.input_location_error.setVisible(False)
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(20, 20, 20, 20)
        self.layout.setSpacing(15)
        
        self.layout.addWidget(self.label_name)
        self.layout.addWidget(self.input_name)
        self.layout.addWidget(self.input_name_error) 
        
        self.layout.addWidget(self.label_location)
        self.layout.addWidget(self.input_location)
        self.layout.addWidget(self.input_location_error) 
        
        self.button_container = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.button_container.setObjectName("ConfirmModalButtonBox")
        self.button_container.setFixedHeight(60)

        for button in self.button_container.buttons():
            
            button.setFixedHeight(35)
            button.setFixedWidth(90)
            button.setObjectName("ConfirmModalButton")
            button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

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

    def get_form_data(self) -> StorageData:
        
        data = StorageData(
            id = None,
            name = self.input_name.text() if self.input_name.text() != "" else None,
            location = self.input_location.text() if self.input_location.text() != "" else None
        )
        
        self.log.debug("Form data: %s" % data)
        
        return data
    
    def exec_async(self) -> asyncio.Future:
        
        self._future = asyncio.get_event_loop().create_future()
        
        self.input_name.clear()
        self.input_location.clear()
        
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

