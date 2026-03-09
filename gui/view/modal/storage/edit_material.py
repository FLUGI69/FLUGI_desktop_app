import asyncio
import logging
from datetime import datetime

from PyQt6.QtWidgets import (
    QDialog, 
    QVBoxLayout,
    QLabel, 
    QDialogButtonBox, 
    QWidget, 
    QHBoxLayout,
    QLineEdit,
    QDoubleSpinBox,
    QComboBox,
    QDateTimeEdit
)
from PyQt6.QtCore import Qt, QDateTime, QDate, QTime
from PyQt6.QtGui import QCursor

from utils.dc.material import MaterialData
from utils.logger import LoggerMixin
from config import Config

class EditMaterialModal(QDialog, LoggerMixin):
    
    log: logging.Logger
    
    def __init__(self, parent = None):
        
        super().__init__(parent)
        
        self._future = None
        
        self.setWindowTitle("Edit inventory:")
        
        self.setModal(True)
        
        self.setMinimumWidth(500)

        self.__init_modal()
        
        self.adjustSize()
            
    def __init_modal(self):
        
        self.setObjectName("AddWarehouseModal")
        
        self.label_dropdown = QLabel("Storage:")
        self.dropdown_select_storage = QComboBox()
        self.dropdown_select_storage.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.dropdown_select_storage.setFixedHeight(35)
        self.dropdown_select_storage.addItem("")

        self.label_name = QLabel("Name:")
        self.input_name = QLineEdit()
        self.input_name.setObjectName("input_unit")
        self.input_name.setFixedHeight(35)

        self.label_manufacture_number = QLabel("Type / Serial number:")
        self.input_manufacture_number = QLineEdit()
        self.input_manufacture_number.setObjectName("input_unit")
        self.input_manufacture_number.setFixedHeight(35)

        self.label_quantity = QLabel("Quantity:")
        self.input_quantity = QDoubleSpinBox()
        self.input_quantity.setDecimals(4)
        self.input_quantity.setSingleStep(0.1)
        self.input_quantity.setMinimum(0)
        self.input_quantity.setMaximum(1_000_000)
        self.input_quantity.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.input_quantity.setObjectName("input_quantity")
        self.input_quantity.setFixedHeight(35)

        self.label_unit = QLabel("Unit:")
        self.input_unit = QLineEdit()
        self.input_unit.setObjectName("input_unit")
        self.input_unit.setFixedHeight(35)

        self.label_manufacture_date = QLabel("Manufacturing year:")
        self.manufacture_date = QDateTimeEdit()
        self.manufacture_date.setFixedHeight(35)
        self.manufacture_date.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.manufacture_date.setCalendarPopup(True)
        self.manufacture_date.setMinimumDateTime(QDateTime(QDate(2000, 1, 1), QTime(0, 0)))
        
        self.label_price = QLabel("Net unit price:")
        self.input_price = QDoubleSpinBox()
        self.input_price.setDecimals(2)
        self.input_price.setSingleStep(0.01)
        self.input_price.setMinimum(0)
        self.input_price.setMaximum(10_000_000)
        self.input_price.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.input_price.setFixedHeight(35)
        self.input_price.setObjectName("input_quantity")

        self.label_purchase_source = QLabel("Purchased from (company, site, distributor):")
        self.input_purchase_source = QLineEdit()
        self.input_purchase_source.setObjectName("input_unit")
        self.input_purchase_source.setFixedHeight(35)
        
        self.label_purchase_date = QLabel("Purchase date:")
        self.input_purchase_date = QDateTimeEdit()
        self.input_purchase_date.setFixedHeight(35)
        self.input_purchase_date.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.input_purchase_date.setCalendarPopup(True)
        self.input_purchase_date.setMinimumDateTime(QDateTime(QDate(2000, 1, 1), QTime(0, 0)))
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(20, 20, 20, 20)
        self.layout.setSpacing(15)

        self.layout.addWidget(self.label_dropdown)
        self.layout.addWidget(self.dropdown_select_storage)

        self.layout.addWidget(self.label_name)
        self.layout.addWidget(self.input_name)

        self.layout.addWidget(self.label_manufacture_number)
        self.layout.addWidget(self.input_manufacture_number)

        self.layout.addWidget(self.label_quantity)
        self.layout.addWidget(self.input_quantity)

        self.layout.addWidget(self.label_unit)
        self.layout.addWidget(self.input_unit)

        self.layout.addWidget(self.label_manufacture_date)
        self.layout.addWidget(self.manufacture_date)

        self.layout.addWidget(self.label_price)
        self.layout.addWidget(self.input_price)

        self.layout.addWidget(self.label_purchase_source)
        self.layout.addWidget(self.input_purchase_source)
        
        self.layout.addWidget(self.label_purchase_date)
        self.layout.addWidget(self.input_purchase_date)

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

    def update_parameters_from_previous_reference(self, previous_data: MaterialData, emit_result_list: list[tuple[str, int]]):
        
        self.dropdown_select_storage.clear()
        
        self.default_datetime = previous_data.manufacture_date
        self.default_purchase_date = previous_data.purchase_date
        self.previous_data = previous_data
        # print(previous_data)
        # print(emit_result_list)

        self.selected_index = -1

        for index, (description, id) in enumerate(emit_result_list):
            
            self.dropdown_select_storage.addItem(description, id)
            
            if id == previous_data.id:
                
                self.selected_index = index

        if self.selected_index >= 0:
            
            self.dropdown_select_storage.setCurrentIndex(self.selected_index)
        
    def get_form_data(self) -> MaterialData:
        
        data = MaterialData(
            id = None,
            storage_id = self.dropdown_select_storage.currentData() if self.dropdown_select_storage.currentData() is not None else self.previous_data.storage_id,
            name = self.input_name.text().strip() if self.input_name.text().strip() != self.previous_data.name else None,
            manufacture_number = self.input_manufacture_number.text() if self.input_manufacture_number.text() != self.previous_data.manufacture_number else None,
            quantity = self.input_quantity.value(),
            unit = self.input_unit.text().strip() if self.input_unit.text().strip() != self.previous_data.unit else None,
            manufacture_date = self.manufacture_date.dateTime().toPyDateTime() if self.manufacture_date.dateTime() != self.default_datetime else None,
            price = self.input_price.value(),
            purchase_source = self.input_purchase_source.text().strip() if self.input_purchase_source.text().strip() != self.previous_data.purchase_source else None,
            inspection_date = datetime.now(Config.time.timezone_utc),
            purchase_date = self.input_purchase_date.dateTime().toPyDateTime() if self.input_purchase_date.dateTime() != self.default_purchase_date else None,
            is_deleted = self.previous_data.is_deleted,
            deleted_date = self.previous_data.deleted_date,
        )
        
        self.log.debug("Form data: %s" % data)
        
        return data
    
    def exec_async(self) -> asyncio.Future:
        
        self._future = asyncio.get_event_loop().create_future()
        
        self.input_name.setText(self.previous_data.name)
        self.input_quantity.setValue(self.previous_data.quantity)
        self.input_unit.setText(self.previous_data.unit)
        self.input_price.setValue(self.previous_data.price)
        self.input_manufacture_number.setText(self.previous_data.manufacture_number)
        self.manufacture_date.setDateTime(self.default_datetime)
        self.input_purchase_date.setDateTime(self.default_purchase_date)
        self.input_purchase_source.setText(self.previous_data.purchase_source)
        
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

