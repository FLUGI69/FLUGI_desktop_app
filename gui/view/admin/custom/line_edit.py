from PyQt6.QtWidgets import QLineEdit
from PyQt6.QtCore import Qt
import asyncio

class SearchLineEdit(QLineEdit):
    
    def __init__(self, 
        btn_callback,
        parent = None
        ):
        
        super().__init__(parent)
        
        self.btn_callback = btn_callback 

    def keyPressEvent(self, event):
        
        key = event.key()
        
        modifiers = event.modifiers()

        if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            
            if modifiers & Qt.KeyboardModifier.ShiftModifier:
                
                super().keyPressEvent(event)
                
                return
            
            else:
                
                asyncio.ensure_future(self.btn_callback(0))
                
                return

        super().keyPressEvent(event)