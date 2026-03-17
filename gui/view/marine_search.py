import hashlib
from functools import partial
import re
import sys
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
    QListWidgetItem
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
        
        self.marine_traffic_list: t.List[MarineTrafficData] = []
        
        self.input_name = ""
        
        self.playwright = None
        
        self.browser_context: BrowserContext | None = None
        
        self.page: Page | None = None
        
        self.playwright_dir = Path(sys.executable).parent / "_internal" / "gui" / "playwright" \
            if getattr(sys, 'frozen', False) else Path(Config.marine_traffic.playwright_dir)
  
        self.info_bar = InfoBar()
        
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

    def random_viewport(self):
        
        return random.choice(Config.marine_traffic.viewports)

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
    
    def make_dir(self):
        
        self.playwright_dir.mkdir(parents = True, exist_ok = True)
        
        profiles_dir = self.playwright_dir / "playwright_profiles"
        
        profiles_dir.mkdir(parents = True, exist_ok = True)

        self.user_agent = random.choice(Config.marine_traffic.user_agents)
        
        self.accept_lang = random.choice(Config.marine_traffic.langs)
        
        profile_hash = hashlib.md5(f"{self.user_agent}|{self.accept_lang}".encode()).hexdigest()

        self.profile_dir = profiles_dir / profile_hash
        
        self.profile_dir.mkdir(parents = True, exist_ok = True)
          
    async def build_browser_context(self):
        
        self.make_dir()
    
        width, height = self.random_viewport()

        self.info_bar.addText(">>> Starting search on Marine Traffic with Playwright Chromium...")

        self.playwright = await self.playwright_manager.start()
        
        self.browser_context = await self.playwright.chromium.launch_persistent_context(
            executable_path = str(self.playwright_dir / "chromium" / "chromium-1187" / "chrome-win" / "chrome.exe"),
            user_data_dir = str(self.profile_dir),
            headless = True,
            viewport = {"width": width, "height": height},
            user_agent = self.user_agent,
            extra_http_headers = {"Accept-Language": self.accept_lang},
            ignore_https_errors = True,
            args = ["--start-maximized","--disable-blink-features=AutomationControlled"],
        )
        
    async def handle_cookies_banner(self, timeout: int = 4000):
        """
        Robustly handles GDPR / cookie consent popup.
        Works with iframe or shadow DOM.
        """
        try:
            
            popup_found = False

            popup_locator = self.page.locator("#qc-cmp2-ui")
            
            try:
                
                await popup_locator.wait_for(timeout = timeout)
                
                popup_found = True
                
            except TimeoutError:
                
                popup_found = False

            if popup_found is False:
                
                for frame in self.page.frames:
                    
                    popup_locator = frame.locator("#qc-cmp2-ui")
                    
                    try:
                        
                        await popup_locator.wait_for(timeout = timeout)
                        
                        self.log.debug("Consent popup found in iframe: %s" % frame.url)
                        
                        popup_found = True
                        
                        break
                    
                    except TimeoutError:
                        continue

            if popup_found is False:
                
                self.log.debug("No consent popup appeared on the page")
                
                return

            agree_button = popup_locator.locator("button.css-1yp8yiu")
            
            self.info_bar.addText("🔔 Cookie consent popup detected, trying to accept...")
            
            try:
                
                await agree_button.click(timeout = timeout)
                
                self.log.info("Consent dialog detected and 'AGREE' button clicked successfully")
                
                self.info_bar.addText("✅ Cookie consent elfogadva")
                
            except TimeoutError:
                
                self.log.debug("Consent dialog exists, but 'AGREE' button was not found or clickable")

        except Exception as e:
            
            self.log.exception("Exception occurred while handling consent dialog: %s" % str(e))

    # async def click_live_map_button(self, page: Page, result: MarineTrafficData):
        
        # await button.click()
        
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
            
            if self.page is not None:
                
                view_on_map_url = Config.marine_traffic.base_url + marine_traffic_data.view_on_map_href
                
                self.info_bar.addText("🌐 Opening map view for ship %s: %s..." % (
                    marine_traffic_data.ship_name.capitalize(),
                    view_on_map_url
                    )
                )
                
                self.log.debug("Navigating to Marine Traffic 'View on Map' URL: %s" % view_on_map_url)
                
                response = await self.page.goto(
                    url = view_on_map_url, 
                    wait_until = "domcontentloaded"
                )
                
                if response.status == 200:
                    
                    await self.page.wait_for_selector("body")

                    self.log.info("View on map of %s[%d] is opened" % (
                        marine_traffic_data.ship_name if marine_traffic_data.ship_name is not None else "Unknown",
                        marine_traffic_data.ship_id if marine_traffic_data.ship_id is not None else "Unknown"
                        )
                    )
                    
                    async with self.page.expect_response(
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
            
            if self.page is not None:
                
                more_details_url = Config.marine_traffic.target_uri + marine_traffic_data.more_deatails_href
                
                self.info_bar.addText("🌐 Opening and reviewing detailed data for ship %s: %s..." % (
                    marine_traffic_data.ship_name.capitalize(),
                    more_details_url
                    )
                )
                
                self.log.debug("Navigating to Marine Traffic URL: %s" % more_details_url)
                
                response = await self.page.goto(
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

                    missing_datas = [field for field, value in marine_traffic_data.model_dump().items() if value is None]
                    # print(missing_datas)  

                    try:
                        
                        if len(missing_datas) > 0: 
                            
                            for data in missing_datas:
                                
                                try:
                                   
                                    locator = self.page.locator(f"text=/.*{data}.*/i").locator("xpath=..")
                                    
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
                        
                        await self._extract_reported_time_and_location()

    async def _extract_reported_time_and_location(self):
        
        try:
            
            block_locator = self.page.locator("#vesselDetails_summarySection")

            text = await block_locator.inner_text()

            location_match = re.search(r"located in the (.*?) \(reported", text)
            reported_match = re.search(r"reported (.*?)\)", text)

            location = location_match.group(1).strip() if location_match is not None else None
            reported = reported_match.group(1).strip() if reported_match is not None else None
            
            self.info_bar.addText("📍 Last position: %s - reported: %s" % (
                location, 
                reported
                )
            )
            
            self.log.debug("Extracted reported location and time: location = '%s', reported = '%s'" % (
                location if location is not None else "Unknown",
                reported if reported is not None else "Unknown"
                )
            )

        except Exception as e:
            
            self.log.exception("Failed extracting summary location/time: %s" % str(e))
                
    async def __pharse_list_item(self, list_item: Locator):
        
        try:
            
            a_tags = await list_item.locator("a").all()

            a_tag = None
            href_value = None
            view_on_map_href = None
            ship_id = None

            if len(a_tags) > 0:
      
                a_tag = a_tags[0]
                
                href_value = await a_tag.get_attribute("href")
                
                if href_value is not None:
                    
                    ship_id_match = re.search(r"shipid:(\d+)", href_value)
                    
                    if ship_id_match is not None:
                        
                        ship_id = ship_id_match.group(1)
                        
                    else:
                        
                        ship_id = None

                if len(a_tags) > 1:
                    
                    view_on_map_href = await a_tags[1].get_attribute("href")

            if a_tag is None:
                
                a_tag = list_item
            
            h5_elements = await a_tag.locator("h5").all()
            
            h5_text = await h5_elements[0].inner_text() if len(h5_elements) > 0 else ""
            
            ship_name_cleaned = re.sub(r"(\(.*?\)|\[.*?\])", "", h5_text).strip()

            flag_spans = await a_tag.locator("span[role='img']").all()
            
            flag_value = None
            
            if len(flag_spans) > 0:
                
                flag_attr = await flag_spans[0].get_attribute("aria-label")
                
                if flag_attr is not None:
                    
                    flag_value = flag_attr.lower()

            p_elements = await a_tag.locator("p").all()
            
            info_text = await p_elements[0].inner_text() if len(p_elements) > 0 else ""

            type_match = re.search(r"Type:\s*([^,]+)", info_text)
            
            type_value = type_match.group(1).strip() if type_match else None

            mmsi_match = re.search(r"MMSI:\s*(\d+)", info_text)
            
            mmsi_value = mmsi_match.group(1) if mmsi_match else None

            call_sign_match = re.search(r"Call Sign:\s*([\w\d]+)", info_text)
            
            call_sign_value = call_sign_match.group(1) if call_sign_match else None

            imo_match = re.search(r"IMO:\s*(\d+)", info_text)
            
            imo_value = imo_match.group(1) if imo_match else None

            ex_name_match = re.search(r"Ex Name:\s*(.+)", info_text, re.I)
            
            if ex_name_match is not None:
                
                ex_name_value = ex_name_match.group(1).strip()
                
                ship_name_cleaned = f"{ship_name_cleaned} Ex name: {ex_name_value}"

            self.marine_traffic_list.append(MarineTrafficData(
                id = None,
                ship_name = ship_name_cleaned,
                more_deatails_href = href_value,
                view_on_map_href = view_on_map_href,
                ship_id = int(ship_id) if ship_id is not None else None,
                type_name = type_value,
                flag = flag_value,
                mmsi = int(mmsi_value) if mmsi_value is not None else None,
                call_sign = call_sign_value,
                imo = int(imo_value) if imo_value is not None else None
                )
            )

        except Exception as e:
            
            self.log.exception("Error parsing list item: %s" % str(e))
    
    async def handle_searching(self, 
        ship_name: str,
        timeout: int = 5000
        ):
        
        try:

            toolbar_input = self.page.locator("input.MuiInputBase-input")
            
            await toolbar_input.wait_for(state = "visible", timeout = timeout)
            
            await toolbar_input.click()

            await toolbar_input.fill(ship_name)
            
            await toolbar_input.press("Enter")

            self.info_bar.addText("🔍 Search started for ship: %s" % ship_name)

            results_container = self.page.locator("div.MuiContainer-root").filter(has = self.page.locator("div.MuiListItem-root"))
    
            await results_container.wait_for(state = "visible", timeout = timeout)
            
            self.marine_traffic_list = []
            
            await self.collect_results(results_container, timeout = timeout)
            
            self.info_bar.addText("Finished search: found %d results for name '%s' <<<" % (
                len(self.marine_traffic_list),
                self.input_name
                )
            )
            
            if len(self.marine_traffic_list) > 0:
                
                await self.populate_results_list(
                    number_of_items = len(self.marine_traffic_list),
                    marine_traffic_list = self.marine_traffic_list
                )
            
        except TimeoutError:
            
            self.info_bar.addText("ℹ️ No results found or results did not load in time")
            
            self.log.warning("No search results found or they did not load in time")
            
        except Exception as e:
            
            self.info_bar.addText("❌ Error while searching ship: %s" % str(e))
            
            self.log.exception("Error during ship search: %s" % str(e))
    
    async def collect_results(self, results_container: Locator, timeout: int = 1500):
        """
        Collects and parses all paginated list items from the results container.
        Calls __pharse_list_item() for each element on each page.
        """
        
        try:
            pagination = results_container.locator("nav[aria-label='pagination navigation']")
            
            try:
                await pagination.wait_for(state = "visible", timeout = timeout)
                
            except TimeoutError:
                
                self.log.info("No pagination detected -> collecting single page results")
                
                list_items = await results_container.locator("div.MuiListItem-root").all()
                
                for item in list_items:
                    
                    await self.__pharse_list_item(item)
                    
                return

            self.log.info("Pagination detected -> collecting paginated results")

            page_buttons = await pagination.locator("button.MuiPaginationItem-page").all()
            
            total_pages = len(page_buttons)
            
            self.log.debug("Total pages detected: %d" % (total_pages))

            for target_page in range(1, total_pages + 1):
                
                pagination = results_container.locator("nav[aria-label='pagination navigation']")
                
                page_btn = pagination.locator("button.MuiPaginationItem-page", has_text = str(target_page))

                try:
                    
                    await expect(page_btn).to_have_attribute("aria-current", "page", timeout = 800)
                    
                    self.log.debug("Already on page %d", target_page)
                    
                except AssertionError:
                    
                    prev_first_text = await results_container.locator("div.MuiListItem-root").first.text_content()
                    
                    await page_btn.wait_for(state = "visible", timeout = timeout)
                   
                    await page_btn.click()

                    await expect(page_btn).to_have_attribute("aria-current", "page", timeout=timeout)

                    try:
                        
                        await expect(results_container.locator("div.MuiListItem-root").first).not_to_have_text(prev_first_text, timeout = 1200)
                    
                    except Exception:
                        
                        self.log.debug("Content check skipped, page switched by aria-current.")

                list_items = await results_container.locator("div.MuiListItem-root").all()
                
                self.log.debug("Found %d list items on page %d" % (
                    len(list_items), 
                    target_page
                    )
                )

                for idx, list_item in enumerate(list_items, start = 1):
                    
                    try:
                        await self.__pharse_list_item(list_item)
                        
                        self.log.debug("Parsed item %d on page %d" % (
                            idx, 
                            target_page
                            )
                        )
                        
                    except Exception as e:
                        
                        self.log.warning("Item parse failed on page %d: %s" % (
                            target_page, 
                            str(e)
                            )
                        )

            self.log.info("Finished collecting %d pages of results" % total_pages)

        except Exception as e:
            
            self.log.exception("Error collecting paginated results: %s" % (str(e)))

    async def ensure_page(self) -> Page:
        """
        Ensures that the Playwright persistent browser context and page are usable.
        Returns a Page object that is guaranteed to be alive.

        - If the browser context is None, a new context and page will be created.
        - If a page already exists but its URL is not "about:blank", the page will be closed
        and the context rebuilt to ensure a clean page.
        - This guarantees that every returned Page is in a clean state (about:blank)
        suitable for fast searches.
        - Any exceptions during page creation or context handling are caught, the context is
        rebuilt, and a new Page is created.
        
        Returns:
            Page -> usable Page object with URL set to about:blank
        """
        if self.browser_context is None:
        
            await self.build_browser_context()
        
        try:
            
            self.page = self.browser_context.pages[0] if len(self.browser_context.pages) > 0 else await self.browser_context.new_page()

            if self.page.url != "about:blank":
                
                await self.page.close()
                
                self.page = None
                
                raise Exception()
        
        except Exception:
            
            self.page = None

            try:
                
                await self.browser_context.close()
                
            except Exception:
                pass
            
            await self.build_browser_context()
            
            self.page = self.browser_context.pages[0] if len(self.browser_context.pages) > 0 else await self.browser_context.new_page()
           
        return self.page
  
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
