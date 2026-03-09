from PyQt6.QtCore import QThread, QObject
import typing as t
import logging

from utils.logger import LoggerMixin

class QthreadManager(QThread, LoggerMixin):
    
    log: logging.Logger

    def __init__(self, 
        app_ref: QObject | None = None,
        *args, 
        **kwargs
        ):
        
        super().__init__(*args, **kwargs)
        
        self._app_ref = app_ref
        
        self._auto_register()

    def _auto_register(self):
        
        registrar = self._search_qt_thread_holder(self._app_ref)

        if registrar:
            
            registrar._qt_threads.append(self)
            
            self.log.debug("Registered in: %s" % repr(registrar))
            
        else:
            
            self.log.warning("Could not find any _qt_threads target in QObject tree")

    def _search_qt_thread_holder(self, obj: QObject | None) -> t.Optional[object]:
        """Recursively searches for an object with the _qt_threads attribute in the app_ref hierarchy."""
       
        if obj is None:
            
            return None

        if hasattr(obj, "_qt_threads"):
            
            return obj

        for child in obj.children():
            
            result = self._search_qt_thread_holder(child)
            
            if result:
                
                return result

        return None