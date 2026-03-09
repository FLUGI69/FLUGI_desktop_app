import os, sys
import logging
import asyncio
import typing as t
from qasync import asyncSlot
from datetime import datetime, date, timedelta
from base64 import b64encode
from pathlib import Path
from decimal import Decimal

from PyQt6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QListWidget,
    QPushButton,
    QLineEdit,
    QHeaderView,
    QFrame,
    QLabel,
    QListWidgetItem,
    QFormLayout,
    QComboBox,
    QTextEdit,
    QTableWidget,
    QScrollArea
)

from PyQt6.QtCore import Qt, QSize, pyqtSignal, QTimer, QUrl
from PyQt6.QtGui import QIcon, QFont, QPixmap, QCursor, QDesktopServices
from PyQt6.QtWebEngineWidgets import QWebEngineView

from markupsafe import Markup
from weasyprint import HTML

from utils.logger import LoggerMixin
from utils.dc.admin.rental_history import RentalHistoryData, RentalHistoryCacheData
from services.admin.rental_history_cache import RentalHistoryCacheService
from ..modal.admin.edit_rental_history import EditRentalHistoryModal
from ..modal.confirm_action import ConfirmActionModal
from utils.enums.storage_item_type_enum import StorageItemTypeEnum
from config import Config
from db import queries

if t.TYPE_CHECKING:
    
    from .admin import AdminView

