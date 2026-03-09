import asyncio
import sys
import logging
from pathlib import Path
from datetime import datetime

from PyQt6.QtWidgets import (
    QDialog, 
    QVBoxLayout,
    QLabel, 
    QDialogButtonBox, 
    QWidget, 
    QHBoxLayout,
    QDoubleSpinBox,
    QDateTimeEdit
)
from PyQt6.QtCore import Qt, QDateTime, QDate, QTime
from PyQt6.QtGui import QCursor, QMovie

from utils.dc.tenant_data import TenantData
from utils.logger import LoggerMixin
from config import Config

class ExtendTenantModal(QDialog, LoggerMixin):
    
    log: logging.Logger
    
    def __init__(self, parent = None):
        
        super().__init__(parent)
        
        self._future = None
        
        self.previous_data: TenantData | None = None
        
        self.setWindowTitle("Extend rental:")
        
        self.setModal(True)
        
        self.setMinimumWidth(500)

        self.__init_modal()
        
        self.adjustSize()
            
    def __init_modal(self):
        
        self.setObjectName("AddWarehouseModal")

        main_layout = QVBoxLayout(self)
        main_layout.addWidget(self.set_top_section())
        main_layout.addLayout(self.set_bottom_section())

    def set_top_section(self):
        
        topbar = QWidget()
        topbar.setObjectName("Topbar")
        
        top_layout = QVBoxLayout(topbar)
        top_layout.setContentsMargins(10, 10, 10, 10)
        top_layout.setSpacing(10)

        self.title = QLabel()
        self.title.setObjectName("BoatTitleLabel")
        self.title.setAlignment(Qt.AlignmentFlag.AlignCenter) 
        self.title.setFixedHeight(40)
        
        middle_labels = self.set_middle_labels()
        
        bottom_box = self.set_bottom_box()
        
        top_layout.addWidget(self.title)
        top_layout.addLayout(middle_labels)
        top_layout.addLayout(bottom_box)
        
        return topbar
    
    def set_middle_labels(self):
        
        middle_labels_layout = QHBoxLayout()
        
        self.current_start_label = QLabel()
        self.current_start_label.setObjectName("BoatTitleLabel") 
        self.current_start_label.setAlignment(Qt.AlignmentFlag.AlignCenter) 
        self.current_start_label.setFixedHeight(35)
        
        self.current_end_label = QLabel()
        self.current_end_label.setObjectName("BoatTitleLabel")
        self.current_end_label.setAlignment(Qt.AlignmentFlag.AlignCenter) 
        self.current_end_label.setFixedHeight(35)  
        
        middle_labels_layout.addWidget(self.current_start_label)
        middle_labels_layout.addWidget(self.current_end_label)
        
        return middle_labels_layout
    
    def set_bottom_box(self):
        
        bottom_box = QHBoxLayout()
        
        if getattr(sys, "frozen", False):
            
            path = Path(sys.executable).parent / "_internal" / Config.gif.donald_money
            
        else:
            
            path = Path(Config.gif.donald_money)

        self.overlay_label = QLabel()
        self.overlay_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.overlay_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

        self.movie = QMovie(str(path))
        
        self.overlay_label.setMovie(self.movie)

        self.overlay_label.setFixedSize(80, 80)
        self.overlay_label.setScaledContents(True)

        self.movie.start()
        
        bottom_box.addWidget(self.overlay_label)
        
        return bottom_box
    
    def set_bottom_section(self):

        bottom_layout = QVBoxLayout()
        bottom_layout.setContentsMargins(20, 20, 20, 20)
        bottom_layout.setSpacing(15)

        self.label_quantity = QLabel("Rented quantity:")
        
        self.input_quantity = QDoubleSpinBox()
        self.input_quantity.setDecimals(4)
        self.input_quantity.setSingleStep(1)
        self.input_quantity.setMinimum(0)
        self.input_quantity.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.input_quantity.setObjectName("input_quantity")
        self.input_quantity.setFixedHeight(35)

        self.label_rental_end_date = QLabel("Rental end:")
        
        self.rental_end = QDateTimeEdit()
        self.rental_end.setFixedHeight(35)
        self.rental_end.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.rental_end.setCalendarPopup(True)
        self.rental_end.setMinimumDateTime(QDateTime(QDate(2000, 1, 1), QTime(0, 0)))
        
        self.rental_end_error = QLabel()
        self.rental_end_error.setObjectName("error")
        self.rental_end_error.setVisible(False)

        self.label_rental_price = QLabel()
        
        self.input_rental_price = QDoubleSpinBox()
        self.input_rental_price.setDecimals(2)
        self.input_rental_price.setSingleStep(0.01)
        self.input_rental_price.setMinimum(0)
        self.input_rental_price.setMaximum(10_000_000)
        self.input_rental_price.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.input_rental_price.setFixedHeight(35)
        self.input_rental_price.setObjectName("input_quantity")
        
        bottom_layout.addWidget(self.label_rental_end_date)
        bottom_layout.addWidget(self.rental_end)
        bottom_layout.addWidget(self.rental_end_error)
        
        bottom_layout.addWidget(self.label_rental_price)
        bottom_layout.addWidget(self.input_rental_price)
        
        bottom_layout.addWidget(self.label_quantity)
        bottom_layout.addWidget(self.input_quantity)

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

        self.button_container.accepted.connect(self.validate_field)
        self.button_container.rejected.connect(self.reject)

        button_widget = QWidget()
        button_layout = QHBoxLayout(button_widget)
        button_layout.addStretch()
        button_layout.addWidget(self.button_container)
        button_layout.addStretch()
        button_layout.setContentsMargins(0, 0, 0, 0)
        button_layout.setSpacing(10)

        bottom_layout.addWidget(button_widget)

        return bottom_layout
    
    def validate_field(self):
        
        has_error = False
        
        current_date_input = self.rental_end.dateTime().toPyDateTime()
        
        if current_date_input == self.default_datetime:

            self.rental_end_error.setText("Rental end cannot be the same as the previous")
            self.rental_end_error.setVisible(True)

            self.log.warning("Input validation failed: rental_end (%s) cannot be the same as previous rental_end (%s)" % (
                current_date_input, 
                self.default_datetime
                )
            )

            has_error = True

        elif current_date_input <= self.start_date:

            self.rental_end_error.setText("Rental end nem lehet ugyan annyi vagy kevesebb mint a kezdete")
            self.rental_end_error.setVisible(True)

            self.log.warning("Input validation failed: rental_end (%s) cannot be before or same as rental_start (%s)" % (
                current_date_input, 
                self.start_date
                )
            )

            has_error = True

        elif current_date_input.replace(microsecond = 0) < self.default_datetime.replace(microsecond = 0):

            self.rental_end_error.setText("Rental end cannot be earlier than the current rental end")
            self.rental_end_error.setVisible(True)

            self.log.warning("Input validation failed: rental_end (%s) cannot be earlier than previous rental_end (%s)" % (
                current_date_input, 
                self.default_datetime
                )
            )

            has_error = True

        else:

            self.rental_end_error.setVisible(False)
        
        if has_error == False:
            
            self.accept()
    
    def update_parameters_from_previous_reference(self, previous_data: TenantData):
        
        self.previous_data = previous_data
        
        if self.previous_data is not None:
            
            self.default_quantity = self.previous_data.quantity
            
            self.default_datetime = self.previous_data.rental_end if self.previous_data.rental_end is not None else datetime.now()
           
            self.default_rental_price = self.previous_data.rental_price
            
            self.title_text = self.previous_data.tenant_name
            
            self.start_date = self.previous_data.rental_start
            
            self.end_date = self.previous_data.rental_end
         
            rental_price_label_text = "Rental price (Net price for total duration):" if self.previous_data.rental_end is not None else "Rental price (Net price daily rate):"
            
            self.label_rental_price.setText(rental_price_label_text)

    def get_form_data(self) -> TenantData:
        
        previous_data = self.previous_data
        
        if previous_data is not None:
            
            data = TenantData(
                tenant_id = previous_data.tenant_id,
                item_type = previous_data.item_type,
                item_id = previous_data.item_id,
                item_name = previous_data.item_name,
                quantity = self.input_quantity.value(),
                tenant_name = previous_data.tenant_name,
                rental_start = previous_data.rental_start,
                rental_end = self.rental_end.dateTime().toPyDateTime(),
                returned = previous_data.returned,
                rental_price = self.input_rental_price.value(),
                is_daily_price = previous_data.is_daily_price
            )
            
            self.log.debug("Form data: %s" % data)
            
            return data
    
    def exec_async(self) -> asyncio.Future:
        
        self._future = asyncio.get_event_loop().create_future()
        
        self.rental_end_error.setVisible(False)
        
        self.title.setText(self.title_text)
        self.current_start_label.setText(self.start_date.strftime(Config.time.timeformat))
        self.current_end_label.setText(self.end_date.strftime(Config.time.timeformat) if self.end_date is not None else "N/A")
        self.rental_end.setDateTime(self.default_datetime)
        self.input_rental_price.setValue(self.default_rental_price)
        self.input_quantity.setValue(0)
        
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
