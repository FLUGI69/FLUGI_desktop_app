from qasync import asyncSlot
import os
import asyncio
import typing as t
import logging
from datetime import datetime

from PyQt6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QComboBox,
    QLineEdit,
    QFrame,
    QLineEdit,
    QStackedWidget,
    QPushButton,
    QLabel,
    QTableWidget
)
from PyQt6.QtGui import QCursor, QDesktopServices, QIcon
from PyQt6.QtCore import Qt, pyqtSignal, QUrl, QSize, QTimer

from weasyprint import HTML

from utils.logger import LoggerMixin
from services.admin.tenant_datatable_cache import AdminTenantsCacheService
from view.admin.custom import CustomCalendar
from utils.dc.tenant_data import TenantData
from utils.dc.admin.tenant_items import AdminTenantsCacheData
from view.tables.admin.tenant import TenantsTable
from ..modal.confirm_action import ConfirmActionModal
from ..modal.admin.extend_tenant import ExtendTenantModal
from exceptions import InsufficientQuantityError
from exceptions import RentalPeriodExpiredError
from db import queries
from config import Config

if t.TYPE_CHECKING:
    
    from .admin import AdminView

class TenantsContent(QWidget, LoggerMixin):
    
    log: logging.Logger
    
    table_data_loaded = pyqtSignal(object)

    def __init__(self,
        admin: 'AdminView'
        ):
        
        super().__init__()
        
        self.admin_view = admin
        
        self.spinner = admin.main_window.app.spinner

        self.datatable_helper = admin.main_window.app.datatable_helper
        
        self.rental_worker = admin.rental_worker
        
        self.tenant_cache_data: AdminTenantsCacheData | None = None
        
        if admin.main_window.app.tenant_cache_service is None:
            
            self.tenant_datatable_cache = AdminTenantsCacheService(
                redis_client = admin.redis_client,
                rental_lock = admin.main_window.app.rental_lock
            )
            admin.main_window.app.tenant_cache_service = self.tenant_datatable_cache
       
        else:
          
            self.tenant_datatable_cache = admin.main_window.app.tenant_cache_service
        
        self.previous_tenants: TenantData | None = None
        
        self.tenants_table = TenantsTable(self)
        
        self.confirm_action_modal = ConfirmActionModal(self)
        
        self.extend_tenant_modal = ExtendTenantModal(self)
        
        self.results_table = None
        
        self.error_labels = {}
        
        asyncio.create_task(
            self.load_cache_data(
                cache_id = Config.redis.cache.tenants.id,
                exp = Config.redis.cache.tenants.exp,
                update_rental_cache = False
            )
        )
        
        self.__init_view()
        
        self.table_data_loaded.connect(self.on_table_data_loaded)
    
    @staticmethod
    def icon(name: str) -> QIcon:
        
        return QIcon(os.path.join(Config.icon.icon_dir, name))
    
    def __init_view(self):
        
        main_layout = QHBoxLayout(self)
    
        # Side menu
        menu_layout = QVBoxLayout()
        menu_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        menu_layout.setContentsMargins(0, 0, 0, 0)

        self.menu_buttons = {
            "extend_tenant": QPushButton("Hosszabbítás")
        }        
        
        self.error_label = QLabel()
        self.error_label.setObjectName("error")
        self.error_label.setVisible(False) 
        self.error_label.setMaximumWidth(380)

        self.extend_rental = self.menu_buttons["extend_tenant"]
        
        for name, button in self.menu_buttons.items():

            button.setFixedWidth(200)
            button.setFixedHeight(50)
            button.setCursor(Qt.CursorShape.PointingHandCursor)

            if name == "extend_tenant":
                
                button.setObjectName("ModifyStockBtn")
            
            container_widget = QWidget()
            container_layout = QVBoxLayout(container_widget)
            container_layout.setContentsMargins(0, 0, 0, 0)
            container_layout.setSpacing(2)

            error_label = QLabel()
            error_label.setObjectName("error")
            error_label.setVisible(False)  
            error_label.setMaximumWidth(200)

            container_layout.addWidget(button)
            container_layout.addWidget(error_label)

            self.error_labels[button] = error_label

            menu_layout.addWidget(container_widget)
            
            button.clicked.connect(lambda _, b = button: self._handle_action(b))
            
        menu_widget = QFrame()
        menu_widget.setLayout(menu_layout)
        menu_widget.setFixedWidth(200)
        main_layout.addWidget(menu_widget)
        
        # Content area
        widget = QWidget()
    
        right_panel = QVBoxLayout()
        right_panel.setContentsMargins(0, 0, 0, 0)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Keresés...")
        self.search_input.setObjectName("WarehouseSearchInput")
        self.search_input.textChanged.connect(self._handle_search_input)

        self.print_btn = QPushButton()
        self.print_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.print_btn.setFixedHeight(50)
        self.print_btn.setObjectName("TrashButton")
        self.print_btn.setToolTip("Nyomtatás")
        self.print_btn.setIcon(TenantsContent.icon("printer.svg"))
        self.print_btn.setIconSize(QSize(25, 25))
        self.print_btn.clicked.connect(self.__print_table)
        
        search_layout = QHBoxLayout()
        search_layout.addWidget(self.search_input, 1)
        search_layout.addWidget(self.print_btn)

        right_panel.addLayout(search_layout)

        self.content_container = QWidget()
        self.content_container.setObjectName("MaterialTableContainer")
        self.content_container.setLayout(QVBoxLayout())
        self.content_container.layout().setContentsMargins(0, 0, 0, 0)
        
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)

        self.stack = QStackedWidget()
        
        self.content_container.layout().addWidget(self.stack)
        
        right_panel.addWidget(self.content_container)
        
        right_widget = QWidget()
        right_widget.setLayout(right_panel)
        
        main_layout.addWidget(right_widget)
       
        self.__set_content(self.tenants_table)

    def __print_table(self):
        
        html_content = self.generate_html()
        
        print(html_content)
        
    def generate_html(self):
        print("generate_html")
        
    @asyncSlot()
    async def _handle_action(self, sender: QPushButton):
      
        if isinstance(sender, QPushButton):
            
            self.error_labels[sender].setVisible(False)
            
            if sender is self.extend_rental:
                
                self.log.debug("Extend button clicked in TenantContent")
                
                selected_data = self.tenants_table.get_selected_datatable_items()
                
                if not selected_data:
                    
                    self.log.warning("No item selected for modify")
                    
                    self.error_labels[sender].setText("Válassz elemet a módosításhoz")
                    self.error_labels[sender].setVisible(True)
                                    
                    return

                if len(selected_data) > 1:
                    
                    self.log.warning("Multiple items selected. Only one item can be edited at a time")
                    
                    self.error_labels[sender].setText("Egyszerre csak egy elemet válassz")
                    self.error_labels[sender].setVisible(True)
                    
                    return

                self.previous_tenants = selected_data[0]
                
                self.extend_tenant_modal.update_parameters_from_previous_reference(self.previous_tenants)
                
                accepted = await self.extend_tenant_modal.exec_async()
                
                if accepted:
                    
                    to_data: TenantData = self.extend_tenant_modal.get_form_data()
                    
                    rental_price_label = "Bérlés összege / időszak:" if self.previous_tenants.rental_end is not None else "Bérlés összege / nap:"
                    
                    increased_rental_price_label = "Növelt bérlés összege / időszak:" \
                        if self.previous_tenants.rental_end is not None else "Növelt bérlés összege / nap:"
                    
                    price_modified_text = f"{increased_rental_price_label} {to_data.rental_price:,.2f}".replace(",", ".") + " HUF" \
                        if self.previous_tenants.rental_price != to_data.rental_price else ""
                    
                    rental_end_text = self.previous_tenants.rental_end.strftime(Config.time.timeformat) \
                        if self.previous_tenants.rental_end is not None else "N/A"

                    if self.previous_tenants.quantity + to_data.quantity == self.previous_tenants.quantity:
                        
                        rented_quantity_text = "Nem módosult"
                        
                    else:
                        
                        rented_quantity_text = f"{self.previous_tenants.quantity:.4f} -> {self.previous_tenants.quantity + to_data.quantity:.4f}"
                    
                    confirm_text = (
                        "Bérelt időszak meghosszabbítása:\n\n"
                        f"Bérlő: {to_data.tenant_name}\n"
                        f"Bérelt tárgy: {to_data.item_name}\n"
                        f"{rental_price_label} {self.previous_tenants.rental_price:,.2f}".replace(",", ".") + " HUF\n"
                        f"Bérlés kezdete: {self.previous_tenants.rental_start}\n\n"
                        f"Bérlés vége: {rental_end_text} --> "
                        f"{to_data.rental_end.strftime(Config.time.timeformat) or datetime.now().strftime(Config.time.timeformat)}\n"
                        f"Bérelt mennyiség: {rented_quantity_text}"
                    )
                    
                    if price_modified_text != "":
                        
                        confirm_text += f"\n{price_modified_text}"

                    confirm_text += "\n\nBiztosan folytatod?"
               
                    self.confirm_action_modal.set_action_message(confirm_text)
                    
                    confirm = await self.confirm_action_modal.exec_async()
                    
                    if not confirm:
                        
                        return
                    
                    elif confirm:
                  
                        await self.__extend_tenant(
                            sender = sender,
                            to_data = to_data,
                            from_data = self.previous_tenants
                        )
                
    def _handle_search_input(self, text: str):
        print(text)

    async def __extend_tenant(self, sender: QPushButton, to_data: TenantData, from_data: TenantData):
        
        to_data.rental_end = to_data.rental_end if to_data.rental_end.date() != datetime.now().date() else None
        
        self.log.debug("Comparing tenant data: from %s -> %s" % (
            from_data, 
            to_data
            )
        )

        if to_data is not None and from_data is not None:

            try:

                await queries.update_tenant_by_id(
                    tenant_id = from_data.tenant_id,
                    item_type = from_data.item_type,
                    current_quantity = from_data.quantity,
                    current_rental_start = from_data.rental_start,
                    current_price = from_data.rental_price,
                    new_quantity = to_data.quantity,
                    new_price = to_data.rental_price,
                    is_daily_price = from_data.is_daily_price,
                    current_rental_end = from_data.rental_end,
                    new_rental_end = to_data.rental_end
                )

            except RentalPeriodExpiredError as e:
                
                self.log.warning(e.message)
                
                self.error_labels[sender].setText("Lejárt bérleti szerződés")
                self.error_labels[sender].setVisible(True)
                
            except InsufficientQuantityError as e:
                
                self.log.warning(e.message)
                
                self.error_labels[sender].setText("Nincs rendelkezésre álló mennyiség")
                self.error_labels[sender].setVisible(True)
            
            await self.tenant_datatable_cache.clear_cache(Config.redis.cache.tenants.id)
            
            await self.load_cache_data(
                cache_id = Config.redis.cache.tenants.id,
                exp = Config.redis.cache.tenants.exp,
                update_rental_cache = True
            )
                
    def _emit_cache_data_safe(self, item: AdminTenantsCacheData):
        
        QTimer.singleShot(0, lambda: self.table_data_loaded.emit(item))
        
    async def load_cache_data(self, cache_id: str, exp: int, update_rental_cache: bool):
         
        self.tenant_cache_data = await self.tenant_datatable_cache.get_tenant_datatable_data_from_cache(
            tenant_cache_id = cache_id,
            exp = exp
        )
        
        self._emit_cache_data_safe(self.tenant_cache_data)
        
        calendar_content = self.admin_view.main_window.get_calendar_content()
        
        if calendar_content is not None and isinstance(calendar_content.calendar, CustomCalendar):
            
            custom_calendar = calendar_content.calendar
            
            custom_calendar.set_marked_dates(self.tenant_cache_data)
        
        if update_rental_cache == True:
            
            self.rental_worker.notify_cache_update_needed(True)
    
    def on_table_data_loaded(self, cache_data: AdminTenantsCacheData):
      
        if cache_data is not None and hasattr(cache_data, "items"):
            
            self.results_table.load_data(cache_data)

    def __set_content(self, new_view: QWidget):
        
        index = self.stack.indexOf(new_view)
        
        if index == -1:
            
            self.stack.addWidget(new_view)
            
            index = self.stack.indexOf(new_view)

        self.stack.setCurrentIndex(index)
        
        self.results_table = new_view
    