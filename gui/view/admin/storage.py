from qasync import asyncSlot
import os
import asyncio
import typing as t
import logging
import base64
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
    QInputDialog
)
from PyQt6.QtGui import QCursor, QDesktopServices, QIcon
from PyQt6.QtCore import Qt, pyqtSignal, QUrl, QSize, QTimer

from weasyprint import HTML
import pandas as pd

from utils.logger import LoggerMixin
from services.admin.storage_dropdown_cache import StorageCacheService
from services.admin.storage_datatable_cache import AdminStorageItemsCacheService
from utils.dc.admin.storage import StorageCacheData, StorageData
from utils.dc.admin.storage_items import AdminStorageItemsCacheData
from utils.dc.material import MaterialData
from utils.dc.tools import ToolsData
from utils.dc.device import DeviceData
from view.tables.admin.storage import StorageTable
from view.modal.admin.add_storage import AddStorageModal
from view.modal.admin.edit_storage import EditStorageModal
from ..modal.confirm_action import ConfirmActionModal
from db import queries
from config import Config

if t.TYPE_CHECKING:
    
    from .admin import AdminView

class AdminStorageContent(QWidget, LoggerMixin):
    
    log: logging.Logger
    
    dropdown_data_loaded = pyqtSignal(object)
    
    table_data_loaded = pyqtSignal(object)
    
    def __init__(self,
        admin: 'AdminView'
        ):
        
        super().__init__()
        
        self.spinner = admin.main_window.app.spinner
        
        self._admin_storage_lock = asyncio.Lock()
        
        self.datatable_helper = admin.main_window.app.datatable_helper
        
        self.storage_cache_data: StorageCacheData | None = None
        
        self.storage_cache = StorageCacheService(admin.redis_client)
        
        self.storage_datatable_cache = AdminStorageItemsCacheService(admin.redis_client)
        
        self.storage_table = StorageTable(self)
        
        self.add_storage_modal = AddStorageModal(self)
        
        self.edit_storage_modal = EditStorageModal(self)
        
        self.confirm_action_modal = ConfirmActionModal(self)
        
        self.results_table = None
        
        self.error_labels = {}
        
        asyncio.create_task(
            self.load_cache_data(
                target = Config.redis.cache.storage.target,
                cache_id = Config.redis.cache.storage.id,
                exp = Config.redis.cache.storage.exp
            )
        )
        
        asyncio.create_task(
            self.load_cache_data(
                target = Config.redis.cache.storage_items.target,
                cache_id = Config.redis.cache.storage_items.id,
                exp = Config.redis.cache.storage_items.exp
            )
        )
        
        self.storage_datatable_data: AdminStorageItemsCacheData | None = None
        
        self.__init_view()
        
        self.dropdown_data_loaded.connect(self.on_dropdown_data_loaded)
        
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
            "add_btn": QPushButton("Add"),
            "edit_btn": QPushButton("Edit storage")
        }        
        
        self.error_label = QLabel()
        self.error_label.setObjectName("error")
        self.error_label.setVisible(False) 
        self.error_label.setMaximumWidth(380)

        self.add_btn = self.menu_buttons["add_btn"]
        self.edit_btn = self.menu_buttons["edit_btn"]
        
        for name, button in self.menu_buttons.items():

            button.setFixedWidth(200)
            button.setFixedHeight(50)
            button.setCursor(Qt.CursorShape.PointingHandCursor)

            if name == "add_btn":
                
                button.setObjectName("AddStockBtn")
                
            elif name == "edit_btn":
                
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
        self.search_input.setPlaceholderText("Search...")
        self.search_input.setObjectName("WarehouseSearchInput")
        self.search_input.textChanged.connect(self._handle_search_input)

        self.dropdown_select_storage = QComboBox()
        self.dropdown_select_storage.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.dropdown_select_storage.setFixedHeight(50)
        self.dropdown_select_storage.addItem("")
        
        self.dropdown_select_storage.currentIndexChanged.connect(lambda _, cb = self.dropdown_select_storage: self._handle_action(cb))

        self.print_btn = QPushButton()
        self.print_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.print_btn.setFixedHeight(50)
        self.print_btn.setObjectName("TrashButton")
        self.print_btn.setToolTip("Print")
        self.print_btn.setIcon(AdminStorageContent.icon("printer.svg"))
        self.print_btn.setIconSize(QSize(25, 25))
        self.print_btn.clicked.connect(self.__print_table)
        
        self.download_btn = QPushButton()
        self.download_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.download_btn.setFixedHeight(50)
        self.download_btn.setObjectName("TrashButton")
        self.download_btn.setToolTip("Letöltés Excel")
        self.download_btn.setIcon(AdminStorageContent.icon("download.svg"))
        self.download_btn.setIconSize(QSize(25, 25))
        self.download_btn.clicked.connect(self.__download_excel)
        
        search_layout = QHBoxLayout()
        search_layout.addWidget(self.search_input, 1)
        search_layout.addWidget(self.dropdown_select_storage, 1)
        search_layout.addWidget(self.print_btn)
        search_layout.addWidget(self.download_btn)

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
       
        self.__set_content(self.storage_table)

    def __print_table(self):
        
        html_content = self.generate_html()
        
        if html_content is not None:

            export_dir = "exports"
            
            if os.path.exists(export_dir) is False:
                
                os.makedirs(export_dir)
            
            current_timestamp = datetime.now(Config.time.timezone_utc).strftime(Config.time.timestamp_format)
            
            pdf_file = os.path.join(export_dir, f"storage_list_{current_timestamp}.pdf")
            
            HTML(string = html_content).write_pdf(pdf_file)
            
            QDesktopServices.openUrl(QUrl.fromLocalFile(pdf_file))

    def __download_excel(self):
        
        if self.storage_datatable_data is None or not hasattr(self.storage_datatable_data, "items"):
            return

        current_year = datetime.now(Config.time.timezone_utc).year
        
        dialog = QInputDialog(self)
        dialog.setWindowTitle("Év kiválasztása")
        dialog.setInputMode(QInputDialog.InputMode.IntInput)
        dialog.setIntRange(2000, 2100)
        dialog.setIntValue(current_year)
        dialog.setStyleSheet(Config.styleSheets.input_dialog)
        
        accepted = dialog.exec()
        year = dialog.intValue()

        if accepted:
                
            filtered_items = []
            
            for item in self.storage_datatable_data.items:
                
                purchase_date = getattr(item, "purchase_date", None)
                
                if purchase_date is not None and hasattr(purchase_date, "year") and purchase_date.year == year:
                    
                    filtered_items.append(item)
            
            if len(filtered_items) == 0:
                return

            rows = []
            
            for idx, item in enumerate(filtered_items):
                
                price_value = getattr(item, "price", None)
                
                formatted_price = "{:,.0f}".format(price_value).replace(",", ".") if price_value is not None else "N/A"
                
                rows.append({
                    "#": idx,
                    "Megnevezés": self.datatable_helper.getAttribute(item, "name"),
                    "Gyáriszám": self.datatable_helper.getAttribute(item, "manufacture_number"),
                    "Mennyiség": str(self.datatable_helper.getAttribute(item, "quantity")),
                    "Gyártási év": self.datatable_helper.getAttributeDate(item, "manufacture_date"),
                    "Ár": formatted_price,
                    "Üzembe helyezés időpontja": self.datatable_helper.getAttributeDate(item, "commissioning_date"),
                    "Beszerzés forrása": self.datatable_helper.getAttribute(item, "purchase_source"),
                    "Beszerzés időpontja": self.datatable_helper.getAttributeDate(item, "purchase_date"),
                    "Ellenőrző felülvizsgálatok időpontja": self.datatable_helper.getAttributeDate(item, "inspection_date"),
                    "Selejtezve": "Igen" if getattr(item, "is_scrap", False) is True else "Nem" if getattr(item, "is_scrap", False) is False else "N/A",
                })
            
            df = pd.DataFrame(rows)
            
            export_dir = "exports"
            
            if os.path.exists(export_dir) == False:
                
                os.makedirs(export_dir)
            
            current_timestamp = datetime.now(Config.time.timezone_utc).strftime(Config.time.timestamp_format)
            
            xlsx_file = os.path.join(export_dir, f"konyveles_{current_timestamp}.xlsx")
            
            df.to_excel(xlsx_file, index = False)
            
            QDesktopServices.openUrl(QUrl.fromLocalFile(xlsx_file))

    def generate_html(self):
        
        header = Config.html_setup.admin_storage_content.header
        
        title = Config.html_setup.admin_storage_content.title

        date_str = datetime.now(Config.time.timezone_utc).strftime(Config.time.timeformat)
        
        date_html = f"<div style='text-align:center; font-size:10pt; margin-bottom: 15px;'>{date_str}</div>"

        if self.storage_datatable_data is not None and hasattr(self.storage_datatable_data, "items"):
            
            self.data = self.storage_datatable_data.items

            rows_per_page = 12
            
            pages = []

            filtered_data = [item for item in self.data if not isinstance(item, MaterialData)]

            for page_start in range(0, len(filtered_data), rows_per_page):
                
                chunk = filtered_data[page_start:page_start + rows_per_page]

                table_rows = ""
                
                for idx, item in enumerate(chunk, page_start + 1):
                    
                    price_value = getattr(item, "price", None)
                    
                    formatted_price = "{:,.0f}".format(price_value).replace(",", ".") if price_value is not None else "N/A"
                    
                    table_rows += f"""
                    <tr>
                        <td>{idx}</td>
                        <td>{self.datatable_helper.getAttribute(item, "name")}</td>
                        <td>{self.datatable_helper.getAttribute(item, "manufacture_number")}</td>
                        <td>{str(self.datatable_helper.getAttribute(item, "quantity"))}</td>
                        <td>{self.datatable_helper.getAttributeDate(item, "manufacture_date")}</td>
                        <td>{formatted_price}</td>
                        <td>{self.datatable_helper.getAttributeDate(item, "commissioning_date")}</td>
                        <td>{self.datatable_helper.getAttribute(item, "purchase_source")}</td>
                        <td>{self.datatable_helper.getAttributeDate(item, "purchase_date")}</td>
                        <td>{self.datatable_helper.getAttributeDate(item, "inspection_date")}</td>
                        <td>{"Yes" if getattr(item, "is_scrap", False) is True else "No" \
                            if getattr(item, "is_scrap", False) is False else "N/A"}</td>
                    </tr>
                    """

                page_html = f"""
                <div style='page-break-after: always;'>
                    {header}
                    {title}
                    {date_html}
                    <table>
                        <thead>
                            <tr>
                                <th>#</th>
                                <th>Name</th>
                                <th>Serial number</th>
                                <th>Quantity</th>
                                <th>Manufacturing year</th>
                                <th>Price</th>
                                <th>Commissioning date</th>
                                <th>Purchase source</th>
                                <th>Purchase date</th>
                                <th>Inspection dates</th>
                                <th>Scrapezve</th>
                            </tr>
                        </thead>
                        <tbody>
                            {table_rows}
                        </tbody>
                    </table>
                </div>
                """

                pages.append(page_html)

            full_html = f"""
            <html>
            <head>
            <style>
                body {{ margin: 1.5cm; font-family: Priceial, sans-serif; }}
                table {{ width: 100%; border-collapse: collapse; font-size: 10pt; }}
                th, td {{ border: 1px solid black; padding: 4px; text-align: center; word-wrap: break-word; }}
                th {{ background-color: #cccccc; }}
                @page {{ size: A4 landscape; margin: 0.5cm; }}
            </style>
            </head>
            <body>
                {''.join(pages)}
            </body>
            </html>
            """

            return full_html

    def on_dropdown_data_loaded(self, cache_data: StorageCacheData):
        
        self.dropdown_select_storage.clear()
        
        if cache_data is not None and hasattr(cache_data, "items"):
            
            self.dropdown_select_storage.addItem("")
            
            for storage_data in cache_data.items:
                
                formatted_str = f"Name: | {storage_data.name} | Location: | {storage_data.location} |"
          
                self.dropdown_select_storage.addItem(formatted_str, storage_data.id)
            
    def on_table_data_loaded(self, cache_data: AdminStorageItemsCacheData):
      
        if cache_data is not None and hasattr(cache_data, "items"):
            
            self.results_table.load_data(cache_data)
    
    def _emit_cache_data_safe(self,
        target: str,
        item: t.Union[
            AdminStorageItemsCacheData,
            StorageCacheData
        ]):
        
        if target == "dropdown":
            
            QTimer.singleShot(0, lambda: self.dropdown_data_loaded.emit(item))
            
        elif target == "table":
            
            QTimer.singleShot(0, lambda: self.table_data_loaded.emit(item))
    
    async def load_cache_data(self, target: str, cache_id: str, exp: int):
        
        if target == "dropdown" and isinstance(self.dropdown_select_storage, QComboBox):
            
            storage_cache_data = await self.storage_cache.get_storage_data_from_cache(
                storage_cache_id = cache_id,
                exp = exp
            )
            
            self.storage_cache_data = storage_cache_data
     
            self._emit_cache_data_safe( 
                target = target,
                item = storage_cache_data
            )
            
        elif target == "table" and isinstance(self.results_table, StorageTable):
            
            self.storage_datatable_data = await self.storage_datatable_cache.get_storage_datatable_data_from_cache(
                storage_cache_id = cache_id,
                exp = exp
            )
            
            self._emit_cache_data_safe(
                target = target, 
                item = self.storage_datatable_data
            )
                  
    @asyncSlot()
    async def _handle_action(self, sender: t.Optional[t.Union[QPushButton, QComboBox]]):
      
        if isinstance(sender, QPushButton):
            
            if sender is self.add_btn:
                
                accepted = await self.add_storage_modal.exec_async()

                if accepted:
                    
                    data = self.add_storage_modal.get_form_data()
                    
                    confirm_text = (
                        f"You are recording the following item:\n\n"
                        f"Name:\n{data.name}\n\n"
                        f"Telephely:\n{data.location}"
                        "\nBiztosan folytatod?"
                    )
                    
                    self.confirm_action_modal.set_action_message(confirm_text)
                    
                    confirm = await self.confirm_action_modal.exec_async()

                    if not confirm:
                    
                        return
                    
                    elif confirm:
                    
                        await self.__handle_add_data(
                            data = data,
                            sender = sender
                        )
                
            elif sender is self.edit_btn:
                
                pass
        
        elif isinstance(sender, QComboBox):
            
            if sender is self.dropdown_select_storage:
                
                if isinstance(self.results_table, StorageTable):
                        
                    storage_id_filter = self.dropdown_select_storage.currentData()
                    
                    if storage_id_filter is None:
                        
                        self.log.debug("No storage ID filter selected, skipping filtering")
                        
                        self.results_table.load_data(self.storage_datatable_data)
                        
                        return
                    
                    filtered_data = []
                    
                    if self.storage_datatable_data is not None:
                        
                        for storage_datatable_item in self.storage_datatable_data.items:
                            
                            if storage_id_filter is not None and storage_datatable_item.storage_id == storage_id_filter:
                                
                                filtered_data.append(storage_datatable_item)
                                
                        if len(filtered_data) > 0:
                            
                            filtered_cache = AdminStorageItemsCacheData(items = filtered_data)
                            
                            self.log.debug("Filtered storage data: %s" % str(filtered_cache))
                            
                            self.results_table.load_data(filtered_cache)
                            
                        else: 
                            
                            self.log.info("No storage items matched the selected storage ID filter")
                            
                            self.results_table.load_data(self.storage_datatable_data)
                            
    async def __handle_add_data(self, data: StorageData, sender: QPushButton):
        
        if isinstance(sender, QPushButton):
            
            if isinstance(data, StorageData):
                    
                try:
                    
                    async with self._admin_storage_lock:
                        
                        await queries.insert_storage_data(
                            name = data.name,
                            location = data.location
                        )

                    await self.storage_cache.clear_cache(Config.redis.cache.storage.id)
                    
                    await self.storage_datatable_cache.clear_cache(Config.redis.cache.storage_items.id)
                    
                    await self.load_cache_data(
                        target = Config.redis.cache.storage.target,
                        cache_id = Config.redis.cache.storage.id, 
                        exp = Config.redis.cache.storage.exp
                    )
                    
                    await self.load_cache_data(
                        target = Config.redis.cache.storage_items.target,
                        cache_id = Config.redis.cache.storage_items.id, 
                        exp = Config.redis.cache.storage_items.exp
                    )

                    self.error_labels[sender].setVisible(False)
                    
                    self.log.info("Dropdown and datatable refreshed after insert")

                except Exception as e:
                    
                    self.error_labels[sender].setText("Failed to save the data")
                    self.error_labels[sender].setVisible(True)
                    
                    self.log.exception("Failed to insert storage data: %s" % str(e))
                    
                finally:
                    
                    self.spinner.hide()
          
    def _handle_search_input(self, text: str):
        
        if isinstance(self.results_table, StorageTable):
            
            text_lower = text.strip().lower()
            
            if not text_lower:
            
                self.results_table.load_data(self.storage_datatable_data)
                
                return

            filtered_data = []
            
            for item in self.storage_datatable_data.items:
                
                if item is None:
                    
                    continue
                
                if isinstance(item, MaterialData):
                    
                    if ((item.name and text_lower in item.name.lower()) or
                        (item.manufacture_number and text_lower in item.manufacture_number.lower()) or
                        (item.unit and text_lower in item.unit.lower()) or
                        (item.purchase_source and text_lower in item.purchase_source.lower()) or
                        (item.price is not None and text_lower in str(item.price)) or
                        (item.quantity is not None and text_lower in str(item.quantity)) or
                        (item.manufacture_date and text_lower in item.manufacture_date.isoformat().lower()) or
                        (item.inspection_date and text_lower in item.inspection_date.isoformat().lower())
                        ):
                        
                        filtered_data.append(item)

                elif isinstance(item, DeviceData):
                    
                    if ((item.name and text_lower in item.name.lower()) or
                        (item.manufacture_number and text_lower in item.manufacture_number.lower()) or
                        (item.purchase_source and text_lower in item.purchase_source.lower()) or
                        (item.price is not None and text_lower in str(item.price)) or
                        (item.quantity is not None and text_lower in str(item.quantity)) or
                        (item.is_scrap is not None and text_lower in ("igen" if item.is_scrap else "nem")) or
                        (item.manufacture_date and text_lower in item.manufacture_date.isoformat().lower()) or
                        (item.commissioning_date and text_lower in item.commissioning_date.isoformat().lower()) or
                        (item.inspection_date and text_lower in item.inspection_date.isoformat().lower())
                        ):
                        
                        filtered_data.append(item)

                elif isinstance(item, ToolsData):
                    
                    if ((item.name and text_lower in item.name.lower()) or
                        (item.manufacture_number and text_lower in item.manufacture_number.lower()) or
                        (item.purchase_source and text_lower in item.purchase_source.lower()) or
                        (item.price is not None and text_lower in str(item.price)) or
                        (item.quantity is not None and text_lower in str(item.quantity)) or
                        (item.returned is not None and text_lower in ("igen" if item.returned else "nem")) or
                        (item.is_scrap is not None and text_lower in ("igen" if item.is_scrap else "nem")) or
                        (item.manufacture_date and text_lower in item.manufacture_date.isoformat().lower()) or
                        (item.commissioning_date and text_lower in item.commissioning_date.isoformat().lower()) or
                        (item.inspection_date and text_lower in item.inspection_date.isoformat().lower())
                        ):
                        
                        filtered_data.append(item)
            
            filtered_cache = AdminStorageItemsCacheData(items = filtered_data)
            
            self.log.debug("Filtered storage data: %s" % str(filtered_cache))
            
            self.results_table.load_data(filtered_cache)        
            
    def __set_content(self, new_view: QWidget):
        
        index = self.stack.indexOf(new_view)
        
        if index == -1:
            
            self.stack.addWidget(new_view)
            
            index = self.stack.indexOf(new_view)

        self.stack.setCurrentIndex(index)
        
        self.results_table = new_view
    

