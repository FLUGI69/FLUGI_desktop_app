import hashlib
from functools import partial
import re
from qasync import asyncSlot
import typing as t
from datetime import datetime
import asyncio
import os
import random
from pathlib import Path
import logging

from PyQt6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QPushButton,
    QLineEdit,
    QLineEdit,
    QLabel,
    QGroupBox,
    QListWidget,
    QFrame,
    QTextEdit,
    QSizePolicy,
    QListWidgetItem,
    QDialog
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QIcon, QFont, QPixmap

from playwright.async_api import expect, BrowserContext, Page, TimeoutError, Locator

from config import Config
from utils.logger import LoggerMixin
from .admin.custom.line_edit import SearchLineEdit
from services.marine_traffic_search_cache import MarineTrafficCacheService
from utils.dc.marine_traffic.search_data import MarineTrafficData
from utils.dc.marine_traffic.vessel_position import VesselPosition
from .modal.confirm_action import ConfirmActionModal
from .modal.map import MapModal
from db import queries
from routes.api.overpass import OverpassAPI
from routes.api.async_playwright import AsyncPlaywright 
from utils.handlers.widgets.info_bar import InfoBar

if t.TYPE_CHECKING:
    
    from .main_window import MainWindow

class MarineTrafficSearchView(QWidget, LoggerMixin):
    
    log: logging.Logger
    
    def __init__(self,
        main_window: 'MainWindow'
        ):

        super().__init__()
        
        self.spinner = main_window.app.spinner
        
        self.main_window = main_window
        
        self.overpass_api = OverpassAPI(main_window.app)
        
        self.playwright_manager = main_window.app.playwright_manager
        
        self.marine_traffic_search_cache = MarineTrafficCacheService(main_window.redis_client)
        
        self.confirm_action_modal = ConfirmActionModal(self)
        
        self.input_name = ""

        self.info_bar = InfoBar()
        
        self.async_playwright = AsyncPlaywright(
            playwright_manager = self.playwright_manager,
            info_bar = self.info_bar
        )
        
        self.__init_view()
        
    def __init_view(self):
        
        self.results_table = None
        
        main_layout = QVBoxLayout(self)

        self.top_section = self.set_top_section()

        search_result_group = self.set_search_result_list()

        # main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(self.top_section)
        main_layout.addWidget(search_result_group)

    @staticmethod
    def icon(name: str) -> QIcon:
  
        return QIcon(os.path.join(Config.icon.icon_dir, name))   

    def set_top_section(self):
        
        self.search_fields = []
        self.error_labels = []
        self.search_buttons = []
        self.add_buttons = []
        
        self._search_callbacks = [
            self.__search_marine,
            # self._handle_add_marine_btn,
        ]
        
        search_group = QGroupBox()
        search_layout = QHBoxLayout(search_group)

        col_layout = QVBoxLayout()

        title_label = QLabel("Marine Traffic")
        title_label.setObjectName("BoatTitleLabel")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setFixedHeight(35)
        title_label.setMaximumWidth(380)
        
        self.input_field = SearchLineEdit(btn_callback = self.__on_btn_clicked)
        self.input_field.setObjectName("BoatSearchInput")
        self.input_field.setPlaceholderText("Search...")
        self.input_field.setFixedHeight(35)
        self.input_field.setMaximumWidth(380)

        self.error_label = QLabel()
        self.error_label.setObjectName("error")
        self.error_label.setVisible(False) 
        self.error_label.setMaximumWidth(380)

        search_btn = QPushButton("Search")
        search_btn.setObjectName("BoatSearchBtn")
        search_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        search_btn.setFixedHeight(35)
        search_btn.setMaximumWidth(380)
        search_btn.clicked.connect(partial(self.__on_btn_clicked, 0))
        
        # add_btn = QPushButton("Add")
        # add_btn.setObjectName("BoatSearchBtn")
        # add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        # add_btn.setFixedHeight(35)
        # add_btn.setMaximumWidth(380)
        # add_btn.clicked.connect(partial(self.__on_btn_clicked, 1))

        col_layout.addWidget(title_label)
        col_layout.addWidget(self.input_field)
        col_layout.addWidget(self.error_label)
        col_layout.addWidget(search_btn)
        # col_layout.addWidget(add_btn)

        self.search_fields.append(self.input_field)
        self.error_labels.append(self.error_label)
        self.search_buttons.append(search_btn)
        # self.add_buttons.append(add_btn)

        search_layout.addLayout(col_layout)

        return search_group
    
    def set_search_result_list(self):
        
        search_group = QGroupBox()
        
        col_layout = QVBoxLayout(search_group)
        col_layout.setContentsMargins(0, 0, 0, 0)
    
        self.search_result_list = QListWidget()
        self.search_result_list.setObjectName("MessageList")
        self.search_result_list.setFrameShape(QFrame.Shape.NoFrame)
        self.search_result_list.setMouseTracking(True)
        
        self.search_result_list.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.search_result_list.setCursor(Qt.CursorShape.PointingHandCursor)
        
        col_layout.addWidget(self.info_bar)
        col_layout.addWidget(self.search_result_list)
        
        return search_group
        
    @asyncSlot()
    async def __on_btn_clicked(self, idx: int):
        
        if self.search_result_list is not None:
            
            self.spinner.show(self.search_result_list)
            
        try:
            
            # if idx == 1:
         
            #     # await self._handle_add_marine_btn()
                 
            if idx < len(self._search_callbacks):
                
                await self._search_callbacks[idx]()
                
        except Exception as e:

            self.log.exception("Search callback failed: %s" % str(e))
        
        finally:
            
            self.spinner.hide()
        
    async def populate_results_list(self, 
        number_of_items: int,
        marine_traffic_list: t.List[MarineTrafficData]
        ):
        
        self.search_result_list.clear()
        
        self.log.debug("Populating result list with %d items of %s data" % (
            number_of_items,
            marine_traffic_list[0].__class__.__name__
            )
        )
        
        if len(marine_traffic_list) > 0:
            
            self.search_result_list.setUniformItemSizes(True)

            font = QFont()
            
            font.setPointSize(10)
            
            for search_result in marine_traffic_list:
                
                list_item = QListWidgetItem()
                
                container = QWidget()
                container.setFixedHeight(35)
                
                flag_label = QLabel()
                flag_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

                flag_code = search_result.flag.lower() if search_result.flag is not None else "nan"
          
                pixmap = QPixmap(os.path.join(Config.flags.flag_dir, f"{flag_code}.png"))

                if not pixmap.isNull():
    
                    scaled_pixmap = pixmap.scaled(QSize(32, 20), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                    
                    flag_label.setPixmap(scaled_pixmap)
               
                else:
                    
                    self.log.error("Could not load flag image for code %s" % flag_code)
                
                ship_name_label = QLabel(search_result.ship_name if search_result.ship_name is not None else "N/A")
                ship_name_label.setFont(font)
                
                ship_id_label = QLabel(str(search_result.ship_id) if search_result.ship_id is not None else "N/A")
                ship_id_label.setFont(font)
                
                ship_type_label = QLabel(search_result.type_name if search_result.type_name is not None else "N/A")
                ship_type_label.setFont(font)
                
                mmsi_label = QLabel(str(search_result.mmsi) if search_result.mmsi is not None else "N/A")
                mmsi_label.setFont(font)
                
                imo_label = QLabel(str(search_result.imo) if search_result.imo is not None else "N/A")
                imo_label.setFont(font)
                
                callsign_label = QLabel(search_result.callsign if search_result.callsign is not None else "N/A")
                callsign_label.setFont(font)
                
                more_details_btn = QPushButton()
                more_details_btn.setObjectName("TrashButton")
                more_details_btn.setCursor(Qt.CursorShape.PointingHandCursor)
                more_details_btn.setIcon(MarineTrafficSearchView.icon("info.svg"))
                more_details_btn.setIconSize(QSize(20, 20))
                more_details_btn.setToolTip("More information")
                
                more_details_btn.clicked.connect(lambda _, item = list_item: self.more_details_clicked(item))
                
                add_to_fleet_btn = QPushButton()
                add_to_fleet_btn.setObjectName("TrashButton")
                add_to_fleet_btn.setCursor(Qt.CursorShape.PointingHandCursor)
                add_to_fleet_btn.setIcon(MarineTrafficSearchView.icon("add.svg"))
                add_to_fleet_btn.setIconSize(QSize(20, 20))
                add_to_fleet_btn.setToolTip("Add to fleet")
                
                add_to_fleet_btn.clicked.connect(lambda _, item = list_item: self.add_to_fleet(item))
                
                view_on_map_btn = QPushButton()
                view_on_map_btn.setObjectName("TrashButton")
                view_on_map_btn.setCursor(Qt.CursorShape.PointingHandCursor)
                view_on_map_btn.setIcon(MarineTrafficSearchView.icon("search.svg"))
                view_on_map_btn.setIconSize(QSize(20, 20))
                view_on_map_btn.setToolTip("View location")
                
                view_on_map_btn.clicked.connect(lambda _, item = list_item: self.view_on_map(item))
                
                h_layout = QHBoxLayout(container)
                h_layout.setContentsMargins(5, 2, 5, 2)
                h_layout.setSpacing(0)

                widgets = [
                    flag_label,
                    ship_name_label,
                    ship_id_label,
                    ship_type_label,
                    mmsi_label,
                    imo_label,
                    callsign_label,
                    more_details_btn,
                    add_to_fleet_btn,
                    view_on_map_btn
                ]
                
                h_layout.addStretch(1)

                for w in widgets:
                    
                    h_layout.addWidget(w)
                    h_layout.addStretch(1)
                
                container.setLayout(h_layout)
                
                list_item.setSizeHint(container.sizeHint())
                
                self.search_result_list.addItem(list_item)
                self.search_result_list.setItemWidget(list_item, container)
                self.search_result_list.setSpacing(2)
                
                list_item.setData(Qt.ItemDataRole.UserRole, search_result)
    
    @asyncSlot(QListWidgetItem)
    async def view_on_map(self, list_item: QListWidgetItem):
        
        marine_traffic_data: MarineTrafficData = list_item.data(Qt.ItemDataRole.UserRole)

        if marine_traffic_data is not None and marine_traffic_data.view_on_map_href is not None:
            
            if self.async_playwright.page is not None:
                
                view_on_map_url = Config.marine_traffic.base_url + marine_traffic_data.view_on_map_href
                
                self.info_bar.addText("🌐 Opening map view for ship %s: %s..." % (
                    marine_traffic_data.ship_name.capitalize(),
                    view_on_map_url
                    )
                )
                
                self.log.debug("Navigating to Marine Traffic 'View on Map' URL: %s" % view_on_map_url)
                
                response = await self.async_playwright.page.goto(
                    url = view_on_map_url, 
                    wait_until = "domcontentloaded"
                )
                
                if response.status == 200:
                    
                    await self.async_playwright.page.wait_for_selector("body")

                    self.log.info("View on map of %s[%d] is opened" % (
                        marine_traffic_data.ship_name if marine_traffic_data.ship_name is not None else "Unknown",
                        marine_traffic_data.ship_id if marine_traffic_data.ship_id is not None else "Unknown"
                        )
                    )
                    
                    async with self.async_playwright.page.expect_response(
                        lambda response: f"getvesseljson/shipid:{marine_traffic_data.ship_id}" in response.url
                        ) as response_info:
                        
                        response_obj = await response_info.value  

                    try:
                        
                        response_data = await response_obj.json()  

                        vessel_position = VesselPosition(
                            ship_name = marine_traffic_data.ship_name,
                            lat = response_data.get("LAT"),
                            lon = response_data.get("LON")
                        )

                        self.log.info("Position retrieved: %s [%d] -> lat: %.5f, lon: %.5f" % (
                            marine_traffic_data.ship_name,
                            marine_traffic_data.ship_id,
                            vessel_position.lat,
                            vessel_position.lon
                            )
                        )
                        
                        nearest_harbor, distance_km, nearest_name = await asyncio.to_thread(
                            self.overpass_api.get_nearest_harbor,
                            lat = vessel_position.lat,
                            lon = vessel_position.lon
                        )
                        
                        self.map_modal = MapModal(
                            vessel = vessel_position,
                            nearest_harbor = nearest_harbor,
                            distance_km = distance_km,
                            nearest_name = nearest_name,
                            parent = self
                        )
            
                        self.map_modal.show()
                        
                        self.map_modal.load_map()

                    except Exception as e:
                        
                        self.log.exception("Failed to retrieve the ship's position: %s" % str(e))
                    
    @asyncSlot(QListWidgetItem)
    async def add_to_fleet(self, list_item: QListWidgetItem):
        
        marine_traffic_data: MarineTrafficData = list_item.data(Qt.ItemDataRole.UserRole)

        if marine_traffic_data is not None and marine_traffic_data.ship_id is not None:
            
            self.info_bar.addText("🛟 Adding ship to your personal fleet: %s..." % (
                marine_traffic_data.ship_name.capitalize()
                )
            )
            
            self.log.debug("Adding ship to personal fleet: %s (Details URL: %s)" % (
                    marine_traffic_data.ship_name,
                    marine_traffic_data.more_deatails_href
                )
            )
            
            try:
                
                await queries.insert_boat_data(
                    name = marine_traffic_data.ship_name,
                    ship_id = marine_traffic_data.ship_id if marine_traffic_data.ship_id is not None else None ,
                    imo = marine_traffic_data.imo if marine_traffic_data.imo is not None else None,
                    mmsi = marine_traffic_data.mmsi if marine_traffic_data.mmsi is not None else None,
                    type_name = marine_traffic_data.type_name if marine_traffic_data.type_name is not None else None,
                    callsign = marine_traffic_data.callsign if marine_traffic_data.callsign is not None else None,
                    more_deatails_href = marine_traffic_data.more_deatails_href if marine_traffic_data.more_deatails_href is not None else None,
                    view_on_map_href = marine_traffic_data.view_on_map_href if marine_traffic_data.view_on_map_href is not None else None,
                    flag = marine_traffic_data.flag if marine_traffic_data.flag is not None else None
                )
            
            except Exception as e:
                
                self.log.exception("Unexpected error occured: %s" % str(e))
            
            finally:
                
                self.info_bar.addText("✅ %s added successfully" % (marine_traffic_data.ship_name))
        
    @asyncSlot(QListWidgetItem)
    async def more_details_clicked(self, list_item: QListWidgetItem):
        
        marine_traffic_data: MarineTrafficData = list_item.data(Qt.ItemDataRole.UserRole)
        # print(marine_traffic_data)
        
        if marine_traffic_data is not None and marine_traffic_data.more_deatails_href is not None:
            
            if self.async_playwright.page is not None:
                
                more_details_url = Config.marine_traffic.target_uri + marine_traffic_data.more_deatails_href
                
                self.info_bar.addText("🌐 Opening and reviewing detailed data for ship %s: %s..." % (
                    marine_traffic_data.ship_name.capitalize(),
                    more_details_url
                    )
                )
                
                self.log.debug("Navigating to Marine Traffic URL: %s" % more_details_url)
                
                response = await self.async_playwright.page.goto(
                    url = more_details_url, 
                    wait_until = "domcontentloaded"
                )
                
                if response.status == 200:
                    
                    await self.page.wait_for_selector("body")

                    self.log.info("More details of %s[%d] is oppened" % (
                        marine_traffic_data.ship_name if marine_traffic_data.ship_name is not None else "Unknown",
                        marine_traffic_data.ship_id if marine_traffic_data.ship_id is not None else "Unknown"
                        )
                    )
                    
                    field_label = {
                        "flag": "Flag",
                        "mmsi": "MMSI",
                        "callsign": "Call sign",
                        "imo": "IMO",
                        "type_name": "General vessel type",
                        "reported_destination": "Reported destination",
                        "matched_destination": "Matched destination",
                    }

                    missing_datas = [field for field, value in marine_traffic_data.model_dump().items() if value is None]
                    # print(missing_datas)  

                    try:
                        
                        if len(missing_datas) > 0: 
                            
                            for data in missing_datas:
                                                                
                                if data == "id":
                                    continue
                                
                                label = field_label.get(data, data)
                                
                                try:
                                   
                                    locator = self.async_playwright.page.locator(f"th:text-is('{label}')").locator("xpath=following-sibling::td")
                                    
                                    text_value = await locator.inner_text()
                                    
                                    if text_value != "-":
                                        
                                        self.log.debug("Found missing data for '%s': %s" % (data, text_value))
                                    
                                        setattr(marine_traffic_data, data, text_value)
                                        
                                    else:
                                        
                                        self.log.debug("Missing data for '%s' is reported as '-' on the page" % data)
                                    
                                except Exception as e:
                                    
                                    self.log.warning("Could not extract missing data '%s': %s" % (data, str(e)))
                        
                    except Exception as e:
                        
                        self.log.exception("Unexpected error occurred during scraping data: %s" % str(e))
                        
                    finally:
                        
                        self.info_bar.addText("✅ All available information found for ship %s" % (
                            marine_traffic_data.ship_name if marine_traffic_data.ship_name is not None else "Unknown"
                            )
                        )
                                                
                        self.log.info("All available information successfully extracted for ship %s(%d)" % (
                            marine_traffic_data.ship_name if marine_traffic_data.ship_name is not None else "Unknown",
                            marine_traffic_data.ship_id if marine_traffic_data.ship_id is not None else "Unknown"
                            )
                        )
                        
                        await self.async_playwright._extract_reported_time_and_location()
                        
                        self._update_list_item_row(list_item, marine_traffic_data)
                        
                        self._show_destination_dialog(marine_traffic_data)
                        
    def _update_list_item_row(self, list_item: QListWidgetItem, data: MarineTrafficData):
        
        list_item.setData(Qt.ItemDataRole.UserRole, data)
        
        container = self.search_result_list.itemWidget(list_item)
        
        if container is None:
            return
        
        layout = container.layout()
        
        label_fields = [
            (1, data.ship_name),
            (2, str(data.ship_id) if data.ship_id is not None else "N/A"),
            (3, data.type_name if data.type_name is not None else "N/A"),
            (4, str(data.mmsi) if data.mmsi is not None else "N/A"),
            (5, str(data.imo) if data.imo is not None else "N/A"),
            (6, data.callsign if data.callsign is not None else "N/A"),
        ]
        
        widget_index = 0
        
        for i in range(layout.count()):
            
            item = layout.itemAt(i)
            widget = item.widget() if item is not None else None
            
            if widget is not None and isinstance(widget, QLabel):
                
                for label_idx, value in label_fields:
                    
                    if widget_index == label_idx:
                        
                        widget.setText(value if value is not None else "N/A")
                
                widget_index += 1
    
    def _show_destination_dialog(self, data: MarineTrafficData):
        
        reported = data.reported_destination if data.reported_destination is not None else "N/A"
        matched = data.matched_destination if data.matched_destination is not None else "N/A"
        
        dialog = QDialog(self)
        dialog.setObjectName("ConfirmModal")
        dialog.setWindowTitle("%s - Destination data" % (data.ship_name if data.ship_name is not None else "N/A"))
        
        layout = QHBoxLayout(dialog)
        
        reported_label = QLabel("Reported destination:\n%s" % reported)
        reported_label.setStyleSheet(Config.styleSheets.label)
        reported_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        matched_label = QLabel("Matched destination:\n%s" % matched)
        matched_label.setStyleSheet(Config.styleSheets.label)
        matched_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        ok_btn = QPushButton("OK")
        ok_btn.setObjectName("WorkBtn")
        ok_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        ok_btn.setFixedHeight(35)
        ok_btn.setFixedWidth(150)
        ok_btn.clicked.connect(dialog.close)
        
        layout.addWidget(reported_label)
        layout.setSpacing(20)
        layout.addWidget(matched_label)
        layout.setSpacing(20)
        layout.addWidget(ok_btn)
        
        dialog.open()
  
    async def __search_marine(self):
        
        # self.results_table.clearContents()
        
        self.info_bar.clearText()
        
        self.input_name = self.search_fields[0].text().strip()

        if not self.input_name:
            
            self.log.warning("[MARINE] Empty search input provided, skipping search")
            
            self.error_labels[0].setText("Search field cannot be empty")
            self.error_labels[0].setVisible(True)
            
            self.spinner.hide()
            
            return 
        
        if len(self.input_name) <= 3:
            
            self.log.warning("[MARINE] Search input is too short, skipping search")
            
            self.error_labels[0].setText("(%s) Too short for search" % (str(self.input_name)))
            self.error_labels[0].setVisible(True)
            
            self.spinner.hide()
            
            return 
        
        self.error_labels[0].setVisible(False)
                
        try:
              
            self.page = await self.ensure_page()
     
            if self.page is not None:
                
                self.page.set_default_navigation_timeout(timeout = 20000)
                
                self.page.set_default_timeout(timeout = 10000)
                
                self.info_bar.addText("🌐 Opening the following page: %s..." % Config.marine_traffic.target_uri)
                
                self.log.debug("Navigating to Marine Traffic URL: %s" % Config.marine_traffic.target_uri)
    
                response = await self.page.goto(
                    url = Config.marine_traffic.target_uri, 
                    wait_until = "domcontentloaded"
                )
                
                if response.status == 200:
                
                    await self.page.wait_for_selector("body")
    
                    self.log.info("Marine Traffic page loaded successfully")
                
                    await self.handle_cookies_banner()
                    
                    self.info_bar.addText("✅ Page loaded and ready for search")

                    await self.handle_searching(self.input_name)

                else:
                    
                    self.info_bar.addText("❌ Loading error, status: %s" % str(response.status))  
                        
        except Exception as e:
            
            self.log.exception("An error occurred during the search: %s" % str(e))
            
            self.info_bar.addText("❌ Error during search: %s" % str(e))
