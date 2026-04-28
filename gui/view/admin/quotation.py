import os, sys
import logging
import asyncio
import json
import re
import typing as t
from datetime import datetime, date, timedelta
from decimal import Decimal
from base64 import b64encode
from uuid import uuid4
from openai import OpenAIError

from PyQt6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QPushButton,
    QLineEdit,
    QHeaderView,
    QFrame,
    QLabel,
    QFormLayout,
    QComboBox,
    QTextEdit,
    QTableWidget,
    QScrollArea,
    QTabWidget,
    QCheckBox
)

from PyQt6.QtCore import Qt, QSize, QUrl, pyqtSignal
from PyQt6.QtGui import QIcon, QCursor, QDesktopServices, QColor
from PyQt6.QtWebEngineWidgets import QWebEngineView

from markupsafe import Markup
from weasyprint import HTML

from utils.logger import LoggerMixin
from utils.enums.tax_number_type_enum import TaxNumberTypeEnum
from utils.enums.hun_price_category_enum import HunPriceCategoryEnum
from utils.enums.hun_price_tier_enum import HunPriceTierEnum
from utils.dc.admin.quotation import QuotationData, QuotationTableData, ClientData
from utils.dc.admin.work.other_work_prices_hun import OtherWorkPricesHun
from config import Config
from db import queries

if t.TYPE_CHECKING:
    
    from .admin import AdminView

