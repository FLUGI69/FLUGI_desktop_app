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
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QCursor

from utils.dc.admin.rental_history import RentalHistoryData
from utils.dc.tenant_data import TenantData
from utils.logger import LoggerMixin
from config import Config

class EditRentalHistoryModal(QDialog, LoggerMixin):
    
    log: logging.Logger
    
    def __init__(self, parent = None):
        
        super().__init__(parent)
        
        self._future = None
        
        self.previous_rental_history_data: RentalHistoryData = None
        
        self.setWindowTitle("Edit inventory:")
        
        self.setModal(True)
        
        self.setMinimumWidth(500)

        self.__init_modal()
        
        self.adjustSize()
            
    def __init_modal(self):
        
        self.setObjectName("EditToolsModal")
        
        main_layout = QVBoxLayout(self)
        main_layout.addWidget(self.set_top_widget())
        main_layout.addLayout(self.set_bottom_layout())
    
    def set_middle_labels(self):
        
        middle_labels_layout = QHBoxLayout()
     
        info_label = QLabel("Tenant / rented item:")
        info_label.setObjectName("BoatTitleLabel") 
        info_label.setAlignment(Qt.AlignmentFlag.AlignCenter) 
        info_label.setFixedHeight(25)
        
        self.current_tenant_name_label = QLabel()
        self.current_tenant_name_label.setObjectName("BoatTitleLabel") 
        self.current_tenant_name_label.setAlignment(Qt.AlignmentFlag.AlignCenter) 
        self.current_tenant_name_label.setFixedHeight(25)
        
        self.current_item_name_label = QLabel()
        self.current_item_name_label.setObjectName("BoatTitleLabel")
        self.current_item_name_label.setAlignment(Qt.AlignmentFlag.AlignCenter) 
        self.current_item_name_label.setFixedHeight(25)  
        
        middle_labels_layout.addWidget(info_label)
        middle_labels_layout.addWidget(self.current_tenant_name_label)
        middle_labels_layout.addWidget(self.current_item_name_label)
        
        return middle_labels_layout
        
    def set_bottom_labels(self):
        
        bottom_labels_layout = QHBoxLayout()
        
        self.current_start_label = QLabel()
        self.current_start_label.setObjectName("BoatTitleLabel") 
        self.current_start_label.setAlignment(Qt.AlignmentFlag.AlignCenter) 
        self.current_start_label.setFixedHeight(25)
        
        self.current_end_label = QLabel()
        self.current_end_label.setObjectName("BoatTitleLabel")
        self.current_end_label.setAlignment(Qt.AlignmentFlag.AlignCenter) 
        self.current_end_label.setFixedHeight(25)  
        
        bottom_labels_layout.addWidget(self.current_start_label)
        bottom_labels_layout.addWidget(self.current_end_label)
        
        return bottom_labels_layout
    
    def set_top_widget(self):
        
        topbar = QWidget()
        topbar.setObjectName("Topbar")
        
        top_layout = QVBoxLayout(topbar)
        top_layout.setContentsMargins(10, 10, 10, 10)
        top_layout.setSpacing(10)
        
        self.title = QLabel("Modify rental status")
        self.title.setObjectName("BoatTitleLabel")
        self.title.setAlignment(Qt.AlignmentFlag.AlignCenter) 
        self.title.setFixedHeight(40)
        
        middle_labels = self.set_middle_labels()
        
        bottom_labels = self.set_bottom_labels()
        
        top_layout.addWidget(self.title)
        top_layout.addLayout(middle_labels)
        top_layout.addLayout(bottom_labels)
        
        return topbar
    
    def set_bottom_layout(self):
        
        self.label_returned = QLabel("Visszaadva:")
        self.dropdown_returned = QComboBox()
        self.dropdown_returned.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.dropdown_returned.addItem("", None)
        self.dropdown_returned.addItem("Yes", True)
        self.dropdown_returned.addItem("No", False)
        self.dropdown_returned.setFixedHeight(35)
        
        self.label_is_paid = QLabel("Kifizetve:")
        self.dropdown_is_paid = QComboBox()
        self.dropdown_is_paid.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.dropdown_is_paid.addItem("", None)
        self.dropdown_is_paid.addItem("Yes", True)
        self.dropdown_is_paid.addItem("No", False)
        self.dropdown_is_paid.setFixedHeight(35)
        
        self.bottom_layout = QVBoxLayout()
        self.bottom_layout.setContentsMargins(20, 20, 20, 20)
        self.bottom_layout.setSpacing(15)
        
        self.bottom_layout.addWidget(self.label_returned)
        self.bottom_layout.addWidget(self.dropdown_returned)
        
        self.bottom_layout.addWidget(self.label_is_paid)
        self.bottom_layout.addWidget(self.dropdown_is_paid)
        
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

        self.bottom_layout.addWidget(button_widget)
        
        return self.bottom_layout    
    
    def set_modal_labels_with_previous_reference(self, previous_reference: RentalHistoryData):
        
        self.previous_rental_history_data = previous_reference
        
        if self.previous_rental_history_data is not None:

            self.current_tenant_name_label.setText(self.previous_rental_history_data.tenant.tenant_name)
            self.current_item_name_label.setText(self.previous_rental_history_data.tenant.item_name)
            
            self.current_start_label.setText(self.previous_rental_history_data.tenant.rental_start.strftime(Config.time.timeformat))
            self.current_end_label.setText(self.previous_rental_history_data.tenant.rental_end.strftime(Config.time.timeformat))

            self.set_dropdown_value(
                dropdown = self.dropdown_returned, 
                value = self.previous_rental_history_data.tenant.returned
            )

            self.set_dropdown_value(
                dropdown = self.dropdown_is_paid, 
                value = self.previous_rental_history_data.is_paid
            )
           
    def set_dropdown_value(self, dropdown: QComboBox, value: bool | None):
        
        if value is None:
            
            dropdown.setCurrentIndex(0)
            
        elif value is True:
            
            dropdown.setCurrentIndex(1) 
            
        else:
            
            dropdown.setCurrentIndex(2) 
            
    def get_form_data(self) -> RentalHistoryData:
        
        if self.previous_rental_history_data is not None:
            
            data = RentalHistoryData(
                is_paid = True if self.dropdown_is_paid.currentData() is True else False,
                tenant = TenantData(
                    tenant_id = self.previous_rental_history_data.tenant.tenant_id,
                    item_type = self.previous_rental_history_data.tenant.item_type,
                    item_id = self.previous_rental_history_data.tenant.item_id, 
                    item_name = self.previous_rental_history_data.tenant.item_name, 
                    quantity = self.previous_rental_history_data.tenant.quantity,
                    tenant_name = self.previous_rental_history_data.tenant.tenant_name,
                    rental_start = self.previous_rental_history_data.tenant.rental_start,
                    rental_end = self.previous_rental_history_data.tenant.rental_end,
                    returned = True if self.dropdown_returned.currentData() is True else False,
                    rental_price = self.previous_rental_history_data.tenant.rental_price,
                    is_daily_price = self.previous_rental_history_data.tenant.is_daily_price
                )
            )
                
            self.log.debug("Form data: %s" % data)
            
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

