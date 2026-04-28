import typing as t
import logging
import asyncio

from PyQt6.QtCore import QObject, pyqtSignal

from utils.logger import LoggerMixin
from db.async_redis.async_redis import AsyncRedisClient

if t.TYPE_CHECKING:
    from routes.api.google import UserClientView

class EmailLLMIngestionWorker(QObject, LoggerMixin):
    
    log: logging.Logger
    
    finished = pyqtSignal()
    
    def __init__(self,
        user_client: 'UserClientView',
        redis_client: AsyncRedisClient
        ):
        
        super().__init__()
        
        self.__running = True
        
    @property
    def _running(self) -> bool:
        return self.__running is True
    
    @_running.setter
    def _running(self, value: bool):
        self.__running = value

    def stop(self):
        
        self._running = False
        
        self._wake_event.set()
        
        if self._task and self._task.done() == False:
            
            self._task.cancel()
            
    async def _run_loop(self):
        
        self._task = asyncio.current_task()
        
        self.log.info("EmailLLMIngestionWorker -> Start")
        
        try:
            
            while self._running == True:
                
                await asyncio.sleep(1)
                print("EmailLLMIngestionWorker is running...")

        except asyncio.CancelledError:
            raise
        
        finally:
            
            self.finished.emit()