class PriceQuotationContent(QWidget, LoggerMixin):

    log: logging.Logger
    
    refresh_other_work_prices = pyqtSignal()
    
    refresh_other_work_prices_hun = pyqtSignal()

    def __init__(self,
        admin_view: 'AdminView'         
        ):
        
        super().__init__()
        
        self.admin_view = admin_view
        
        self.utility_calculator = admin_view.main_window.app.utility_calculator
        
        self.available_currencies = self.utility_calculator.available_currencies

        self.quotation_template = admin_view.main_window.app.templates["price_quotation"]
        
        self.jinja_env = admin_view.main_window.app.jinja_env
        
        self.openai = admin_view.main_window.app.openai
        
        self._openai_lock = admin_view.main_window.app.openapi_lock
        
        self._preview_order_number = Markup(f"{date.today().strftime('%Y')}????")
        
        self.__init_view()
        
        asyncio.ensure_future(self._fetch_preview_order_number())
        asyncio.ensure_future(self._fetch_existing_clients())
     
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

            scroll_layout.addWidget(self.set_language_section())
            scroll_layout.addWidget(self.set_currencies_section())
            scroll_layout.addWidget(self.set_client_header_section())
            scroll_layout.addWidget(self.set_work_details_section())
            scroll_layout.addWidget(self.set_additional_information_and_other_prices_section())

            self.scroll_area.setWidget(scroll_content)

            preview = self.set_preview_section()

            main_layout.addWidget(self.scroll_area, 3)
            main_layout.addWidget(preview, 2)

            self.update_preview()
    
    def set_language_section(self):
        
        frame = QFrame()
        layout = QVBoxLayout(frame)
        
        lang_label = QLabel("Nyelv")
        lang_label.setStyleSheet(Config.styleSheets.label)
        
        self.language_dropdown = QComboBox()
        self.language_dropdown.setObjectName("Dropdown")
        self.language_dropdown.setStyleSheet(Config.styleSheets.dropdown_style)
        self.language_dropdown.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.language_dropdown.setFixedHeight(50)
        
        for code, name in Config.lang.lang_codes.items():
            
            self.language_dropdown.addItem(name, code)
        
        self.language_dropdown.setCurrentIndex(0)
        
        layout.addWidget(lang_label)
        layout.addWidget(self.language_dropdown)
        
        return frame
    
    def set_currencies_section(self):
        
        frame = QFrame()
        layout = QHBoxLayout(frame)

        input_label = QLabel("Ár beviteli pénznem")
        input_label.setStyleSheet(Config.styleSheets.label)
        
        self.currency_input_dropdown = QComboBox()
        self.currency_input_dropdown.setObjectName("Dropdown")
        self.currency_input_dropdown.setStyleSheet(Config.styleSheets.dropdown_style)
        self.currency_input_dropdown.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.currency_input_dropdown.setFixedHeight(50)

        output_label = QLabel("Kimeneti pénznem")
        output_label.setStyleSheet(Config.styleSheets.label)
        
        self.currency_output_dropdown = QComboBox()
        self.currency_output_dropdown.setObjectName("Dropdown")
        self.currency_output_dropdown.setStyleSheet(Config.styleSheets.dropdown_style)
        self.currency_output_dropdown.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.currency_output_dropdown.setFixedHeight(50)
        
        self.prepare_dropwdown_currencies()

        left = QVBoxLayout()
        left.addWidget(input_label)
        left.addWidget(self.currency_input_dropdown)
        
        right = QVBoxLayout()
        right.addWidget(output_label)
        right.addWidget(self.currency_output_dropdown)

        layout.addLayout(left)
        layout.addLayout(right)
        
        return frame

    def set_client_header_section(self):
        
        frame = QFrame()
        frame_layout = QVBoxLayout(frame)
        
        self.client_tab_widget = QTabWidget()
        self.client_tab_widget.tabBar().setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

        new_client_tab = QWidget()
        new_client_layout = QFormLayout(new_client_tab)
        
        self.client_name = QLineEdit()
        self.client_name.setFixedHeight(50)
        self.client_name.setStyleSheet(Config.styleSheets.line_edit)
        self.client_name.setPlaceholderText("Megrendelő neve (Example Company Ltd.)")
        
        self.client_name_error = QLabel()
        self.client_name_error.setObjectName("error")
        self.client_name_error.setVisible(False)
        
        self.client_address = QLineEdit()
        self.client_address.setFixedHeight(50)
        self.client_address.setStyleSheet(Config.styleSheets.line_edit)
        self.client_address.setPlaceholderText("Megrendelő címe (Example Street 1, Budapest, Hungary)")
        
        self.client_country = QLineEdit()
        self.client_country.setFixedHeight(50)
        self.client_country.setStyleSheet(Config.styleSheets.line_edit)
        self.client_country.setPlaceholderText("Ország (Hungary)")
        
        self.client_vat = QLineEdit()
        self.client_vat.setFixedHeight(50)
        self.client_vat.setStyleSheet(Config.styleSheets.line_edit)
        
        self.client_vat_error = QLabel()
        self.client_vat_error.setObjectName("error")
        self.client_vat_error.setVisible(False)
        
        self.tax_type_dropdown = QComboBox()
        self.tax_type_dropdown.setObjectName("Dropdown")
        self.tax_type_dropdown.setStyleSheet(Config.styleSheets.dropdown_style)
        self.tax_type_dropdown.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.tax_type_dropdown.setFixedHeight(50)
        self.tax_type_dropdown.setFixedWidth(150)
        
        self.tax_type_dropdown.addItem("VAT", TaxNumberTypeEnum.VAT)
        self.tax_type_dropdown.addItem("UID", TaxNumberTypeEnum.UID)
        self.tax_type_dropdown.addItem("EIN / TIN", TaxNumberTypeEnum.EIN)
        self.tax_type_dropdown.addItem("MVA", TaxNumberTypeEnum.MVA)
        self.tax_type_dropdown.addItem("VKN", TaxNumberTypeEnum.VKN)
        
        self.tax_type_dropdown.setCurrentIndex(0)
        self.tax_type_dropdown.currentIndexChanged.connect(self._on_tax_type_changed)
        
        self._on_tax_type_changed()
        
        tax_layout = QHBoxLayout()
        tax_layout.addWidget(self.tax_type_dropdown)
        tax_layout.addWidget(self.client_vat)

        new_client_layout.addRow(self.client_name)
        new_client_layout.addRow(self.client_name_error)
        new_client_layout.addRow(self.client_address)
        new_client_layout.addRow(self.client_country)
        new_client_layout.addRow(tax_layout)
        new_client_layout.addRow(self.client_vat_error)
        
        existing_client_tab = QWidget()
        existing_client_layout = QVBoxLayout(existing_client_tab)
        
        self.existing_client_dropdown = QComboBox()
        self.existing_client_dropdown.setObjectName("Dropdown")
        self.existing_client_dropdown.setStyleSheet(Config.styleSheets.dropdown_style)
        self.existing_client_dropdown.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.existing_client_dropdown.setFixedHeight(50)
        self.existing_client_dropdown.setMaxVisibleItems(15)
        self.existing_client_dropdown.addItem("-- Válassz klienst --", None)
        self.existing_client_dropdown.currentIndexChanged.connect(
            lambda: asyncio.ensure_future(self._on_existing_client_changed())
        )
        
        existing_fields_layout = QFormLayout()
        
        self.existing_client_name = QLineEdit()
        self.existing_client_name.setFixedHeight(50)
        self.existing_client_name.setStyleSheet(Config.styleSheets.line_edit)
        self.existing_client_name.setPlaceholderText("Megrendelő neve")
        
        self.existing_client_name_error = QLabel()
        self.existing_client_name_error.setObjectName("error")
        self.existing_client_name_error.setVisible(False)
        
        self.existing_client_address = QLineEdit()
        self.existing_client_address.setFixedHeight(50)
        self.existing_client_address.setStyleSheet(Config.styleSheets.line_edit)
        self.existing_client_address.setPlaceholderText("Megrendelő címe")
        
        self.existing_client_country = QLineEdit()
        self.existing_client_country.setFixedHeight(50)
        self.existing_client_country.setStyleSheet(Config.styleSheets.line_edit)
        self.existing_client_country.setPlaceholderText("Ország")
        
        self.existing_client_vat = QLineEdit()
        self.existing_client_vat.setFixedHeight(50)
        self.existing_client_vat.setStyleSheet(Config.styleSheets.line_edit)
        
        self.existing_client_vat_error = QLabel()
        self.existing_client_vat_error.setObjectName("error")
        self.existing_client_vat_error.setVisible(False)
        
        self.existing_tax_type_dropdown = QComboBox()
        self.existing_tax_type_dropdown.setObjectName("Dropdown")
        self.existing_tax_type_dropdown.setStyleSheet(Config.styleSheets.dropdown_style)
        self.existing_tax_type_dropdown.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.existing_tax_type_dropdown.setFixedHeight(50)
        self.existing_tax_type_dropdown.setFixedWidth(150)
        
        self.existing_tax_type_dropdown.addItem("VAT", TaxNumberTypeEnum.VAT)
        self.existing_tax_type_dropdown.addItem("UID", TaxNumberTypeEnum.UID)
        self.existing_tax_type_dropdown.addItem("EIN / TIN", TaxNumberTypeEnum.EIN)
        self.existing_tax_type_dropdown.addItem("MVA", TaxNumberTypeEnum.MVA)
        self.existing_tax_type_dropdown.addItem("VKN", TaxNumberTypeEnum.VKN)
        
        self.existing_tax_type_dropdown.setCurrentIndex(0)
        self.existing_tax_type_dropdown.currentIndexChanged.connect(self._on_existing_tax_type_changed)
        
        self._on_existing_tax_type_changed()
        
        existing_tax_layout = QHBoxLayout()
        existing_tax_layout.addWidget(self.existing_tax_type_dropdown)
        existing_tax_layout.addWidget(self.existing_client_vat)
        
        existing_fields_layout.addRow(self.existing_client_name)
        existing_fields_layout.addRow(self.existing_client_name_error)
        existing_fields_layout.addRow(self.existing_client_address)
        existing_fields_layout.addRow(self.existing_client_country)
        existing_fields_layout.addRow(existing_tax_layout)
        existing_fields_layout.addRow(self.existing_client_vat_error)
        
        existing_client_layout.addWidget(self.existing_client_dropdown)
        existing_client_layout.addLayout(existing_fields_layout)
        
        self.client_tab_widget.addTab(new_client_tab, "Új kliens")
        self.client_tab_widget.addTab(existing_client_tab, "Meglévő kliens")
        
        frame_layout.addWidget(self.client_tab_widget)

        return frame

    def set_work_details_section(self):
        
        frame = QFrame()
        layout = QVBoxLayout(frame)

        self.boat_name = QLineEdit()
        self.boat_name.setFixedHeight(50)
        self.boat_name.setStyleSheet(Config.styleSheets.line_edit)
        self.boat_name.setPlaceholderText("Hajó neve (MS Viktoria)")

        self.work_description = QTextEdit()
        self.work_description.setAcceptRichText(False)
        self.work_description.setStyleSheet(Config.styleSheets.text_edit)
        self.work_description.setFixedHeight(150)
        self.work_description.setPlaceholderText("Munka leírása (Hőlégszivattyú csere)")

        vat_layout = QHBoxLayout()
        
        self.surcharge_dropdown = QComboBox()
        self.surcharge_dropdown.setObjectName("Dropdown")
        self.surcharge_dropdown.setStyleSheet(Config.styleSheets.dropdown_style)
        self.surcharge_dropdown.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.surcharge_dropdown.setFixedHeight(50)
        self.surcharge_dropdown.addItem("Nincs felár", False)
        self.surcharge_dropdown.addItem("Felár %", True)
        self.surcharge_dropdown.setCurrentIndex(0)
        
        self.surcharge_percentage_input = QLineEdit()
        self.surcharge_percentage_input.setFixedHeight(50)
        self.surcharge_percentage_input.setFixedWidth(120)
        self.surcharge_percentage_input.setStyleSheet(Config.styleSheets.line_edit)
        self.surcharge_percentage_input.setPlaceholderText("%")
        
        vat_layout.addWidget(self.surcharge_dropdown)
        vat_layout.addWidget(self.surcharge_percentage_input)
        vat_layout.addStretch()
        
        layout.addLayout(vat_layout)

        self.work_table = QTableWidget(0, 5)
        self.work_table.setStyleSheet(Config.styleSheets.table_widget)
        self.work_table.setHorizontalHeaderLabels(["Megnevezés", "Mennyiség", "Mennyiségi egység", "Netto ár", ""])
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

        add_row_btn = QPushButton("Hozzáadás")
        add_row_btn.setObjectName("WorkBtn")
        add_row_btn.setStyleSheet(Config.styleSheets.work_btn)
        add_row_btn.setFixedWidth(200)
        add_row_btn.setFixedHeight(50)
        add_row_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        add_row_btn.clicked.connect(self.add_row)
        
        label = QLabel("Munka részletei")
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
        layout.setSpacing(2)
        
        label = QLabel("További információk")
        label.setStyleSheet(Config.styleSheets.label)
        label.setContentsMargins(0, 0, 0, 0)

        layout.addWidget(label)
        
        self.additional_info = QTextEdit()
        self.additional_info.setAcceptRichText(False)
        self.additional_info.setStyleSheet(Config.styleSheets.text_edit)
        self.additional_info.setFixedHeight(150)
        self.additional_info.setPlaceholderText("Kiegészítő információk")
        
        layout.addWidget(self.additional_info)

        checkbox_layout = QHBoxLayout()
        
        self.custom_prices_checkbox = QCheckBox("Egyedi árak módosítása (EUR-ban megadva)")
        self.custom_prices_checkbox.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.custom_prices_checkbox.setStyleSheet(Config.styleSheets.label)
        self.custom_prices_checkbox.stateChanged.connect(self._on_custom_prices_toggled)
        
        checkbox_layout.addWidget(self.custom_prices_checkbox)
        checkbox_layout.addStretch()
        
        layout.addLayout(checkbox_layout)
        
        self.custom_prices_container = QWidget()
        self.custom_prices_container.setVisible(False)
        prices_layout = QFormLayout(self.custom_prices_container)
        prices_layout.setSpacing(8)
        
        self.price_work_during_hours = QLineEdit()
        self.price_work_during_hours.setFixedHeight(50)
        self.price_work_during_hours.setStyleSheet(Config.styleSheets.line_edit)
        self.price_work_during_hours.setPlaceholderText("Munka munkaidőben")
        
        self.price_work_outside_hours = QLineEdit()
        self.price_work_outside_hours.setFixedHeight(50)
        self.price_work_outside_hours.setStyleSheet(Config.styleSheets.line_edit)
        self.price_work_outside_hours.setPlaceholderText("Munkaidőn kívül és szombaton")
        
        self.price_work_sundays = QLineEdit()
        self.price_work_sundays.setFixedHeight(50)
        self.price_work_sundays.setStyleSheet(Config.styleSheets.line_edit)
        self.price_work_sundays.setPlaceholderText("Vasárnap és ünnepnapokon +100%")
        
        self.price_travel_budapest = QLineEdit()
        self.price_travel_budapest.setFixedHeight(50)
        self.price_travel_budapest.setStyleSheet(Config.styleSheets.line_edit)
        self.price_travel_budapest.setPlaceholderText("Utazás Budapesten belül")
        
        self.price_travel_outside = QLineEdit()
        self.price_travel_outside.setFixedHeight(50)
        self.price_travel_outside.setStyleSheet(Config.styleSheets.line_edit)
        self.price_travel_outside.setPlaceholderText("Utazás Budapesten kívül / külföld")
        
        self.price_travel_time = QLineEdit()
        self.price_travel_time.setFixedHeight(50)
        self.price_travel_time.setStyleSheet(Config.styleSheets.line_edit)
        self.price_travel_time.setPlaceholderText("Utazási idő")
        
        self.price_travel_time_outside = QLineEdit()
        self.price_travel_time_outside.setFixedHeight(50)
        self.price_travel_time_outside.setStyleSheet(Config.styleSheets.line_edit)
        self.price_travel_time_outside.setPlaceholderText("Utazási idő munkaidőn kívül +50%")
        
        self.price_travel_time_sundays = QLineEdit()
        self.price_travel_time_sundays.setFixedHeight(50)
        self.price_travel_time_sundays.setStyleSheet(Config.styleSheets.line_edit)
        self.price_travel_time_sundays.setPlaceholderText("Utazási idő vasárnap +100%")
        
        self.price_accommodation = QLineEdit()
        self.price_accommodation.setFixedHeight(50)
        self.price_accommodation.setStyleSheet(Config.styleSheets.line_edit)
        self.price_accommodation.setPlaceholderText("Szállás")
        
        prices_layout.addRow(QLabel("Munka munkaidőben:"), self.price_work_during_hours)
        prices_layout.addRow(QLabel("Munkaidőn kívül és szombaton:"), self.price_work_outside_hours)
        prices_layout.addRow(QLabel("Vasárnap és ünnepnapokon +100%:"), self.price_work_sundays)
        prices_layout.addRow(QLabel("Utazás Budapesten belül:"), self.price_travel_budapest)
        prices_layout.addRow(QLabel("Utazás Budapesten kívül / külföld:"), self.price_travel_outside)
        prices_layout.addRow(QLabel("Utazási idő:"), self.price_travel_time)
        prices_layout.addRow(QLabel("Utazási idő munkaidőn kívül +50%:"), self.price_travel_time_outside)
        prices_layout.addRow(QLabel("Utazási idő vasárnap +100%:"), self.price_travel_time_sundays)
        prices_layout.addRow(QLabel("Szállás:"), self.price_accommodation)
        
        prices_btn_layout = QHBoxLayout()
        
        self.load_prices_btn = QPushButton("Árak betöltése")
        self.load_prices_btn.setObjectName("WorkBtn")
        self.load_prices_btn.setStyleSheet(Config.styleSheets.work_btn)
        self.load_prices_btn.setFixedSize(200, 50)
        self.load_prices_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.load_prices_btn.clicked.connect(self._load_current_prices)
        
        self.save_prices_btn = QPushButton("Árak mentése")
        self.save_prices_btn.setObjectName("WorkBtn")
        self.save_prices_btn.setStyleSheet(Config.styleSheets.work_btn)
        self.save_prices_btn.setFixedSize(200, 50)
        self.save_prices_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.save_prices_btn.clicked.connect(lambda: asyncio.ensure_future(self._save_other_work_prices()))
        
        prices_btn_layout.addWidget(self.load_prices_btn)
        prices_btn_layout.addWidget(self.save_prices_btn)
        prices_btn_layout.addStretch()
        
        prices_layout.addRow(prices_btn_layout)
        
        layout.addWidget(self.custom_prices_container)
        
        hun_checkbox_layout = QHBoxLayout()
        
        self.custom_prices_hun_checkbox = QCheckBox("Magyar árak módosítása (HUF + ÁFA)")
        self.custom_prices_hun_checkbox.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.custom_prices_hun_checkbox.setStyleSheet(Config.styleSheets.label)
        self.custom_prices_hun_checkbox.stateChanged.connect(self._on_custom_prices_hun_toggled)
        
        hun_checkbox_layout.addWidget(self.custom_prices_hun_checkbox)
        hun_checkbox_layout.addStretch()
        
        layout.addLayout(hun_checkbox_layout)
        
        self.custom_prices_hun_container = QWidget()
        self.custom_prices_hun_container.setVisible(False)
        hun_prices_layout = QFormLayout(self.custom_prices_hun_container)
        hun_prices_layout.setSpacing(8)
        
        hun_prices_layout.addRow(QLabel("Felmérés és szállítás rezsióradíja:"))
        
        self.hun_survey_weekday = QLineEdit()
        self.hun_survey_weekday.setFixedHeight(50)
        self.hun_survey_weekday.setStyleSheet(Config.styleSheets.line_edit)
        self.hun_survey_weekday.setPlaceholderText("Hétköznap H-P 08:00-17:00")
        
        self.hun_survey_weekend = QLineEdit()
        self.hun_survey_weekend.setFixedHeight(50)
        self.hun_survey_weekend.setStyleSheet(Config.styleSheets.line_edit)
        self.hun_survey_weekend.setPlaceholderText("Munkaidőn kívül és szombaton +50%")
        
        self.hun_survey_sunday = QLineEdit()
        self.hun_survey_sunday.setFixedHeight(50)
        self.hun_survey_sunday.setStyleSheet(Config.styleSheets.line_edit)
        self.hun_survey_sunday.setPlaceholderText("Vasárnap ünnepnapokon +100%")
        
        hun_prices_layout.addRow(QLabel("Hétköznap H-P 08:00-17:00:"), self.hun_survey_weekday)
        hun_prices_layout.addRow(QLabel("Munkaidőn kívül és szombaton +50%:"), self.hun_survey_weekend)
        hun_prices_layout.addRow(QLabel("Vasárnap ünnepnapokon +100%:"), self.hun_survey_sunday)
        
        hun_prices_layout.addRow(QLabel(""))
        hun_prices_layout.addRow(QLabel("Javítás és karbantartás rezsióradíja:"))
        
        self.hun_repair_weekday = QLineEdit()
        self.hun_repair_weekday.setFixedHeight(50)
        self.hun_repair_weekday.setStyleSheet(Config.styleSheets.line_edit)
        self.hun_repair_weekday.setPlaceholderText("Hétköznap H-P 08:00-17:00")
        
        self.hun_repair_weekend = QLineEdit()
        self.hun_repair_weekend.setFixedHeight(50)
        self.hun_repair_weekend.setStyleSheet(Config.styleSheets.line_edit)
        self.hun_repair_weekend.setPlaceholderText("Munkaidőn kívül és szombaton +50%")
        
        self.hun_repair_sunday = QLineEdit()
        self.hun_repair_sunday.setFixedHeight(50)
        self.hun_repair_sunday.setStyleSheet(Config.styleSheets.line_edit)
        self.hun_repair_sunday.setPlaceholderText("Vasárnap ünnepnapokon +100%")
        
        hun_prices_layout.addRow(QLabel("Hétköznap H-P 08:00-17:00:"), self.hun_repair_weekday)
        hun_prices_layout.addRow(QLabel("Munkaidőn kívül és szombaton +50%:"), self.hun_repair_weekend)
        hun_prices_layout.addRow(QLabel("Vasárnap ünnepnapokon +100%:"), self.hun_repair_sunday)
        
        hun_prices_layout.addRow(QLabel(""))
        hun_prices_layout.addRow(QLabel("Kiszállási díjak:"))
        
        self.hun_travel_budapest = QLineEdit()
        self.hun_travel_budapest.setFixedHeight(50)
        self.hun_travel_budapest.setStyleSheet(Config.styleSheets.line_edit)
        self.hun_travel_budapest.setPlaceholderText("Budapest területén / alkalom")
        
        self.hun_travel_outside_km = QLineEdit()
        self.hun_travel_outside_km.setFixedHeight(50)
        self.hun_travel_outside_km.setStyleSheet(Config.styleSheets.line_edit)
        self.hun_travel_outside_km.setPlaceholderText("Vidékre / km")
        
        hun_prices_layout.addRow(QLabel("Budapest területén (/ alkalom):"), self.hun_travel_budapest)
        hun_prices_layout.addRow(QLabel("Vidékre (/ km):"), self.hun_travel_outside_km)
        
        hun_prices_layout.addRow(QLabel(""))
        hun_prices_layout.addRow(QLabel("Utazási idő vidékre:"))
        
        self.hun_travel_time_weekday = QLineEdit()
        self.hun_travel_time_weekday.setFixedHeight(50)
        self.hun_travel_time_weekday.setStyleSheet(Config.styleSheets.line_edit)
        self.hun_travel_time_weekday.setPlaceholderText("Hétköznap H-P 08:00-17:00")
        
        self.hun_travel_time_weekend = QLineEdit()
        self.hun_travel_time_weekend.setFixedHeight(50)
        self.hun_travel_time_weekend.setStyleSheet(Config.styleSheets.line_edit)
        self.hun_travel_time_weekend.setPlaceholderText("Munkaidőn kívül és szombaton +50%")
        
        self.hun_travel_time_sunday = QLineEdit()
        self.hun_travel_time_sunday.setFixedHeight(50)
        self.hun_travel_time_sunday.setStyleSheet(Config.styleSheets.line_edit)
        self.hun_travel_time_sunday.setPlaceholderText("Vasárnap ünnepnapokon +100%")
        
        hun_prices_layout.addRow(QLabel("Hétköznap H-P 08:00-17:00:"), self.hun_travel_time_weekday)
        hun_prices_layout.addRow(QLabel("Munkaidőn kívül és szombaton +50%:"), self.hun_travel_time_weekend)
        hun_prices_layout.addRow(QLabel("Vasárnap ünnepnapokon +100%:"), self.hun_travel_time_sunday)
        
        hun_prices_btn_layout = QHBoxLayout()
        
        self.load_prices_hun_btn = QPushButton("HUF árak betöltése")
        self.load_prices_hun_btn.setObjectName("WorkBtn")
        self.load_prices_hun_btn.setStyleSheet(Config.styleSheets.work_btn)
        self.load_prices_hun_btn.setFixedSize(200, 50)
        self.load_prices_hun_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.load_prices_hun_btn.clicked.connect(self._load_current_prices_hun)
        
        self.save_prices_hun_btn = QPushButton("HUF árak mentése")
        self.save_prices_hun_btn.setObjectName("WorkBtn")
        self.save_prices_hun_btn.setStyleSheet(Config.styleSheets.work_btn)
        self.save_prices_hun_btn.setFixedSize(200, 50)
        self.save_prices_hun_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.save_prices_hun_btn.clicked.connect(lambda: asyncio.ensure_future(self._save_other_work_prices_hun()))
        
        hun_prices_btn_layout.addWidget(self.load_prices_hun_btn)
        hun_prices_btn_layout.addWidget(self.save_prices_hun_btn)
        hun_prices_btn_layout.addStretch()
        
        hun_prices_layout.addRow(hun_prices_btn_layout)
        
        layout.addWidget(self.custom_prices_hun_container)

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
        self.web_view.page().setBackgroundColor(QColor("#363636"))
        self.web_view.setVisible(False)
        self.web_view.loadFinished.connect(lambda ok: self.web_view.setVisible(True))

        scroll.setWidget(self.web_view)

        btn_layout = QHBoxLayout()
        
        self.render_button = QPushButton("Előnézet frissítése")
        self.render_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.render_button.setObjectName("WorkBtn")
        self.render_button.setStyleSheet(Config.styleSheets.work_btn)
        self.render_button.setFixedSize(200, 50)
        self.render_button.clicked.connect(self.update_preview)

        self.export_button = QPushButton("PDF exportálása")
        self.export_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.export_button.setObjectName("WorkBtn")
        self.export_button.setStyleSheet(Config.styleSheets.work_btn)
        self.export_button.setFixedSize(200, 50)
        self.export_button.clicked.connect(lambda: asyncio.ensure_future(self._export_pdf_async()))

        btn_layout.addWidget(self.render_button)
        btn_layout.addWidget(self.export_button)

        layout.addWidget(scroll)
        layout.addLayout(btn_layout)

        return frame
    
    def update_preview(self):
        
        html = self.render_html()
        self.web_view.setHtml(html)
    
    async def _fetch_preview_order_number(self):
        
        try:
            
            self._preview_order_number = await queries.select_next_order_number_preview()
            
            self.log.debug("Preview order number: %s" % self._preview_order_number)
            
        except Exception as e:
            
            self.log.error("Failed to fetch preview order number: %s" % str(e))
    
    def _on_tax_type_changed(self):
        
        placeholders = {
            TaxNumberTypeEnum.VAT: "Adószám (HU14515404242)",
            TaxNumberTypeEnum.UID: "UID szám (CHE-123.456.789 MWST)",
            TaxNumberTypeEnum.EIN: "EIN / TIN szám (12-3456789)",
            TaxNumberTypeEnum.MVA: "MVA szám (NO123456789MVA)",
            TaxNumberTypeEnum.VKN: "VKN szám (1234567890)"
        }
        
        tax_type = self.tax_type_dropdown.currentData()
        
        self.client_vat.setPlaceholderText(placeholders.get(tax_type, "Adószám"))
    
    def _on_existing_tax_type_changed(self):
        
        placeholders = {
            TaxNumberTypeEnum.VAT: "Adószám (HU14515404242)",
            TaxNumberTypeEnum.UID: "UID szám (CHE-123.456.789 MWST)",
            TaxNumberTypeEnum.EIN: "EIN / TIN szám (12-3456789)",
            TaxNumberTypeEnum.MVA: "MVA szám (NO123456789MVA)",
            TaxNumberTypeEnum.VKN: "VKN szám (1234567890)"
        }
        
        tax_type = self.existing_tax_type_dropdown.currentData()
        
        self.existing_client_vat.setPlaceholderText(placeholders.get(tax_type, "Adószám"))
    
    async def _fetch_existing_clients(self):
        
        try:
            
            clients = await queries.select_all_clients()
            
            self.existing_client_dropdown.blockSignals(True)
            
            self.existing_client_dropdown.clear()
            self.existing_client_dropdown.addItem("-- Válassz klienst --", None)
            
            for client in clients:
                
                display_text = f"{client.name} – {client.tax_number}"
                
                self.existing_client_dropdown.addItem(display_text, client.id)
            
            self.existing_client_dropdown.setCurrentIndex(0)
            
            self.existing_client_dropdown.blockSignals(False)
            
            self.log.debug("Loaded %d existing clients" % len(clients))
            
        except Exception as e:
            
            self.log.error("Failed to fetch existing clients: %s" % str(e))
    
    async def _on_existing_client_changed(self):
        
        client_id = self.existing_client_dropdown.currentData()
        
        if client_id is None:
            
            self.existing_client_name.clear()
            self.existing_client_address.clear()
            self.existing_client_country.clear()
            self.existing_client_vat.clear()
            self.existing_tax_type_dropdown.setCurrentIndex(0)
            
            return
        
        try:
            
            client = await queries.select_client_by_id(client_id)
            
            if client is None:
                
                self.log.warning("Client with id %d not found" % client_id)
                
                return
            
            self.existing_client_name.setText(client.name)
            self.existing_client_address.setText(client.address)
            self.existing_client_country.setText(client.country)
            self.existing_client_vat.setText(client.tax_number)
            
            tax_type_index = self.existing_tax_type_dropdown.findData(client.tax_number_type)
            
            if tax_type_index >= 0:
                
                self.existing_tax_type_dropdown.setCurrentIndex(tax_type_index)
            
            self.log.debug("Loaded client data for id %d: %s" % (client_id, client.name))
            
        except Exception as e:
            
            self.log.error("Failed to fetch client by id %d: %s" % (client_id, str(e)))
    
    @staticmethod
    def _validate_tax_number(tax_number: str, tax_type: TaxNumberTypeEnum) -> bool:
        
        patterns = {
            TaxNumberTypeEnum.VAT: r'^[A-Z]{2}\d{8,12}$',
            TaxNumberTypeEnum.UID: r'^CHE-?\d{3}\.?\d{3}\.?\d{3}\s*(MWST|TVA|IVA)$',
            TaxNumberTypeEnum.EIN: r'^\d{2}-?\d{7}$',
            TaxNumberTypeEnum.MVA: r'^NO\d{9}MVA$',
            TaxNumberTypeEnum.VKN: r'^\d{10}$'
        }
        
        pattern = patterns.get(tax_type)
        
        if pattern is None:
            
            return False
        
        return re.match(pattern, tax_number) is not None
    
    def _on_custom_prices_toggled(self, state):
        
        self.custom_prices_container.setVisible(state == Qt.CheckState.Checked.value)
    
    def _on_custom_prices_hun_toggled(self, state):
        
        self.custom_prices_hun_container.setVisible(state == Qt.CheckState.Checked.value)
    
    def _load_current_prices_hun(self):
        
        hun_prices = getattr(self.admin_view.main_window, 'other_work_prices_hun', None)
        
        if hun_prices is None:
            
            self.log.warning("HUF prices not loaded yet")
            
            return
        
        self.hun_survey_weekday.setText(str(round(float(hun_prices.survey_delivery.weekday), 2)))
        self.hun_survey_weekend.setText(str(round(float(hun_prices.survey_delivery.weekend), 2)))
        self.hun_survey_sunday.setText(str(round(float(hun_prices.survey_delivery.sunday), 2)))
        
        self.hun_repair_weekday.setText(str(round(float(hun_prices.repair_maintenance.weekday), 2)))
        self.hun_repair_weekend.setText(str(round(float(hun_prices.repair_maintenance.weekend), 2)))
        self.hun_repair_sunday.setText(str(round(float(hun_prices.repair_maintenance.sunday), 2)))
        
        self.hun_travel_budapest.setText(str(round(float(hun_prices.travel_budapest), 2)))
        self.hun_travel_outside_km.setText(str(round(float(hun_prices.travel_outside_km), 2)))
        
        self.hun_travel_time_weekday.setText(str(round(float(hun_prices.travel_time.weekday), 2)))
        self.hun_travel_time_weekend.setText(str(round(float(hun_prices.travel_time.weekend), 2)))
        self.hun_travel_time_sunday.setText(str(round(float(hun_prices.travel_time.sunday), 2)))
    
    def _parse_hun_price_field(self, field) -> Decimal:
        
        text = field.text().replace(",", ".").strip()
        
        return Decimal(str(round(float(text), 2))) if text else Decimal("0")
    
    async def _save_other_work_prices_hun(self):
        
        try:
            
            tier_prices = {
                HunPriceCategoryEnum.SURVEY_DELIVERY: {
                    HunPriceTierEnum.WEEKDAY: self._parse_hun_price_field(self.hun_survey_weekday),
                    HunPriceTierEnum.WEEKEND: self._parse_hun_price_field(self.hun_survey_weekend),
                    HunPriceTierEnum.SUNDAY: self._parse_hun_price_field(self.hun_survey_sunday),
                },
                HunPriceCategoryEnum.REPAIR_MAINTENANCE: {
                    HunPriceTierEnum.WEEKDAY: self._parse_hun_price_field(self.hun_repair_weekday),
                    HunPriceTierEnum.WEEKEND: self._parse_hun_price_field(self.hun_repair_weekend),
                    HunPriceTierEnum.SUNDAY: self._parse_hun_price_field(self.hun_repair_sunday),
                },
                HunPriceCategoryEnum.TRAVEL_TIME: {
                    HunPriceTierEnum.WEEKDAY: self._parse_hun_price_field(self.hun_travel_time_weekday),
                    HunPriceTierEnum.WEEKEND: self._parse_hun_price_field(self.hun_travel_time_weekend),
                    HunPriceTierEnum.SUNDAY: self._parse_hun_price_field(self.hun_travel_time_sunday),
                },
            }
            
            await queries.update_other_work_prices_hun(
                travel_budapest = self._parse_hun_price_field(self.hun_travel_budapest),
                travel_outside_km = self._parse_hun_price_field(self.hun_travel_outside_km),
                tier_prices = tier_prices
            )
            
            self.refresh_other_work_prices_hun.emit()
            
            self.log.info("HUF other work prices updated successfully")
            
        except Exception as e:
            
            self.log.error("Failed to update HUF other work prices: %s" % str(e))
    
    def _load_current_prices(self):
        
        prices = self.admin_view.main_window.other_work_prices.model_dump()
        
        _, output_currency = self.get_currency_settings()
        
        display_currency = output_currency if output_currency is not None else "EUR"
        
        field_map = {
            "work_during_hours": self.price_work_during_hours,
            "work_outside_hours": self.price_work_outside_hours,
            "work_sundays": self.price_work_sundays,
            "travel_budapest": self.price_travel_budapest,
            "travel_outside": self.price_travel_outside,
            "travel_time": self.price_travel_time,
            "travel_time_outside": self.price_travel_time_outside,
            "travel_time_sundays": self.price_travel_time_sundays,
            "accommodation": self.price_accommodation,
        }
        
        for key, field in field_map.items():
            
            eur_value = float(prices[key])
            
            converted = self.convert_price(eur_value, "EUR", display_currency)
            
            field.setText(str(round(converted, 2)))
    
    async def _save_other_work_prices(self):
        
        _, output_currency = self.get_currency_settings()
        
        display_currency = output_currency if output_currency is not None else "EUR"
        
        field_map = {
            "work_during_hours": self.price_work_during_hours,
            "work_outside_hours": self.price_work_outside_hours,
            "work_sundays": self.price_work_sundays,
            "travel_budapest": self.price_travel_budapest,
            "travel_outside": self.price_travel_outside,
            "travel_time": self.price_travel_time,
            "travel_time_outside": self.price_travel_time_outside,
            "travel_time_sundays": self.price_travel_time_sundays,
            "accommodation": self.price_accommodation,
        }
        
        try:
            
            eur_values = {}
            
            for key, field in field_map.items():
                
                text = field.text().replace(",", ".").strip()
                
                value = float(text) if text else 0.0
                
                eur_values[key] = Decimal(str(round(self.convert_price(value, display_currency, "EUR"), 2)))
            
            await queries.update_other_work_prices(
                eur_values["work_during_hours"],
                eur_values["work_outside_hours"],
                eur_values["work_sundays"],
                eur_values["travel_budapest"],
                eur_values["travel_outside"],
                eur_values["travel_time"],
                eur_values["travel_time_outside"],
                eur_values["travel_time_sundays"],
                eur_values["accommodation"]
            )
            
            self.refresh_other_work_prices.emit()
            
            self.log.info("Other work prices updated successfully")
            
        except Exception as e:
            
            self.log.error("Failed to update other work prices: %s" % str(e))
        
    async def _export_pdf_async(self):
        
        is_existing_client = self.client_tab_widget.currentIndex() == 1
        
        if is_existing_client:
            
            client_name = self.existing_client_name.text().strip()
            client_address = self.existing_client_address.text().strip()
            client_country = self.existing_client_country.text().strip()
            client_vat = self.existing_client_vat.text().strip()
            tax_type = self.existing_tax_type_dropdown.currentData()
            name_error_label = self.existing_client_name_error
            vat_error_label = self.existing_client_vat_error
            
        else:
            
            client_name = self.client_name.text().strip()
            client_address = self.client_address.text().strip()
            client_country = self.client_country.text().strip()
            client_vat = self.client_vat.text().strip()
            tax_type = self.tax_type_dropdown.currentData()
            name_error_label = self.client_name_error
            vat_error_label = self.client_vat_error
        
        description = self.work_description.toPlainText().strip()
        
        information = self.additional_info.toPlainText().strip()
        
        name_error_label.setVisible(False)
        vat_error_label.setVisible(False)
        
        has_error = False
        
        if client_name == "":
            
            name_error_label.setText("Megrendelő neve kötelező")
            name_error_label.setVisible(True)
            
            self.log.warning("Input validation failed: 'client_name' field is empty")
            
            has_error = True
        
        if client_vat == "":
            
            vat_error_label.setText("Adószám megadása kötelező")
            vat_error_label.setVisible(True)
            
            self.log.warning("Input validation failed: 'client_vat' field is empty")
            
            has_error = True
        
        if client_vat != "" and self._validate_tax_number(client_vat, tax_type) is False:
            
            vat_error_label.setText("Az adószám nem felel meg a(z) %s formátumnak" % tax_type.value)
            vat_error_label.setVisible(True)
            
            self.log.warning("Tax number '%s' does not match %s format" % (client_vat, tax_type.value))
            
            has_error = True
        
        if has_error is True:
            
            return
        
        real_order_number = await queries.insert_quotation_with_order(
            client_name = client_name,
            client_address = client_address,
            client_country = client_country,
            client_tax_number = client_vat,
            client_tax_number_type = tax_type,
            project_description = description,
            other_information = information,
            client_tax_number_raw = client_vat
        )
        
        self.log.debug("Quotation saved with order number: %s" % real_order_number)
        
        html_hu = self.render_html(order_number = real_order_number)
        
        if html_hu == "":
            return
        
        quotations_dir = "quotations"
        
        unique_id = uuid4().hex[:8]
        
        current_timestamp = datetime.now(Config.time.timezone_utc).strftime(Config.time.timestamp_format)
        
        safe_boat_name = self.boat_name.text().strip().replace(" ", "_")
        
        pdf_filename = f"{safe_boat_name}_[{current_timestamp}]_{unique_id}.pdf"
        
        hungarian_dir = os.path.join(quotations_dir, "hungarian")
        
        os.makedirs(hungarian_dir, exist_ok = True)
        
        hu_pdf_file = os.path.join(hungarian_dir, pdf_filename)
        
        doc_hu = HTML(string = html_hu).render()
        
        if len(doc_hu.pages) > 1:
            
            html_hu = self.render_html(order_number = real_order_number, show_page_numbers = True)
            HTML(string = html_hu).write_pdf(hu_pdf_file)
            
        else:
            
            doc_hu.write_pdf(hu_pdf_file)
        
        self.log.debug("Hungarian PDF saved: %s" % hu_pdf_file)
        
        lang_code = self.language_dropdown.currentData()
        
        if lang_code is not None and lang_code != "HU":
            
            try:
                
                template_translations = await self._translate_template_strings(lang_code)
                
                user_translations = await self._translate_user_content(lang_code)
                
                all_translations = {**template_translations, **user_translations}
                
                translator = lambda x, t = all_translations: t.get(x, x)
                
                html_other = self.render_html(
                    translator = translator,
                    translated_content = all_translations,
                    order_number = real_order_number
                )
                
                other_dir = os.path.join(quotations_dir, "other")
                
                os.makedirs(other_dir, exist_ok = True)
                
                other_pdf_file = os.path.join(other_dir, pdf_filename)
                
                doc_other = HTML(string = html_other).render()
                
                if len(doc_other.pages) > 1:
                    
                    html_other = self.render_html(
                        translator = translator,
                        translated_content = all_translations,
                        order_number = real_order_number,
                        show_page_numbers = True
                    )
                    
                    HTML(string = html_other).write_pdf(other_pdf_file)
                    
                else:
                    
                    doc_other.write_pdf(other_pdf_file)
                
                self.log.debug("Translated PDF saved: %s" % other_pdf_file)
                
                QDesktopServices.openUrl(QUrl.fromLocalFile(os.path.abspath(other_pdf_file)))
                
            except (OpenAIError, json.JSONDecodeError) as e:
                
                self.log.error("Translation failed, only Hungarian PDF saved: %s" % str(e))
        
        QDesktopServices.openUrl(QUrl.fromLocalFile(os.path.abspath(hu_pdf_file)))
        
        await self._fetch_preview_order_number()
        
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
        remove_btn.setToolTip("Törlés")
        remove_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        remove_btn.clicked.connect(lambda _, r = row: self.remove_row(r))
        
        self.work_table.setCellWidget(row, 4, remove_btn)
        
    def remove_row(self, row):
        
        self.work_table.removeRow(row)
        
        for r in range(self.work_table.rowCount()):
            
            btn = self.work_table.cellWidget(r, 4)
            
            if btn is not None and isinstance(btn, QPushButton):
                
                btn.clicked.disconnect()
                
                btn.clicked.connect(lambda _, r = r: self.remove_row(r))
    
    def svg_to_base64(self, filename):
        
        with open(filename, "rb") as f:
            
            return b64encode(f.read()).decode("utf-8")

    def get_currency_symbol(self, currency_code: str) -> str:
        
        return Config.quotation.currency_symbols.get(currency_code, currency_code)
    
    def get_currency_settings(self):
        
        input_currency = self.currency_input_dropdown.currentData()
        
        output_currency = self.currency_output_dropdown.currentData()
        
        return input_currency, output_currency
    
    def convert_price(self, value: float, from_currency: str, to_currency: str) -> float:
        # print(f"Converting price: {value} from {from_currency} to {to_currency}")
        
        if from_currency is not None and to_currency is not None and from_currency != to_currency:
            
            return self.utility_calculator.exchange_value(value, from_currency, to_currency)
        
        return value

    @staticmethod
    def format_quantity(qty: float) -> str:
        
        if qty == int(qty):
            
            return f"{int(qty):,}".replace(",", ".")
        
        formatted = f"{qty:.4f}".rstrip("0").rstrip(".")
        
        parts = formatted.split(".")
        
        int_part = f"{int(parts[0]):,}".replace(",", ".")
        
        return f"{int_part},{parts[1]}" if len(parts) > 1 else int_part

    @staticmethod
    def format_price(value: float) -> str:
        
        if value == int(value):
            
            return f"{int(value):,}".replace(",", ".")
        
        formatted = f"{value:.2f}".rstrip("0").rstrip(".")
        
        parts = formatted.split(".")
        
        int_part = f"{int(parts[0]):,}".replace(",", ".")
        
        return f"{int_part},{parts[1]}" if len(parts) > 1 else int_part

    def get_surcharge_settings(self):
        
        enabled = self.surcharge_dropdown.currentData()
        
        percent = 0.0
        
        if enabled is True:
            
            try:
                
                percent = float(self.surcharge_percentage_input.text().replace(",", "."))
                
            except ValueError:
                
                percent = 0.0
                
        return enabled, percent

    def _get_hun_prices(self) -> OtherWorkPricesHun | None:
        
        return getattr(self.admin_view.main_window, 'other_work_prices_hun', None)
    
    def _get_converted_prices(self) -> dict:
        
        _, output_currency = self.get_currency_settings()
        
        display_currency = output_currency if output_currency is not None else "HUF"
        # print("Display currency:", display_currency)
        
        if self.custom_prices_checkbox.isChecked():
            
            field_map = {
                "work_during_hours": self.price_work_during_hours,
                "work_outside_hours": self.price_work_outside_hours,
                "work_sundays": self.price_work_sundays,
                "travel_budapest": self.price_travel_budapest,
                "travel_outside": self.price_travel_outside,
                "travel_time": self.price_travel_time,
                "travel_time_outside": self.price_travel_time_outside,
                "travel_time_sundays": self.price_travel_time_sundays,
                "accommodation": self.price_accommodation,
            }
            
            converted = {}
            
            for key, field in field_map.items():
                
                text = field.text().replace(",", ".").strip()
                
                value = float(text) if text else 0.0
                
                converted[key] = self.format_price(value)
            
            return converted
        
        raw_prices = self.admin_view.main_window.other_work_prices.model_dump()
        
        converted = {}
        
        for key, eur_value in raw_prices.items():
            
            value = self.convert_price(float(eur_value), "EUR", display_currency)
            
            converted[key] = self.format_price(value)
        
        return converted

    def get_table_data(self) -> QuotationData:
        
        items = []
        
        enabled, surcharge_percent = self.get_surcharge_settings()
        
        multiplier = 1 + (surcharge_percent / 100) if enabled is True and surcharge_percent > 0 else 1.0
        
        input_currency, output_currency = self.get_currency_settings()
        
        source_currency = input_currency if input_currency is not None else "HUF"
        
        display_currency = output_currency if output_currency is not None else "HUF"
        
        currency_symbol = self.get_currency_symbol(display_currency)
        
        for row in range(self.work_table.rowCount()):
            
            name_item = self.work_table.item(row, 0)
            
            qty_item = self.work_table.item(row, 1)
            
            unit_item = self.work_table.item(row, 2)
            
            price_item = self.work_table.item(row, 3)
            
            if name_item is not None and qty_item is not None and \
                unit_item is not None and price_item is not None:
                
                try:
                    
                    qty = float(qty_item.text().replace(",", "."))
                    
                except ValueError:
                    
                    qty = 0
                    
                qty_display = self.format_quantity(qty)
                
                price_text = price_item.text().replace("Ft", "").replace("€", "").replace("$", "").replace(" ", "").replace(",", ".")
              
                try:
                    
                    unit_price = float(price_text)
                    
                except ValueError:
                    
                    unit_price = 0
                    
                line_total = unit_price * qty * multiplier
                
                if source_currency != display_currency:
                        
                    line_total = self.convert_price(line_total, source_currency, display_currency)
                    
                price_display = f"{currency_symbol} {self.format_price(line_total)}"
                
                items.append(QuotationTableData(
                    name = name_item.text(),
                    quantity = qty_display,
                    unit = unit_item.text(),
                    price = price_display,
                    line_total = line_total
                ))
                
        client = ClientData(
            name = self.existing_client_name.text() if self.client_tab_widget.currentIndex() == 1 else self.client_name.text(),
            address = self.existing_client_address.text() if self.client_tab_widget.currentIndex() == 1 else self.client_address.text(),
            country = self.existing_client_country.text() if self.client_tab_widget.currentIndex() == 1 else self.client_country.text(),
            vat = self.existing_client_vat.text() if self.client_tab_widget.currentIndex() == 1 else self.client_vat.text()
        )
        
        return QuotationData(
            currency_symbol = currency_symbol,
            client = client,
            items = items
        )
    
    def render_html(self, 
        translator = None, 
        translated_content: dict = None, 
        order_number: str = None, 
        show_page_numbers: bool = False
        ):
    
        if translator is None:
            translator = lambda x: x
    
        today = date.today()
        
        valid_until = today + timedelta(days = 7)
        
        if order_number is None:
            order_number = self._preview_order_number
        
        order_number = Markup(order_number)
        
        svg_dir_path = os.path.join(os.path.dirname(sys.executable), "_internal/gui/static/assets/img/svg") \
            if getattr(sys, 'frozen', False) else os.path.join(os.path.dirname(__file__), "../../static/assets/img/svg")
    
        cts_logo = self.svg_to_base64(os.path.join(svg_dir_path, "cts_logo.svg")) # gui\static\assets\img\svg\cts_logo.svg
        cred_logo = self.svg_to_base64(os.path.join(svg_dir_path, "credithworthiness_logo.svg")) # gui\static\assets\img\svg\credithworthiness_logo.svg
        
        quotation_data = self.get_table_data()
        
        total_price = sum(item.line_total for item in quotation_data.items)
        
        boat_name = self.boat_name.text().strip()
        
        description = self.work_description.toPlainText()
        
        information = self.additional_info.toPlainText()
        
        items = quotation_data.items
        
        if translated_content is not None:
            
            boat_name = translated_content.get(boat_name, boat_name)
            
            description = translated_content.get(description.strip(), description)
            
            information = translated_content.get(information.strip(), information)
            
            translated_items = []
            
            for item in items:
                
                translated_items.append(QuotationTableData(
                    name = translated_content.get(item.name.strip(), item.name),
                    quantity = item.quantity,
                    unit = translated_content.get(item.unit.strip(), item.unit),
                    price = item.price,
                    line_total = item.line_total
                ))
            
            items = translated_items
        
        lang_code = self.language_dropdown.currentData()
        
        hun_prices = self._get_hun_prices() if lang_code == "HU" else None
        
        html = self.quotation_template.render(
            cts_logo = cts_logo,
            cred_logo = cred_logo,
            data_lenght = "less-than-six" if len(items) < 6 else "greater-than-six",
            boat_name = boat_name,
            order_number = order_number,
            client = quotation_data.client,
            data = items,
            prices = self._get_converted_prices(),
            hun_prices = hun_prices,
            description = Markup(description.replace("\n","<br>")),
            information = Markup(information.replace("\n","<br>")),
            total_price = self.format_price(total_price),
            currency_symbol = quotation_data.currency_symbol,
            current_date = Markup(today.strftime("%Y. %m. %d.")),
            valid_until_date = Markup(valid_until.strftime("%Y. %m. %d.")),
            max_rows = len(items),
            show_page_numbers = show_page_numbers,
            _ = translator
        )
        
        return html
    
    def _extract_template_strings(self) -> list:
        
        template_source, _, _ = self.jinja_env.loader.get_source(self.jinja_env, "price_quotation.html")
        
        matches = re.findall(r'_\("([^"]+)"\)', template_source)
        
        return list(dict.fromkeys(matches))
    
    def _get_lang_dir(self) -> str:
        
        if getattr(sys, 'frozen', False):
            
            return os.path.join(os.path.dirname(sys.executable), "lang")
        
        return os.path.join(os.path.dirname(__file__), "../../lang")
    
    def _get_lang_json_file_path(self, lang_code: str) -> str:
        
        lang_dir = self._get_lang_dir()
        
        os.makedirs(lang_dir, exist_ok = True)
        
        return os.path.join(lang_dir, f"{lang_code}.json")
    
    def _load_lang_json_cache(self, lang_code: str) -> dict:
        
        po_path = self._get_lang_json_file_path(lang_code)
        
        if os.path.exists(po_path):
            
            with open(po_path, "r", encoding = "utf-8") as f:
                
                return json.load(f)
        
        return {}
    
    def _save_lang_json_cache(self, lang_code: str, translations: dict):
        
        po_path = self._get_lang_json_file_path(lang_code)
        
        with open(po_path, "w", encoding = "utf-8") as f:
            
            json.dump(translations, f, ensure_ascii = False, indent = 2)
        
        self.log.debug("Json cache saved: %s" % po_path)
    
    def _collect_user_content_strings(self) -> list:
        
        strings = []
        
        boat = self.boat_name.text().strip()
        
        if boat != "":
            
            strings.append(boat)
        
        desc = self.work_description.toPlainText().strip()
        
        if desc != "":
            
            strings.append(desc)
        
        info = self.additional_info.toPlainText().strip()
        
        if info != "":
            
            strings.append(info)
        
        for row in range(self.work_table.rowCount()):
            
            name_item = self.work_table.item(row, 0)
            
            unit_item = self.work_table.item(row, 2)
            
            if name_item is not None and name_item.text().strip() != "":
                
                strings.append(name_item.text().strip())
            
            if unit_item is not None and unit_item.text().strip() != "":
                
                strings.append(unit_item.text().strip())
        
        return list(dict.fromkeys(strings))
    
    async def _call_openai_translate(self, lang_code: str, strings: list) -> dict:
        
        lang_name = Config.lang.lang_codes.get(lang_code, lang_code)
        
        prompt_text = json.dumps(strings, ensure_ascii = False)
        
        async with self._openai_lock:
            
            response = await self.openai.chat.completions.create(
                model = "gpt-5.1",
                messages = [
                    {"role": "system", "content": f"A célnyelv: {lang_name} (kód: {lang_code}). \
                        Fordítsd le az alábbi magyar szövegeket erre a nyelvre. \
                        Csak egy érvényes JSON objektummal válaszolj, ahol a kulcsok az eredeti magyar szövegek, \
                        az értékek pedig a lefordított szövegek. Semmi magyarázás, semmi körítés."},
                    {"role": "user", "content": prompt_text}
                ],
            )
        
        result = response.choices[0].message.content.strip()
        
        self.log.debug("Translation result for %s: %s" % (lang_code, result))
        
        cleaned = re.sub(r"^```json\s*", "", result)
        cleaned = re.sub(r"\s*```$", "", cleaned).strip()
        
        return json.loads(cleaned)
    
    async def _translate_template_strings(self, lang_code: str) -> dict:
        
        cache = self._load_lang_json_cache(lang_code)
        
        template_strings = self._extract_template_strings()
        
        missing = [s for s in template_strings if s not in cache]
        
        if len(missing) > 0:
            
            self.log.debug("Translating %d template strings for %s" % (len(missing), lang_code))
            
            new_translations = await self._call_openai_translate(lang_code, missing)
            
            cache.update(new_translations)
            
            self._save_lang_json_cache(lang_code, cache)
        
        else:
            
            self.log.debug("All template strings cached for %s" % lang_code)
        
        return cache
    
    async def _translate_user_content(self, lang_code: str) -> dict:
        
        user_strings = self._collect_user_content_strings()
        
        if len(user_strings) == 0:
            
            return {}
        
        self.log.debug("Translating %d user content strings for %s" % (len(user_strings), lang_code))
        
        return await self._call_openai_translate(lang_code, user_strings)
    
    def prepare_dropwdown_currencies(self):
        
        all_currencies = ["HUF"] + sorted(self.available_currencies)
        
        self.currency_input_dropdown.clear()
        self.currency_input_dropdown.addItem("-- Beviteli pénznem --", None)
        
        for text in all_currencies:
            
            self.currency_input_dropdown.addItem(text, text)
        
        self.currency_output_dropdown.clear()
        self.currency_output_dropdown.addItem("-- Nincs átváltás --", None)
        
        for text in all_currencies:
            
            self.currency_output_dropdown.addItem(text, text)