from playwright.async_api import async_playwright, Playwright
import typing as t
import logging
import asyncio

from utils.logger import LoggerMixin

if t.TYPE_CHECKING:
    
    from async_loop import QtApplication

class PlayWrightContextManager(LoggerMixin):
    
    log: logging.Logger
    
    def __init__(self,
        app: 'QtApplication'
        ):
        
        self.app = app
        
        self._manager = None
        
        self._playwright: Playwright | None = None
        
        self._playwright_task: asyncio.Task | None = None 
        
    async def __aenter__(self):

        if self._playwright is not None:
            
            return self._playwright

        self._manager = async_playwright()
        
        self._playwright = await self._manager.__aenter__()
        
        self._playwright_task = self.app.loop.create_task(self.playwright_session())
        
        self.app._bg_tasks.append(self._playwright_task)
        
        return self._playwright
    
    async def playwright_session(self):
        
        try:
            
            await asyncio.Event().wait()
            
        except asyncio.CancelledError:
            
            pass
    
    async def start(self) -> Playwright:
        
        self.log.info("Async Playwright context manager -> START")
        
        return await self.__aenter__()

    async def stop(self):

        async with self.app.playwright_lock:
            
            if self._playwright is not None:
            
                try:
            
                    await self._manager._connection.stop_async()
                    
                except AttributeError:
        
                    await self._playwright.__aexit__(None, None, None)
                    
                except Exception as e:
                    
                    self.log.exception("Error while stopping Playwright: %s" % str(e))
                    
                finally:
                    
                    self.log.info("Async Playwright context manager -> STOP")
                    
                    self._playwright = None
                    
                    if self._playwright_task is not None:
                        
                        self._playwright_task.cancel()
                        
                        try:
                            
                            await self._playwright_task
                            
                        except asyncio.CancelledError:
                            
                            pass
                        
                        self._playwright_task = None