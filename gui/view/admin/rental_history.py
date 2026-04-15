import os
import logging
import asyncio
import typing as t
from qasync import asyncSlot
from datetime import datetime

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

from PyQt6.QtCore import Qt, QSize, pyqtSignal, QTimer
from PyQt6.QtGui import QIcon, QFont, QPixmap, QCursor

from utils.logger import LoggerMixin
from utils.dc.admin.rental_history import RentalHistoryData, RentalHistoryCacheData
from services.admin.rental_history_cache import RentalHistoryCacheService
from ..modal.admin.edit_rental_history import EditRentalHistoryModal
from ..modal.confirm_action import ConfirmActionModal
from utils.enums.storage_item_type_enum import StorageItemTypeEnum
from config import Config
from db import queries

if t.TYPE_CHECKING:
    
    from .admin import AdminView

class RentalHistoryContent(QWidget, LoggerMixin):
    
    log: logging.Logger
    
    data_loaded = pyqtSignal(object)
    
    def __init__(self,
        admin_view: 'AdminView'         
        ):
        
        super().__init__()

        self.admin_view = admin_view
        
        self.cache_data: RentalHistoryCacheData | None = None
        
        self.rental_history_cache = RentalHistoryCacheService(
            redis_client = admin_view.redis_client,
            rental_lock = admin_view.main_window.app.rental_lock
        )
        
        self.confirm_action_modal = ConfirmActionModal()
        
        self.rental_history_modal = EditRentalHistoryModal()
        
        self.rental_worker = admin_view.rental_worker
        
        self.rental_end = admin_view.rental_end
        
        self.rental_end.rental_end_event.connect(self.get_rental_history)
        
        self.__init_view()
        
        asyncio.create_task(self.load_cache_data())
        
        self.data_loaded.connect(self.on_data_loaded)
    
    @staticmethod
    def icon(name: str) -> QIcon:
  
        return QIcon(os.path.join(Config.icon.icon_dir, name))    
        
    def __init_view(self):
        
        main_layout = QVBoxLayout(self)

        self.topbar = self.set_topbar()
        
        self.rental_history_list = self.set_login_history()
        self.rental_history_list.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.rental_history_list.setCursor(Qt.CursorShape.PointingHandCursor)
        
        main_layout.setContentsMargins(9, 9, 9, 9)
        main_layout.addWidget(self.topbar)
        main_layout.addWidget(self.rental_history_list)
        
    def set_login_history(self) -> QListWidget:
        
        rental_history_list = QListWidget()
        rental_history_list.setObjectName("MessageList")
        rental_history_list.setFrameShape(QFrame.Shape.NoFrame)
        rental_history_list.setMouseTracking(True)
        
        return rental_history_list
    
    def set_topbar(self):

        topbar = QWidget()
        topbar.setObjectName("Topbar")
        
        topbar_layout = QVBoxLayout(topbar)
        topbar_layout.setContentsMargins(10, 10, 10, 10)
        topbar_layout.setSpacing(8)
        
        title_row = QHBoxLayout()

        title = QLabel("Bérlési előzmények")
        title.setObjectName("BoatTitleLabel")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setFixedHeight(40)
        
        title_row.addWidget(title)

        lower_row = QHBoxLayout()
        
        self.input_field = QLineEdit()
        self.input_field.setObjectName("BoatSearchInput")
        self.input_field.setFixedHeight(35)
        self.input_field.setPlaceholderText("Keresés...")
        self.input_field.setCursor(Qt.CursorShape.PointingHandCursor)
        self.input_field.textChanged.connect(self._handle_search_input)
        
        self.print_btn = QPushButton()
        self.print_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.print_btn.setFixedHeight(50)
        self.print_btn.setObjectName("TrashButton")
        self.print_btn.setToolTip("Nyomtatás")
        self.print_btn.setIcon(RentalHistoryContent.icon("printer.svg"))
        self.print_btn.setIconSize(QSize(25, 25))
        self.print_btn.clicked.connect(self.__print_table)
        
        lower_row.addWidget(self.input_field)
        lower_row.addWidget(self.print_btn)
        
        header = QWidget()
        
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(5, 2, 5, 2)
        h_layout.setSpacing(0)
        h_layout.addStretch(1)

        header_labels = [
            "Bérlő",
            "Bérelt tárgy",
            "Mennyiség",
            "Bérlés kezdete",
            "Bérlés vége",
            "Visszaadva",
            "Fizetve",
            "Összesen",
            ""
        ]

        font = QFont()
        font.setPointSize(10)
        font.setBold(True)

        self.topbar_labels = []
        
        for text in header_labels:
            
            lbl = QLabel(text)
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setFont(font)
            
            h_layout.addWidget(lbl)
            h_layout.addStretch(1)
            
            self.topbar_labels.append(lbl)
        
        topbar_layout.addLayout(title_row)
        topbar_layout.addLayout(lower_row)
        topbar_layout.addWidget(header)
        
        return topbar
    
    def __print_table(self):
        print("print")

    def _emit_cache_data_safe(self, item: RentalHistoryCacheData):
        
        QTimer.singleShot(0, lambda: self.data_loaded.emit(item))
 
    @asyncSlot(RentalHistoryCacheData)
    async def get_rental_history(self, rental_history_cache: RentalHistoryCacheData):
        
        self.log.debug("Rental history Emit -> %s" % str(rental_history_cache))
       
        if not isinstance(rental_history_cache, RentalHistoryCacheData):
           
            self.log.error("Invalid rental_history data provided to get history")
            
            return
        
        self._emit_cache_data_safe(rental_history_cache)
    
    def on_data_loaded(self, cache_data):
        
        if isinstance(cache_data, RentalHistoryCacheData) and hasattr(cache_data, "items"):
        
            self._refhresh_headers_and_tenant_list(cache_data.items)
        
    def _refhresh_headers_and_tenant_list(self, rental_histories: t.List[RentalHistoryData]):
        
        if len(rental_histories) > 0:
            
            self.populate_rental_history_list(rental_histories)
    
    def populate_rental_history_list(self, rental_histories: t.List[RentalHistoryData]):
        
        self.rental_history_list.clear()
        
        self.log.debug("Populating rental history list with %d items of (%s) data" % (
            len(rental_histories),
            rental_histories[0].__class__.__name__
            )
        )
        
        self.rental_history_list.setUniformItemSizes(True)
        
        font = QFont()
        font.setPointSize(10)
            
        for rental_history in rental_histories:
            
            tenant_name = rental_history.tenant.tenant_name if rental_history.tenant.tenant_name is not None else "N/A"
            
            item_name = rental_history.tenant.item_name if rental_history.tenant.item_name is not None else "N/A"
            
            quantity = f"{rental_history.tenant.quantity:.4f}" if rental_history.tenant.quantity is not None else "N/A"
            
            rental_start = rental_history.tenant.rental_start.strftime(Config.time.timeformat) if rental_history.tenant.rental_start is not None else "N/A"
            
            rental_end = "Nincs megadva" if rental_history.tenant.rental_end is None else rental_history.tenant.rental_end.strftime(Config.time.timeformat)
            
            returned = "Igen" if rental_history.tenant.returned is True else "Nem"
            
            is_paid = "Igen" if rental_history.is_paid is True else "Nem"
            
            amount = f"{rental_history.tenant.rental_price:,.2f}".replace(",", ".") + " HUF" if rental_history.tenant.rental_price != 0 else "Kölcsön adva"
            
            list_item = QListWidgetItem()
            
            container = QWidget()
            container.setFixedHeight(35)
            
            tenant_name_label = QLabel(tenant_name)
            tenant_name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            tenant_name_label.setFont(font)
            
            tool_name_label = QLabel(item_name)
            tool_name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            tool_name_label.setFont(font)
            
            quantity_label = QLabel(quantity)
            quantity_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            quantity_label.setFont(font)
            
            rental_start_label = QLabel(rental_start)
            rental_start_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            rental_start_label.setFont(font)
            
            rental_end_label = QLabel(rental_end)
            rental_end_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            rental_end_label.setFont(font)
            
            returned_label = QLabel(returned)
            returned_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            returned_label.setFont(font)
            
            if rental_history.tenant.returned == True:
                
                returned_label.setStyleSheet(Config.styleSheets.success)
                
            else: 
                
                returned_label.setStyleSheet(Config.styleSheets.failed)
            
            is_paid_label = QLabel(is_paid)
            is_paid_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            is_paid_label.setFont(font)
            
            if rental_history.is_paid == True:
                
                is_paid_label.setStyleSheet(Config.styleSheets.success)
                
            else: 
                
                is_paid_label.setStyleSheet(Config.styleSheets.failed)
            
            amount_label = QLabel(amount)
            amount_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            amount_label.setFont(font)
        
            edit_btn = QPushButton()
            edit_btn.setObjectName("TrashButton")
            edit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            edit_btn.setIcon(RentalHistoryContent.icon("edit.svg"))
            edit_btn.setIconSize(QSize(20, 20))
            edit_btn.setToolTip("Módosítás")
            
            edit_btn.clicked.connect(lambda _, item = list_item: self.on_button_clicked(item)) 
            
            h_layout = QHBoxLayout(container)
            h_layout.setContentsMargins(5, 2, 5, 2)
            h_layout.setSpacing(0)

            widgets = [
                tenant_name_label,
                tool_name_label,
                quantity_label,
                rental_start_label,
                rental_end_label,
                returned_label,
                is_paid_label,
                amount_label,
                edit_btn
            ]
            
            h_layout.addStretch(1)

            for w in widgets:
                
                h_layout.addWidget(w)
                h_layout.addStretch(1)
            
            container.setLayout(h_layout)
            
            list_item.setSizeHint(container.sizeHint())
            
            self.rental_history_list.addItem(list_item)
            self.rental_history_list.setItemWidget(list_item, container)
            self.rental_history_list.setSpacing(0)
            
            list_item.setData(Qt.ItemDataRole.UserRole, rental_history)
            
    async def load_cache_data(self):
        
        now = datetime.now(Config.time.timezone_utc)
        
        self.cache_data = await self.rental_history_cache.get_rentals_from_cache(
            rentals_cache_id = f"{now.year}-{str(now.month).zfill(2)}",
            exp = Config.redis.cache.rental_history.exp
        )
        
        self._emit_cache_data_safe(self.cache_data)
    
    def _handle_search_input(self, text: str):
        
        text_lower = text.strip().lower()
        
        if not text_lower:
            
            self._emit_cache_data_safe(self.cache_data)
            
            return
        
        filtered_items = [
            rental_history for rental_history in self.cache_data.items
            if (
                (rental_history.tenant.tenant_id is not None and text_lower in str(rental_history.tenant.tenant_id).lower()) or
                (text_lower in str(rental_history.tenant.item_id).lower()) or
                (rental_history.tenant.item_name and text_lower in rental_history.tenant.item_name.lower()) or
                (rental_history.tenant.quantity is not None and text_lower in f"{rental_history.tenant.quantity:.4f}") or
                (rental_history.tenant.tenant_name and text_lower in rental_history.tenant.tenant_name.lower()) or
                (rental_history.tenant.rental_start and text_lower in str(rental_history.tenant.rental_start).lower()) or
                (rental_history.tenant.rental_end and text_lower in str(rental_history.tenant.rental_end).lower()) or
                (rental_history.tenant.returned is not None and text_lower in ("igen" if rental_history.tenant.returned else "nem")) or
                (rental_history.tenant.rental_price is not None and text_lower in f"{rental_history.tenant.rental_price:.2f}")
            )
        ]
        
        self.log.debug("Filtering rental history with text '%s'. %d items matched: %s" % (
            text_lower, 
            len(filtered_items), 
            filtered_items
            )
        )
        
        self._emit_cache_data_safe(RentalHistoryCacheData(items = filtered_items))
        
    @asyncSlot(QListWidgetItem)
    async def on_button_clicked(self, list_item: QListWidgetItem):
  
        previous_rental_history: RentalHistoryData = list_item.data(Qt.ItemDataRole.UserRole)
        
        self.log.debug("Previous rental history: %s" % previous_rental_history)
        
        if previous_rental_history is not None:
            
            self.rental_history_modal.previous_rental_history_data = previous_rental_history
            
            self.rental_history_modal.set_modal_labels_with_previous_reference(previous_rental_history)

            accepted = await self.rental_history_modal.exec_async()
            
            if accepted:
                
                updated_data = self.rental_history_modal.get_form_data()
                
                self.log.debug("Returned: %s -> %s" % (previous_rental_history.tenant.returned, updated_data.tenant.returned))
                
                self.log.debug("Payment status (is_paid): %s -> %s" % (previous_rental_history.is_paid, updated_data.is_paid))
                
                prev_returned = "bérlőnél van" if previous_rental_history.tenant.returned else "raktárban van"
                new_returned = "bérlőnél van" if updated_data.tenant.returned else "raktárban van"

                prev_paid = "törlesztve" if previous_rental_history.is_paid else "hátralékos"
                new_paid = "törlesztve" if updated_data.is_paid else "hátralékos"

                lines = []

                if prev_returned != new_returned:
                    
                    lines.append(f"{updated_data.tenant.item_name} {prev_returned} --> {new_returned}")

                if prev_paid != new_paid:
                    
                    lines.append(f"Költségek: {prev_paid} --> {new_paid}")

                lines.append(f"Összeg: {updated_data.tenant.rental_price:,.0f}".replace(",", ".") + " HUF")

                confirm_text = (
                    f"{updated_data.tenant.tenant_name} bérlési adatait módosítod:\n\n"
                    + "\n".join(lines)
                    + "\n\nBiztosan folytatod?"
                )
                                
                self.confirm_action_modal.set_action_message(confirm_text)
                
                confirm = await self.confirm_action_modal.exec_async()
                
                if not confirm:

                    return
                
                elif confirm:
                    
                    await self._update_rental_history(
                        from_data = previous_rental_history,
                        to_data = updated_data
                    )
                    
    async def _update_rental_history(self, from_data: RentalHistoryData, to_data: RentalHistoryData) -> None:
        
        returned = to_data.tenant.returned if from_data.tenant.returned != to_data.tenant.returned else None
            
        is_paid = to_data.is_paid if from_data.is_paid != to_data.is_paid else None
            
        await queries.update_rental_history_by_tenant_id(
            tenant_id = from_data.tenant.tenant_id,
            item_type = from_data.tenant.item_type,
            item_id = from_data. tenant.item_id,
            current_is_paid = from_data.is_paid,
            current_returned = from_data.tenant.returned,
            current_rental_start = from_data.tenant.rental_start,
            current_rental_end = from_data.tenant.rental_end,
            current_amount = from_data.tenant.rental_price,
            rented_quantity = from_data.tenant.quantity,
            new_is_paid = is_paid,
            new_returned = returned
        )
            
        self.rental_worker.notify_cache_update_needed(True)
        
        tenants_content = self.admin_view.get_tenants_content()
        
        await tenants_content.tenant_datatable_cache.clear_cache(Config.redis.cache.tenants.id)
        
        admin_storage_content = self.admin_view.get_admin_storage_content()
        
        await admin_storage_content.storage_cache.clear_cache(Config.redis.cache.storage.id)
        
        await admin_storage_content.storage_datatable_cache.clear_cache(Config.redis.cache.storage_items.id)
        
        main_window = self.admin_view.main_window
        
        if main_window is not None:
            
            storage_view = main_window.get_storage_view()
        
            if from_data.tenant.item_type == StorageItemTypeEnum.DEVICE:
            
                await storage_view.devices_cache_service.clear_cache(Config.redis.cache.devices.id)
            
            elif from_data.tenant.item_type == StorageItemTypeEnum.TOOL:
                
                await storage_view.tools_cache_service.clear_cache(Config.redis.cache.tools.id)
            
        await self.load_cache_data()