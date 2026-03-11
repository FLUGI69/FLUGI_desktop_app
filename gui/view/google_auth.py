from pathlib import Path
import logging
import typing as t 
import sys
import asyncio
import aiohttp
import socket
import platform
import winreg

from PyQt6.QtCore import Qt, QTimer
from qasync import asyncSlot
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QHBoxLayout,
    QSizePolicy
)
from PyQt6.QtGui import QPixmap, QPalette, QColor, QFont, QImage, QPainter
from PyQt6.QtSvg import QSvgRenderer
from PyQt6.QtCore import QSize as _QSize

from utils.logger import LoggerMixin
from routes.api.google.exceptions import (
    GmailException,
    ConnectionError,
    AuthenticationError,
)
from routes.api.google import UserClientView
from .main_window import MainWindow
from config import Config
from utils.handlers.widgets.clickable import ClickableWidget
from utils.dc.ip_info import IPInfo
from utils.dc.user_device import UserDevice

if t.TYPE_CHECKING:
    
    from async_loop import QtApplication

class GmailLoginWindow(QWidget, LoggerMixin):
    
    log: logging.Logger
    
    def __init__(self,
        app: 'QtApplication'
        ):
        
        super().__init__()
        
        self.app = app
        
        self.user_id = Config.google.user_id
        
        self.scopes = Config.google.scopes
        
        if getattr(sys, "frozen", False):
            
            self.base_path = Path(sys.executable).parent / "_internal"
            
            self.logo_path = self.base_path / Config.google.paths.logo
            
            self.google_icon_path = self.base_path / Config.google.paths.google_icon
                
        else:

            self.logo_path = Path(Config.google.paths.logo)
            
            self.google_icon_path = Path(Config.google.paths.google_icon)
  
        self.reminder_worker = app.reminder_worker

        self._lock = app.google_lock
        
        self.db = app.db
        
        self.redis_client = app.redis_client
        
        self.notifier = app.notifier

        self.setWindowTitle("Example Company Ltd. - Gmail Login")
        
        self.__init_view()

    def __init_view(self):
        
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, QColor("#424242"))
        
        self.setPalette(palette)
        
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(10)
        
        if self.logo_path.exists():
            
            logo_label = QLabel()
            
            renderer = QSvgRenderer(str(self.logo_path))
            
            if renderer.isValid():
                
                default_size = renderer.defaultSize()
                
                scale = 400 / default_size.width()
                
                target = _QSize(400, int(default_size.height() * scale))
                
                image = QImage(target, QImage.Format.Format_ARGB32_Premultiplied)
                image.fill(0)
                
                painter = QPainter(image)
                
                renderer.render(painter)
                
                painter.end()
                
                logo_label.setPixmap(QPixmap.fromImage(image))
            
            logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            layout.addWidget(logo_label)
            
            layout.addSpacing(20)

        # Title
        title = QLabel("Sign in with your Google account.")
        title.setObjectName("GoogleAuthTitle")
        title.setMinimumWidth(300) 
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        # Status label
        self.status_label = QLabel()
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setObjectName("error")

        # Custom button layout
        self.button_container = ClickableWidget(on_click = lambda _: self.__handle_login(), object_name = "LoginContainer")
        self.button_container.setCursor(Qt.CursorShape.PointingHandCursor)
        self.button_container.setFixedSize(220, 50)

        button_layout = QHBoxLayout(self.button_container)
        button_layout.setContentsMargins(10, 5, 10, 5)
        # button_layout.setSpacing(10)

        # Google icon
        if self.google_icon_path.exists():
            
            icon_label = QLabel()
            
            google_pixmap = QPixmap(str(self.google_icon_path)).scaled(
                50, 50, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
            )
            
            icon_label.setPixmap(google_pixmap)
            icon_label.setContentsMargins(0, 0, 0, 0)
            icon_label.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
            
            button_layout.addWidget(icon_label)

        # Text label
        text_label = QLabel("Sign in")
        text_label.setObjectName("Googlebtntext")
        text_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        text_label.setContentsMargins(0, 0, 0, 0)
        text_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        font = QFont()
        font.setBold(True)
        
        text_label.setFont(font)
        
        button_layout.addWidget(text_label)
        # button_layout.setSpacing(4)

        layout.addWidget(title)
        layout.addSpacing(20)
        layout.addWidget(self.status_label)
        layout.addWidget(self.button_container, alignment = Qt.AlignmentFlag.AlignCenter)

        self.setLayout(layout)
        
    @asyncSlot()
    async def __handle_login(self) -> None:
        
        self.log.info("OAuth login attempt")
        
        self.status_label.setObjectName("info")
        self.status_label.setText("Connecting to Google account...")
        self.status_label.style().unpolish(self.status_label)
        self.status_label.style().polish(self.status_label)

        self._login_task = asyncio.current_task()
         
        try:
            
            ip_info = await self.get_ip_info()

            user_device = self.create_user_device(ip_info)

            self.user_client = UserClientView(
                user_id = self.user_id,
                scopes = self.scopes,
                user_device = user_device
            )
            
            await self.user_client.check_google_token_exists()
      
            await self.user_client.authorize()

            if self.user_client.is_authorized == True and self.user_client.creds is not None:
                
                self.status_label.setObjectName("success")
                self.status_label.setText("Successful login...")
                self.status_label.style().unpolish(self.status_label)
                self.status_label.style().polish(self.status_label)
                
                QTimer.singleShot(1000, self._open_main_window)
                
        except AuthenticationError as e:
            
            self._handle_error("Authentication Error", e)

        except ConnectionError as e:
            
            self._handle_error("Connection Error", e)

        except GmailException as e:
            
            self._handle_error("Gmail Exception", e)
            
        except Exception as e:
            
            self._handle_error("Unexpected error", e)

        finally:
            
            self._login_task = None
              
    def get_machine_guid(self):
        
        try:
            
            key = winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"SOFTWARE\Microsoft\Cryptography"
            )
            
            guid, _ = winreg.QueryValueEx(key, "MachineGuid")
            
            return guid
        
        except Exception as e:
            
            self.log.exception("Failed to retrieve Machine GUID from registry: %s" % str(e))
            
            return None
    
    def create_user_device(self, ip_info: IPInfo) -> UserDevice:
        
        if ip_info is not None:
            
            try:

                device_name = socket.gethostname()
                
                if not device_name:
                    
                    self.log.warning("Failed to retrieve device name: %s" % device_name)
                    
                    device_name = "Unknown"
                    
                self.log.debug("Device name: %s" % device_name)

                os_info = platform.system() + " " + platform.release()
                
                if not os_info.strip():
                    
                    self.log.warning("Failed to retrieve OS information: %s" % os_info)
                    
                    os_info = "Unknown OS"
                    
                self.log.debug("OS info: %s" % os_info)

                ip_address = getattr(ip_info, "ip", None)
                
                if not ip_address:
                    
                    self.log.warning("IP address is missing: %s" % str(ip_address))
                    
                    ip_address = "0.0.0.0"
                    
                self.log.debug("IP address: %s" % ip_address)

                location_parts = [part for part in [ip_info.city, ip_info.region, ip_info.country] if part]
                
                location = ", ".join(location_parts) if location_parts else "Unknown location"
            
                self.log.debug("Location: %s" % location)
                
                guid = self.get_machine_guid()

                return UserDevice(
                    username = None,
                    guid = guid if guid is not None else "Unknown",
                    device_name = device_name,
                    os = os_info,
                    ip_address = ip_address,
                    location = location
                )

            except Exception as e:
                
                self.log.exception("Error creating UserDevice: %s" % str(e))
                
                raise
            
    # TODO: Adding a later Geolocation API call to improve location accuracy
    async def get_ip_info(self) -> IPInfo:
        
        try:
            
            async with aiohttp.ClientSession() as session:
                
                async with session.get(Config.ip_info.url, timeout = 5) as response:
                    
                    self.log.debug("HTTP request sent to %s" % Config.ip_info.url)
                    
                    self.log.debug("Response status: %s" % str(response.status))

                    if response.status != 200:
                        
                        self.log.warning("Non-200 response received: %s" % str(response.status))
                        
                        return IPInfo()

                    try:
                        
                        data = await response.json()
                        
                    except Exception as e:
                        
                        self.log.exception("Failed to decode JSON: %s" % e)
                        
                        return IPInfo()

                    self.log.debug("Raw IP info: %s" % data)

                    if not data:
                        
                        self.log.warning("Received empty data from IP info API")
                        
                        return IPInfo()

                    ip_info = IPInfo(
                        ip = data.get("ip"),
                        city = data.get("city"),
                        region = data.get("region"),
                        country = data.get("country"),
                        loc = data.get("loc"),
                        org = data.get("org"),
                        postal = data.get("postal"),
                        timezone = data.get("timezone")
                    )

                    missing_fields = [k for k, v in ip_info.__dict__.items() if not v]
                    
                    if missing_fields:
                        
                        self.log.warning("Missing fields in IP info: %s" % missing_fields)

                    return ip_info

        except Exception as e:
            
            self.log.exception("Failed to get IP info from %s: %s" % (
                Config.ip_info.url,
                str(e)
                )
            )
            
            return IPInfo()
    
    def _open_main_window(self) -> None:

        self.main_window = MainWindow(
            app = self.app,
            user_client = self.user_client,
            gmail_login_window = self
        )
    
        self.main_window.show()
        
        self.hide()
        
        self.log.debug("Successfully authenticated")
        
    def _handle_error(self, title: str, exc: Exception) -> None:
        
        self.status_label.setObjectName("error")
        self.status_label.setText(title)
        self.status_label.style().unpolish(self.status_label)
        self.status_label.style().polish(self.status_label)

        self.log.error("%s: %s", title, exc)
            
    def closeEvent(self, event):
        
        if hasattr(self, "_login_task") and self._login_task is not None:
            
            self._login_task.cancel()
            
        super().closeEvent(event)

