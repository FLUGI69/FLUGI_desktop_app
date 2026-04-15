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
    QLabel,
    QGroupBox,
    QListWidget,
    QFrame,
    QSizePolicy,
    QListWidgetItem,
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QIcon, QFont, QPixmap, QFontMetrics

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
from routes.api.geocoding import GeocodingAPI
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
        
        self.geocoding_api = GeocodingAPI()
        
        self.playwright_manager = main_window.app.playwright_manager
        
        self.marine_traffic_search_cache = MarineTrafficCacheService(
            redis_client = main_window.redis_client,
            marine_traffic_lock = main_window.app.marine_traffic_lock
        )
        
        self.confirm_action_modal = ConfirmActionModal(self)
        
        self.input_name = ""

        self.info_bar = InfoBar()
        
        self.async_playwright = AsyncPlaywright(
            playwright_manager = self.playwright_manager,
            info_bar = self.info_bar
        )
        
        self.row_maximum_col_widths = []
        self.all_collumns = None
        self.global_max_col_width: int | None = None
        self._recalculate_widths = True
        
        self.__init_view()
        
    def __init_view(self):
        
        # self.results_table = None
        
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
        self.input_field.setPlaceholderText("Keresés...")
        self.input_field.setFixedHeight(35)
        self.input_field.setMaximumWidth(380)

        self.error_label = QLabel()
        self.error_label.setObjectName("error")
        self.error_label.setVisible(False) 
        self.error_label.setMaximumWidth(380)

        search_btn = QPushButton("Keresés")
        search_btn.setObjectName("BoatSearchBtn")
        search_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        search_btn.setFixedHeight(35)
        search_btn.setMaximumWidth(380)
        search_btn.clicked.connect(partial(self.__on_btn_clicked, 0))
        
        # add_btn = QPushButton("Hozzáadás")
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

    # async def click_live_map_button(self, page: Page, result: MarineTrafficData):
        
        # await button.click()
        
    async def populate_results_list(self, 
        number_of_items: int,
        marine_traffic_list: t.List[MarineTrafficData]
        ):
        
        if self._recalculate_widths is True:
            
            self.row_maximum_col_widths.clear()
        
        self.search_result_list.clear()
        self.search_result_list.setUniformItemSizes(False)
        
        self.log.debug("Populating result list with %d items of %s data" % (
            number_of_items,
            marine_traffic_list[0].__class__.__name__
            )
        )
        
        try:
            
            if len(marine_traffic_list) > 0:

                font = QFont()
                font.setPointSize(10)
                font.setBold(True)
                
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
                        flag_label.setToolTip("Lobogó")
                
                    else:
                        
                        self.log.error("Could not load flag image for code %s" % flag_code)
                    
                    ship_name_label = QLabel(search_result.ship_name if search_result.ship_name is not None else "N/A")
                    ship_name_label.setFont(font)
                    ship_name_label.setToolTip("Hajó neve")
                    
                    ship_id_label = QLabel(str(search_result.ship_id) if search_result.ship_id is not None else "N/A")
                    ship_id_label.setFont(font)
                    ship_id_label.setToolTip("Hajó azonosító")
                    
                    ship_type_label = QLabel(search_result.type_name if search_result.type_name is not None else "N/A")
                    ship_type_label.setFont(font)
                    ship_type_label.setToolTip("Hajó típusa")
                    
                    mmsi_label = QLabel(str(search_result.mmsi) if search_result.mmsi is not None else "N/A")
                    mmsi_label.setFont(font)
                    mmsi_label.setToolTip("MMSI szám")
                    
                    imo_label = QLabel(str(search_result.imo) if search_result.imo is not None else "N/A")
                    imo_label.setFont(font)
                    imo_label.setToolTip("IMO szám")
                    
                    callsign_label = QLabel(search_result.callsign if search_result.callsign is not None else "N/A")
                    callsign_label.setFont(font)
                    callsign_label.setToolTip("Hívójel")
                    
                    reported_dest_label = QLabel(search_result.reported_destination if search_result.reported_destination is not None else "N/A")
                    reported_dest_label.setFont(font)
                    reported_dest_label.setToolTip("Jelentett úticél")
                    
                    matched_dest_label = QLabel(search_result.matched_destination if search_result.matched_destination is not None else "N/A")
                    matched_dest_label.setFont(font)
                    matched_dest_label.setToolTip("Egyeztetett úticél")
                    
                    position_received_label = QLabel(search_result.position_received if search_result.position_received is not None else "N/A")
                    position_received_label.setFont(font)
                    position_received_label.setToolTip("Pozíció jelentve")
                    
                    scrape_details_btn = QPushButton()
                    scrape_details_btn.setObjectName("TrashButton")
                    scrape_details_btn.setCursor(Qt.CursorShape.PointingHandCursor)
                    scrape_details_btn.setIcon(MarineTrafficSearchView.icon("info.svg"))
                    scrape_details_btn.setIconSize(QSize(20, 20))
                    scrape_details_btn.setToolTip("Részletek lekérése")
                    
                    scrape_details_btn.clicked.connect(lambda _, item = list_item: self.scrape_details_clicked(item))
                    
                    add_to_fleet_btn = QPushButton()
                    add_to_fleet_btn.setObjectName("TrashButton")
                    add_to_fleet_btn.setCursor(Qt.CursorShape.PointingHandCursor)
                    add_to_fleet_btn.setIcon(MarineTrafficSearchView.icon("add.svg"))
                    add_to_fleet_btn.setIconSize(QSize(20, 20))
                    add_to_fleet_btn.setToolTip("Flottához adás")
                    
                    add_to_fleet_btn.clicked.connect(lambda _, item = list_item: self.add_to_fleet(item))
                    
                    view_on_map_btn = QPushButton()
                    view_on_map_btn.setObjectName("TrashButton")
                    view_on_map_btn.setCursor(Qt.CursorShape.PointingHandCursor)
                    view_on_map_btn.setIcon(MarineTrafficSearchView.icon("search.svg"))
                    view_on_map_btn.setIconSize(QSize(20, 20))
                    view_on_map_btn.setToolTip("Helyzet megtekintése")
                    
                    view_on_map_btn.clicked.connect(lambda _, item = list_item: self.view_on_map(item))
                    
                    h_layout = QHBoxLayout(container)
                    h_layout.setContentsMargins(50, 0, 0, 0)
                    
                    widgets = [
                        flag_label,
                        ship_name_label,
                        ship_id_label,
                        ship_type_label,
                        mmsi_label,
                        imo_label,
                        callsign_label,
                        reported_dest_label,
                        matched_dest_label,
                        position_received_label,
                        scrape_details_btn,
                        add_to_fleet_btn,
                        view_on_map_btn
                    ]
                    
                    if self.all_collumns is None:
                        
                        self.all_collumns = len(widgets)

                    if self._recalculate_widths is True:
                
                        current_row_max_col_width = max([QFontMetrics(w.font()).horizontalAdvance(w.text()) 
                            for w in widgets if isinstance(w, QLabel)])
                        
                        self.row_maximum_col_widths.append(current_row_max_col_width)

                    for w in widgets:
    
                        if isinstance(w, QLabel):

                            w.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
                            w.setContentsMargins(0, 0, 0, 0)
                            w.setWordWrap(False)
                    
                        h_layout.addWidget(w)
                    
                    list_item.setSizeHint(QSize(container.sizeHint().width(), 35))
                    
                    self.search_result_list.addItem(list_item)
                    self.search_result_list.setItemWidget(list_item, container)
                    self.search_result_list.setSpacing(0)
                    
                    list_item.setData(Qt.ItemDataRole.UserRole, search_result)

                self.calculate_global_col_width_for_search_list(self.search_result_list)
            
            else:
                
                no_result_label = QLabel("Nincs találat")
                no_result_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                no_result_label.setFont(QFont("", 12, QFont.Weight.Bold))
                
                no_result_item = QListWidgetItem()
                no_result_item.setSizeHint(QSize(self.search_result_list.width(), 50))
                
                self.search_result_list.addItem(no_result_item)
                self.search_result_list.setItemWidget(no_result_item, no_result_label)
            
        finally:
            
            self.search_result_list.setUpdatesEnabled(True)
    
    def calculate_global_col_width_for_search_list(self, list_widget: QListWidget):
    
        # print(row_maximum_col_widths)
        if len(self.row_maximum_col_widths) > 0:
          
            self.global_max_col_width: int = max(self.row_maximum_col_widths)
            # print("Global max text width:", global_max_width)
            # print("Number of columns:", all_collumns)
            if self.global_max_col_width is not None:
                    
                if self.all_collumns is not None:
                    
                    first_container = list_widget.itemWidget(list_widget.item(0))
                    spacing = first_container.layout().spacing() if first_container is not None else 6
                    
                    row_width = 40 + (9 * 150) + (3 * 30) + 50 + (spacing * (self.all_collumns - 1))
                    
                    for i in range(list_widget.count()):
                        
                        item = list_widget.item(i)
            
                        if item is not None:
                            
                            container = list_widget.itemWidget(item)

                            container.setMaximumWidth(int(row_width))
                            
                            item.setSizeHint(QSize(int(row_width), item.sizeHint().height()))
                            
                            layout = container.layout()

                            for j in range(layout.count()):
                                
                                child = layout.itemAt(j)
                                
                                if child is not None:
                                    
                                    child.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

                                    widget = child.widget()
                                
                                    if widget is not None:
                                        
                                        x = 1.5

                                        if j == 0:
                                        
                                            widget.setFixedWidth(40)
                                            
                                        elif j > 0 and j <= 9:
                                        
                                            widget.setFixedWidth(150)
                                            
                                            if isinstance(widget, QLabel):
                                                widget.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
                                            
                                        elif j > 9:
                                            
                                            if isinstance(widget, QPushButton):
                                                
                                                widget.setFixedWidth(30)
                                                widget.setFixedHeight(30)    
  
                                        else:
                                            
                                            widget.setFixedWidth(int(self.global_max_col_width * x))

            self._recalculate_widths = False    
    
    def _get_row_button(self, list_item: QListWidgetItem, layout_index: int) -> QPushButton | None:
        
        container = self.search_result_list.itemWidget(list_item)
        
        if container is not None:
            
            item = container.layout().itemAt(layout_index)
            
            if item is not None:
                
                w = item.widget()
                
                if isinstance(w, QPushButton):
                    
                    return w
        
        return None
    
    @asyncSlot(QListWidgetItem)
    async def scrape_details_clicked(self, list_item: QListWidgetItem):
        
        btn = self._get_row_button(list_item, 10)
        
        if btn is not None:
            btn.setEnabled(False)
        
        try:
            
            marine_traffic_data: MarineTrafficData = list_item.data(Qt.ItemDataRole.UserRole)
            
            if marine_traffic_data is not None and marine_traffic_data.more_deatails_href is not None:
                
                page = await self.async_playwright.ensure_page()
                
                if page is not None:
                    
                    try:
                        
                        updated = await self.async_playwright.scrape_single_vessel_details(marine_traffic_data)
                        
                        self._update_list_item_row(list_item, updated)
                        
                    except Exception as e:
                        
                        self.log.exception("Failed to scrape details for %s: %s" % (
                            marine_traffic_data.ship_name, str(e)
                            )
                        )
        
        finally:
            
            if btn is not None:
                btn.setEnabled(True)
    
    @asyncSlot(QListWidgetItem)
    async def view_on_map(self, list_item: QListWidgetItem):
        
        btn = self._get_row_button(list_item, 12)
        
        if btn is not None:
            btn.setEnabled(False)
        
        try:
            
            marine_traffic_data: MarineTrafficData = list_item.data(Qt.ItemDataRole.UserRole)

            if marine_traffic_data is not None and marine_traffic_data.view_on_map_href is not None:
                
                page = await self.async_playwright.ensure_page()
                
                if page is not None:
                    
                    view_on_map_url = Config.marine_traffic.base_url + marine_traffic_data.view_on_map_href
                
                self.info_bar.addText("🌐 Megnyitom a %s hajó térképen való megtekintését: %s..." % (
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

                        self.log.debug("Position retrieved: %s [%d] -> lat: %.5f, lon: %.5f" % (
                            marine_traffic_data.ship_name,
                            marine_traffic_data.ship_id,
                            vessel_position.lat,
                            vessel_position.lon
                            )
                        )
                        
                        place_name = None
                        
                        try:
                            
                            place_name = await asyncio.to_thread(
                                self.geocoding_api.reverse_geocode,
                                lat = vessel_position.lat,
                                lon = vessel_position.lon
                            )
                                
                        except Exception as e:
                            
                            self.log.warning("Failed to reverse geocode: %s" % str(e))
                        
                        self.map_modal = MapModal(
                            vessel = vessel_position,
                            place_name = place_name,
                            parent = self
                        )
            
                        self.map_modal.show()
                        
                        self.map_modal.load_map()

                    except Exception as e:
                        
                        self.log.exception("Failed to retrieve the ship's position: %s" % str(e))
        
        finally:
            
            if btn is not None:
                btn.setEnabled(True)
                    
    @asyncSlot(QListWidgetItem)
    async def add_to_fleet(self, list_item: QListWidgetItem):
        
        btn = self._get_row_button(list_item, 11)
        
        if btn is not None:
            btn.setEnabled(False)
        
        try:
            
            marine_traffic_data: MarineTrafficData = list_item.data(Qt.ItemDataRole.UserRole)

            if marine_traffic_data is not None and marine_traffic_data.ship_id is not None:
                
                self.info_bar.addText("🛟 Hozzáadom a hajót a személyes flottádhoz: %s..." % (
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
                    
                    self.info_bar.addText("✅ %s hozzáadása kész" % (marine_traffic_data.ship_name))
        
        finally:
            
            if btn is not None:
                btn.setEnabled(True)
        
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
            (7, data.reported_destination if data.reported_destination is not None else "N/A"),
            (8, data.matched_destination if data.matched_destination is not None else "N/A"),
            (9, data.position_received if data.position_received is not None else "N/A"),
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

    def _update_list_item_by_index(self, index: int, data: MarineTrafficData):
        
        list_item = self.search_result_list.item(index)
        
        if list_item is not None:
            
            self._update_list_item_row(list_item, data)
    
    async def __search_marine(self):
        
        # self.results_table.clearContents()
        
        self.info_bar.clearText()
        
        self.input_name = self.search_fields[0].text().strip()

        if not self.input_name:
            
            self.log.warning("[MARINE] Empty search input provided, skipping search")
            
            self.error_labels[0].setText("Kereső mező nem lehet üres")
            self.error_labels[0].setVisible(True)
            
            self.spinner.hide()
            
            return 
        
        if len(self.input_name) <= 3:
            
            self.log.warning("[MARINE] Search input is too short, skipping search")
            
            self.error_labels[0].setText("(%s) Túl rövid a kereséshez" % (str(self.input_name)))
            self.error_labels[0].setVisible(True)
            
            self.spinner.hide()
            
            return 
        
        self.error_labels[0].setVisible(False)
        
        cache_id = self.input_name.lower()
        
        cached = await self.marine_traffic_search_cache.get_prev_search_data_from_cache(cache_id)
        
        if cached is not None and len(cached.items) > 0:
            
            self.info_bar.addText("✅ Találatok betöltve a gyorsítótárból (%d db)" % len(cached.items))
            
            self.async_playwright.marine_traffic_list = cached.items
            
            await self.populate_results_list(
                number_of_items = len(cached.items),
                marine_traffic_list = cached.items
            )
            
            return
                
        try:
            
            self.info_bar.addText("▶▶▶Elindítom a keresést a Marine Traffic oldalán Playwright Chromiummal...")
              
            page = await self.async_playwright.ensure_page()
     
            if page is not None:
                
                page.set_default_navigation_timeout(timeout = 20000)
                
                page.set_default_timeout(timeout = 10000)
                
                self.info_bar.addText("🌐 Megnyitom a következő oldalt: %s..." % Config.marine_traffic.target_uri)
                
                self.log.debug("Navigating to Marine Traffic URL: %s" % Config.marine_traffic.target_uri)
    
                response = await page.goto(
                    url = Config.marine_traffic.target_uri, 
                    wait_until = "domcontentloaded"
                )
                
                if response.status == 200:
                
                    await page.wait_for_selector("body")
    
                    self.log.info("Marine Traffic page loaded successfully")
                
                    await self.async_playwright.handle_cookies_banner()
                    
                    self.info_bar.addText("✅ Az oldal betöltődött és készen áll a keresésre")

                    await self.async_playwright.handle_searching(self.input_name)
                    
                    if len(self.async_playwright.marine_traffic_list) > 0:
                        
                        await self.marine_traffic_search_cache.cache_marine_search_data(
                            marine_cache_id = cache_id,
                            exp = Config.redis.cache.marine_traffic.exp,
                            raw_data = self.async_playwright.marine_traffic_list
                        )
                        
                        await self.populate_results_list(
                            number_of_items = len(self.async_playwright.marine_traffic_list),
                            marine_traffic_list = self.async_playwright.marine_traffic_list
                        )

                else:
                    
                    self.info_bar.addText("❌ Betöltési hiba, státusz: %s" % str(response.status))  
                        
        except Exception as e:
            
            self.log.exception("An error occurred during the search: %s" % str(e))
            
            self.info_bar.addText("❌ Hiba történt keresés közben: %s" % str(e))

    async def cleanup(self):
        
        self.log.info("Cleaning up Marine Traffic search view")
        
        self.search_result_list.clear()
        
        self.input_field.clear()
        
        self.info_bar.clearText()
        
        self.error_labels[0].setVisible(False)
        
        self.async_playwright.marine_traffic_list.clear()
        
        if self.async_playwright.browser_context is not None:
            
            try:
                
                await self.async_playwright.browser_context.close()
                
                self.log.info("Playwright browser context closed")
                
            except Exception as e:
                
                self.log.warning("Failed to close browser context: %s" % str(e))
            
            finally:
                
                self.async_playwright.browser_context = None
                self.async_playwright.page = None