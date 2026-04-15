import os
import logging
import asyncio
from functools import partial
import typing as t
from qasync import asyncSlot
from datetime import datetime

from PyQt6.QtWidgets import (
    QGroupBox,
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QListWidget,
    QPushButton,
    QLineEdit,
    QSizePolicy,
    QFrame,
    QLabel,
    QListWidgetItem
)

from PyQt6.QtCore import Qt, QSize, pyqtSignal, QTimer
from PyQt6.QtGui import QIcon, QFont, QPixmap, QCursor, QFontMetrics

from ..modal.map import MapModal
from utils.dc.marine_traffic.vessel_position import VesselPosition
from utils.logger import LoggerMixin
from utils.dc.admin.fleet import FleetData, FleetCacheData
from services.admin.fleet_cache import FleetCacheService
from config import Config
from db import queries

if t.TYPE_CHECKING:
    
    from .admin import AdminView
    
class FleetContent(QWidget, LoggerMixin):
    
    log: logging.Logger
    
    data_loaded = pyqtSignal(object)
    
    def __init__(self,
        admin_view: 'AdminView'         
        ):
        
        super().__init__()
        
        self.spinner = admin_view.main_window.app.spinner
        
        self.marine_view = admin_view.main_window.get_marine_traffic_view()
        
        self.row_maximum_col_widths = []
        self.all_collumns = None
        self.global_max_col_width: int | None = None
        self._recalculate_widths = True
        
        self._items_per_page = 25
        self._page = 0
        self._full_data: t.List[FleetData] = []
        
        self.fleet_cache_service = FleetCacheService(
            redis_client = admin_view.main_window.app.redis_client,
            fleet_lock = admin_view.main_window.app.fleet_lock
        )
        
        self._search_timer = QTimer()
        self._search_timer.setSingleShot(True)
        self._search_timer.setInterval(250)
        self._search_timer.timeout.connect(lambda: self.__do_search(self.search_input.text()))

        self.__init_view()
        
        asyncio.create_task(self.load_cache_data())
        
        self.data_loaded.connect(self.on_data_loaded)
        
    def __init_view(self):
        
        main_layout = QVBoxLayout(self)
        
        self.filter_section = self.__set_filter_section()
        fleet_list = self.__set_fleet_list()
        
        main_layout.addWidget(self.filter_section)
        main_layout.addWidget(fleet_list)

    @staticmethod
    def icon(name: str) -> QIcon:
  
        return QIcon(os.path.join(Config.icon.icon_dir, name))   
          
    def __set_filter_section(self):
        
        search_group = QGroupBox()
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Keresés...")
        self.search_input.setObjectName("WarehouseSearchInput")
        self.search_input.textChanged.connect(self.__handle_search_input)
        
        search_layout = QHBoxLayout()
        search_layout.addWidget(self.search_input)
        
        search_group.setLayout(search_layout)
        
        return search_group
        
    def __set_fleet_list(self):
        
        search_group = QGroupBox()
        
        col_layout = QVBoxLayout(search_group)
        col_layout.setContentsMargins(0, 0, 0, 0)
    
        self.fleet_list = QListWidget()
        self.fleet_list.setObjectName("MessageList")
        self.fleet_list.setFrameShape(QFrame.Shape.NoFrame)
        self.fleet_list.setMouseTracking(True)
        
        self.fleet_list.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.fleet_list.setCursor(Qt.CursorShape.PointingHandCursor)
        
        self.prev_btn = QPushButton()
        self.prev_btn.setIcon(FleetContent.icon("chevron-left.svg"))
        self.prev_btn.setFixedWidth(60)
        self.prev_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.prev_btn.clicked.connect(lambda: self._change_top_page(-1))
        
        pagination = QHBoxLayout()
        pagination.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.page_label = QLabel("1 / 1")
        self.page_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.page_label.setFixedWidth(80)
        
        self.next_btn = QPushButton()
        self.next_btn.setIcon(FleetContent.icon("chevron-right.svg"))
        self.next_btn.setFixedWidth(60)
        self.next_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.next_btn.clicked.connect(lambda: self._change_top_page(1))
       
        pagination.addWidget(self.prev_btn)
        pagination.addWidget(self.page_label)
        pagination.addWidget(self.next_btn)
        
        col_layout.addWidget(self.fleet_list)
        col_layout.addSpacing(20)
        col_layout.addLayout(pagination)
        col_layout.addSpacing(20)
        
        return search_group
    
    @asyncSlot(QListWidgetItem)
    async def __show_on_map(self, list_item: QListWidgetItem):
        
        boat: FleetData = list_item.data(Qt.ItemDataRole.UserRole)
        
        if boat is not None and boat.view_on_map_href is not None:
            
            page = await self.marine_view.async_playwright.ensure_page()
            
            if page is not None:
                
                view_on_map_url = Config.marine_traffic.base_url + boat.view_on_map_href
                
                self.log.debug("Navigating to Marine Traffic 'View on Map' URL: %s" % view_on_map_url)
                
                response = await self.marine_view.async_playwright.page.goto(
                    url = view_on_map_url, 
                    wait_until = "domcontentloaded"
                )
                
                if response.status == 200:
                    
                    await self.marine_view.async_playwright.page.wait_for_selector("body")

                    self.log.info("View on map of %s[%d] is opened" % (
                        boat.name if boat.name is not None else "Unknown",
                        boat.ship_id if boat.ship_id is not None else "Unknown"
                        )
                    )
                    
                    async with self.marine_view.async_playwright.page.expect_response(
                        lambda response: f"getvesseljson/shipid:{boat.ship_id}" in response.url
                        ) as response_info:
                        
                        response_obj = await response_info.value  

                    try:
                        
                        response_data = await response_obj.json()  

                        vessel_position = VesselPosition(
                            ship_name = boat.name,
                            lat = response_data.get("LAT"),
                            lon = response_data.get("LON")
                        )

                        self.log.debug("Position retrieved: %s [%d] -> lat: %.5f, lon: %.5f" % (
                            boat.name,
                            boat.ship_id,
                            vessel_position.lat,
                            vessel_position.lon
                            )
                        )
                        
                        place_name = None
                        
                        try:
                            
                            place_name = await asyncio.to_thread(
                                self.marine_view.geocoding_api.reverse_geocode,
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
                
    def __handle_search_input(self):
        self._search_timer.start()
    
    def __do_search(self, text: str):
        
        text = text.strip().lower()
        print("Searching for:", text)
        
    def _emit_cache_data_safe(self, item: FleetCacheData):
        QTimer.singleShot(0, lambda: self.data_loaded.emit(item))
    
    async def load_cache_data(self):
        
        self.cache_data = await self.fleet_cache_service.get_fleet_from_cache(
            fleet_cache_id = Config.redis.cache.fleet.id, 
            exp = Config.redis.cache.fleet.exp
        )
        
        self._emit_cache_data_safe(self.cache_data)
        
    def on_data_loaded(self, cache_data):
        
        if isinstance(cache_data, FleetCacheData) and hasattr(cache_data, "items"):
            
            if len(cache_data.items) > 0:
                
                self.populate_fleet_list(cache_data.items)
                
    def populate_fleet_list(self, boats: t.List[FleetData]):
        
        if self._recalculate_widths is True:
            
            self.row_maximum_col_widths.clear()
        
        self.fleet_list.clear()
        self.fleet_list.setUniformItemSizes(False)
        
        try:
            
            self._full_data = boats
            
            visible_data = [d for d in boats if isinstance(d, FleetData)]
            
            total_pages = max(1, (len(visible_data) + self._items_per_page - 1) // self._items_per_page)
            self._page = max(0, min(self._page, total_pages - 1))
            
            start_idx = self._page * self._items_per_page
            
            page_data = visible_data[start_idx:start_idx + self._items_per_page]
            
            self.page_label.setText(f"{self._page + 1} / {total_pages}")
            
            font = QFont()
            font.setPointSize(10)
            font.setBold(True)
            
            for boat in page_data:
                
                list_item = QListWidgetItem()
                
                container = QWidget()
                container.setFixedHeight(35)
                                
                id_label = QLabel(str(boat.id))
                id_label.setFont(font)
                id_label.setToolTip("Hajó azonosítója")
                
                flag_label = QLabel()
                flag_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

                flag_code = boat.flag.lower() if boat.flag is not None else "nan"
            
                pixmap = QPixmap(os.path.join(Config.flags.flag_dir, f"{flag_code}.png"))

                if not pixmap.isNull():

                    scaled_pixmap = pixmap.scaled(QSize(32, 20), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                    
                    flag_label.setPixmap(scaled_pixmap)
                    flag_label.setToolTip("Lobogó")
                
                else:
                    
                    self.log.error("Could not load flag image for code %s" % flag_code)
                    
                boat_name_label = QLabel(boat.name)
                boat_name_label.setFont(font)
                boat_name_label.setToolTip("Hajó neve")
                
                ship_id_label = QLabel(str(boat.ship_id) if boat.ship_id is not None else "N/A")
                ship_id_label.setFont(font)
                ship_id_label.setToolTip("Hajó azonosító marine traffic-en")
                
                imo_label = QLabel(str(boat.imo) if boat.imo is not None else "N/A")
                imo_label.setFont(font)
                imo_label.setToolTip("Hajó IMO száma")

                mmsi_label = QLabel(str(boat.mmsi) if boat.mmsi is not None else "N/A")
                mmsi_label.setFont(font)
                mmsi_label.setToolTip("Hajó MMSI száma")
                
                callsign_label = QLabel(boat.callsign if boat.callsign is not None else "N/A")
                callsign_label.setFont(font)
                callsign_label.setToolTip("Hajó hívójele")

                type_name_label = QLabel(boat.type_name if boat.type_name is not None else "N/A")
                type_name_label.setFont(font)
                type_name_label.setToolTip("Hajó típusa")

                show_on_map = QPushButton()
                show_on_map.setObjectName("TrashButton")
                show_on_map.setCursor(Qt.CursorShape.PointingHandCursor)
                show_on_map.setIcon(FleetContent.icon("search.svg"))
                show_on_map.setIconSize(QSize(20, 20))
                show_on_map.setToolTip("Mutatás a térképen")
                
                show_on_map.clicked.connect(lambda _, item = list_item: self.__show_on_map(item)) 
                
                h_layout = QHBoxLayout(container)
                h_layout.setContentsMargins(50, 0, 0, 0)
                
                widgets = [
                    id_label,
                    flag_label,
                    boat_name_label,
                    ship_id_label,
                    imo_label,
                    mmsi_label,
                    callsign_label,
                    type_name_label,
                    show_on_map
                ]
                
                if self.all_collumns is None:
                    
                    self.all_collumns = len(widgets)

                if self._recalculate_widths is True:
            
                    current_row_max_col_width = max([QFontMetrics(w.font()).horizontalAdvance(w.text()) 
                        for w in widgets if isinstance(w, QLabel)])
                    
                    self.row_maximum_col_widths.append(current_row_max_col_width)

                for idx, w in enumerate(widgets):
  
                    if isinstance(w, QLabel):

                        w.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
                        w.setContentsMargins(0, 0, 0, 0)
                        w.setWordWrap(False)
                
                    h_layout.addWidget(w)
                    
                    if idx == 2:
                        h_layout.addSpacing(30)
                
                list_item.setSizeHint(QSize(container.sizeHint().width(), 35))
                
                self.fleet_list.addItem(list_item)
                self.fleet_list.setItemWidget(list_item, container)
                self.fleet_list.setSpacing(0)
                
                list_item.setData(Qt.ItemDataRole.UserRole, boat)
            
            self.calculate_global_col_width_for_fleet_list(self.fleet_list)
            
        finally:
            
            self.fleet_list.setUpdatesEnabled(True)
            
    def _change_top_page(self, delta: int):
        
        self._page += delta
        self.populate_fleet_list(self._full_data)
    
    def calculate_global_col_width_for_fleet_list(self, list_widget: QListWidget):
    
        # print(row_maximum_col_widths)
        if len(self.row_maximum_col_widths) > 0:
          
            self.global_max_col_width: int = max(self.row_maximum_col_widths)
            # print("Global max text width:", global_max_width)
            # print("Number of columns:", all_collumns)
            if self.global_max_col_width is not None:
                    
                if self.all_collumns is not None:
                    
                    first_container = list_widget.itemWidget(list_widget.item(0))
                    spacing = first_container.layout().spacing() if first_container is not None else 6
                    
                    row_width = (2 * 40) + (6 * 150) + (1 * 30) + 50 + 30 + (spacing * (self.all_collumns - 1))
                    
                    for i in range(list_widget.count()):
                        
                        item = list_widget.item(i)
            
                        if item is not None:
                            
                            container = list_widget.itemWidget(item)

                            container.setMaximumWidth(row_width)
                            
                            item.setSizeHint(QSize(row_width, item.sizeHint().height()))
                            
                            layout = container.layout()

                            for j in range(layout.count()):
                                
                                child = layout.itemAt(j)
                                
                                if child is not None:
                                    
                                    child.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
                                
                                    widget = child.widget()
                                
                                    if widget is not None:
                                        
                                        x = 1.5

                                        if j <= 1:
                                        
                                            widget.setFixedWidth(40)
                                            
                                        elif j >= 2 and j <= 7:
                                        
                                            widget.setFixedWidth(150)
                                            
                                            if isinstance(widget, QLabel):
                                                widget.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
                                            
                                        elif j == 8:
                                            
                                            if isinstance(widget, QPushButton):
                                                
                                                widget.setFixedWidth(30)
                                                widget.setFixedHeight(30)     
                                                                                           
                                        else:
                                            
                                            widget.setFixedWidth(int(self.global_max_col_width * x))

            self._recalculate_widths = False     