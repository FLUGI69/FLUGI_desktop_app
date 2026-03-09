import sys
import ctypes
import atexit
import logging
import functools
from PyQt6.QtWidgets import QApplication
from async_loop.qt_app import QtApplication
import inspect

from utils.logger import LoggerMixin
from .patches import PollWrapper
from .patches import ProcessEventsWrapper
from .patches import patch_iocpproactor_poll
from config import Config

class Init(LoggerMixin):
    
    log: logging.Logger
    
    _single_instance_mutex = None
    
    def __init__(self):
        
        super().__init__()
        
        self.ensure_single_instance()  
    
    def ensure_single_instance(self):
       
        self._single_instance_mutex = ctypes.windll.kernel32.CreateMutexW(None, True, Config.mutex.name)
        
        last_error = ctypes.windll.kernel32.GetLastError()
        
        if last_error == 183:
            
            self.log.error("Application is already running! Exiting...")
            
            sys.exit(0)

        atexit.register(self.release_mutex)

    def release_mutex(self):
        
        if self._single_instance_mutex is not None and self._single_instance_mutex != 0:
            
            ctypes.windll.kernel32.ReleaseMutex(self._single_instance_mutex)
            
            self._single_instance_mutex = None
    
    def _patched_finish_socket_func(self, original, transferred, key, ov):
        
        try:
            
            return original(transferred, key, ov)
        
        except ConnectionResetError as e:
            
            if getattr(e, "winerror", None) == 995:
                
                self.log.debug("Suppressed WinError 995 in patched finish_socket_func")
                
                return None
            
            raise
        
        except OSError as e:
            
            if getattr(e, "winerror", None) == 995:
                
                self.log.debug("Suppressed WinError 995 (OSError) in patched finish_socket_func")
                
                return None
            
            raise

    def _patched_process_events(self, original_process_events, self_obj, transferred, key, ov):
        
        try:
            
            return original_process_events(self_obj, transferred, key, ov)
        
        except ConnectionResetError as e:
            
            if getattr(e, "winerror", None) == 995:
                
                self.log.debug("Suppressed WinError 995 in patched _process_events")
                
                return None
            
            raise
        
        except OSError as e:
            
            if getattr(e, "winerror", None) == 995:
                
                self.log.debug("Suppressed WinError 995 (OSError) in patched _process_events")
                
                return None
            
            raise

    def monkey_patch(self):
        
        try:
            
            import asyncio.windows_events
            
            func = getattr(asyncio.windows_events, "finish_socket_func", None)

            if func is not None:
                
                patched = functools.partial(self._patched_finish_socket_func, func)
                
                asyncio.windows_events.finish_socket_func = patched
                
                self.log.debug("Patched asyncio.windows_events.finish_socket_func")
                
            else:
                
                for alt in ("finish_recv", "finish_send", "finish_accept"):
                    
                    alt_func = getattr(asyncio.windows_events, alt, None)
                    
                    if callable(alt_func):
                        
                        setattr(asyncio.windows_events, alt, functools.partial(self._patched_finish_socket_func, alt_func))
                        
                        self.log.debug("Patched asyncio.windows_events.%s instead (fallback)" % alt)
                        
        except (ImportError, AttributeError) as e:
            
            self.log.debug("Skipped patching asyncio.windows_events socket funcs: %s" % str(e))

        try:
            
            import qasync._windows
            
            EventPoller = getattr(qasync._windows, "_EventPoller", None)

            if EventPoller is not None:
                
                if hasattr(EventPoller, "_process_events"):
                    
                    original_process_events = EventPoller._process_events
                    
                    EventPoller._process_events = ProcessEventsWrapper(self, original_process_events)
                    
                    self.log.debug("Patched _EventPoller._process_events")
                    
                elif hasattr(EventPoller, "_poll"):
                    
                    original_poll = EventPoller._poll
                    
                    EventPoller._poll = PollWrapper(original_poll, self.log)
                    
                    self.log.debug("Patched _EventPoller._poll as fallback (WinError 995)")
                    
                else:
                    
                    self.log.debug("No suitable method found to patch on _EventPoller")
                    
            else:
                
                self.log.debug("EventPoller not found in qasync._windows")
                
        except (ImportError, AttributeError) as e:
            
            self.log.debug("Skipped patching qasync._windows._EventPoller: %s" % str(e))

        try:
            
            from qasync._windows import _IocpProactor
            
            patch_iocpproactor_poll(_IocpProactor, self.log)
            
        except ImportError as e:
            
            self.log.debug("Skipped patching _IocpProactor._poll: %s" % str(e))
            
    @staticmethod
    def compare_config_modules(actual_config, example_config, log: logging.Logger):

        missing_snippets = []

        for name, example_cls in inspect.getmembers(example_config, inspect.isclass):
            
            if not hasattr(actual_config, name):
                
                attrs = [attr for attr in dir(example_cls) \
                    if not attr.startswith("__") and not inspect.isbuiltin(getattr(example_cls, attr))
                ]
                
                attrs_str = "\n    " + "\n    ".join(
                    ["%s = %s" % (a, repr(getattr(example_cls, a))) for a in attrs]
                )
                
                class_def = "\nclass %s:\n%s\n" % (name, attrs_str if attrs else "    pass")

                missing_snippets.append("'%s' class not found in config.py.\nPlease add this:%s" % (
                    name, 
                    class_def
                    )
                )
                
                continue

            actual_cls = getattr(actual_config, name)
            
            for attr in dir(example_cls):
                
                if attr.startswith("__"):
    
                    continue
                
                if not hasattr(actual_cls, attr):
                    
                    value = getattr(example_cls, attr)
                    
                    attr_line = "%s = %s" % (attr, repr(value))
                    
                    class_def = "\nclass %s:\n    %s\n" % (name, attr_line)
                    
                    missing_snippets.append("'%s' attribute missing in class '%s': \nPlease add this -> %s" % (
                        attr, 
                        name, 
                        class_def
                        )
                    )

        if missing_snippets:
            
            log.error("Config validation failed. Missing items detected:\n%s" % ("\n".join(missing_snippets)))

            sys.exit("Config validation failed")
            
    def config_reference_check(self):
        
        if not getattr(sys, 'frozen', False):
            
            from config import config as actual_config
            from config import config_example as example_config

            self.compare_config_modules(actual_config.Config, example_config.Config, self.log)
            
    @staticmethod
    def pyqt_application() -> 'QtApplication':
        
        import version
        
        from interfaces import Interfaces

        app = QApplication(sys.argv)
        
        info = version.get_version_info()

        return Interfaces.setup_app(
            info = info, 
            app = app
        )