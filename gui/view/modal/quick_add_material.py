import asyncio
import logging
import typing as t

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
from utils.dc.material import MaterialData
from utils.logger import LoggerMixin

class QuickAddMaterialModal(QDialog, LoggerMixin):
    
    log: logging.Logger
    
    finished_signal = pyqtSignal()
    
    def __init__(self, parent = None):
        
        super().__init__(parent)
        
        self._future = None
        
        self.selected_work = None
        
        self.selected_material = None
        
        self.setWindowTitle("Gyors anyag hozzáadás munkához")
        
        self.setModal(True)
        
        self.setMinimumWidth(600)

        self.__init_modal()
        
        self.adjustSize()
            
    def __init_modal(self):
        
        self.setObjectName("ConfirmModal")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        self.work_label = QLabel("Válaszd ki a munkát:")
        self.work_label.setObjectName("ConfirmModalLabel")
        self.work_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.work_combo = QComboBox(self)
        self.work_combo.setFixedHeight(35)
        self.work_combo.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        
        self.material_label = QLabel("Válaszd ki az anyagot:")
        self.material_label.setObjectName("ConfirmModalLabel")
        self.material_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.material_combo = QComboBox(self)
        self.material_combo.setFixedHeight(35)
        self.material_combo.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(20, 20, 20, 20)
        self.layout.setSpacing(15)
        self.layout.addWidget(self.work_label)
        self.layout.addWidget(self.work_combo)
        self.layout.addWidget(self.material_label)
        self.layout.addWidget(self.material_combo)

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
        
        self.log.debug("Setting selected works (len: %d): %s" % (len(works), str(works[:10])))
        
        self.works = works
        
        self.work_combo.clear()

        for work in works:
            
            display_text = f"{work.id} -> (Hajó: {work.boat_name}) – {work.description}"
            
            self.work_combo.addItem(display_text, work)

    def set_materials(self, materials: t.List[MaterialData]):
        
        self.log.debug("Setting materials (len: %d): %s" % (len(materials), str(materials[:10])))
        
        self.materials = materials
        
        self.material_combo.clear()

        for material in materials:
            
            display_text = f"{material.name} (Mennyiség: {material.quantity:.4f} {material.unit or ''})"
            
            self.material_combo.addItem(display_text, material)

    def __handle_accept(self):
        
        self.selected_work = self.work_combo.currentData()
        
        self.selected_material = self.material_combo.currentData()
        
        self.accept()

    def get_selected_work(self) -> SelectedWorkData:
        
        return self.selected_work
    
    def get_selected_material(self) -> MaterialData:
        
        return self.selected_material
    
    def exec_async(self) -> asyncio.Future:
        
        self._future = asyncio.get_event_loop().create_future()
        
        self.log.info("Starting asynchronous modal execution, future created and modal opened")
        
        self.accepted.connect(self._on_accepted)
        self.rejected.connect(self._on_rejected)
        
        self.open()
        
        return self._future

    def _on_accepted(self):
        
        if self._future and not self._future.done():
            
            self.log.info("Modal accepted by the user setting future result to True")
            
            self._future.set_result(True)
            
        else:
            
            self.log.warning("Accepted signal received, but future is already done or missing")
        
        self._disconnect_signals()
        
        self.log.info("Disconnected accepted and rejected signals after acceptance")

    def _on_rejected(self):
        
        if self._future and not self._future.done():
            
            self.log.info("Modal rejected by the user setting future result to False")
            
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
