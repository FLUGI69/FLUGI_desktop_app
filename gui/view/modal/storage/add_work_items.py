import asyncio
import logging

from PyQt6.QtWidgets import (
    QDialog, 
    QVBoxLayout,
    QLabel, 
    QDialogButtonBox, 
    QWidget, 
    QHBoxLayout,
    QComboBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QCursor

from utils.dc.selected_works import SelectedWorkData
from utils.logger import LoggerMixin

class AddWorkItemsModal(QDialog, LoggerMixin):
    
    log: logging.Logger
    
    finished_signal = pyqtSignal()
    
    def __init__(self, parent = None):
        
        super().__init__(parent)
        
        self._future = None
        
        self.selected_boat = None
        
        self.setWindowTitle("Selection")
        
        self.setModal(True)
        
        self.setMinimumWidth(500)

        self.__init_modal()
        
        self.adjustSize()
            
    def __init_modal(self):
        
        self.setObjectName("ConfirmModal")

        self.message_label = QLabel("Select the work you want to attach the part to:")
        self.message_label.setObjectName("ConfirmModalLabel")
        self.message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
 
        self.combo_box = QComboBox(self)
        self.combo_box.setFixedHeight(35)
        self.combo_box.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(20, 20, 20, 20)
        self.layout.setSpacing(15)
        self.layout.addWidget(self.message_label)
        self.layout.addWidget(self.combo_box)

  
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

        self.button_container.accepted.connect(self.__handle_accept)
        self.button_container.rejected.connect(self.reject)

        button_widget = QWidget()
        button_layout = QHBoxLayout(button_widget)
        button_layout.addStretch()
        button_layout.addWidget(self.button_container)
        button_layout.addStretch()
        button_layout.setContentsMargins(0, 0, 0, 0)
        button_layout.setSpacing(10)

        self.layout.addWidget(button_widget)

    def set_works(self, works: list[SelectedWorkData]):
        
        self.log.debug("Setting selected works:%s" % (str(works)))
        
        self.works = works
        
        self.combo_box.clear()

        for work in works:
            
            display_text = f"{work.id} -> (Ship: {work.boat_name}) – {work.description}"
            
            self.combo_box.addItem(display_text, work)

    def __handle_accept(self):
        
        self.selected_works = self.combo_box.currentData()
        
        self.accept()

    def get_selected_works(self):
        
        return self.selected_works
    
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