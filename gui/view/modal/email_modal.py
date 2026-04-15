import asyncio
import logging

from PyQt6.QtWidgets import (
    QDialog, 
    QVBoxLayout
)
from PyQt6.QtCore import Qt

from utils.dc.gmail_response_data import EmailHeaders
from utils.logger import LoggerMixin
from PyQt6.QtWebEngineWidgets import QWebEngineView

class EmailModal(QDialog, LoggerMixin):
    
    log: logging.Logger
    
    def __init__(self):
        
        super().__init__()
        
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, True)
        
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        
        self.resize(900, 700)

        self._future = None
        
        self._web_view = QWebEngineView()
        
        self.email_header: EmailHeaders | None = None

        self.__init_modal()

    def __init_modal(self):
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        layout.addWidget(self._web_view)

    def load_html(self, html_content: str) -> None:

        self._web_view.setHtml(html_content)
            
    def exec_async(self) -> asyncio.Future:
        
        self._future = asyncio.get_event_loop().create_future()
        
        self.log.info("Starting asynchronous modal execution, future created and modal opened")
        
        self.accepted.connect(self._on_accepted)
        self.rejected.connect(self._on_rejected)
        
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        
        self.show()
    
        return self._future

    def _on_accepted(self):
        
        if self._future and not self._future.done():
            
            self.log.info("Modal accepted by the user setting future result to True")
            
            self._future.set_result(True)
            
        else:
            
            self.log.warning("Accepted signal received, but future is already done or missing")
        
        self._disconnect_signals()
        
        self.log.info("Disconnected accepted and rejected signals after acceptance")

    def _on_rejected(self):
        
        if self._future and not self._future.done():
            
            self.log.info("Modal rejected by the user setting future result to False")
            
            self._future.set_result(False)
            
        else:
            
            self.log.warning("Rejected signal received, but future is already done or missing")
        
        self._disconnect_signals()
        
        self.log.info("Disconnected accepted and rejected signals after rejection")

    def _disconnect_signals(self):
        
        try:
            
            self.accepted.disconnect(self._on_accepted)
            self.rejected.disconnect(self._on_rejected)
            
            self.log.debug("Successfully disconnected modal signals")
            
        except TypeError:
            
            self.log.warning("Attempted to disconnect signals that were not connected")

    def closeEvent(self, event):
        
        if self._future and not self._future.done():
            
            self.log.info("Modal closed without explicit accept/reject; setting future result to False")
            
            self._future.set_result(False)
        
        self._disconnect_signals()
        
        self.log.info("Modal closed signals disconnected and closing event propagated")
        
        super().closeEvent(event)
