from PyQt6.QtCore import QObject, pyqtSignal, QTimer
from datetime import datetime, timedelta
import asyncio
import traceback
import logging

from config import Config
from utils.logger import LoggerMixin
from utils.dc.admin.rental_history import RentalHistoryData, RentalHistoryCacheData
from services.admin.rental_history_cache import RentalHistoryCacheService
from db.async_redis import AsyncRedisClient
from utils.handlers.math import UtilityCalculator

class RentalWorker(QObject, LoggerMixin):
    
    log: logging.Logger
    
    rental_end_emit = pyqtSignal(object)
    
    finished = pyqtSignal()

    def __init__(self, 
        redis_client: AsyncRedisClient, 
        rental_lock: asyncio.Lock,
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
        
        self.rental_history_cache = RentalHistoryCacheService(
            redis_client = redis_client,
            rental_lock = rental_lock
        )
        
        self.rental_history_cache_data = None
        
        self.clear_cache = False
        
        self._wake_event = asyncio.Event()
    
    @property
    def cache_needs_refresh(self) -> bool:
        
        return self._cache_needs_refresh is True
    
    def _emit_rental_end_safe(self, item: RentalHistoryCacheData):
        
        QTimer.singleShot(0, lambda: self.rental_end_emit.emit(item))
    
    def stop(self):
        
        self._running = False
        
        if self._task and self._task.done() == False:
            
            self._task.cancel()

    def notify_cache_update_needed(self, clear_cache):
        
        if clear_cache == True:
            
            now = datetime.now(Config.time.timezone_utc)
            
            asyncio.create_task(self.rental_history_cache.clear_cache(f"{now.year}-{str(now.month).zfill(2)}"))

        self._cache_needs_refresh = True
        
        self.rental_history_cache_data = None
        
        self._wake_event.set()

    async def _run_loop(self):
        
        self.log.info("RentalWorker -> Start")
        
        try:
            
            while self._running:
                
                now = datetime.now(Config.time.timezone_utc)
                # print(now)

                if self.cache_needs_refresh or (self._next_wakeup_time and now >= self._next_wakeup_time):
                    
                    try:
 
                        if self.rental_history_cache_data is None:
                            
                            self.rental_history_cache_data = await self.rental_history_cache.get_rentals_from_cache(
                                rentals_cache_id = f"{now.year}-{str(now.month).zfill(2)}",
                                exp = Config.redis.cache.rental_history.exp
                            )
                            
                        next_rental_end_time = None
                        
                        if isinstance(self.rental_history_cache_data, RentalHistoryCacheData) and self.rental_history_cache_data.items \
                            and all(isinstance(item, RentalHistoryData) for item in self.rental_history_cache_data.items):
                            
                            for item in self.rental_history_cache_data.items:
                                
                                if item.tenant.rental_end is not None:
                                    
                                    rental_end = self.utility_calculator.parse_datetime_safe(item.tenant.rental_end)
                                
                                    if now >= rental_end:
                                        
                                        self._emit_rental_end_safe(self.rental_history_cache_data)
                                     
                                        break
                                        
                                    else:
                                        
                                        if next_rental_end_time is None or rental_end < next_rental_end_time:
                                            
                                            next_rental_end_time = rental_end

                        self._next_wakeup_time = next_rental_end_time
                        
                        self._cache_needs_refresh = False
                        
                    except Exception as e:
                        
                        self.log.error("Rental cache fetch failed: %s\n%s", str(e), traceback.format_exc())
                        
                        self._next_wakeup_time = now + timedelta(seconds = 30)

                # Smart sleep: wait until next rental end or cache invalidation
                sleep_seconds = self.interval
                
                if self._next_wakeup_time is not None:
                    
                    delta = (self._next_wakeup_time - datetime.now(Config.time.timezone_utc)).total_seconds()
                    
                    sleep_seconds = max(1, min(delta, 300))
                
                self._wake_event.clear()
                
                try:
                    
                    await asyncio.wait_for(self._wake_event.wait(), timeout = sleep_seconds)
                    
                except asyncio.TimeoutError:
                    pass

        except asyncio.CancelledError:
            raise
        
        finally:
            
            self.finished.emit()