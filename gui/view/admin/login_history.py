import os
import logging
import asyncio
import typing as t
from qasync import asyncSlot

from PyQt6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QListWidget,
    QPushButton,
    QLineEdit,
    QSizePolicy,
    QFrame,
    QLabel,
    QListWidgetItem
)

from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QIcon, QFont, QPixmap

from utils.logger import LoggerMixin
from utils.dc.admin.login_history import LoginHistory
from config import Config
from db import queries

if t.TYPE_CHECKING:
    
    from .admin import AdminView

class LoginHistoryContent(QWidget, LoggerMixin):
    
    log: logging.Logger
    
    def __init__(self,
        admin_view: 'AdminView'         
        ):
        
        super().__init__()
        
        self.login_history: t.List[LoginHistory] = []
        
        self.gmail_view = admin_view.main_window.gmail_login_window
        
        self.guid = self.gmail_view.get_machine_guid()
        
        self.__init_view()
        
        asyncio.create_task(self._load_current_device_login_history())
        
    @staticmethod
    def icon(name: str) -> QIcon:
  
        return QIcon(os.path.join(Config.icon.icon_dir, name))    
        
    def __init_view(self):
        
        main_layout = QVBoxLayout(self)

        self.topbar = self.set_topbar()
        
        self.login_history_list = self.set_login_history()
        self.login_history_list.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.login_history_list.setCursor(Qt.CursorShape.PointingHandCursor)
        
        main_layout.setContentsMargins(9, 9, 9, 9)
        main_layout.addWidget(self.topbar)
        main_layout.addWidget(self.login_history_list)
        
    def set_login_history(self) -> QListWidget:
        
        login_history_list = QListWidget()
        login_history_list.setObjectName("MessageList")
        login_history_list.setFrameShape(QFrame.Shape.NoFrame)
        login_history_list.setMouseTracking(True)
        
        return login_history_list
    
    def set_topbar(self):

        topbar = QWidget()
        topbar.setObjectName("Topbar")
        
        topbar_layout = QVBoxLayout(topbar)
        topbar_layout.setContentsMargins(10, 10, 10, 10)
        topbar_layout.setSpacing(8)
        
        title_row = QHBoxLayout()

        title = QLabel("Aktuális eszköz")
        title.setObjectName("BoatTitleLabel")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setFixedHeight(40)
        
        title_row.addWidget(title)
        
        upper_row = QHBoxLayout()
        
        self.topbar_labels = [] 
        for i in range(4):
            
            lbl = QLabel()
            lbl.setObjectName("BoatTitleLabel")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setFixedHeight(35)
            
            upper_row.addWidget(lbl)
            
            self.topbar_labels.append(lbl)
            
        # upper_row.addStretch()

        lower_row = QHBoxLayout()
        
        self.input_field = QLineEdit()
        self.input_field.setObjectName("BoatSearchInput")
        self.input_field.setFixedHeight(35)
        self.input_field.setPlaceholderText("Új felhasználónév megadása...")
        self.input_field.setCursor(Qt.CursorShape.PointingHandCursor)
        
        modify_button = QPushButton("Módosítás")
        modify_button.setObjectName("BoatSearchBtn")
        modify_button.setFixedHeight(35)
        modify_button.setCursor(Qt.CursorShape.PointingHandCursor)
        modify_button.clicked.connect(lambda: asyncio.create_task(self.on_modify_btn_clicked()))
        
        lower_row.addWidget(self.input_field)
        lower_row.addWidget(modify_button)
        
        topbar_layout.addLayout(title_row)
        topbar_layout.addLayout(upper_row)
        topbar_layout.addLayout(lower_row)
        
        return topbar

    def update_login_history_usernames(self, new_username: str):
        
        count = self.login_history_list.count()
        
        self.log.info("Total items in login history: %d" % count)
        
        for i in range(count):
            
            item = self.login_history_list.item(i)
            
            container = self.login_history_list.itemWidget(item)
            
            if container is not None:
            
                layout = container.layout()
                
                if layout is not None:
                    
                    for j in range(layout.count()):
                        
                        layout_item = layout.itemAt(j)
                        
                        widget = layout_item.widget()
                        
                        if widget and isinstance(widget, QLabel) and widget.objectName() == "UsernameLabel":
                        
                            old_text = widget.text()
                        
                            widget.setText(new_username)
                            
                            self.log.debug("Item %d: Username label updated :'%s' -> '%s'" % (
                                i,
                                old_text,
                                new_username
                                )
                            )
                            
                            break  

    async def on_modify_btn_clicked(self):
        
        field = self.input_field.text().strip()
        
        if field != "":
            
            if self.guid is not None:
                
                await queries.update_device_name_by_guid(
                    guid = self.guid,
                    name = field
                )
                
                self.update_login_history_usernames(field)
                
                self.topbar_labels[0].setText(field)
                
                self.input_field.clear()
            
    async def _load_current_device_login_history(self) -> None:
    
        if self.guid is not None:
                
            query_results = await queries.select_current_device_by_guid(self.guid)
            
            if query_results is not None:
                
                self.login_history = [LoginHistory(
                    username = query_results.username,
                    guid = query_results.guid,
                    device_name = query_results.device_name,
                    os = query_results.os,
                    ip_address = query_results.ip_address,
                    location = query_results.location,
                    login_time = row.login_time,
                    success = row.success
                ) for row in query_results.login_histories]
                # print(self.login_history)
                
                topbar_values = [
                    query_results.username if query_results.username is not None else "Nincs név",
                    query_results.device_name,
                    query_results.os,
                    query_results.ip_address
                ]
                
                for lbl, value in zip(self.topbar_labels, topbar_values):
                    
                    lbl.setText(str(value))
                
                self.populate_login_history_list(self.login_history)
                
    def populate_login_history_list(self, login_history: LoginHistory) -> None:
        
        self.login_history_list.clear()
        
        self.log.debug("Populating login history list with %d items. Username: %s Guid: (%s)" % (
            len(login_history),
            login_history[0].username,
            login_history[0].guid
            )
        )
        
        if len(login_history) > 0:
            
            self.login_history_list.setUniformItemSizes(True)
            
            font = QFont()
            font.setPointSize(10)
            font.setBold(True)
            
            for login in login_history:
                
                location_parts = [p.strip() for p in login.location.split(",")]
          
                city = location_parts[0] if len(location_parts) > 0 else None
                
                region = location_parts[1] if len(location_parts) > 1 else None
                
                country_code = location_parts[2] if len(location_parts) > 2 else None
    
                list_item = QListWidgetItem()
                
                container = QWidget()
                container.setFixedHeight(35)
                
                flag_label = QLabel()
                flag_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

                flag_code = country_code.lower() if country_code is not None else "nan"
                
                pixmap = QPixmap(os.path.join(Config.flags.flag_dir, f"{flag_code}.png"))
                
                if not pixmap.isNull():
    
                    scaled_pixmap = pixmap.scaled(QSize(32, 20), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                    
                    flag_label.setPixmap(scaled_pixmap)
               
                else:
                    
                    self.log.error("Could not load flag image for code %s" % flag_code)
                
                username_label = QLabel(login.username if login.username is not None else login.guid)
                username_label.setObjectName("UsernameLabel")
                username_label.setFont(font)
                
                status_label = QLabel("Sikeres" if login.success == True else "Sikertelen")
                status_label.setAutoFillBackground(True)
                status_label.setFont(font)
                
                if login.success == True:
                    
                    status_label.setStyleSheet(Config.styleSheets.success)
                    
                else:
                    
                    status_label.setStyleSheet(Config.styleSheets.failed)
                    
                ip_address_label = QLabel(login.ip_address if login.ip_address is not None else "N/A")
                ip_address_label.setFont(font)
                
                platform_label = QLabel(login.os if login.os is not None else "N/A")
                platform_label.setFont(font)
                
                location_str = f"{city if city is not None else "N/A"}, {region if region is not None else "N/A"}" 
                
                location_label = QLabel(location_str)
                location_label.setFont(font)
                
                login_time_str = login.login_time.strftime(Config.time.timeformat)
                    
                login_time_label = QLabel(login_time_str)
                login_time_label.setFont(font)
                login_time_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                
                trash_btn = QPushButton()
                trash_btn.setObjectName("TrashButton")
                trash_btn.setCursor(Qt.CursorShape.PointingHandCursor)
                trash_btn.setIcon(LoginHistoryContent.icon("trash.svg"))
                trash_btn.setIconSize(QSize(20, 20))
                trash_btn.setToolTip("Törlés")
                
                trash_btn.clicked.connect(lambda _, item = list_item: self.on_delete_clicked(item))
                
                h_layout = QHBoxLayout(container)
                h_layout.setContentsMargins(5, 2, 5, 2)
                h_layout.setSpacing(0)

                widgets = [
                    flag_label,
                    username_label,
                    status_label,
                    ip_address_label,
                    platform_label,
                    location_label,
                    login_time_label,
                    trash_btn
                ]
                
                h_layout.addStretch(1)

                for w in widgets:
                    
                    h_layout.addWidget(w)
                    h_layout.addStretch(1)
                
                container.setLayout(h_layout)
                
                list_item.setSizeHint(QSize(container.sizeHint().width(), 35))
                
                self.login_history_list.addItem(list_item)
                self.login_history_list.setItemWidget(list_item, container)
                self.login_history_list.setSpacing(0)
                
                list_item.setData(Qt.ItemDataRole.UserRole, login)
                
    @asyncSlot(QListWidgetItem)
    async def on_delete_clicked(self, list_item: QListWidgetItem):
        
        login_history: LoginHistory = list_item.data(Qt.ItemDataRole.UserRole)
        print(login_history)