class PriceQuotationContent(QWidget, LoggerMixin):

    log: logging.Logger
    
    def __init__(self,
        admin_view: 'AdminView'         
        ):
        
        super().__init__()
        
        self.admin_view = admin_view
        
        self.dropdown_items = admin_view.main_window.app.utility_calculator.available_currencies

        self.quotation_template = admin_view.main_window.app.templates["price_quotation"]
        
        self.other_work_prices = admin_view.main_window.other_work_prices
        
        self.__init_view()
     
    @staticmethod
    def icon(name: str) -> QIcon:
  
        return QIcon(os.path.join(Config.icon.icon_dir, name))
        
    def __init_view(self):
        
            main_layout = QHBoxLayout(self)

            self.scroll_area = QScrollArea()
            self.scroll_area.setWidgetResizable(True)
            self.scroll_area.setStyleSheet(Config.styleSheets.work_scroll)

            scroll_content = QWidget()
            scroll_layout = QVBoxLayout(scroll_content)
            scroll_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
            scroll_layout.setSpacing(20)

            scroll_layout.addWidget(self.set_currencies_section())
            scroll_layout.addWidget(self.set_client_header_section())
            scroll_layout.addWidget(self.set_work_details_section())
            scroll_layout.addWidget(self.set_additional_information_and_other_prices_section())

            self.scroll_area.setWidget(scroll_content)

            preview = self.set_preview_section()

            main_layout.addWidget(self.scroll_area, 3)
            main_layout.addWidget(preview, 2)

            self.update_preview()
    
    def set_currencies_section(self):
        
        frame = QFrame()
        layout = QFormLayout(frame)

        self.currency_dropdown = QComboBox()
        self.currency_dropdown.setObjectName("Dropdown")
        self.currency_dropdown.setStyleSheet(Config.styleSheets.dropdown_style)
        self.currency_dropdown.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.currency_dropdown.setFixedHeight(50)
        
        self.prepare_dropwdown_currencies()

        layout.addRow(self.currency_dropdown)
        
        return frame

    def set_client_header_section(self):
        
        frame = QFrame()
        layout = QFormLayout(frame)

        self.client_name = QLineEdit()
        self.client_name.setFixedHeight(50)
        self.client_name.setStyleSheet(Config.styleSheets.line_edit)
        self.client_name.setPlaceholderText("Client name (Example Company Ltd.)")
        
        self.client_address = QLineEdit()
        self.client_address.setFixedHeight(50)
        self.client_address.setStyleSheet(Config.styleSheets.line_edit)
        self.client_address.setPlaceholderText("Client address (1234 Example Street 11.)")
        
        self.client_country = QLineEdit()
        self.client_country.setFixedHeight(50)
        self.client_country.setStyleSheet(Config.styleSheets.line_edit)
        self.client_country.setPlaceholderText("Country (Example Country)")
        
        self.client_vat = QLineEdit()
        self.client_vat.setFixedHeight(50)
        self.client_vat.setStyleSheet(Config.styleSheets.line_edit)
        self.client_vat.setPlaceholderText("Tax number (VAT-12345678-121-232)")

        layout.addRow(self.client_name)
        layout.addRow(self.client_address)
        layout.addRow(self.client_country)
        layout.addRow(self.client_vat)

        return frame

    def set_work_details_section(self):
        
        frame = QFrame()
        layout = QVBoxLayout(frame)

        self.boat_name = QLineEdit()
        self.boat_name.setFixedHeight(50)
        self.boat_name.setStyleSheet(Config.styleSheets.line_edit)
        self.boat_name.setPlaceholderText("Ship name (MS Viktoria)")

        self.work_description = QTextEdit()
        self.work_description.setStyleSheet(Config.styleSheets.text_edit)
        self.work_description.setFixedHeight(150)
        self.work_description.setPlaceholderText("Work description (Heat pump replacement)")

        self.work_table = QTableWidget(0, 5)
        self.work_table.setStyleSheet(Config.styleSheets.table_widget)
        self.work_table.setHorizontalHeaderLabels(["Name", "Quantity", "Unit", "Net price", ""])
        self.work_table.setFixedHeight(250)
        self.work_table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.work_table.verticalHeader().setDefaultSectionSize(50)
        
        header = self.work_table.horizontalHeader()
        header.setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)
        header.setStretchLastSection(False)

        widths = [200, 200, 200, 200, 100]
        
        for i in range(self.work_table.columnCount()):
            
            header.setSectionResizeMode(i, QHeaderView.ResizeMode.Fixed)
            
            self.work_table.setColumnWidth(i, widths[i])

        add_row_btn = QPushButton("Add")
        add_row_btn.setObjectName("WorkBtn")
        add_row_btn.setStyleSheet(Config.styleSheets.work_btn)
        add_row_btn.setFixedWidth(200)
        add_row_btn.setFixedHeight(50)
        add_row_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        add_row_btn.clicked.connect(self.add_row)
        
        label = QLabel("Work details")
        label.setStyleSheet(Config.styleSheets.label)

        layout.addWidget(label)
        
        layout.addWidget(self.boat_name)
        layout.addWidget(self.work_description)
        layout.addWidget(self.work_table)
        layout.addWidget(add_row_btn)

        return frame

    def set_additional_information_and_other_prices_section(self):
        
        frame = QFrame()
        layout = QVBoxLayout(frame)
        
        label = QLabel("Additional information")
        label.setStyleSheet(Config.styleSheets.label)

        layout.addWidget(label)
        
        self.additional_info = QTextEdit()
        self.additional_info.setStyleSheet(Config.styleSheets.text_edit)
        self.additional_info.setFixedHeight(150)
        self.additional_info.setPlaceholderText("Additional information")
        
        layout.addWidget(self.additional_info)

        return frame
    
    def set_preview_section(self):

        frame = QFrame()
        layout = QVBoxLayout(frame)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        scroll = QScrollArea()
        scroll.setStyleSheet(Config.styleSheets.scroll_area)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        self.web_view = QWebEngineView()
        self.web_view.setMinimumSize(1000, 1400)

        scroll.setWidget(self.web_view)

        btn_layout = QHBoxLayout()
        
        self.render_button = QPushButton("Update Preview")
        self.render_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.render_button.setObjectName("WorkBtn")
        self.render_button.setStyleSheet(Config.styleSheets.work_btn)
        self.render_button.setFixedSize(200, 50)
        self.render_button.clicked.connect(self.update_preview)

        self.export_button = QPushButton("Export PDF")
        self.export_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.export_button.setObjectName("WorkBtn")
        self.export_button.setStyleSheet(Config.styleSheets.work_btn)
        self.export_button.setFixedSize(200, 50)
        self.export_button.clicked.connect(self.export_pdf)

        btn_layout.addWidget(self.render_button)
        btn_layout.addWidget(self.export_button)

        layout.addWidget(scroll)
        layout.addLayout(btn_layout)

        return frame
    
    def update_preview(self):
        
        html = self.render_html()
        self.web_view.setHtml(html)
        
    def export_pdf(self):
        
        html = self.render_html()
        
        if html != "":
      
            quotations_dir = "quotations"
            
            if os.path.exists(quotations_dir) is False:
                
                os.makedirs(quotations_dir)
            
            current_timestamp = datetime.now(Config.time.timezone_utc).strftime("%Y%m%d%H%M%S%f")
            
            safe_boat_name = self.boat_name.text().strip().replace(" ", "_")
            
            pdf_file = os.path.join(quotations_dir, f"{safe_boat_name}_[{current_timestamp}].pdf")
            
            HTML(string = html).write_pdf(pdf_file)
            
            QDesktopServices.openUrl(QUrl.fromLocalFile(pdf_file))
        
    def add_row(self):
        
        row = self.work_table.rowCount()
        
        self.work_table.insertRow(row)

        remove_btn = QPushButton()
        remove_btn.setObjectName("WorkBtn")
        remove_btn.setStyleSheet(Config.styleSheets.work_btn)
        remove_btn.setFixedWidth(100)
        remove_btn.setFixedHeight(50)
        remove_btn.setIcon(PriceQuotationContent.icon("trash.svg"))
        remove_btn.setIconSize(QSize(20, 20))
        remove_btn.setToolTip("Delete")
        remove_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        remove_btn.clicked.connect(lambda _, r = row: self.remove_row(r))
        
        self.work_table.setCellWidget(row, 4, remove_btn)
        
    def remove_row(self, row):
        
        self.work_table.removeRow(row)
        
        for r in range(self.work_table.rowCount()):
            btn = self.work_table.cellWidget(r, 4)
            if btn:
                btn.clicked.disconnect()
                btn.clicked.connect(lambda _, r=r: self.remove_row(r))
    
    def svg_to_base64(self, filename):
        
        with open(filename, "rb") as f:
            
            return b64encode(f.read()).decode("utf-8")

    def get_table_data(self):
        data = []

        for row in range(self.work_table.rowCount()):
            name_item = self.work_table.item(row, 0)
            qty_item = self.work_table.item(row, 1)
            unit_item = self.work_table.item(row, 2)
            price_item = self.work_table.item(row, 3)

            if name_item and qty_item and unit_item and price_item:
         
                try:
                    qty = float(qty_item.text())
                except ValueError:
                    qty = 0

                if qty.is_integer():
                    qty_display = str(int(qty))
                else:
                    qty_display = str(qty)

                price_text = price_item.text().replace("Ft", "").replace(" ", "")
                try:
                    price = float(price_text)
                except ValueError:
                    price = 0

                total_price = price * qty
                price_display = f"€ {total_price:.2f}" 

                data.append({
                    "name": name_item.text(),
                    "qty": qty_display,
                    "unit": unit_item.text(),
                    "price": price_display
                })

        return data
    
    def render_html(self):
    
        today = date.today()
        
        valid_until = today + timedelta(days = 7)
        
        order_number = Markup(f"{today.strftime('%Y')}{2:04d}")
        
        svg_dir_path = os.path.join(os.path.dirname(sys.executable), "_internal/gui/static/assets/img/svg") \
            if getattr(sys, 'frozen', False) else os.path.join(os.path.dirname(__file__), "../../static/assets/img/svg")
    
        cts_logo = self.svg_to_base64(os.path.join(svg_dir_path, "cts_logo.svg")) # gui\static\assets\img\svg\cts_logo.svg
        cred_logo = self.svg_to_base64(os.path.join(svg_dir_path, "credithworthiness_logo.svg")) # gui\static\assets\img\svg\credithworthiness_logo.svg
        
        client = {
            "name": self.client_name.text(),
            "address": self.client_address.text(),
            "country": self.client_country.text(),
            "vat": self.client_vat.text()
        }
        
        table_data = self.get_table_data()
        
        html = self.quotation_template.render(
            cts_logo = cts_logo,
            cred_logo = cred_logo,
            data_lenght = "less-than-six" if len(table_data) < 6 else "greater-than-six",
            boat_name = self.boat_name.text().strip(),
            order_number = order_number,
            client = client,
            data = table_data,
            prices = self.other_work_prices.model_dump(),
            description = Markup(self.work_description.toPlainText().replace("\n","<br>")),
            information = Markup(self.additional_info.toPlainText().replace("\n","<br>")),
            total_price = 1780,
            current_date = Markup(today.strftime("%Y. %m. %d.")),
            valid_until_date = Markup(valid_until.strftime("%Y. %m. %d.")),
            max_rows = len(table_data),
            _ = lambda x: x
        )
        
        return html
    
    def prepare_dropwdown_currencies(self):
        
        if len(self.dropdown_items) > 0:
            
            self.currency_dropdown.clear()
            self.currency_dropdown.addItem("")
            
            for text in self.dropdown_items:
                
                self.currency_dropdown.addItem(text, text)

