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
    QLineEdit,
    QDoubleSpinBox,
    QDateTimeEdit,
    QComboBox
)
from PyQt6.QtCore import Qt, QDateTime, QDate, QTime
from PyQt6.QtGui import QCursor

from utils.dc.tools import ToolsData
from utils.dc.device import DeviceData
from utils.logger import LoggerMixin
from utils.enums.storage_item_type_enum import StorageItemTypeEnum
from utils.dc.tenant_data import TenantData
from utils.handlers.math import UtilityCalculator

class AddLeaseModal(QDialog, LoggerMixin):
    
    log: logging.Logger

    def __init__(self, parent = None):
        
        super().__init__(parent)
        
        self._future = None
        
        self.is_quantity_zero = None
        
        self.utility_calculator: UtilityCalculator = None
        
        self.previous_data: t.Union[ToolsData, DeviceData] = None
        
        self.setWindowTitle("Bérlőhöz adás")
        
        self.setModal(True)
        
        self.setMinimumWidth(500)

        self.__init_modal()
        
        self.adjustSize()
            
    def __init_modal(self):
        
        self.setObjectName("AddToolsModal")
        
        """
        When recording in the database, amounts are always in Hungarian Forints, 
        however, other currencies can also be specified here. (Current MNB exchange rate)
        """
        self.label_currencies = QLabel("Pénznem (alapértelmezetten HUF):")
        self.dropdown_select_currencies = QComboBox()
        self.dropdown_select_currencies.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.dropdown_select_currencies.setFixedHeight(35)
        self.dropdown_select_currencies.addItem("")
        
        self.dropdown_select_currencies_error = QLabel()
        self.dropdown_select_currencies_error.setObjectName("error")
        self.dropdown_select_currencies_error.setVisible(False)
        
        self.label_tenant_name = QLabel("Bérlő neve:")
        self.input_tenant_name = QLineEdit()
        self.input_tenant_name.setFixedHeight(35)
        self.input_tenant_name.setObjectName("input_unit")
        
        self.tenant_error_label = QLabel()
        self.tenant_error_label.setObjectName("error")
        self.tenant_error_label.setVisible(False)
        
        self.min_datetime = QDateTime.currentDateTime()
        
        self.label_date_from = QLabel("Bérlés kezdete:")
        self.date_from = QDateTimeEdit()
        self.date_from.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.date_from.setCalendarPopup(True)
        self.date_from.setFixedHeight(35)
        self.date_from.setMinimumDateTime(QDateTime(QDate(2025, 1, 1), QTime(0, 0)))
        self.date_from.setDateTime(self.min_datetime)
        
        self.rental_start_error_label = QLabel()
        self.rental_start_error_label.setObjectName("error")
        self.rental_start_error_label.setVisible(False)

        self.label_date_to = QLabel("Bérlés vége (ha egyenlő a bérlés kezdetével akkor napi ár):")
        self.date_to = QDateTimeEdit()
        self.date_to.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.date_to.setFixedHeight(35)
        self.date_to.setCalendarPopup(True)
        self.date_to.setMinimumDateTime(QDateTime(QDate(2025, 1, 1), QTime(0, 0)))
        self.date_to.setDateTime(self.min_datetime)
        
        self.rental_end_error_label = QLabel()
        self.rental_end_error_label.setObjectName("error")
        self.rental_end_error_label.setVisible(False)

        self.label_price = QLabel("Bérleti díj (Netto egységár)")
        self.input_price = QDoubleSpinBox()
        self.input_price.setDecimals(2)
        self.input_price.setSingleStep(0.01)
        self.input_price.setMinimum(0)
        self.input_price.setMaximum(1_000_000)
        self.input_price.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.input_price.setObjectName("input_quantity")
        self.input_price.setFixedHeight(35)
        
        self.price_error_label = QLabel()
        self.price_error_label.setObjectName("error")
        self.price_error_label.setVisible(False)
        
        self.label_quantity = QLabel("Mennyiség:")
        self.input_quantity = QDoubleSpinBox()
        self.input_quantity.setDecimals(4)
        self.input_quantity.setSingleStep(1)
        self.input_quantity.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.input_quantity.setObjectName("input_quantity")
        self.input_quantity.setFixedHeight(35)
        
        self.quantity_error_label = QLabel()
        self.quantity_error_label.setObjectName("error")
        self.quantity_error_label.setVisible(False)

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(20, 20, 20, 20)
        self.layout.setSpacing(15)
        
        self.layout.addWidget(self.label_currencies)
        self.layout.addWidget(self.dropdown_select_currencies)
        
        self.layout.addWidget(self.label_tenant_name)
        self.layout.addWidget(self.input_tenant_name)
        self.layout.addWidget(self.tenant_error_label) 

        self.layout.addWidget(self.label_date_from)
        self.layout.addWidget(self.date_from)
        self.layout.addWidget(self.rental_start_error_label) 

        self.layout.addWidget(self.label_date_to)
        self.layout.addWidget(self.date_to)
        self.layout.addWidget(self.rental_end_error_label) 

        self.layout.addWidget(self.label_price)
        self.layout.addWidget(self.input_price)
        self.layout.addWidget(self.price_error_label) 
        
        self.layout.addWidget(self.label_quantity)
        self.layout.addWidget(self.input_quantity)
        self.layout.addWidget(self.quantity_error_label) 

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

        self.button_container.accepted.connect(self.on_send_clicked)
        self.button_container.rejected.connect(self.reject)

        button_widget = QWidget()
        button_layout = QHBoxLayout(button_widget)
        button_layout.addStretch()
        button_layout.addWidget(self.button_container)
        button_layout.addStretch()
        button_layout.setContentsMargins(0, 0, 0, 0)
        button_layout.setSpacing(10)

        self.layout.addWidget(button_widget)

    def prepare_dropwdown_currencies(self, dropdown_items: list[str]):
        
        if len(dropdown_items) > 0:
            
            self.dropdown_select_currencies.clear()
            self.dropdown_select_currencies.addItem("")
            
            for text in dropdown_items:
                
                self.dropdown_select_currencies.addItem(text, text)
    
    def on_send_clicked(self):
        
        self.tenant_error_label.setVisible(False)
        self.rental_start_error_label.setVisible(False)
        self.rental_end_error_label.setVisible(False)
        self.price_error_label.setVisible(False)
        self.quantity_error_label.setVisible(False)

        has_error = False
        
        tenant_name = self.input_tenant_name.text().strip()
        rental_start = self.date_from.dateTime().toPyDateTime()
        rental_end = self.date_to.dateTime().toPyDateTime()
        rental_price = self.input_price.value()
        modal_quanity = self.input_quantity.value()
        
        if self.utility_calculator is not None:
            
            if self.utility_calculator.is_zero(modal_quanity) == True:
                
                self.quantity_error_label.setText("Nem adtál hozzá mennyiséget")
                self.quantity_error_label.setVisible(True)
                
                self.log.warning("You did not add a quantity for the selected tool(s) | device(s)")
                
                has_error = True
        
        if self.is_quantity_zero  is not None and self.is_quantity_zero  is True:
            
            self.quantity_error_label.setText("Nem rendelkezel megfelelő mennyiséggel")
            self.quantity_error_label.setVisible(True)
            
            self.log.warning("Insufficient quantity available for the selected tool(s) | device(s)")
            
            has_error = True

        if not tenant_name:
            
            self.tenant_error_label.setText("A bérlő neve kötelező.")
            self.tenant_error_label.setVisible(True)
            
            self.log.warning("Tenant name is required")
            
            has_error = True

        if rental_start < self.min_datetime:
            
            self.rental_start_error_label.setText("A kezdődátum nem lehet korábbi, mint a jelenlegi időpont")
            self.rental_start_error_label.setVisible(True)
            
            self.log.warning("Rental start date is earlier than the current datetime.")
            
            has_error = True

        if rental_end < rental_start:
            
            self.rental_end_error_label.setText("A visszahozatal dátuma nem lehet korábbi mint a bérlés kezdete")
            self.rental_end_error_label.setVisible(True)
            
            self.log.warning("Input validation failed: 'rental_end' must be later than 'rental_start'")
            
            has_error = True

        if rental_price <= 0:
            
            self.price_error_label.setText("A bérleti díj nem lehet nulla vagy negatív")
            self.price_error_label.setVisible(True)
            
            self.log.warning("Rental price cannot be negative")
            
            has_error = True

        if has_error == False:
            
            self.accept()
    
    def get_form_data(self, item: t.Optional[t.Union[ToolsData, DeviceData]]) -> TenantData:
        
        currency = self.dropdown_select_currencies.currentText() if self.dropdown_select_currencies.currentText() != "" else "HUF"
      
        rental_price_value = self.input_price.value() if self.input_price.value() > 0 else None
        
        if rental_price_value is not None:
            
            exchanged_price = self.utility_calculator.exchange_currency_to_huf(
                value = rental_price_value,
                from_currency = currency
            )
            
            if self.input_quantity.value() > 1:
                
                rental_price = exchanged_price*self.input_quantity.value()
                
            else:
                
                rental_price = exchanged_price
            
        data = TenantData(
            tenant_id = None,
            item_type = StorageItemTypeEnum.TOOL if isinstance(item, ToolsData) else StorageItemTypeEnum.DEVICE,
            item_id = item.id if item.id is not None else None,
            item_name = item.name if item.name is not None else None,
            quantity = self.input_quantity.value(),
            tenant_name = self.input_tenant_name.text().strip() if self.input_tenant_name.text().strip() != "" else None,
            rental_start = self.date_from.dateTime().toPyDateTime(),
            rental_end = self.date_to.dateTime().toPyDateTime() if self.date_to.dateTime() != self.min_datetime else None,
            returned = False,
            rental_price = rental_price
        )
        
        self.log.debug("Form data: %s" % (data))
        
        return data
    
    def exec_async(self) -> asyncio.Future:
        
        self._future = asyncio.get_event_loop().create_future()
        
        self.min_datetime = QDateTime.currentDateTime()
        
        self.quantity_error_label.setVisible(False)
        self.tenant_error_label.setVisible(False)
        self.rental_start_error_label.setVisible(False)
        self.rental_end_error_label.setVisible(False)
        self.price_error_label.setVisible(False)
        
        self.dropdown_select_currencies.setCurrentIndex(0)
        self.input_tenant_name.clear()
        self.date_from.setDateTime(self.min_datetime)
        self.date_to.setDateTime(self.min_datetime)
        self.input_price.setValue(0)
        self.input_quantity.setValue(0)
        self.input_quantity.setMinimum(0)
        self.input_quantity.setMaximum(self.previous_data.quantity)
        
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