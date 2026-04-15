import os, sys
from pathlib import Path
import typing as t
import asyncio
from qasync import asyncSlot
import logging

from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QPushButton,
    QLabel,
    QSizePolicy
)
from PyQt6.QtCore import Qt, QTimer, QTime, QDate, QSize, QPoint
from PyQt6.QtGui import QIcon, QPixmap, QPalette, QBrush, QResizeEvent, QColor, QImage, QPainter, QMouseEvent
from PyQt6.QtSvg import QSvgRenderer

from config import Config
from utils.logger import LoggerMixin
from .email import EmailView
from .translate import TranslateView
from .storage import StorageView
from .mahart_search import MahartPortsSearchView
from .marine_search import MarineTrafficSearchView
from .todo import TodoView
from .admin.admin import AdminView
from .admin.fleet import FleetContent
from utils.dc.admin.reminder import CalendarData, CalendarCacheData
from .admin.works.works import AdminWorksContent
from .modal.reminder_alert import ReminderAlertModal
from services.admin.calendar_reminder_cache import CalendarReminderCacheService
from utils.dc.admin.work.other_work_prices import OtherWorkPrices
from utils.dc.admin.work.other_work_prices_hun import OtherWorkPricesHun, HunPriceTier
from utils.enums.hun_price_category_enum import HunPriceCategoryEnum
from utils.enums.hun_price_tier_enum import HunPriceTierEnum
from view.admin.custom import CustomCalendar
from .modal.elements import ReminderDay
from .admin.calendar import CalendarContent
from routes.api.google.user_client import UserClientView
from utils.dc.websocket.reminder_event import ReminderEvent
from db import queries

if t.TYPE_CHECKING:
    
    from async_loop import QtApplication
    from view.google_auth import GmailLoginWindow

