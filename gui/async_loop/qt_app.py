import sys
import logging
import asyncio
import inspect
import signal
import multiprocessing
import typing as t
from openai import AsyncOpenAI
from qasync import QEventLoop
from PyQt6.QtWidgets import QApplication
from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import QCoreApplication
from jinja2 import Environment, FileSystemLoader, Template
from mnb import Mnb
from pathlib import Path

from utils.logger import LoggerMixin
from view.google_auth import GmailLoginWindow
from utils.handlers.event.calendar_notifier import CalendarNotifier
from utils.handlers.event.rental_end import RentalEnd
from db.db import MySQLDatabase
from utils.handlers.data_table import DataTableHelper
from db.async_redis import AsyncRedisClient
from services.backgound_tasks.reminders_checking import ReminderWorker
from services.backgound_tasks.rentals_checking import RentalWorker
from utils.dc.running_tasks import RunningTasks
from utils.handlers.math import UtilityCalculator
from services.qthread_manager import QthreadManager
from utils.handlers.spinner import Spinner
from websocket.ws_client import QtApplicationSocketClient
from services.backgound_tasks.otp_zip_worker import OTPZipWorker
from services.backgound_tasks.playwright_context_manager import PlayWrightContextManager
from config import Config

Callback = t.Callable[["QtApplication"], t.Awaitable[None] | None]

