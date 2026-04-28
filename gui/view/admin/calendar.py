from qasync import asyncSlot
from datetime import datetime
import asyncio
import typing as t
import logging

from PyQt6.QtWidgets import (
    QWidget, 
    QVBoxLayout, 
    QCalendarWidget
)
from PyQt6.QtCore import QDate, pyqtSignal, QTimer

from utils.logger import LoggerMixin
from ..modal import ReminderModal
from ..modal import ReminderDayModal
from .custom import CustomCalendar
from utils.dc.admin.reminder import CalendarData, CalendarCacheData
from services.admin.calendar_reminder_cache import CalendarReminderCacheService
from config import Config
from db import queries

if t.TYPE_CHECKING:
    
    from .admin import AdminView

class CalendarContent(QWidget, LoggerMixin):
    
    log: logging.Logger
    
    data_loaded = pyqtSignal(object)
    
    def __init__(self,
        admin: 'AdminView'
        ):
        
        super().__init__()

        self.admin = admin
        
        self.current_time = datetime.now(Config.time.timezone_utc)
        
        self.reminder_worker = admin.reminder_worker
        
        self.utility_calculator = admin.main_window.app.utility_calculator
        
        self.reminder_modal = ReminderModal()
        
        self.reminder_day_modal = ReminderDayModal()
        
        if admin.main_window.app.reminder_cache_service is None:

            self.reminders_cache = CalendarReminderCacheService(
                redis_client = admin.redis_client,
                reminder_lock = admin.main_window.app.reminder_lock
            )
            admin.main_window.app.reminder_cache_service = self.reminders_cache
            
        else:

            self.reminders_cache = admin.main_window.app.reminder_cache_service
        
        self.calendar = CustomCalendar()
        
        self._modal_future = None
 
        self.__init_view()
        
        self.data_loaded.connect(self.on_data_loaded)
        
    def __init_view(self):
        
        layout = QVBoxLayout(self)
        
        self.calendar.setGridVisible(True)
        self.calendar.setVerticalHeaderFormat(QCalendarWidget.VerticalHeaderFormat.NoVerticalHeader)
        self.calendar.setSelectedDate(QDate.currentDate())
        self.calendar.clicked.connect(self.on_date_clicked)
        
        layout.addWidget(self.calendar)

        self.setLayout(layout)
        
    def showEvent(self, event):
        
        super().showEvent(event)

        if not hasattr(self, '_cache_loading_started'):
            
            self._cache_loading_started = True
            
            asyncio.create_task(self.load_cache_data())
            
    def _emit_cache_data_safe(self, item: CalendarCacheData):
        
        QTimer.singleShot(0, lambda: self.data_loaded.emit(item))
        
    async def load_cache_data(self):
        
        self.cache_data = await self.reminders_cache.get_reminders_from_cache(
            calendar_cache_id = self._create_cache_id(),
            exp = Config.redis.cache.reminders.exp
        )

        self.reminder_worker.notify_cache_update_needed(self.cache_data)

        self._emit_cache_data_safe(self.cache_data)

    def on_data_loaded(self, cache_data: CalendarCacheData):

        self.calendar.set_marked_dates(cache_data)
        
    def _create_cache_id(self) -> str:
        
        year = str(self.current_time.year)
        month = str(self.current_time.month).zfill(2) 

        return f"{year}-{month}"
    
    @asyncSlot(QDate)
    async def on_date_clicked(self, date: QDate):
        
        if self._modal_future and not self._modal_future.done():
            
            self.log.warning("Modal is already open. Ignoring new click")
            
            return 
        
        is_exist, calendar_data_list = await self.check_modal_data_is_exist(date)
        
        if is_exist == True and len(calendar_data_list) > 0:
            
            self.reminder_day_modal.calendar_date = date
            self.reminder_day_modal.load_day_data(calendar_data_list)
            self.reminder_day_modal.utility_calculator = self.utility_calculator
            
            self._modal_future = self.reminder_day_modal.exec_async()
            
            accepted = await self._modal_future
            
            self._modal_future = None

            if accepted:
                
                calendar_data = self.reminder_day_modal.get_modal_data()
                
                if calendar_data is not None:
                    
                    await self._handle_insert_data(calendar_data)
            
        elif is_exist == False:
        
            self.reminder_modal.calendar_date = date
            
            self.reminder_modal.utility_calculator = self.utility_calculator
            
            self._modal_future = self.reminder_modal.exec_async()
            
            accepted = await self._modal_future
            
            self._modal_future = None

            if accepted:
                
                calendar_data = self.reminder_modal.get_modal_data()
                
                if calendar_data is not None:
                    
                    await self._handle_insert_data(calendar_data)
    
    async def _handle_insert_data(self, calendar_data: CalendarData):
        
        if isinstance(calendar_data, CalendarData):
          
            await queries.insert_reminder(
                note = calendar_data.note,
                reminder_date = calendar_data.date,
                used = calendar_data.used,
            )
                
            await self.reminders_cache.clear_cache(self._create_cache_id())

            await self.load_cache_data()
                       
    async def check_modal_data_is_exist(self, date: QDate) -> t.Optional[t.Tuple[bool, t.Optional[t.List[CalendarData]]]]:
        
        existing_cache = await self.reminders_cache.get_reminders_from_cache(
            calendar_cache_id = self._create_cache_id(),
            exp = Config.redis.cache.reminders.exp
        )
        
        if existing_cache is not None:
            
            if (isinstance(existing_cache, CalendarCacheData) and existing_cache.items \
                and all(isinstance(item, CalendarData) for item in existing_cache.items)
                ):

                date_py = datetime(date.year(), date.month(), date.day()).date()
                
                calendar_data_list = []
                
                for item in existing_cache.items:
                    
                    item_date_py = item.date.date()  # datetime -> date
                    
                    if date_py == item_date_py:
                        
                        calendar_data_list.append(item)
                
                if len(calendar_data_list) > 0:
                    
                    return True, calendar_data_list
                        
                return False, calendar_data_list
            
            raise TypeError("Invalid cache data: expected CalendarCacheData with CalendarData items")
        
        return False, None
        