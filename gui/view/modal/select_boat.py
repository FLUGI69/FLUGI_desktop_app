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

from utils.dc.mahart_ports.selected_boats import SelectedBoatData
from utils.logger import LoggerMixin

class SelectBoatModal(QDialog, LoggerMixin):

    log: logging.Logger

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

        self.message_label = QLabel("Select the boat from your fleet you want to add to:")
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

    def set_boats(self, boats: list[SelectedBoatData]):
        
        self.log.debug("Setting selected boats:\n%s" % "\n".join(str(boat) for boat in boats))

        self.combo_box.clear()

        for boat in boats:
            
            flag_emoji = self.country_flag_emoji(boat.flag if boat.flag is not None else "n.a")
            
            display_text = f"{boat.name if boat.name is not None else "n.a"} {flag_emoji} – {boat.country if boat.country is not None else "n.a"} (MMSI: {boat.mmsi if boat.mmsi is not None else 'n.a.'})"
            
            self.combo_box.addItem(display_text, boat)

    def country_flag_emoji(self, country_code: str) -> str:
        
        if len(country_code) != 2:
            
            return ""
        
        return chr(127397 + ord(country_code[0].upper())) + chr(127397 + ord(country_code[1].upper()))

    def __handle_accept(self):
        
        self.selected_boat = self.combo_box.currentData()
        
        self.accept()

    def get_selected_boat(self):
        
        return self.selected_boat
    
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