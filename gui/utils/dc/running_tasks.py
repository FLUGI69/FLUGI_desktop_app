import logging
from dataclass import DataclassBaseModel
import typing as t
import asyncio
import threading

from services.backgound_tasks.reminders_checking import ReminderWorker
from services.backgound_tasks.rentals_checking import RentalWorker
from services.backgound_tasks.otp_zip_worker import OTPZipWorker
from services.backgound_tasks.email import EmailLLMIngestionWorker
from db.async_redis import AsyncRedisClient
from db.db import MySQLDatabase
from websocket.redis_event_brodcaster import QtRedisEventBroadcaster 
from websocket.gmail_push_notification import QtGmailPushNotification
from services.backgound_tasks.playwright_context_manager.playwright_context_manager import PlayWrightContextManager

class RunningTasks(DataclassBaseModel):
    
    asyncio_tasks: t.Optional[t.List[asyncio.Task]] = None
    
    python_threads: t.Optional[t.List[threading.Thread]] = None
    
    qt_threads: t.Optional[t.List[object]] = None
    
    background_tasks: t.Optional[t.List[asyncio.Task]] = None

    async def collect(
        self,
        loop: asyncio.AbstractEventLoop,
        log: t.Any,
        qt_threads: t.Optional[t.List[object]] = None,
        bg_tasks: t.Optional[t.List[asyncio.Task]] = None,
        ) -> None:
        
        current_task = asyncio.current_task()
        
        self.asyncio_tasks = [t for t in asyncio.all_tasks(loop = loop) if t is not current_task]

        self.python_threads = threading.enumerate()

        if qt_threads is None:

            self.qt_threads = []

        elif not isinstance(qt_threads, list):

            raise TypeError("qt_threads must be a list or None")

        else:

            self.qt_threads = qt_threads

        if bg_tasks is None:
        
            self.background_tasks = []
        
        elif not isinstance(bg_tasks, list):
        
            raise TypeError("background_tasks must be a list or None")
        
        else:
        
            self.background_tasks = bg_tasks

        log.debug("Asyncio tasks running (%s):" % (len(self.asyncio_tasks),))
        
        for i, task in enumerate(self.asyncio_tasks, start = 1):
        
            try:
        
                coro = task.get_coro()
                coro_name = getattr(coro, '__qualname__', str(coro))
        
                log.debug("  [%02d] %s (done -> %s, cancelled -> %s)" % (
                    i, 
                    coro_name, 
                    task.done(), 
                    task.cancelled()
                ))
        
            except Exception as e:
        
                log.warning("  [%02d] Failed to inspect asyncio task: %s" % (i, str(e)))

        await asyncio.sleep(0)

        log.debug("Python threads running (%s):" % (len(self.python_threads),))
        
        for i, t in enumerate(self.python_threads, start = 1):
        
            log.debug("  [%02d] name: %s ident: %s daemon: %s alive: %s" % (
                i,
                t.name, 
                t.ident, 
                t.daemon, 
                t.is_alive()
            ))

        await asyncio.sleep(0)

        log.debug("Qt QThreads running (%s):" % (len(self.qt_threads),))
        
        for i, t in enumerate(self.qt_threads, start = 1):
            
            try:
                
                if not (hasattr(t, 'objectName') and callable(t.objectName)):
                    
                    raise RuntimeError("QThread object missing 'objectName()' method")
                
                if not (hasattr(t, 'isRunning') and callable(t.isRunning)):
                
                    raise RuntimeError("QThread object missing 'isRunning()' method")
                
                if not (hasattr(t, 'isFinished') and callable(t.isFinished)):
                
                    raise RuntimeError("QThread object missing 'isFinished()' method")

                log.debug("  [%02d] objectName: %s isRunning: %s isFinished: %s" % (
                    i, 
                    t.objectName(), 
                    t.isRunning(), 
                    t.isFinished()
                ))
                
            except Exception as e:
               
                log.warning("Could not inspect QThread #%d: %s" % (i, str(e)))

        await asyncio.sleep(0)
       
        log.debug("Tracked background tasks (%s):" % (len(self.background_tasks),))
        
        for i, task in enumerate(self.background_tasks, start = 1):
            
            try:
                
                coro = task.get_coro()
                coro_name = getattr(coro, '__qualname__', str(coro))
                
                log.debug("  [%02d] %s (done -> %s, cancelled -> %s)" % (
                    i, 
                    coro_name, 
                    task.done(), 
                    task.cancelled()
                ))
            
            except Exception as e:
                
                log.warning("  [%02d] Failed to inspect background task: %s" % (i, str(e)))

        await asyncio.sleep(0)

    async def shutdown(
        self,
        log: logging.Logger,
        reminder_worker: t.Optional[ReminderWorker] = None,
        rental_worker: t.Optional[RentalWorker] = None,
        otp_zip_worker: t.Optional[OTPZipWorker] = None,
        email_ingestion_worker: t.Optional[EmailLLMIngestionWorker] = None,
        gmail_push_notification: t.Optional[QtGmailPushNotification] = None,
        redis_client: t.Optional[AsyncRedisClient] = None,
        playwright_manager: t.Optional[PlayWrightContextManager] = None,
        redis_event_broadcaster: t.Optional[QtRedisEventBroadcaster] = None,
        db: t.Optional[MySQLDatabase] = None,
        loop: asyncio.AbstractEventLoop = None,
        qt_threads: t.Optional[t.List[object]] = None,
        ) -> None:
        
        try:
            
            log.info("="*80)
            log.info("Initiating graceful shutdown of all running tasks and resources -> Start")
            log.info("="*80)
            
            if loop is None:
             
                raise RuntimeError("Event loop is required for shutdown")

            if reminder_worker is not None:
               
                if not hasattr(reminder_worker, 'stop') or not callable(reminder_worker.stop):
                  
                    raise RuntimeError("reminder_worker must have a callable 'stop()' method")
               
                reminder_worker.stop()
              
                if not hasattr(reminder_worker, "_task"):
                  
                    raise RuntimeError("reminder_worker missing '_task' attribute")
                
                task = reminder_worker._task
               
                if task is not None:
                    
                    try:
                   
                        await task
                  
                    except asyncio.CancelledError:
                     
                        log.debug("Reminder worker task cancelled")
                   
                    except Exception as e:   
              
                        log.exception("Exception while waiting reminder worker task: %s" % str(e))
                        
            if rental_worker is not None:
                
                if not hasattr(rental_worker, 'stop') or not callable(rental_worker.stop):
                  
                    raise RuntimeError("rental_worker must have a callable 'stop()' method")
               
                rental_worker.stop()
              
                if not hasattr(rental_worker, "_task"):
                  
                    raise RuntimeError("rental_worker missing '_task' attribute")
                
                task = rental_worker._task
               
                if task is not None:
                    
                    try:
                   
                        await task
                  
                    except asyncio.CancelledError:
                     
                        log.debug("Rental worker task cancelled")
                   
                    except Exception as e:   
              
                        log.exception("Exception while waiting rental worker task: %s" % str(e))
            
            if otp_zip_worker is not None:
                
                if not hasattr(otp_zip_worker, 'stop') or not callable(otp_zip_worker.stop):
                  
                    raise RuntimeError("otp_zip_worker must have a callable 'stop()' method")
               
                otp_zip_worker.stop()
              
                if not hasattr(otp_zip_worker, "_task"):
                  
                    raise RuntimeError("otp_zip_worker missing '_task' attribute")
                
                task = otp_zip_worker._task
               
                if task is not None:
                    
                    try:
                   
                        await task
                  
                    except asyncio.CancelledError:
                        pass
                   
                    except Exception as e:   
              
                        log.exception("Exception while waiting OTP zip worker task: %s" % str(e))
                        
            if email_ingestion_worker is not None:
               
                if not hasattr(email_ingestion_worker, 'stop') or not callable(email_ingestion_worker.stop):
                  
                    raise RuntimeError("email_ingestion_worker must have a callable 'stop()' method")
               
                email_ingestion_worker.stop()
              
                if not hasattr(email_ingestion_worker, "_task"):
                  
                    raise RuntimeError("email_ingestion_worker missing '_task' attribute")
                
                task = email_ingestion_worker._task
               
                if task is not None:
                    
                    try:
                   
                        await task
                  
                    except asyncio.CancelledError:
                        pass
                   
                    except Exception as e:   
              
                        log.exception("Exception while waiting email ingestion worker task: %s" % str(e))
                        
            if gmail_push_notification is not None and hasattr(gmail_push_notification, 'ssh_tunnel'):
                
                try:
                    
                    if gmail_push_notification.sio.connected:
                        
                        await gmail_push_notification.sio.disconnect()
                        
                except Exception as e:
                    
                    log.exception("Error disconnecting websocket client: %s" % str(e))
                
                reconnect_service = gmail_push_notification.ssh_tunnel.reconnect_service if hasattr(gmail_push_notification.ssh_tunnel, 'reconnect_service') else None
                
                if reconnect_service is not None:
                   
                    if not hasattr(reconnect_service, "is_running"):
                        
                        raise RuntimeError("gmail_push_notification.ssh_tunnel.reconnect_service missing 'is_running' attribute")
                    
                    reconnect_service.is_running = False
                    
                    gmail_push_notification.ssh_tunnel.stop()
            
            if playwright_manager is not None:
                
                if not hasattr(playwright_manager, 'stop') or not callable(playwright_manager.stop):
                  
                    raise RuntimeError("playwright_manager must have a callable 'stop()' method")
                
                await playwright_manager.stop()
                
                if not hasattr(playwright_manager, "_playwright_task"):
                  
                    raise RuntimeError("playwright_manager missing '_playwright_task' attribute")
                
                task = playwright_manager._playwright_task
               
                if task is not None:
                    
                    try:
                   
                        await task
                  
                    except asyncio.CancelledError:
                     
                        log.debug("Playwright manager task cancelled")
                   
                    except Exception as e:   
              
                        log.exception("Exception while waiting playwright manager task: %s" % str(e))

            if redis_client is not None:
              
                if not hasattr(redis_client, 'client'):
                  
                    raise RuntimeError("redis_client missing 'client' attribute")
               
                if redis_client.client is not None:
                  
                    if not hasattr(redis_client, 'close') or not callable(redis_client.close):
                     
                        raise RuntimeError("redis_client must have a callable 'close()' method")
                   
                    try:
                        
                        await redis_client.close()
                   
                    except Exception as e:
                        
                        log.warning("Error while closing Redis client: %s" % str(e))

            if db is not None:
                
                if not hasattr(db, "ssh_tunnel"):
                
                    raise RuntimeError("db missing 'ssh_tunnel' attribute")
                
                if hasattr(db.ssh_tunnel, "reconnect_service"):
                    
                    reconnect_service = db.ssh_tunnel.reconnect_service
                    
                    if not hasattr(reconnect_service, "is_running"):
                        
                        raise RuntimeError("db.ssh_tunnel.reconnect_service missing 'is_running' attribute")
                    
                    reconnect_service.is_running = False
                    
                    db.ssh_tunnel.stop()
                
            if redis_client is not None and hasattr(redis_client, 'ssh_tunnel'):
                
                reconnect_service = redis_client.ssh_tunnel.reconnect_service if hasattr(redis_client.ssh_tunnel, 'reconnect_service') else None
                
                if reconnect_service is not None:
                   
                    if not hasattr(reconnect_service, "is_running"):
                        
                        raise RuntimeError("redis_client.ssh_tunnel.reconnect_service missing 'is_running' attribute")
                    
                    reconnect_service.is_running = False
                    
                    redis_client.ssh_tunnel.stop()

            if redis_event_broadcaster is not None and hasattr(redis_event_broadcaster, 'ssh_tunnel'):
                
                try:
                    
                    if redis_event_broadcaster.sio.connected:
                        
                        await redis_event_broadcaster.sio.disconnect()
                        
                except Exception as e:
                    
                    log.exception("Error disconnecting websocket client: %s" % str(e))
                
                reconnect_service = redis_event_broadcaster.ssh_tunnel.reconnect_service if hasattr(redis_event_broadcaster.ssh_tunnel, 'reconnect_service') else None
                
                if reconnect_service is not None:
                   
                    if not hasattr(reconnect_service, "is_running"):
                        
                        raise RuntimeError("redis_event_broadcaster.ssh_tunnel.reconnect_service missing 'is_running' attribute")
                    
                    reconnect_service.is_running = False
                    
                    redis_event_broadcaster.ssh_tunnel.stop()
            
            if self.background_tasks is None:
              
                bg_tasks = []
            
            else:
                
                bg_tasks = self.background_tasks

            other_tasks = [t for t in bg_tasks]
          
            for i, task in enumerate(other_tasks, start = 1):
               
                try:
              
                    coro = task.get_coro()
                    coro_name = getattr(coro, '__qualname__', str(coro))
              
                except Exception:
                
                    coro_name = str(task)
               
                log.debug("  Cancelling background task [%02d]: %s" % (i, coro_name))
                
                task.cancel()
                
                await asyncio.sleep(0)
           
            await asyncio.gather(*other_tasks, return_exceptions = True)
         
            await loop.shutdown_asyncgens()
            
            await loop.shutdown_default_executor()
    
            await self.collect(loop, log, qt_threads = qt_threads, bg_tasks = self.background_tasks)

            log.info("="*80)
            log.info("Initiating graceful shutdown of all running tasks and resources -> COMPLETE")
            log.info("="*80)

        except Exception as e:
            
            log.exception("Exception during shutdown of running tasks: %s" % str(e))
