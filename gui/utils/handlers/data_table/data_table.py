import logging
import base64
import typing as t

from utils.logger import LoggerMixin
from config import Config

class DataTableHelper(LoggerMixin):
    
    log: logging.Logger
    
    @classmethod
    def getAttribute(cls, obj, attr: str, default = "N/A") -> t.Any:
        
        value = getattr(obj, attr, None)

        if value is None:
            
            return default
    
        if isinstance(value, str) and not value.strip():
            
            return default
        
        return value
    
    @classmethod
    def getAttributeDate(cls, obj, attr: str, default = "N/A") -> str:
    
        value = getattr(obj, attr, None)
        
        if value is not None:
            
            return value.strftime(Config.time.timeformat)
        
        else:
            
            return default