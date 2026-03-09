import asyncio
import inspect

from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt

class ClickableWidget(QWidget):
    
    def __init__(self, parent = None, on_click = None, object_name: str | None = None,):
        
        super().__init__(parent)
        
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        
        if object_name is not None:
            
            self.setObjectName(object_name)
        
        self._on_click = on_click
        
        self._is_enabled = True
        
        self._is_processing = False 
        
    def setEnabled(self, enabled: bool):
        
        self._is_enabled = enabled
        
        super().setEnabled(enabled) 

    def mousePressEvent(self, event):
        
        if self._is_enabled is False or self._is_processing is True:
            
            return 

        if self._on_click is not None and event.button() == Qt.MouseButton.LeftButton:
            
            self._is_processing = True
            
            self.setEnabled(False)
            
            try:
                
                result = self._on_click(event)
                
                if inspect.iscoroutine(result):
                    
                    asyncio.create_task(self._wrap_async(result))
                    
            except Exception as e:
                
                self._is_processing = False
                
                raise e

        super().mousePressEvent(event)

    async def _wrap_async(self, coro):
        
        try:
            
            await coro
            
        finally:
            
            self._is_processing = False
            
            self.setEnabled(True)