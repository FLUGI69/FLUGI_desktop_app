import asyncio
import sys, os
import logging
import re
import unicodedata
from datetime import datetime
from qrcode import QRCode
from qrcode.constants import ERROR_CORRECT_H
from PIL import Image, ImageDraw
from pathlib import Path
import io

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
    QTextEdit,
    QDateTimeEdit
)
from PyQt6.QtCore import Qt, QDateTime, QDate, QTime
from PyQt6.QtGui import QCursor

from utils.dc.material import MaterialData
from utils.enums.storage_item_type_enum import StorageItemTypeEnum
from utils.logger import LoggerMixin
from config import Config
from db import queries

class AddMaterialModal(QDialog, LoggerMixin):

    log: logging.Logger

    def __init__(self, parent = None):
        
        super().__init__(parent)
        
        if getattr(sys, "frozen", False):
            
            self.base_path = Path(sys.executable).parent / "_internal"
            
            self.logo_path = self.base_path / Config.google.paths.logo
                
        else:

            self.logo_path = Path(Config.google.paths.logo)
        
        self._future = None
    
        self.setWindowTitle("Add to inventory")
        
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

        self.dropdown_select_storage_error = QLabel()
        self.dropdown_select_storage_error.setObjectName("error")
        self.dropdown_select_storage_error.setVisible(False)

        self.label_name = QLabel("Name:")
        self.input_name = QLineEdit()
        self.input_name.setObjectName("input_unit")
        self.input_name.setFixedHeight(35)

        self.input_name_error = QLabel()
        self.input_name_error.setObjectName("error")
        self.input_name_error.setVisible(False)

        self.label_manufacture_number = QLabel("Type / Serial number:")
        self.input_manufacture_number = QLineEdit()
        self.input_manufacture_number.setObjectName("input_unit")
        self.input_manufacture_number.setFixedHeight(35)

        self.input_manufacture_number_error = QLabel()
        self.input_manufacture_number_error.setObjectName("error")
        self.input_manufacture_number_error.setVisible(False)

        self.label_quantity = QLabel("Quantity:")
        self.input_quantity = QDoubleSpinBox()
        self.input_quantity.setDecimals(4)
        self.input_quantity.setSingleStep(0.01)
        self.input_quantity.setMinimum(1)
        self.input_quantity.setMaximum(1_000_000)
        self.input_quantity.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.input_quantity.setObjectName("input_quantity")
        self.input_quantity.setFixedHeight(35)

        self.input_quantity_error = QLabel()
        self.input_quantity_error.setObjectName("error")
        self.input_quantity_error.setVisible(False)

        self.label_unit = QLabel("Unit:")
        self.input_unit = QLineEdit()
        self.input_unit.setObjectName("input_unit")
        self.input_unit.setFixedHeight(35)

        self.input_unit_error = QLabel()
        self.input_unit_error.setObjectName("error")
        self.input_unit_error.setVisible(False)

        self.min_datetime = QDateTime.currentDateTime()

        self.label_manufacture_date = QLabel("Manufacturing year:")
        self.manufacture_date = QDateTimeEdit()
        self.manufacture_date.setFixedHeight(35)
        self.manufacture_date.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.manufacture_date.setCalendarPopup(True)
        self.manufacture_date.setMinimumDateTime(QDateTime(QDate(2000, 1, 1), QTime(0, 0)))
        self.manufacture_date.setDateTime(self.min_datetime)

        self.manufacture_date_error = QLabel()
        self.manufacture_date_error.setObjectName("error")
        self.manufacture_date_error.setVisible(False)

        self.label_price = QLabel("Net unit price:")
        self.input_price = QDoubleSpinBox()
        self.input_price.setDecimals(2)
        self.input_price.setSingleStep(0.01)
        self.input_price.setMinimum(0) 
        self.input_price.setMaximum(10_000_000)
        self.input_price.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.input_price.setFixedHeight(35)
        self.input_price.setObjectName("input_quantity")

        self.input_price_error = QLabel()
        self.input_price_error.setObjectName("error")
        self.input_price_error.setVisible(False)

        self.label_purchase_source = QLabel("Purchased from (company, site, distributor):")
        self.input_purchase_source = QLineEdit()
        self.input_purchase_source.setObjectName("input_unit")
        self.input_purchase_source.setFixedHeight(35)

        self.input_purchase_source_error = QLabel()
        self.input_purchase_source_error.setObjectName("error")
        self.input_purchase_source_error.setVisible(False)
        
        self.label_purchase_date = QLabel("Purchase date:")
        self.input_purchase_date = QDateTimeEdit()
        self.input_purchase_date.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.input_purchase_date.setCalendarPopup(True)
        self.input_purchase_date.setFixedHeight(35)
        self.input_purchase_date.setMinimumDateTime(QDateTime(QDate(2000, 1, 1), QTime(0, 0)))
        self.input_purchase_date.setDateTime(self.min_datetime)

        self.input_purchase_date_error = QLabel()
        self.input_purchase_date_error.setObjectName("error")
        self.input_purchase_date_error.setVisible(False)
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(20, 20, 20, 20)
        self.layout.setSpacing(15)

        self.layout.addWidget(self.label_dropdown)
        self.layout.addWidget(self.dropdown_select_storage)
        self.layout.addWidget(self.dropdown_select_storage_error)

        self.layout.addWidget(self.label_name)
        self.layout.addWidget(self.input_name)
        self.layout.addWidget(self.input_name_error)

        self.layout.addWidget(self.label_manufacture_number)
        self.layout.addWidget(self.input_manufacture_number)
        self.layout.addWidget(self.input_manufacture_number_error)

        self.layout.addWidget(self.label_quantity)
        self.layout.addWidget(self.input_quantity)
        self.layout.addWidget(self.input_quantity_error)

        self.layout.addWidget(self.label_unit)
        self.layout.addWidget(self.input_unit)
        self.layout.addWidget(self.input_unit_error)

        self.layout.addWidget(self.label_manufacture_date)
        self.layout.addWidget(self.manufacture_date)
        self.layout.addWidget(self.manufacture_date_error)

        self.layout.addWidget(self.label_price)
        self.layout.addWidget(self.input_price)
        self.layout.addWidget(self.input_price_error)

        self.layout.addWidget(self.label_purchase_source)
        self.layout.addWidget(self.input_purchase_source)
        self.layout.addWidget(self.input_purchase_source_error)
        
        self.layout.addWidget(self.label_purchase_date)
        self.layout.addWidget(self.input_purchase_date)
        self.layout.addWidget(self.input_purchase_date_error)

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

        self.button_container.accepted.connect(self.validate_fields)
        self.button_container.rejected.connect(self.reject)

        button_widget = QWidget()
        button_layout = QHBoxLayout(button_widget)
        button_layout.addStretch()
        button_layout.addWidget(self.button_container)
        button_layout.addStretch()
        button_layout.setContentsMargins(0, 0, 0, 0)
        button_layout.setSpacing(10)

        self.layout.addWidget(button_widget)

    def validate_fields(self):
        
        has_error = False
        
        current_time = self.min_datetime.toPyDateTime()
        
        storage_id = self.dropdown_select_storage.currentData()
        name = self.input_name.text().strip()
        manufacture_number = self.input_manufacture_number.text().strip()
        quantity = self.input_quantity.value()
        unit = self.input_unit.text().strip()
        manufacture_dt = self.manufacture_date.dateTime()
        price = self.input_price.value()
        purchase_source = self.input_purchase_source.text().strip()
        purchase_date = self.input_purchase_date.dateTime()

        if storage_id is None:
            
            self.dropdown_select_storage_error.setText("You did not select a warehouse")
            self.dropdown_select_storage_error.setVisible(True)
            
            self.log.warning("Input validation failed: 'storage' field is empty")
            
            has_error = True
            
        else:
            
            self.dropdown_select_storage_error.setVisible(False)
            
        if name == "":

            self.input_name_error.setText("You did not provide a name")
            self.input_name_error.setVisible(True)

            self.log.warning("Input validation failed: 'name' field is empty")

            has_error = True

        else:

            self.input_name_error.setVisible(False)

        if manufacture_number == "":

            self.input_manufacture_number_error.setText("You did not provide a serial number")
            self.input_manufacture_number_error.setVisible(True)

            self.log.warning("Input validation failed: 'manufacture_number' field is empty")

            has_error = True

        else:

            self.input_manufacture_number_error.setVisible(False)
            
        if quantity <= 1e-4:

            self.input_quantity_error.setText("Quantity must be at least 1")
            self.input_quantity_error.setVisible(True)

            self.log.warning("Input validation failed: 'quantity' field is invalid")

            has_error = True

        else:

            self.input_quantity_error.setVisible(False)

        if unit == "":

            self.input_unit_error.setText("You did not provide a unit of measure")
            self.input_unit_error.setVisible(True)

            self.log.warning("Input validation failed: 'unit' field is empty")

            has_error = True

        else:

            self.input_unit_error.setVisible(False)
            
        if manufacture_dt == current_time:
            
            self.manufacture_date_error.setText("Manufacturing date cannot be exactly the current time")
            self.manufacture_date_error.setVisible(True)
            
            self.log.warning("Input validation failed: 'manufacture_date' equals current time")
            
            has_error = True

        elif manufacture_dt < QDateTime(QDate(2000, 1, 1), QTime(0, 0)):
            
            self.manufacture_date_error.setText("Manufacturing year must be at least 2000")
            self.manufacture_date_error.setVisible(True)
            
            self.log.warning("Input validation failed: 'manufacture_date' field is invalid")
            
            has_error = True

        else:
            
            self.manufacture_date_error.setVisible(False)
            
        if purchase_date == current_time:
            
            self.input_purchase_date_error.setText("Purchase date cannot be exactly the current time")
            self.input_purchase_date_error.setVisible(True)
            
            self.log.warning("Input validation failed: 'purchase_date' equals current time")
            
            has_error = True

        elif purchase_date < QDateTime(QDate(2000, 1, 1), QTime(0, 0)):
            
            self.input_purchase_date_error.setText("Purchase year must be at least 2000")
            self.input_purchase_date_error.setVisible(True)
            
            self.log.warning("Input validation failed: 'purchase_date' field is invalid")
            
            has_error = True

        else:
            
            self.input_purchase_date_error.setVisible(False)

        if price < 1e-2:

            self.input_price_error.setText("Price cannot be negative")
            self.input_price_error.setVisible(True)

            self.log.warning("Input validation failed: 'price' field is invalid")

            has_error = True

        else:

            self.input_price_error.setVisible(False)

        if purchase_source == "":

            self.input_purchase_source_error.setText("You did not provide a purchase source")
            self.input_purchase_source_error.setVisible(True)

            self.log.warning("Input validation failed: 'purchase_source' field is empty")

            has_error = True

        else:

            self.input_purchase_source_error.setVisible(False)
        
        if has_error == False:
            
            self.accept()

    async def get_form_data(self) -> MaterialData:
        
        data = MaterialData(
            id = None,
            storage_id = self.dropdown_select_storage.currentData(),
            name = self.input_name.text() if self.input_name.text() != "" else None,
            manufacture_number = self.input_manufacture_number.text() if self.input_manufacture_number.text() != "" else None,
            quantity = self.input_quantity.value(),
            unit = self.input_unit.text() if self.input_unit.text() != "" else None,
            manufacture_date = self.manufacture_date.dateTime().toPyDateTime() if self.manufacture_date.dateTime() is not None else None,
            price = self.input_price.value(),
            purchase_source = self.input_purchase_source.text() if self.input_purchase_source.text() != "" else None,
            purchase_date = self.input_purchase_date.dateTime().toPyDateTime() if self.input_purchase_date.dateTime() is not None else None,
            inspection_date = datetime.now(Config.time.timezone_utc),
            uuid = None
        )
        
        try:
            
            possible_row_id = await queries.select_next_possible_row_material_id()
            
            data.id = possible_row_id
            
            qr_data = {data.id, StorageItemTypeEnum.MATERIAL}
            
            qr_code = QRCode(
                version = 1,
                error_correction = ERROR_CORRECT_H,
                box_size = 6,
                border = 4
            )
            qr_code.add_data(qr_data)
            qr_code.make(fit = True)
            
            qr_code_img = qr_code.make_image(fill_color = "black", back_color = "white").convert("RGB")

            logo = Image.open(self.logo_path).convert("RGBA")

            qr_width, qr_height = qr_code_img.size

            logo_size = int(qr_width * 0.2)
            
            logo = logo.resize((logo_size, logo_size), Image.LANCZOS)

            border_thickness = 4
            
            frame_color = (66, 133, 244, 255)
            bg_color = (255, 255, 255, 255) 

            logo_bg_size = (logo_size + 2 * border_thickness, logo_size + 2 * border_thickness)
            logo_bg = Image.new("RGBA", logo_bg_size, bg_color)

            draw = ImageDraw.Draw(logo_bg)
            draw.rectangle(
                [(0, 0), (logo_bg_size[0] - 1, logo_bg_size[1] - 1)], 
                outline = frame_color,
                width = border_thickness
            )

            logo_bg.paste(logo, (border_thickness, border_thickness), logo)

            pos = (qr_width - logo_bg_size[0] - 24, qr_height - logo_bg_size[1] - 24)

            qr_code_img = qr_code_img.convert("RGBA")
            qr_code_img.paste(logo_bg, pos, logo_bg)
            qr_code_img = qr_code_img.convert("RGB")

            if getattr(sys, 'frozen', False):
                
                base_dir = Path(sys.executable).parent / "qr_codes"

            else:
                
                base_dir = Config.qr_code.path
                
            now = datetime.now(Config.time.timezone_utc)
            year = str(now.year)
            month = f"{now.month:02}"

            qr_codes_dir = os.path.join(base_dir, year, month)
            
            os.makedirs(qr_codes_dir, exist_ok = True)
            
            name = data.name if data.name is not None else "unknown"
            
            safe_name = unicodedata.normalize('NFKD', name).encode('ascii', 'ignore').decode('ascii')
            safe_name = name.lower()
            safe_name = safe_name.replace(" ", "_")  
            safe_name = re.sub(r"[^a-z0-9_-]", "_", safe_name)  
            safe_name = re.sub(r"_+", "_", safe_name)          
            safe_name = safe_name.strip("_")  
            
            file_name = f"anyag_{possible_row_id}_{safe_name}.png"
            
            out_file = os.path.join(qr_codes_dir, file_name)

            qr_code_img.save(out_file)
            
            buffer = io.BytesIO()
            
            qr_code_img.save(buffer, format = "PNG")
            
            data.uuid = buffer.getvalue()
        
        except Exception as e:
            
            self.log.exception("Error generating QR code or saving file: %s" % str(e))
            raise
        
        self.log.debug("Form data: %s" % data)
        
        return data
    
    def update_dropdown_items(self, items: list[tuple[str, int]]) -> None:
        
        self.dropdown_select_storage.clear()
        self.dropdown_select_storage.addItem("")
        
        for text, id in items:
            
            self.dropdown_select_storage.addItem(text, id)
    
    def exec_async(self) -> asyncio.Future:
        
        self._future = asyncio.get_event_loop().create_future()
        
        self.input_name.clear()
        self.input_quantity.setValue(1)
        self.input_unit.clear()
        self.input_price.setValue(0)
        self.input_manufacture_number.clear()
        self.manufacture_date.setDateTime(self.min_datetime)
        self.input_purchase_source.clear()
        self.input_purchase_date.setDateTime(self.min_datetime)
        self.dropdown_select_storage.setCurrentIndex(0)
        
        self.input_name_error.setVisible(False)
        self.input_quantity_error.setVisible(False)
        self.input_unit_error.setVisible(False)
        self.input_price_error.setVisible(False)
        self.input_manufacture_number_error.setVisible(False)
        self.manufacture_date_error.setVisible(False)
        self.input_purchase_source_error.setVisible(False)
        self.input_purchase_date_error.setVisible(False)
        self.dropdown_select_storage_error.setVisible(False)
    
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