class QtApplication(LoggerMixin):
    
    log: logging.Logger

    def __init__(self, 
        app: QApplication | None = None
        ) -> None:

        self.templates: t.Dict[str, Template] = {}
        
        self.app = app
        
        self.playwright_manager = PlayWrightContextManager(self)
        
        self.mnb_client = Mnb()
        
        self.utility_calculator = UtilityCalculator(self)
        
        self.websocket_enabled = Config.websocket.is_enabled
        
        self.datatable_helper = DataTableHelper()
        
        self.spinner = Spinner(Config.gif.spinner)
        
        self._qt_threads = []
        
        self.qthread_manager = QthreadManager(app_ref = self)
        
        self.qthread_manager.start()
        
        self._shutdown_complete = asyncio.Event()
        
        self.storage_lock = asyncio.Lock()
        self.admin_storage_lock = asyncio.Lock()
        self.fleet_lock = asyncio.Lock()
        self.reminder_lock = asyncio.Lock()
        self.rental_lock = asyncio.Lock()
        self.schedule_lock = asyncio.Lock()
        self.marine_traffic_lock = asyncio.Lock()
        
        self.playwright_lock = asyncio.Lock()
        
        self.google_lock = asyncio.Lock()
        
        self.openapi_lock = asyncio.Lock()

        self._setup_root_logger()
        
        self.notifier = CalendarNotifier()
        
        self.rental_end = RentalEnd()
        
        self.db = MySQLDatabase(
            encoding = "utf8",
            auto_create_db = True,
            auto_create_tables = True,
            auto_add_new_columns = True,
            general_log = False,
            query_timer = True,
            session = True,
            sql_type = "mysql",
            mysql_engine = "InnoDB",
            mysql_charset = "latin2",
            check_column_parameters = True
        )
        
        self.redis_client = AsyncRedisClient()
        
        self.otp_zip_worker: OTPZipWorker | None = None
        
        self.websocket_client: QtApplicationSocketClient = None
    
        self.openai = AsyncOpenAI(api_key = Config.openapi.key)
        
        self.is_dev_mode = False if getattr(sys, "frozen", False) else True
        
        self.templates_path = Path(__file__).parent.parent / "templates" if self.is_dev_mode == True else \
            Path(sys.executable).parent / "_internal" / "gui" / "templates"
        
        if self.templates_path:
            
            self.jinja_env = Environment(loader = FileSystemLoader(self.templates_path))
            
            self.jinja_env.filters["hun_fmt"] = lambda val: "{:,.0f}".format(float(val)).replace(",", " ")
            
            for path in self.templates_path.rglob("*.html"):
                
                rel_path = path.relative_to(self.templates_path).with_suffix("").as_posix()
                
                self.templates[rel_path] = self.jinja_env.get_template(path.relative_to(self.templates_path).as_posix())
                
                self.log.debug("Set template key: '%s' in templates for: %s " % (
                    str(rel_path),
                    str(path)
                    )
                )

        # Qt + asyncio event‑loop bridge
        self.loop = QEventLoop(self.app)
        asyncio.set_event_loop(self.loop)
        self.loop.set_exception_handler(self._handle_loop_exception)
        
        # Lifecycle callback collections
        self._before_startup: t.List[Callback] = []
        self._after_startup: t.List[Callback] = []
        self._before_shutdown: t.List[Callback] = []
        self._after_shutdown: t.List[Callback] = []
        
        # Background tasks tracked for graceful exit
        self._bg_tasks: t.List[asyncio.Task[None]] = []

        # Main window placeholder
        self.main_window: t.Optional[QWidget] = None

        self._about_to_quit_handled = False

        # Bind graceful‑shutdown handler
        self.app.aboutToQuit.connect(self.__on_about_to_quit) # type: ignore[arg-type]

        signal.signal(signal.SIGINT, lambda *_: QCoreApplication.quit())
            
    def _handle_loop_exception(self, loop: asyncio.AbstractEventLoop, context: dict) -> None:
        
        try:
            
            self.log.warning("Loop exception handler invoked with context: %s", context)
            
            exc = context.get("exception")
            
            if exc and isinstance(exc, (ConnectionResetError, OSError)) and getattr(exc, "winerror", None) == 995:
                
                self.log.debug("Suppressed WinError 995 during shutdown (source: %s)", context.get("future") or "unknown")
                
                return

            loop.default_exception_handler(context)
            
        except Exception as e:
            
            self.log.exception("Exception in custom loop handler: %s" % str(e))
        
    def register_before_startup(self, cb: Callback) -> None: self._before_startup.append(cb)
    def register_after_startup(self, cb: Callback) -> None: self._after_startup.append(cb)
    def register_before_shutdown(self, cb: Callback) -> None: self._before_shutdown.append(cb)
    def register_after_shutdown(self, cb: Callback) -> None: self._after_shutdown.append(cb)

    def add_background_task(self,
        coro_or_fn: t.Union[
            t.Callable[[], t.Coroutine[object, object, None]],
            t.Coroutine[object, object, None]
        ]) -> asyncio.Task:
        """
        Accepts:
          - a coroutine function to be called later 
            (e.g. self.add_background_task(self.websocket_client.setup_websocket))
          - an already invoked coroutine object 
            (e.g. self.add_background_task(self.websocket_client.setup_websocket(...)))
        """
        
        if inspect.iscoroutine(coro_or_fn):
            
            coro = coro_or_fn
            
        elif callable(coro_or_fn):
            
            coro = coro_or_fn()
            
        else:
            
            raise TypeError("Expected coroutine or async function")

        task = self.loop.create_task(coro)
        
        self._bg_tasks.append(task)
        
        return task

    async def _run_callbacks(self, callbacks: t.List[Callback]) -> None:
       
        for cb in callbacks:
            
            try:
                
                result = cb(self)  # type: ignore[arg-type]
                
                if inspect.isawaitable(result):
                    
                    await result
                    
            except Exception as e: 
                
                self.log.exception("Lifecycle callback '%s' failed with exception: %s" % (cb.__qualname__, e))
    
    async def _startup(self) -> None:
        
        try:
            
            self.log.debug("Running before-startup callbacks (%d)", len(self._before_startup))
            
            await self._run_callbacks(self._before_startup)
            
            if self.redis_client is not None and await self.redis_client.is_ready():
                
                if self.utility_calculator is not None:
                    
                    self.rental_worker = RentalWorker(
                        redis_client = self.redis_client,
                        rental_lock = self.rental_lock,
                        utility_calculator = self.utility_calculator
                    )
                    
                    self.reminder_worker = ReminderWorker(
                        redis_client = self.redis_client,
                        reminder_lock = self.reminder_lock,
                        utility_calculator = self.utility_calculator
                    )
                    
                    self.reminder_worker.warning_signal.connect(self.notifier.reminder_warning.emit)

                    self.rental_worker.rental_end_emit.connect(self.rental_end.rental_end_event.emit)

                    self.add_background_task(self.reminder_worker._run_loop)
                    
                    self.add_background_task(self.rental_worker._run_loop)

                    if self.websocket_enabled == True:
                    
                        self.websocket_client = QtApplicationSocketClient(
                            app = self,
                            namespace = Config.websocket.namespace
                        )
                        
                        self.add_background_task(self.websocket_client.setup_websocket(
                            host = Config.websocket.host,
                            port =  Config.websocket.port,
                            auth_token = Config.websocket.auth_token,
                            sshtunnel_host = Config.websocket.ssh.host if self.is_dev_mode == False else None,
                            sshtunnel_port = Config.websocket.ssh.port if self.is_dev_mode == False else None,
                            sshtunnel_user = Config.websocket.ssh.user if self.is_dev_mode == False else None,
                            sshtunnel_pass = Config.websocket.ssh.passwd if self.is_dev_mode == False else None,
                            sshtunnel_private_key_path = Config.websocket.ssh.privateKeyPath if self.is_dev_mode == False else None
                            )
                        )

                        self.redis_client.websocket_client = self.websocket_client
                        
            else:
                
                self.log.warning("Skipping reminders: Redis client is not initialized")
            
            self.login_window = GmailLoginWindow(self)
            
            self.login_window.show()

            self.log.info("Login window opened")
            
            self.log.debug("Running after-startup callbacks (%d)", len(self._after_startup))
            
            await self._run_callbacks(self._after_startup)

        except Exception as e:

            self.log.exception("Startup failed: %s" % (str(e)))

            await self._shutdown()
        
    async def _shutdown(self) -> None:
        
        try:
            
            self.log.debug("Running before-shutdown callbacks (%d)" % (len(self._before_shutdown)))
            
            await self._run_callbacks(self._before_shutdown)
            
            running_tasks = RunningTasks()
            
            self.log.info("="*80)
            self.log.info("Gathering running asyncio tasks, Python threads, Qt threads, background tasks")
            self.log.info("="*80)
            
            await running_tasks.collect(
                loop = self.loop,
                log = self.log,
                qt_threads = self._qt_threads,
                bg_tasks = self._bg_tasks,
            )
            
            await running_tasks.shutdown(
                log = self.log,
                reminder_worker = getattr(self, 'reminder_worker', None),
                rental_worker = getattr(self, 'rental_worker', None),
                otp_zip_worker = getattr(self, 'otp_zip_worker', None),
                redis_client = getattr(self, "redis_client", None),
                playwright_manager = getattr(self, "playwright_manager", None),
                websocket_client = getattr(self, "websocket_client", None),
                db = getattr(self, "db", None),
                loop = getattr(self, "loop", None)
            )
            
            self.log.debug("Running after-shutdown callbacks (%d)" % (len(self._after_shutdown)))
            
            await self._run_callbacks(self._after_shutdown)
            
        except Exception as e:
            
            self.log.exception("Shutdown failed: %s" % str(e))
            
        finally:
            
            self.log.warning("Exit")
            
            self.log.warning("%s exit" % multiprocessing.current_process().name)
            
            await self._flush_logs()
            
            self._shutdown_complete.set()
            
            if self.loop.is_closed() is False:
                
                self.loop.stop()
            
    async def _flush_logs(self):

        for handler in logging.getLogger().handlers:
            
            try:
                
                handler.flush()
                
            except Exception:
                pass
            
    def __on_about_to_quit(self) -> None:
        
        if self._about_to_quit_handled:
            
            return
        
        self._about_to_quit_handled = True

        if not any(t for t in asyncio.all_tasks(self.loop) if t.get_coro().__name__ == "_shutdown"):
            
            self.loop.create_task(self._shutdown())
                
    def run(self) -> None:
        
        with self.loop:
            
            try:
                
                self.loop.create_task(self._startup())
                
                self.loop.run_forever()
                
            except KeyboardInterrupt:
                
                self.log.info("Received Ctrl+C, shutting down...")
                
            except Exception as e:
                
                self.log.exception("Unexpected error in main loop: %s" % str(e))
                
            finally:
                
                self.loop.run_until_complete(self._shutdown_complete.wait())

                if self.loop.is_closed() is False:
                    
                    self.loop.close()