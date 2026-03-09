from PyQt6.QtCore import QObject, pyqtSignal, QTimer
from datetime import datetime, timedelta
import asyncio
import traceback
import logging

from config import Config
from utils.logger import LoggerMixin
from utils.dc.admin.reminder import CalendarData, CalendarCacheData
from services.admin.calendar_reminder_cache import CalendarReminderCacheService
from db.async_redis import AsyncRedisClient
from utils.handlers.math import UtilityCalculator
from config import Config

class ReminderWorker(QObject, LoggerMixin):
    
    log: logging.Logger
    
    warning_signal = pyqtSignal(object)
    
    finished = pyqtSignal()

    def __init__(self, 
        redis_client: AsyncRedisClient, 
        app_lock: asyncio.Lock,
        utility_calculator: UtilityCalculator,
        interval_ms = 5000
        ):
        
        super().__init__()
        
        self._task: asyncio.Task | None = None
        
        self._next_wakeup_time: datetime | None = None
        
        self.utility_calculator = utility_calculator
        
        self._cache_needs_refresh = True 
        
        self._running = True
        
        self.interval = interval_ms / 1000
        
        self.reminder_cache = CalendarReminderCacheService(redis_client)
    
        self._lock = app_lock
        
        self.calendar_cache_data = None
    
    @property
    def cache_needs_refresh(self) -> bool:
        
        return self._cache_needs_refresh is True
    
    def _emit_reminder_safe(self, item: CalendarData):
      
        QTimer.singleShot(0, lambda: self.warning_signal.emit(item))
    
    def stop(self):
        
        self._running = False
        
        if self._task and not self._task.done():
            
            self._task.cancel()

    def notify_cache_update_needed(self, cache_data):

        self._cache_needs_refresh = True
        
        self.calendar_cache_data = cache_data

    async def _run_loop(self):
        
        self.log.info("ReminderWorker -> START")
        
        try:
            
            while self._running:
                
                now = datetime.now(Config.time.timezone_utc)
                
                if self.cache_needs_refresh or (self._next_wakeup_time and now >= self._next_wakeup_time):
                    
                    try:
                        
                        async with self._lock:
                            
                            if self.calendar_cache_data is None:
                                
                                self.calendar_cache_data = await self.reminder_cache.get_reminders_from_cache(
                                    calendar_cache_id = f"{now.year}-{str(now.month).zfill(2)}",
                                    exp = Config.redis.cache.reminders.exp
                                )
                        
                        next_reminder_time = None
                        
                        if isinstance(self.calendar_cache_data, CalendarCacheData) and self.calendar_cache_data.items \
                            and all(isinstance(item, CalendarData) for item in self.calendar_cache_data.items):
                            
                            for item in self.calendar_cache_data.items:
                                
                                reminder_date = self.utility_calculator.parse_datetime_safe(item.date)
                                
                                if now >= reminder_date:
                                    
                                    self._emit_reminder_safe(item)
                                    
                                    break
                                    
                                else:
                                    
                                    if next_reminder_time is None or reminder_date < next_reminder_time:
                                        
                                        next_reminder_time = reminder_date

                        self._next_wakeup_time = next_reminder_time
                        
                        self._cache_needs_refresh = False
                        
                    except Exception as e:
                        
                        self.log.error("Reminder cache fetch failed: %s\n%s", str(e), traceback.format_exc())
                        
                        self._next_wakeup_time = now + timedelta(seconds = 30)

                await asyncio.sleep(1)

        except asyncio.CancelledError:
            
            self.log.debug("Reminder loop cancelled gracefully")
            raise
        
        finally:
            
            self.log.info("ReminderWorker -> STOP")
            
            self.finished.emit()