import os
from datetime import datetime
import sys
import logging
import colorlog
import builtins
import traceback
import re
from pathlib import Path
import typing as t

from config import Config

class classproperty:
    
    def __init__(self, fget):
        
        self.fget = fget
        
    def __get__(self, instance, owner):
        
        return self.fget(owner)

class LoggerMixin:
    
    if t.TYPE_CHECKING:
        
        log: logging.Logger 
    
    _print_level = getattr(Config.log, "print_level", 15)
    
    _root_configured: bool = False
    
    _logger: t.Optional[logging.Logger] = None
    
    _traceback_buffer = []
    
    _collecting_traceback = False
    
    _startup_time = datetime.now(Config.time.timezone_utc)

    @property
    def log(self) -> logging.Logger:
        
        if self._logger is None:
            
            self._setup_root_logger()
            
            self._logger = logging.getLogger(self.__class__.__name__)
            
        return t.cast(logging.Logger, self._logger)

    @classproperty
    def log(cls) -> logging.Logger:
        
        if cls._logger is None:
            
            cls._setup_root_logger()
            
            cls._logger = logging.getLogger(cls.__name__)
            
        return t.cast(logging.Logger, cls._logger)

    @classmethod
    def _print_log(cls, self, message, *args, **kwargs):
        
        if self.isEnabledFor(cls._print_level):
            
            self._log(cls._print_level, message, args, **kwargs)
    
    @classmethod
    def _setup_root_logger(cls) -> None:
        
        if cls._root_configured:
            
            return

        logging.addLevelName(cls._print_level, "PRINT")

        logging.Logger.print = lambda self, message, *a, **kw: cls._print_log(self, message, *a, **kw)

        handlers = []

        console_handler = logging.StreamHandler()
        console_formatter = colorlog.ColoredFormatter(
            "%(log_color)s%(asctime)s [%(levelname)s] %(name)s - %(message)s",
            datefmt = "%Y-%m-%d %H:%M:%S",
            log_colors = {
                'DEBUG': 'light_blue',
                'INFO': '',
                'WARNING': 'yellow',
                'ERROR': 'red',
                'CRITICAL': 'bold_red',
                'PRINT': 'cyan'
            }
        )
    
        console_handler.setFormatter(console_formatter)
        handlers.append(console_handler)

        if getattr(sys, 'frozen', False):
            
            base_dir = Path(sys.executable).parent / "log"

        else:
            
            base_dir = Config.log.path

        now = cls._startup_time
        year = str(now.year)
        month = f"{now.month:02}"

        log_dir = os.path.join(base_dir, year, month)
        
        os.makedirs(log_dir, exist_ok = True)
        
        log_filename = f"{now:%Y-%m-%d-%H_%M_%S}-{Config.log.file_name}"
        log_path = os.path.join(log_dir, log_filename)

        file_handler = logging.FileHandler(
            log_path,
            encoding = Config.log.filehandler.encoding
        )
        
        file_handler.setFormatter(logging.Formatter(Config.log.fmt))
        handlers.append(file_handler)

        logging.basicConfig(
            level = getattr(logging, Config.log.level, logging.INFO),
            handlers = handlers,
            force = True,
        )

        sqla_engine_logger = logging.getLogger("sqlalchemy.engine.Engine")
        sqla_engine_logger.handlers.clear() 
        sqla_engine_logger.propagate = False 
        sqla_engine_logger.setLevel(logging.ERROR)
        logging.getLogger("qasync._windows._EventWorker").setLevel(logging.WARNING)
        logging.getLogger("qasync._windows._EventPoller").setLevel(logging.WARNING)
        logging.getLogger("qasync.QThreadExecutor").setLevel(logging.WARNING)
        logging.getLogger("qasync._QEventLoop").setLevel(logging.WARNING)
        logging.getLogger("googleapiclient.discovery").setLevel(logging.WARNING)
        logging.getLogger("httpcore.http11").setLevel(logging.WARNING)
        logging.getLogger("httpcore.connection").setLevel(logging.WARNING)
        logging.getLogger("openai._base_client").setLevel(logging.WARNING)
        logging.getLogger("asyncio").setLevel(logging.WARNING)
        logging.getLogger("paramiko").setLevel(logging.WARNING) 
        logging.getLogger("qasync._QThreadWorker").setLevel(logging.ERROR)
        logging.getLogger("fontTools").setLevel(logging.ERROR)
        logging.getLogger("fontTools.ttLib.ttFont").setLevel(logging.ERROR)
        logging.getLogger("fontTools.subset").setLevel(logging.ERROR)
        logging.getLogger("zeep.xsd.schema").setLevel(logging.ERROR)
        logging.getLogger("zeep.transports").setLevel(logging.ERROR)
        logging.getLogger("urllib3.connectionpool").setLevel(logging.ERROR)
        logging.getLogger("zeep.wsdl.wsdl").setLevel(logging.ERROR)
        logging.getLogger("PIL.PngImagePlugin").setLevel(logging.ERROR)
        
        cls._root_configured = True

def print_override(*args, **kwargs):
    
    LoggerMixin._setup_root_logger()
    
    msg = " ".join(str(arg) for arg in args)
    
    logger = logging.getLogger("AppLogger")

    if "WinError 995" in msg or "[WinError 995]" in msg:
        return

    if msg.startswith("Traceback (most recent call last):"):
        
        LoggerMixin._traceback_buffer = [msg]
        LoggerMixin._collecting_traceback = True
        
        return

    if "During handling of the above exception" in msg:
        
        if LoggerMixin._collecting_traceback is False:
            
            LoggerMixin._traceback_buffer = [msg]
            LoggerMixin._collecting_traceback = True
            
        else:
            
            LoggerMixin._traceback_buffer.append(msg)
            
        return

    if LoggerMixin._collecting_traceback:
        
        LoggerMixin._traceback_buffer.append(msg)
        
        if msg.strip() == "" or re.match(r"^\w*Error: ", msg) or re.match(r"^\w*Exception: ", msg) or "ValidationError" in msg:
            
            full_trace = "\n".join(LoggerMixin._traceback_buffer)
            logger.error(full_trace)
            
            LoggerMixin._traceback_buffer.clear()
            LoggerMixin._collecting_traceback = False
        
        return
    
    logger.print(msg)

def excepthook(type_, value, tb):
    
    LoggerMixin._setup_root_logger()
    
    logger = logging.getLogger("AppLogger")
    
    trace = "".join(traceback.format_exception(type_, value, tb))
    
    if "WinError 995" in trace or "[WinError 995]" in trace:
        
        return
    
    logger.error(trace)

builtins.print = print_override
sys.excepthook = excepthook