class MainWindow(QMainWindow, LoggerMixin):
    
    log: logging.Logger

    if getattr(sys, "frozen", False):
        
        PATH = Path(sys.executable).parent / "_internal" / Config.img.main_window_bg_path
        
    else:
            
        PATH = Path(Config.img.main_window_bg_path)

    def __init__(self,
        app: 'QtApplication',       
        user_client: UserClientView,
        gmail_login_window: 'GmailLoginWindow'
        ):

        super().__init__()
        
        self._cache_clearing_in_progress = False
        
        self._close_requested = False
        
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        self._drag_pos: QPoint | None = None
        self._is_maximized = False
        
        self.setWindowTitle("Example Company Ltd.")
        
        self.app = app
        
        self.user_client = user_client
        
        self.gmail_login_window = gmail_login_window
        
        self.other_work_prices: OtherWorkPrices = None
        
        self.current_object_id: int | None = None
        
        self.reminder_worker = app.reminder_worker
        
        self.rental_worker = app.rental_worker
        
        self.custom_calendar = None
        
        self.notifier = app.notifier
        
        self.rental_end = app.rental_end
        
        self.notifier.reminder_warning.connect(self.show_reminder)
        
        self.redis_client = app.redis_client
        
        self.reminder_cache = CalendarReminderCacheService(
            redis_client = app.redis_client,
            reminder_lock = app.reminder_lock
        )
     
        self.reminder_day = None
        
        self._active_reminder_modal: ReminderAlertModal | None = None
        
        self.que_calendar_data_list: list[CalendarData] = []
        
        self._active_reminder_ids: set[int] = set()
        
        self.db = app.db
        
        self.todo_view: TodoView | None = None
        
        self.admin_view: AdminView | None = None
        
        self.storage_view: StorageView | None = None
        
        self.marine_view: MarineTrafficSearchView | None = None
        
        self._bg_pixmap = self.__render_svg_background()
        
        self._last_bg_size = None
        
        self.resize(1280, 720)
        
        self.__init_ui()

        self.__apply_background()
        
        asyncio.ensure_future(self.__select_other_work_prices())
        asyncio.ensure_future(self.__select_other_work_prices_hun())
    
    def closeEvent(self, event):
        
        if getattr(self, "_cache_clearing_in_progress", False):
            
            self._close_requested = True
            
            self.log.warning("Window close requested, waiting for cache clear to finish")
            
            event.ignore()
            
        else:
            
            super().closeEvent(event)
    
    @staticmethod
    def icon(name: str) -> QIcon:

        return QIcon(os.path.join(Config.icon.icon_dir, name))
    
    async def __select_other_work_prices(self) -> OtherWorkPrices:
        
        query_result = await queries.select_existing_other_work_prices()

        self.other_work_prices = OtherWorkPrices(
            work_during_hours = query_result[0].work_during_hours,
            work_outside_hours = query_result[0].work_outside_hours,
            work_sundays = query_result[0].work_sundays,
            travel_budapest = query_result[0].travel_budapest,
            travel_outside = query_result[0].travel_outside,
            travel_time = query_result[0].travel_time,
            travel_time_outside = query_result[0].travel_time_outside,
            travel_time_sundays = query_result[0].travel_time_sundays,
            accommodation = query_result[0].accommodation
        ) 

        self.log.debug("Existing other_work prices selected: %s" % self.other_work_prices)
        
        return self.other_work_prices
    
    async def __select_other_work_prices_hun(self) -> OtherWorkPricesHun | None:
        
        query_result = await queries.select_existing_other_work_prices_hun()
        
        if query_result is None:
            
            self.other_work_prices_hun = None
            
            self.log.debug("No HUF other_work prices found in database")
            
            return None
        
        hun_prices_obj = query_result[0]
        
        tier_map: dict[HunPriceCategoryEnum, dict[HunPriceTierEnum, int]] = {}
        
        for t_row in hun_prices_obj.tiers:
            
            if t_row.category not in tier_map:
                
                tier_map[t_row.category] = {}
            
            tier_map[t_row.category][t_row.tier] = t_row.price
        
        survey_data = tier_map.get(HunPriceCategoryEnum.SURVEY_DELIVERY, {})
        repair_data = tier_map.get(HunPriceCategoryEnum.REPAIR_MAINTENANCE, {})
        travel_data = tier_map.get(HunPriceCategoryEnum.TRAVEL_TIME, {})
        
        self.other_work_prices_hun = OtherWorkPricesHun(
            survey_delivery = HunPriceTier(
                weekday = survey_data.get(HunPriceTierEnum.WEEKDAY, 0),
                weekend = survey_data.get(HunPriceTierEnum.WEEKEND, 0),
                sunday = survey_data.get(HunPriceTierEnum.SUNDAY, 0)
            ),
            repair_maintenance = HunPriceTier(
                weekday = repair_data.get(HunPriceTierEnum.WEEKDAY, 0),
                weekend = repair_data.get(HunPriceTierEnum.WEEKEND, 0),
                sunday = repair_data.get(HunPriceTierEnum.SUNDAY, 0)
            ),
            travel_time = HunPriceTier(
                weekday = travel_data.get(HunPriceTierEnum.WEEKDAY, 0),
                weekend = travel_data.get(HunPriceTierEnum.WEEKEND, 0),
                sunday = travel_data.get(HunPriceTierEnum.SUNDAY, 0)
            ),
            travel_budapest = hun_prices_obj.travel_budapest or 0,
            travel_outside_km = hun_prices_obj.travel_outside_km or 0
        )
        
        self.log.debug("Existing HUF other_work prices selected: %s" % self.other_work_prices_hun)
        
        return self.other_work_prices_hun
    
    @asyncSlot(CalendarData)
    async def show_reminder(self, calendar_data: CalendarData):
   
        if not isinstance(calendar_data, CalendarData):
           
            self.log.error("Invalid calendar data provided to show_reminder")
            
            return
        
        if self._active_reminder_modal is not None and self._active_reminder_modal.isVisible() == True:
            
            self.log.debug("Reminder modal already open, enqueue new calendar_data")
            
            if calendar_data.id not in self._active_reminder_ids:
             
                if not any(calendar_data.id == que_data.id for que_data in self.que_calendar_data_list):
                    
                    self.que_calendar_data_list.append(calendar_data)
            
            return
        
        await self.open_reminder_modal(calendar_data)

    async def open_reminder_modal(self, calendar_data: CalendarData):
   
        self.log.debug("Reminder warning Emit -> %s" % str(calendar_data))
        
        self._active_reminder_modal = ReminderAlertModal(calendar_data, parent = self)
        
        self._active_reminder_ids.add(self._active_reminder_modal.data.id)
       
        await self._active_reminder_modal.exec_async()

        result = self._active_reminder_modal.result_value()

        self._active_reminder_modal = None

        if result == 0:
            
            self._active_reminder_ids.discard(calendar_data.id)
            
            await queries.update_calendar_by_id(
                id = calendar_data.id
            )
            
            await self._handle_cache_refresh(
                calendar_data = calendar_data, 
                refresh_all = True, 
                refresh_day = False
            )
            
            await self._emit_reminder_action(
                reminder_id = calendar_data.id,
                action = "disable",
                calendar_cache_id = calendar_data.calendar_cache_id
            )

        elif result == 1:
            
            self._active_reminder_ids.discard(calendar_data.id)
            
            await queries.update_reminder_datetime_by_id(
                id = calendar_data.id,
                datetime = calendar_data.date
            )
                
            await self._handle_cache_refresh(
                calendar_data = calendar_data, 
                refresh_all = False, 
                refresh_day = True
            )
            
            await self._emit_reminder_action(
                reminder_id = calendar_data.id,
                action = "snooze",
                calendar_cache_id = calendar_data.calendar_cache_id
            )

        else:
            
            self.log.info("Reminder modal closed without user interaction")
            
        if len(self.que_calendar_data_list) > 0:
            
            next_data = self.que_calendar_data_list.pop(0)
   
            if self._active_reminder_modal is None:
               
                await self.open_reminder_modal(next_data)
 
    async def _handle_cache_refresh(self, 
        calendar_data: CalendarData, 
        refresh_all: bool = False,
        refresh_day: bool = False
        ):
        
        if not calendar_data or not calendar_data.calendar_cache_id:
           
            self.log.warning("Missing calendar_cache_id, skipping cache handling")
            
            return

        if not (self.reminder_cache and self.reminder_cache.redis_client and self.reminder_cache.redis_client.client):
          
            self.log.warning("Redis client not ready, skipping cache clear")
           
            return

        await self.reminder_cache.clear_cache(calendar_data.calendar_cache_id)
        
        cache_data = None
        
        if refresh_all is True or refresh_day is True:
            
            cache_data = await self.reminder_cache.get_reminders_from_cache(
                calendar_cache_id = calendar_data.calendar_cache_id,
                exp = Config.redis.cache.reminders.exp
            )
        
        calendar_content = self.get_calendar_content()
        
        if calendar_content is not None and isinstance(calendar_content.calendar, CustomCalendar):
            
            self.custom_calendar = calendar_content.calendar
            
            self.reminder_day = calendar_content.reminder_day_modal.day_view
            
            if refresh_all is True:
                
                self.custom_calendar.set_marked_dates(cache_data)
                
                self._refresh_reminder_day(
                    cache_data = cache_data, 
                    reminder_day = self.reminder_day
                )
                
            elif refresh_day is True:
                
                self._refresh_reminder_day(
                    cache_data = cache_data, 
                    reminder_day = self.reminder_day
                )
    
    def _refresh_reminder_day(self, cache_data: CalendarCacheData, reminder_day: ReminderDay):

        if (isinstance(cache_data, CalendarCacheData) and cache_data.items \
            and all(isinstance(item, CalendarData) for item in cache_data.items)
            ):
      
            reminder_day.update_reminders(cache_data.items)    
            
        else:
            
            self.log.warning("No valid reminder items found in cache data")

    async def _emit_reminder_action(self, reminder_id: int, action: str, calendar_cache_id: str):
        
        ws_client = self.app.websocket_client
        
        if ws_client is not None:
            
            reminder_event = ReminderEvent(
                reminder_id = reminder_id,
                action = action,
                calendar_cache_id = calendar_cache_id
            )
            
            self.log.info("Emitting reminder_action via websocket: %s" % str(reminder_event))
            
            await ws_client.reminder_action(reminder_event)

    async def handle_remote_reminder_action(self, reminder_event: ReminderEvent):
        
        self.log.info("Received remote reminder action: %s" % str(reminder_event))
        
        reminder_id = reminder_event.reminder_id
        
        if self._active_reminder_modal is not None and self._active_reminder_modal.data.id == reminder_id:
            
            self.log.info("Closing active reminder modal for id: %d (remote %s)" % (reminder_id, reminder_event.action))
            
            self._active_reminder_modal._result = None
            self._active_reminder_modal.reject()
        
        self.que_calendar_data_list = [
            item for item in self.que_calendar_data_list if item.id != reminder_id
        ]
        
        self._active_reminder_ids.discard(reminder_id)
        
        if self.reminder_worker is not None:
            
            self.reminder_worker.notify_cache_update_needed(None)
     
    def get_calendar_content(self) -> CalendarContent | None:
        
        if isinstance(self.content_widget, AdminView):
            
            current_content = self.content_widget.get_current_content()
            
            if isinstance(current_content, CalendarContent):
                
                return current_content
        
        elif isinstance(self.content_widget, StorageView):
            
            self.admin_view = self.get_admin_view()
            
            if self.admin_view is not None:
                
                calendar_content = self.admin_view.get_calendar_content()
                
                if calendar_content is not None:
                    
                    return calendar_content
        
        return None
              
    def __init_ui(self):
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        central_widget.setObjectName("MainWindowCentral")

        self.navbar = self.set_navbar()
        self.content_widget = QWidget()
        
        self.main_layout = QVBoxLayout(central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        self.main_layout.addWidget(self.navbar)
        self.main_layout.addWidget(self.content_widget, stretch = 1)
        
        self._set_window_radius(12)

    def __render_svg_background(self) -> QPixmap | None:

        if self.PATH.exists() == False:
            
            return None

        renderer = QSvgRenderer(str(self.PATH))

        if renderer.isValid() == False:
            
            return None

        target = renderer.defaultSize()
        
        if target.isEmpty():
            
            target = QSize(1920, 1080)
        
        else:
            
            scale = max(1920 / target.width(), 1080 / target.height())
            
            target = QSize(int(target.width() * scale), int(target.height() * scale))
        
        image = QImage(target, QImage.Format.Format_ARGB32_Premultiplied)
        image.fill(QColor("#2b2b2b"))
        
        painter = QPainter(image)
        
        renderer.render(painter)
        
        painter.end()

        return QPixmap.fromImage(image)

    def __apply_background(self) -> None:

        central = self.centralWidget()
        
        if central is None:
            return

        if self._bg_pixmap is not None and not self._bg_pixmap.isNull():

            current_size = self.size()
            
            if self._last_bg_size is not None:
                
                w_diff = abs(current_size.width() - self._last_bg_size.width())
                h_diff = abs(current_size.height() - self._last_bg_size.height())
                
                if w_diff < self._last_bg_size.width() * 0.1 and h_diff < self._last_bg_size.height() * 0.1:
                    
                    return
            
            self._last_bg_size = current_size
            
            scaled = self._bg_pixmap.scaled(
                current_size,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )

            bg = QPixmap(current_size)
            bg.fill(QColor("#2b2b2b"))
            
            painter = QPainter(bg)
            
            x = (self.width() - scaled.width()) // 2
            y = (self.height() - scaled.height()) // 2
            
            painter.drawPixmap(x, y, scaled)
            painter.end()

            palette = QPalette()
            
            palette.setBrush(QPalette.ColorRole.Window, QBrush(bg))

            central.setPalette(palette)

            central.setAutoFillBackground(True)
            
        else:
  
            self.resize(420, 180)

    def resizeEvent(self, event: QResizeEvent) -> None:

        if isinstance(self.content_widget, EmailView):
            
            self.__clear_background()
            
        elif isinstance(self.content_widget, TranslateView):

            self.__clear_background()

        elif isinstance(self.content_widget, StorageView):

            self.__clear_background()
            
        elif isinstance(self.content_widget, AdminView):
            
            self.__clear_background()
            
        elif isinstance(self.content_widget, TodoView):
            
            self.__clear_background()
            
        elif isinstance(self.content_widget, MahartPortsSearchView):
            
            self.__clear_background()    
            
        elif isinstance(self.content_widget, MarineTrafficSearchView):
            
            self.__clear_background()    
        
        else:
           
            self.__apply_background()

        super().resizeEvent(event)

    def _is_on_navbar(self, event: QMouseEvent) -> bool:
        
        local_pos = self.navbar.mapFromGlobal(event.globalPosition().toPoint())
        
        return self.navbar.rect().contains(local_pos)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        
        if event.button() == Qt.MouseButton.LeftButton and self._is_on_navbar(event):
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
        
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        
        if self._drag_pos is not None and event.buttons() & Qt.MouseButton.LeftButton:
            
            if self.isMaximized():
                
                self.showNormal()
                self._btn_maximize.setText("☐")
                self._drag_pos = QPoint(self.width() // 2, 25)
                
            self.move(event.globalPosition().toPoint() - self._drag_pos)
        
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        
        self._drag_pos = None
        
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        
        if self._is_on_navbar(event):
            self._toggle_maximize()
        
        else:
            super().mouseDoubleClickEvent(event)

    def __clear_background(self):
        
        central = self.centralWidget()
        
        if central is None:
            return
        
        central.setAutoFillBackground(True)
        
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, QColor("#2b2b2b"))
        
        central.setPalette(palette)
        
    def __set_content_widget(self, new_widget: QWidget):
        
        if isinstance(self.content_widget, MarineTrafficSearchView):
            
            asyncio.create_task(self.content_widget.cleanup())
        
        if self.admin_view is not None:
            
            current_admin_view = self.admin_view.get_current_content()
            
            if isinstance(current_admin_view, FleetContent):
                
                marine_view = current_admin_view.marine_view
                
                if marine_view is not None:
                    
                    asyncio.create_task(marine_view.cleanup())
            
            if current_admin_view is not None and isinstance(current_admin_view, AdminWorksContent):
                
                add_work_widget = current_admin_view.add_work_widget
                edit_work_widget = current_admin_view.edit_work_widget
                
                if add_work_widget is not None:
                   
                    QTimer.singleShot(0, lambda: asyncio.create_task(add_work_widget.reset_form()))
                    
                if edit_work_widget is not None:
                  
                    QTimer.singleShot(0, lambda: asyncio.create_task(edit_work_widget.reset_form(False)))
 
        self.main_layout.removeWidget(self.content_widget)

        self.content_widget.setParent(None)
        self.content_widget = new_widget

        self.main_layout.addWidget(self.content_widget, stretch = 1)

        if isinstance(new_widget, EmailView):

            self.__clear_background()

        elif isinstance(new_widget, TranslateView):

            self.__clear_background()

        elif isinstance(new_widget, StorageView):

            self.__clear_background()
            
            asyncio.create_task(
                new_widget.load_cache_data(
                    cache_id = Config.redis.cache.material.id,
                    exp = Config.redis.cache.material.exp
                )
            )
            
        elif isinstance(new_widget, AdminView):
            
            self.__clear_background()
            
        elif isinstance(new_widget, TodoView):
            
            self.__clear_background()
            
        elif isinstance(new_widget, MahartPortsSearchView):
            
            self.__clear_background()    
            
        elif isinstance(new_widget, MarineTrafficSearchView):
            
            self.__clear_background()    

        else:

            self.__apply_background()

    def create_nav_button(self, text: str, icon_name: str, widget_factory: t.Callable[[], QWidget]):
        
        btn = QPushButton(text)
        btn.setObjectName("Navbtn")
        btn.setIcon(MainWindow.icon(icon_name))
        btn.setCursor(Qt.CursorShape.PointingHandCursor)

        btn.clicked.connect(lambda: (self.log.debug(f"Navigated to: {text}"), self.__set_content_widget(widget_factory()))[-1])
        
        return btn
    
    def _create_refresh_btn(self, icon_name: str, callback: t.Callable[[], t.Awaitable]) -> QPushButton:
        
        btn = QPushButton("Cache")
        btn.setObjectName("Navbtn")
        btn.setIcon(MainWindow.icon(icon_name))
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setIconSize(QSize(20, 20))
        btn.setToolTip("Gyorsítótár frissítése")
        
        btn.clicked.connect(lambda: (self.log.debug("Refresh button clicked"), callback()))

        return btn
    
    def set_navbar(self) -> QWidget:
        
        navbar = QWidget()
        navbar.setFixedHeight(50)
        navbar.setObjectName("Navbar")

        self.datetime_label = QLabel()
        self.datetime_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.datetime_label.setObjectName("Time")
        
        self.timer = QTimer()
        self.timer.timeout.connect(self.__update_datetime)
        self.timer.start(1000)  

        self.__update_datetime()

        layout = QHBoxLayout(navbar)
        layout.setContentsMargins(5, 0, 15, 0)
        layout.setSpacing(10)
        
        self.email_view = EmailView(self)
        
        self.mahart_view = MahartPortsSearchView(self)
        self.mahart_view.refresh_todo.connect(self.refresh_todo_view_table)
        
        self.translate_view = TranslateView(self)
        
        layout.addWidget(self.create_nav_button("Napi Teendő", "calendar.svg", lambda: self.get_todo_view()))
        layout.addWidget(self.create_nav_button("E-mail", "mail.svg", lambda: self.email_view))
        layout.addWidget(self.create_nav_button("Raktár", "box.svg", lambda: self.get_storage_view()))
        layout.addWidget(self.create_nav_button("Mahart Ports", "info.svg", lambda: self.mahart_view))
        layout.addWidget(self.create_nav_button("Marine Traffic", "info.svg", lambda: self.get_marine_traffic_view()))
        layout.addWidget(self.create_nav_button("FlugiCompanyGPT", "book-open.svg", lambda: self.translate_view))
        layout.addWidget(self.create_nav_button("Admin", "tool.svg", lambda: self.get_admin_view()))
        layout.addWidget(self._create_refresh_btn("refresh.svg", self.__clear_all_cache))
        
        layout.addStretch()
        layout.addWidget(self.datetime_label)
        
        layout.addSpacing(10)
        
        btn_minimize = QPushButton("—")
        btn_minimize.setObjectName("WinControlBtn")
        btn_minimize.setFixedSize(36, 36)
        btn_minimize.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_minimize.clicked.connect(self.showMinimized)
        
        self._btn_maximize = QPushButton("☐")
        self._btn_maximize.setObjectName("WinControlBtn")
        self._btn_maximize.setFixedSize(36, 36)
        self._btn_maximize.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_maximize.clicked.connect(self._toggle_maximize)
        
        btn_close = QPushButton("✕")
        btn_close.setObjectName("WinCloseBtn")
        btn_close.setFixedSize(36, 36)
        btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_close.clicked.connect(self.close)
        
        layout.addWidget(btn_minimize)
        layout.addWidget(self._btn_maximize)
        layout.addWidget(btn_close)
    
        return navbar
    
    def _toggle_maximize(self):
        
        if self.isMaximized():
            
            self.showNormal()
            self._btn_maximize.setText("☐")
            self._set_window_radius(12)
       
        else:
            self.showMaximized()
            self._btn_maximize.setText("\u2750")
            self._set_window_radius(0)

    def _set_window_radius(self, radius: int):
        
        central = self.centralWidget()
        
        if central is not None:
            
            central.setStyleSheet(f"""
                #MainWindowCentral {{
                    background: transparent;
                    border: {"1px solid #505050" if radius > 0 else "none"};
                    border-radius: {radius}px;
                }}
            """)
        
        if hasattr(self, 'navbar'):
            
            if radius > 0:
                self.navbar.setStyleSheet("""
                    #Navbar {
                        border-top-left-radius: 12px;
                        border-top-right-radius: 12px;
                    }
                """)
           
            else:
                
                self.navbar.setStyleSheet("")
    
    @asyncSlot(bool)
    async def refresh_todo_view_table(self, refresh_needed: bool):
        
        if refresh_needed is True:
                
            if self.todo_view is not None:
                
                await self.todo_view.load_page()
            
            else:
                
                self.get_todo_view()
                
                await self.refresh_todo_view_table(True)

    @asyncSlot()
    async def __clear_all_cache(self) -> None:
        """
        Clear all cached data in Redis.

        This method removes every cached key and value stored in Redis,
        effectively resetting the entire cache state. It is used when a full
        cache refresh is required to ensure all data is reloaded cleanly.
        """
        
        self.log.info("Clearing all Redis cache -> BEGIN")
        
        try:
            
            self._cache_clearing_in_progress = True
       
            if self.reminder_worker is not None:
                
                self.reminder_worker.notify_cache_update_needed(None)
            
            if self.rental_worker is not None:
                
                self.rental_worker.notify_cache_update_needed(True)
            
            self.admin_view = self.get_admin_view()
                
            if self.admin_view is not None:
                
                admin_storage_content = self.admin_view.get_admin_storage_content()
                
                if admin_storage_content is not None:
                    
                    await admin_storage_content.storage_cache.clear_cache(Config.redis.cache.storage.id)
                    
                    await admin_storage_content.load_cache_data(
                        target = Config.redis.cache.storage.target,
                        cache_id = Config.redis.cache.storage.id,
                        exp = Config.redis.cache.storage.exp
                    )
                    
                    await admin_storage_content.storage_datatable_cache.clear_cache(Config.redis.cache.storage_items.id)

                    await admin_storage_content.load_cache_data(
                        target = Config.redis.cache.storage_items.target,
                        cache_id = Config.redis.cache.storage_items.id,
                        exp = Config.redis.cache.storage_items.exp
                    )

                admin_tenant_content = self.admin_view.get_tenants_content()
                
                if admin_tenant_content is not None:
                    
                    await admin_tenant_content.tenant_datatable_cache.clear_cache(Config.redis.cache.tenants.id)
                    
                    await admin_tenant_content.load_cache_data(
                        cache_id = Config.redis.cache.tenants.id,
                        exp = Config.redis.cache.tenants.exp,
                        update_rental_cache = False
                    )
                        
            storage_view = self.get_storage_view()
            
            if storage_view is not None:
                
                await storage_view.material_cache_service.clear_cache(Config.redis.cache.material.id)
                
                await storage_view.load_cache_data(
                    cache_id = Config.redis.cache.material.id, 
                    exp = Config.redis.cache.material.exp
                )
                
                await storage_view.tools_cache_service.clear_cache(Config.redis.cache.tools.id)
                
                await storage_view.load_cache_data(
                    cache_id = Config.redis.cache.tools.id, 
                    exp = Config.redis.cache.tools.exp
                )
                
                await storage_view.devices_cache_service.clear_cache(Config.redis.cache.devices.id)

                await storage_view.load_cache_data(
                    cache_id = Config.redis.cache.devices.id, 
                    exp = Config.redis.cache.devices.exp
                )
                
                await storage_view.returnable_cache_service.clear_cache(Config.redis.cache.returnable_packaging.id)
                
                await storage_view.load_cache_data(
                    cache_id = Config.redis.cache.returnable_packaging.id, 
                    exp = Config.redis.cache.returnable_packaging.exp
                )
                
            # if self.marine_view is not None:
                
            #     self.marine_view.marine_traffic_search_cache.clear_cache()
       
        finally:
            
            self._cache_clearing_in_progress = False
            
            if getattr(self, "_close_requested", False):
                
                self._close_requested = False
                
                self.close()
                
            self.log.info("Clearing all Redis cache -> END")   
   
    def get_marine_traffic_view(self) -> MarineTrafficSearchView:
        
        if self.marine_view is not None:
            
            return self.marine_view
        
        try:
            
            self.marine_view = MarineTrafficSearchView(self)
            
            return self.marine_view
        
        except Exception as e:
            
            self.log.exception("Failed to create MarineTrafficSearchView: %s" % str(e))
           
            raise
    
    def get_storage_view(self) -> StorageView:
    
        if self.storage_view is not None:
            
            return self.storage_view
        
        try:
            
            self.storage_view = StorageView(self)
            
            return self.storage_view
        
        except Exception as e:
            
            self.log.exception("Failed to create StorageView: %s" % str(e))
           
            raise
    
    def get_todo_view(self) -> TodoView:
        
        if self.todo_view is not None:
            
            return self.todo_view
        
        try:
            
            self.todo_view = TodoView(self)
            
            return self.todo_view
        
        except Exception as e:
            
            self.log.exception("Failed to create TodoView: %s" % str(e))
           
            raise
    
    def get_admin_view(self) -> AdminView:
        
        if self.admin_view is not None:
            
            return self.admin_view
        
        try:
            
            self.admin_view = AdminView(self)
            self.admin_view.refresh_todo.connect(self.refresh_todo_view_table)
            self.admin_view.refresh_other_work_prices.connect(lambda: asyncio.ensure_future(self.__select_other_work_prices()))
            self.admin_view.refresh_other_work_prices_hun.connect(lambda: asyncio.ensure_future(self.__select_other_work_prices_hun()))
            
            return self.admin_view
        
        except Exception as e:
            
            self.log.exception("Failed to create AdminView: %s" % str(e))
           
            raise
        
    def __update_datetime(self):
        
        napok = ["Hétfő", "Kedd", "Szerda", "Csütörtök", "Péntek", "Szombat", "Vasárnap"]

        current_date = QDate.currentDate()
        
        current_date_str = current_date.toString("yyyy.MM.dd")

        nap_index = current_date.dayOfWeek() - 1
        
        nap_nev = napok[nap_index]

        current_time = QTime.currentTime().toString("HH:mm:ss")

        self.datetime_label.setText(f"{nap_nev} {current_date_str}     {current_time}")            