import os
from qasync import asyncSlot
import asyncio
import typing as t
import logging
from datetime import datetime
import base64
from weasyprint import HTML
from collections import defaultdict

from PyQt6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QPushButton,
    QLineEdit,
    QFrame,
    QLineEdit,
    QStackedWidget,
    QLabel,
    QTabBar, 
    QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal, QUrl, QTimer
from PyQt6.QtGui import QIcon, QDesktopServices

from config import Config
from utils.logger import LoggerMixin
from .tables.material import MaterialsTable
from .tables.tools import ToolsTable
from .tables.device import DevicesTable
from .tables.returnable_packaging import ReturnablePackagingTable
from services.material_datatable_cache import MaterialCacheService
from services.devices_datatable_cache import DevicesCacheService
from services.tools_datatable_cache import ToolsCacheService
from services.returnable_packaging_cache import ReturnablePackagingCacheService
from utils.dc.material import MaterialData, MaterialCacheData
from utils.dc.tools import ToolsData, ToolsCacheData
from utils.dc.device import DeviceData, DeviceCacheData
from utils.dc.returnable_packaging import ReturnablePackagingCacheData, ReturnablePackagingData
from utils.dc.tenant_data import TenantData
from utils.dc.admin.storage import StorageCacheData, StorageData
from utils.dc.selected_works import SelectedWorkData
from .modal.storage.add_material import AddMaterialModal
from .modal.storage.edit_material import EditMaterialModal
from .modal.storage.add_work_items import AddWorkItemsModal
from .modal.storage.add_tools import AddToolsModal
from .modal.storage.edit_tools import EditToolsModal
from .modal.storage.add_devices import AddDevicesModal
from .modal.storage.edit_devices import EditDevicesModal
from .modal.storage.add_returnable_packaging import AddReturnablePackagingModal
from .modal.storage.edit_returnable_packaging import EditReturnablePackagingModal
from .modal.confirm_action import ConfirmActionModal
from .modal.storage.add_lease import AddLeaseModal
from .modal.storage.send_back import SendBackModal
from exceptions import ItemCannotBeDeletedWhileRentedError
from utils.enums.storage_item_type_enum import StorageItemTypeEnum

from db import queries

if t.TYPE_CHECKING:
    
    from .main_window import MainWindow

class StorageView(QWidget, LoggerMixin):
    
    log: logging.Logger

    data_loaded = pyqtSignal(object)
    
    def __init__(self,
        main_window: 'MainWindow'
        ):

        super().__init__()

        self.main_window = main_window
        
        self.utility_calculator = main_window.app.utility_calculator
        
        self.datatable_helper = main_window.app.datatable_helper
        
        self.spinner = main_window.app.spinner
  
        self.admin_view = self.main_window.get_admin_view()
        
        self.storage_content = self.admin_view.get_admin_storage_content()
        
        self.storage_content.dropdown_data_loaded.connect(self.on_cache_data_loaded)
        
        self.emit_result_list = None

        self.storage_lock = asyncio.Lock()
        
        self.current_time = datetime.now(Config.time.timezone_utc)
        
        self.reminder_worker = main_window.reminder_worker
        
        self.material_cache_service = MaterialCacheService(main_window.redis_client)
        
        self.tools_cache_service = ToolsCacheService(main_window.redis_client)
        
        self.devices_cache_service = DevicesCacheService(main_window.redis_client)
        
        self.returnable_cache_service = ReturnablePackagingCacheService(main_window.redis_client)
        
        self.confirm_action_modal = ConfirmActionModal(self)

        self.materials_table = MaterialsTable()
        
        self.tools_table = ToolsTable()
        
        self.devices_table = DevicesTable()
        
        self.returnable_table = ReturnablePackagingTable()
        
        self.work_add_modal = AddWorkItemsModal(self)
        
        self.add_modal = AddMaterialModal(self)
        
        self.edit_modal = EditMaterialModal(self)
        
        self.add_tools_modal = AddToolsModal(self)
        
        self.edit_tools_modal = EditToolsModal(self)
        
        self.add_devices_modal = AddDevicesModal(self)
        
        self.edit_devices_modal = EditDevicesModal(self)
        
        self.add_returnable_packaging_modal = AddReturnablePackagingModal(self)
        
        self.edit_returnable_packaging_modal = EditReturnablePackagingModal(self)
        
        self.lease_modal = AddLeaseModal(self)
        
        self.send_back_modal = SendBackModal(self)
        
        self.results_table = None
        
        self.error_labels = {}

        self.__init_view()
        
        self.data_loaded.connect(self.on_data_loaded)

    @staticmethod
    def icon(name: str) -> QIcon:
        
        return QIcon(os.path.join(Config.icon.icon_dir, name))

    def __init_view(self):
        
        main_layout = QHBoxLayout(self)
    
        # Side menu
        self.menu_buttons = {
            "add_btn": QPushButton("Add to inventory"),
            "edit_btn": QPushButton("Edit inventory"),
            "add_work_btn": QPushButton("Add to work"),
            "qr_print_btn": QPushButton("Print QR code"),
            "delete_item_btn": QPushButton("Remove item")
        }    
        
        menu_layout = QVBoxLayout()
        menu_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        menu_layout.setContentsMargins(0, 0, 0, 0)    
        
        self.error_label = QLabel()
        self.error_label.setObjectName("error")
        self.error_label.setVisible(False) 
        self.error_label.setMaximumWidth(380)

        self.add_btn = self.menu_buttons["add_btn"]
        self.edit_btn = self.menu_buttons["edit_btn"]
        self.work_add_btn = self.menu_buttons["add_work_btn"]
        self.qr_code_btn = self.menu_buttons["qr_print_btn"]
        self.delete_item_btn = self.menu_buttons["delete_item_btn"]
        
        for key, button in self.menu_buttons.items():

            button.setFixedWidth(200)
            button.setFixedHeight(50)
            button.setCursor(Qt.CursorShape.PointingHandCursor)

            if key == "add_btn":
                
                button.setObjectName("AddStockBtn")
                
            elif key == "edit_btn":
                
                button.setObjectName("ModifyStockBtn")
                
            elif key == "add_work_btn":
                
                button.setObjectName("ModifyWorkBtn")
            
            elif key == "qr_print_btn":
                
                button.setObjectName("QRPrintBtn")
            
            elif key == "delete_item_btn":
                
                button.setObjectName("ModifyWorkBtn")
                
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
            
            button.clicked.connect(lambda _, b = button: self._handle_menu_click(b))
            
        menu_widget = QFrame()
        menu_widget.setLayout(menu_layout)
        menu_widget.setFixedWidth(200)
        
        main_layout.addWidget(menu_widget)
        
        # Content area
        widget = QWidget()
    
        right_panel = QVBoxLayout()
        right_panel.setContentsMargins(0, 0, 0, 0)
        
        self.tab_bar = QTabBar()
        self.tab_bar.setExpanding(False)
        self.tab_bar.setCursor(Qt.CursorShape.PointingHandCursor)
        self.tab_bar.setShape(QTabBar.Shape.RoundedNorth)
        self.tab_bar.setElideMode(Qt.TextElideMode.ElideNone) 
        self.tab_bar.setFixedHeight(50)
        self.tab_bar.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        self.tab_bar.addTab("Anyagok")      
        self.tab_bar.addTab("Tools")     
        self.tab_bar.addTab("Devices")
        self.tab_bar.addTab("Returnable packaging") 
        self.tab_bar.setCurrentIndex(0) 
        self.tab_bar.currentChanged.connect(lambda _, tb = self.tab_bar: self._handle_menu_click(tb))

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search...")
        self.search_input.setObjectName("WarehouseSearchInput")
        self.search_input.textChanged.connect(self._handle_search_input)

        self.search_input_2 = QLineEdit()
        self.search_input_2.setPlaceholderText("Unit search...")
        self.search_input_2.setObjectName("WarehouseSearchInput")
        self.search_input_2.textChanged.connect(self._handle_size_search_input)

        search_layout = QHBoxLayout()
        search_layout.addWidget(self.tab_bar)
        search_layout.addWidget(self.search_input)
        search_layout.addWidget(self.search_input_2)
        
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
        
        self.__set_content(self.materials_table)
        
        self.results_table = self.materials_table

    def _emit_cache_data_safe(self, 
        item: t.Union[
            MaterialCacheData,
            ToolsCacheData,
            DeviceCacheData,
            ReturnablePackagingCacheData
        ]):
        
        QTimer.singleShot(0, lambda: self.data_loaded.emit(item))
    
    def _handle_size_search_input(self, text: str):
        
        if isinstance(self.results_table, MaterialsTable):
        
            text = text.strip().lower()
            
            if not text:
            
                self.results_table.load_data(self.cache_data)
                
                return
            
            filtered_data = []
            
            for item in self.cache_data.items:
                
                if isinstance(item, MaterialData):
                    
                    if item.unit and text in item.unit.lower():
                        
                        filtered_data.append(item)
                        
            filtered_cache = MaterialCacheData(items = filtered_data)

            self.log.debug("Filtered unit data: %s" % str(filtered_cache))
            
            self.results_table.load_data(filtered_cache)
        
        elif isinstance(self.results_table, ToolsTable):
            
            text = text.strip().lower()
            
            if not text:
            
                self.results_table.load_data(self.cache_data)
                
                return
            
            filtered_data = []
            
            for item in self.cache_data.items:
                
                if isinstance(item, ToolsData):
                    
                    if item.manufacture_number and text in item.manufacture_number.lower():
                        
                        filtered_data.append(item)
                        
            filtered_cache = ToolsCacheData(items = filtered_data)

            self.log.debug("Filtered manufacture_number data: %s" % str(filtered_cache))
            
            self.results_table.load_data(filtered_cache)
            
        elif isinstance(self.results_table, DevicesTable):
            
            text = text.strip().lower()
            
            if not text:
            
                self.results_table.load_data(self.cache_data)
                
                return
            
            filtered_data = []
            
            for item in self.cache_data.items:
                
                if isinstance(item, DeviceData):
                    
                    if item.manufacture_number and text in item.manufacture_number.lower():
                        
                        filtered_data.append(item)
                        
            filtered_cache = DeviceCacheData(items = filtered_data)

            self.log.debug("Filtered manufacture_number data: %s" % str(filtered_cache))
            
            self.results_table.load_data(filtered_cache)
            
        elif isinstance(self.results_table, ReturnablePackagingTable):
            
            text = text.strip().lower()
            
            if not text:
            
                self.results_table.load_data(self.cache_data)
                
                return
            
            filtered_data = []
            
            for item in self.cache_data.items:
                
                if isinstance(item, ReturnablePackagingData):
                    
                    if item.manufacture_number and text in item.manufacture_number.lower():
                        
                        filtered_data.append(item)
                        
            filtered_cache = ReturnablePackagingCacheData(items = filtered_data)

            self.log.debug("Filtered manufacture_number data: %s" % str(filtered_cache))
            
            self.results_table.load_data(filtered_cache)
            
    def _handle_search_input(self, text: str):
        
        if isinstance(self.results_table, MaterialsTable):
            
            text = text.strip().lower()

            if not text:
            
                self.results_table.load_data(self.cache_data)
                
                return

            filtered_data = []

            for item in self.cache_data.items:
                
                if isinstance(item, MaterialData):
                    
                    if ((item.name and text in item.name.lower()) or
                        (item.quantity is not None and text in f"{item.quantity:.4f}") or
                        (item.unit and text in item.unit.lower()) or
                        (item.price is not None and text in f"{item.price:.2f}")
                        ):
                        
                        filtered_data.append(item)

            filtered_cache = MaterialCacheData(items = filtered_data)

            self.log.debug("Filtered material data: %s" % str(filtered_cache))
            
            self.results_table.load_data(filtered_cache)
            
        elif isinstance(self.results_table, ToolsTable):
            
            text = text.strip().lower()

            if not text:
            
                self.results_table.load_data(self.cache_data)
                
                return

            filtered_data = []

            for item in self.cache_data.items:
                
                if isinstance(item, ToolsData):
                    
                    if (
                        (item.name and text in item.name.lower()) or
                        (item.manufacture_number and text in item.manufacture_number.lower()) or
                        (item.price is not None and text in f"{item.price:.2f}") or
                        (item.quantity is not None and text in f"{item.quantity:.4f}") or
                        (item.is_scrap is not None and text in ("igen" if item.is_scrap else "nem"))
                        ):
                        
                        filtered_data.append(item)

            filtered_cache = ToolsCacheData(items = filtered_data)

            self.log.debug("Filtered tools data: %s" % str(filtered_cache))
            
            self.results_table.load_data(filtered_cache)

        elif isinstance(self.results_table, DevicesTable):
            
            text = text.strip().lower()

            if not text:
            
                self.results_table.load_data(self.cache_data)
                
                return

            filtered_data = []

            for item in self.cache_data.items:
                
                if isinstance(item, DeviceData):
                    
                    if (
                        (item.name and text in item.name.lower()) or
                        (item.manufacture_number and text in item.manufacture_number.lower()) or
                        (item.price is not None and text in f"{item.price:.2f}") or 
                        (item.quantity is not None and text in f"{item.quantity:.4f}") or
                        (item.is_scrap is not None and text in ("igen" if item.is_scrap else "nem"))
                        ):
                        
                        filtered_data.append(item)

            filtered_cache = DeviceCacheData(items = filtered_data)

            self.log.debug("Filtered device data: %s" % str(filtered_cache))
            
            self.results_table.load_data(filtered_cache)
            
        elif isinstance(self.results_table, ReturnablePackagingTable):
            
            text = text.strip().lower()

            if not text:
            
                self.results_table.load_data(self.cache_data)
                
                return

            filtered_data = []

            for item in self.cache_data.items:
                
                if isinstance(item, ReturnablePackagingData):
                    
                    if (
                        (item.name and text in item.name.lower()) or
                        (item.manufacture_number and text in item.manufacture_number.lower()) or
                        (item.price is not None and text in f"{item.price:.2f}") or 
                        (item.quantity is not None and text in f"{item.quantity:.4f}") or
                        (item.is_returned is not None and text in ("igen" if item.is_returned else "nem"))
                        ):
                        
                        filtered_data.append(item)

            filtered_cache = ReturnablePackagingCacheData(items = filtered_data)

            self.log.debug("Filtered device data: %s" % str(filtered_cache))
            
            self.results_table.load_data(filtered_cache)

    async def _handle_material_btns(self, sender: QPushButton):
        
        self.log.info("Results table is MaterialsTable - handling button: %s" % sender.text())
        
        if sender is self.add_btn:
            
            self.log.debug("Add button clicked in Material tab")
            
            if self.emit_result_list is not None:
                
                self.add_modal.update_dropdown_items(self.emit_result_list)
                    
                accepted = await self.add_modal.exec_async()

                if accepted:
                    
                    data = await self.add_modal.get_form_data()
                    
                    confirm_text = (
                        f"You are recording the following item:\n\n"
                        f"Storage:\n{data.storage_id}\n\n"
                        f"Name:\n{data.name}\n\n"
                        f"Serial number:\n{data.manufacture_number}\n\n"
                        f"Quantity:\n{data.quantity:.4f}\n\n"
                        f"Unit:\n{data.unit}\n\n"
                        f"Manufacturing year:\n{data.manufacture_date.strftime(Config.time.timeformat)}\n\n"
                        f"Net unit price:\n{data.price:,.2f}".replace(",", ".") + " HUF\n\n"
                        f"Purchase source:\n{data.purchase_source}\n\n"
                        f"Purchase date:\n{data.purchase_date.strftime(Config.time.timeformat)}\n\n"
                        f"Inspection dates:\n{data.inspection_date.strftime(Config.time.timeformat)}\n"
                        "Biztosan folytatod?"
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
            
            self.log.debug("Edit button clicked in Material tab")
            
            selected_data = self.materials_table.get_selected_cache_data()
            
            if not selected_data:
                
                self.log.warning("No item selected for editing")
                
                self.error_labels[sender].setText("Select an item to edit")
                self.error_labels[sender].setVisible(True)
                                
                return

            if len(selected_data) > 1:
                
                self.log.warning("Multiple items selected. Only one item can be edited at a time")
                
                self.error_labels[sender].setText("Select only one item at a time")
                self.error_labels[sender].setVisible(True)
                
                return

            previous_material: MaterialData = selected_data[0]

            if self.emit_result_list is not None:
            
                self.edit_modal.update_parameters_from_previous_reference(
                    previous_data = previous_material,
                    emit_result_list = self.emit_result_list
                )
                
                accepted = await self.edit_modal.exec_async()  
                
                if accepted:
                    
                    to_data = self.edit_modal.get_form_data()

                    name_line = f"{str(previous_material.name) if previous_material.name is not None else 'N/A'} --> " \
                        f"{str(to_data.name) if to_data.name is not None else 'N/A'}"

                    quantity_line = f"{previous_material.quantity:.4f} --> {to_data.quantity:.4f}" \
                        if to_data.quantity != 1e-4 else "N/A"
                    
                    unit_line = f"{str(previous_material.unit) if previous_material.unit is not None else 'N/A'} --> " \
                        f"{str(to_data.unit) if to_data.unit is not None else 'N/A'}"

                    price_line = f"{previous_material.price:,.2f}".replace(",", ".") + " HUF --> " + (f"{to_data.price:,.2f}".replace(",", ".") + " HUF" \
                        if to_data.price != 1e-2 else "N/A"
                    )

                    storage_line = f"{str(previous_material.storage_id) if previous_material.storage_id is not None else 'N/A'} --> " \
                        f"{str(to_data.storage_id) if to_data.storage_id is not None else 'N/A'}"

                    manufacture_number_line = f"{str(previous_material.manufacture_number) if previous_material.manufacture_number is not None else 'N/A'} --> " \
                        f"{str(to_data.manufacture_number) if to_data.manufacture_number is not None else 'N/A'}"

                    manufacture_date_line = f"{previous_material.manufacture_date.strftime(Config.time.timeformat) if previous_material.manufacture_date is not None else 'N/A'} --> " \
                        f"{to_data.manufacture_date.strftime(Config.time.timeformat) if to_data.manufacture_date is not None else 'N/A'}"

                    purchase_source_line = f"{str(previous_material.purchase_source) if previous_material.purchase_source is not None else 'N/A'} --> " \
                        f"{str(to_data.purchase_source) if to_data.purchase_source is not None else 'N/A'}"

                    purchase_date_line = f"{previous_material.purchase_date.strftime(Config.time.timeformat) if previous_material.purchase_date is not None else 'N/A'} --> " \
                        f"{to_data.purchase_date.strftime(Config.time.timeformat) if to_data.purchase_date is not None else 'N/A'}"
                    
                    inspection_date_line = (
                        f"{previous_material.inspection_date.strftime(Config.time.timeformat) if previous_material.inspection_date is not None else 'N/A'} --> "
                        f"{to_data.inspection_date.strftime(Config.time.timeformat) if to_data.inspection_date is not None else 'N/A'}"
                    )
                    
                    confirm_text = f"""
                    <br>You are modifying the following data:<br><br>
                    Name: {name_line}<br>
                    Quantity: {quantity_line}<br>
                    Unit: {unit_line}<br>
                    Net unit price: {price_line}<br>
                    Storage: {storage_line}<br>
                    Type / Serial number: {manufacture_number_line}<br>
                    Manufacturing year: {manufacture_date_line}<br>
                    Beszerezve: {purchase_source_line}<br>
                    Purchase date: {purchase_date_line}<br>
                    Inspection: {inspection_date_line}<br><br>
                    Biztosan folytatod?<br>
                    """
    
                    self.confirm_action_modal.set_action_message(f"<div align='center'>{confirm_text}</div>")
                    
                    confirm = await self.confirm_action_modal.exec_async()
                    
                    if not confirm:
                        
                        return
                    
                    elif confirm:
                        
                        await self.__handle_edit_data(
                            to_data = to_data,
                            from_data = previous_material,
                            sender = sender
                        )
                
        elif sender is self.work_add_btn:
            
            self.log.debug("Add to work button clicked in Material tab")
            
            selected_work_items = self.materials_table.get_selected_cache_data()
            
            if not selected_work_items:
                
                self.log.warning("No item selected for adding")
                
                self.error_labels[sender].setText("Select items to add")
                self.error_labels[sender].setVisible(True)
            
                return       
            
            works_query_result = await queries.select_all_works()

            if len(works_query_result) > 0:
            
                list_works = [
                    SelectedWorkData(
                        id = work.id,
                        boat_id = work.boat_id,
                        description = work.description,
                        start_date = work.start_date,
                        finished_date = work.finished_date,
                        transfered = work.transfered,
                        is_contractor = work.is_contractor,
                        img = work.img,
                        boat_name = work.boat_name,
                    ) for work in works_query_result 
                ]
                
                self.work_add_modal.set_works(list_works)
                
                accepted = await self.work_add_modal.exec_async()

                if accepted:
                        
                    if len(selected_work_items) > 0:
                        
                        selected_work = self.work_add_modal.get_selected_works()
                    
                        await self.__handle_add_accessories(
                            selected_work = selected_work,
                            selected_work_items = selected_work_items,
                            sender = sender                        
                        )
            
            if works_query_result == []:
                
                self.log.warning("Work table is empty, please insert data first")

                self.error_labels[sender].setText("No work found, add data first")
                self.error_labels[sender].setVisible(True)
        
        elif sender is self.qr_code_btn:
            
            self.log.debug("QR code button clicked in Material tab")
            
            selected_items = self.materials_table.get_selected_cache_data()
            
            if not selected_items:
                
                self.log.warning("No item selected for printing")
                
                self.error_labels[sender].setText("Select items to print")
                self.error_labels[sender].setVisible(True)
            
                return       
                
            html_content = self.generate_html(selected_items)
                
            self.__print_table(html_content)
            
        elif sender is self.delete_item_btn:
            
            selected_items = self.materials_table.get_selected_cache_data()
            
            if not selected_items:
                
                self.log.warning("No item selected for deleting")
                
                self.error_labels[sender].setText("Select items to delete")
                self.error_labels[sender].setVisible(True)
            
                return   
            
            await self.__handle_delete_item(
                selected_items = selected_items,
                sender = sender
            )

    async def _handle_tool_btns(self, sender: QPushButton):
        
        self.log.info("Results table is ToolsTable - handling button: %s", sender.text())
        
        if sender is self.add_btn:
            
            self.log.debug("Add button clicked in Tools tab")
            
            if self.emit_result_list is not None:
                
                self.add_tools_modal.update_dropdown_items(self.emit_result_list)
                    
                accepted = await self.add_tools_modal.exec_async()

                if accepted:
                    
                    data = await self.add_tools_modal.get_form_data()
                    
                    confirm_text = (
                        f"You are recording the following item:\n\n"
                        f"Storage:\n{data.storage_id}\n\n"
                        f"Name:\n{data.name}\n\n"
                        f"Type / Serial number:\n{data.manufacture_number}\n\n"
                        f"Quantity:\n{data.quantity:.4f}\n\n"
                        f"Manufacturing year:\n{data.manufacture_date.strftime(Config.time.timeformat)}\n\n"
                        f"Commissioning date:\n{data.commissioning_date.strftime(Config.time.timeformat)}\n\n"
                        f"Net unit price:\n{data.price:,.2f}".replace(",", ".") + " HUF\n\n"
                        f"Purchase source:\n{data.purchase_source}\n\n"
                        f"Purchase date:\n{data.purchase_date.strftime(Config.time.timeformat)}\n\n"
                        f"Inspection dates:\n{data.inspection_date.strftime(Config.time.timeformat)}\n"
                        "\n\nBiztosan folytatod?"
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
            
            self.log.debug("Edit button clicked in Tools tab")
            
            selected_data = self.tools_table.get_selected_cache_data()
            
            if not selected_data:
                
                self.log.warning("No item selected for editing")
                
                self.error_labels[sender].setText("Select an item to edit")
                self.error_labels[sender].setVisible(True)

                return

            if len(selected_data) > 1:
                
                self.log.warning("Multiple items selected. Only one item can be edited at a time")
                
                self.error_labels[sender].setText("Select only one item at a time")
                self.error_labels[sender].setVisible(True)

                return

            previous_tools: ToolsData = selected_data[0]
            
            if self.emit_result_list is not None:
                
                self.edit_tools_modal.previous_tools_data = previous_tools
                
                self.edit_tools_modal.update_parameters_from_previous_reference(
                    emit_result_list = self.emit_result_list
                )
                
                accepted = await self.edit_tools_modal.exec_async()  
                
                if accepted:
                    
                    to_data = self.edit_tools_modal.get_form_data()
                
                    name_line = f"{str(previous_tools.name) if previous_tools.name is not None else 'N/A'} --> " \
                                f"{str(to_data.name) if to_data.name is not None else 'N/A'}"

                    quantity_line = f"{previous_tools.quantity:.4f} --> {to_data.quantity:.4f}" \
                        if to_data.quantity != 1e-4 else "N/A"

                    storage_line = f"{str(previous_tools.storage_id) if previous_tools.storage_id is not None else 'N/A'} --> " \
                                f"{str(to_data.storage_id) if to_data.storage_id is not None else 'N/A'}"

                    manufacture_number_line = f"{str(previous_tools.manufacture_number) if previous_tools.manufacture_number is not None else 'N/A'} --> " \
                                            f"{str(to_data.manufacture_number) if to_data.manufacture_number is not None else 'N/A'}"

                    manufacture_date_line = f"{previous_tools.manufacture_date.strftime(Config.time.timeformat) if previous_tools.manufacture_date is not None else 'N/A'} --> " \
                                            f"{to_data.manufacture_date.strftime(Config.time.timeformat) if to_data.manufacture_date is not None else 'N/A'}"

                    commissioning_date_line = f"{previous_tools.commissioning_date.strftime(Config.time.timeformat) if previous_tools.commissioning_date is not None else 'N/A'} --> " \
                                            f"{to_data.commissioning_date.strftime(Config.time.timeformat) if to_data.commissioning_date is not None else 'N/A'}"

                    price_line = (f"{previous_tools.price:,.2f}".replace(",", ".") + " HUF" if previous_tools.price is not None else "N/A") + " --> " + \
                                (f"{to_data.price:,.2f}".replace(",", ".") + " HUF" if to_data.price is not None else "N/A")

                    purchase_source_line = f"{str(previous_tools.purchase_source) if previous_tools.purchase_source is not None else 'N/A'} --> " \
                                        f"{str(to_data.purchase_source) if to_data.purchase_source is not None else 'N/A'}"

                    purchase_date_line = f"{previous_tools.purchase_date.strftime(Config.time.timeformat) if previous_tools.purchase_date is not None else 'N/A'} --> " \
                                        f"{to_data.purchase_date.strftime(Config.time.timeformat) if to_data.purchase_date is not None else 'N/A'}"

                    inspection_date_line = f"{previous_tools.inspection_date.strftime(Config.time.timeformat) if previous_tools.inspection_date is not None else 'N/A'} --> " \
                                        f"{to_data.inspection_date.strftime(Config.time.timeformat) if to_data.inspection_date is not None else 'N/A'}"

                    is_scrap_line = f"{'Yes' if previous_tools.is_scrap else 'No' if previous_tools.is_scrap == False else 'N/A'} --> " \
                                    f"{'Yes' if to_data.is_scrap else 'No' if to_data.is_scrap == False else 'N/A'}"

                    confirm_text = f"""
                    <br>You are modifying the following data:<br><br>
                    Name: {name_line}<br>
                    Quantity: {quantity_line}<br>
                    Storage: {storage_line}<br>
                    Type / Serial number: {manufacture_number_line}<br>
                    Manufacturing year: {manufacture_date_line}<br>
                    Commissioning: {commissioning_date_line}<br>
                    Net unit price: {price_line}<br>
                    Beszerezve: {purchase_source_line}<br>
                    Purchase date: {purchase_date_line}<br>
                    Inspection: {inspection_date_line}<br>
                    Scrap: {is_scrap_line}<br><br>
                    Biztosan folytatod?<br>
                    """

                    self.confirm_action_modal.set_action_message(f"<div align='center'>{confirm_text}</div>")
                    
                    confirm = await self.confirm_action_modal.exec_async()
                    
                    if not confirm:

                        return
                    
                    elif confirm:
                        
                        await self.__handle_edit_data(
                            to_data = to_data,
                            from_data = previous_tools,
                            sender = sender
                        )
        
        elif sender is self.work_add_btn:
            
            self.log.debug("Add to lease button clicked in Tools tab")
            
            selected_data = self.tools_table.get_selected_cache_data()
            
            if not selected_data:
                
                self.log.warning("No item selected for add")
                
                self.error_labels[sender].setText("Select a tool to add")
                self.error_labels[sender].setVisible(True)

                return

            if len(selected_data) > 1:
                
                self.log.warning("Multiple items selected. Only one item can be add at a time")
                
                self.error_labels[sender].setText("Select only one item at a time")
                self.error_labels[sender].setVisible(True)

                return

            selected_tools: ToolsData = selected_data[0]
            
            if selected_tools.is_scrap == True:
                
                self.log.warning("Selected tool is scrap and cannot be rented: ID = %s, Name = %s" % (
                    selected_tools.id,
                    selected_tools.name
                    )
                )
                
                self.error_labels[sender].setText("The item is scrapped!")
                self.error_labels[sender].setVisible(True)

                return

            self.lease_modal.previous_data = selected_tools
            
            self.prepare_lease_modal(selected_tools.quantity)
            
            accepted = await self.lease_modal.exec_async()
            
            if accepted:
                
                form_data = self.lease_modal.get_form_data(selected_tools)
                # print(form_data)
                
                confirm_text = (
                    "You are adding the following data:\n\n"
                    f"{form_data.quantity:.4f} DB "
                    f"{selected_tools.name if selected_tools.name != '' else 'N/A'} -->\n"
                    f"{str(form_data.tenant_name) if form_data.tenant_name is not None else 'N/A'}\n"
                    f"{form_data.rental_start.strftime(Config.time.timeformat) if form_data.rental_start is not None else 'N/A'}\n"
                    f"{form_data.rental_end.strftime(Config.time.timeformat) if form_data.rental_end is not None else 'N/A'}\n"
                    f"{(f'{form_data.rental_price:,.2f}'.replace(',', '.') + ' HUF') if form_data.rental_price is not None else 'N/A'}\n"
                    "Biztosan folytatod?"
                )
                
                self.confirm_action_modal.set_action_message(confirm_text)
                
                confirm = await self.confirm_action_modal.exec_async()
                
                if not confirm:

                    return
                
                elif confirm:
                    
                    await self.__handle_add_tenant(
                        selected_item = selected_tools,
                        form_data = form_data,
                        sender = sender
                    )

        elif sender is self.qr_code_btn:
            
            self.log.debug("QR code button clicked in Tools tab")
            
            selected_items = self.tools_table.get_selected_cache_data()
            
            if not selected_items:
                
                self.log.warning("No item selected for add")
                
                self.error_labels[sender].setText("Select items to print")
                self.error_labels[sender].setVisible(True)

                return
            
            html_content = self.generate_html(selected_items)
                
            self.__print_table(html_content)
                
        elif sender is self.delete_item_btn:
            
            selected_items = self.tools_table.get_selected_cache_data()
            
            if not selected_items:
                
                self.log.warning("No item selected for deleting")
                
                self.error_labels[sender].setText("Select items to delete")
                self.error_labels[sender].setVisible(True)
            
                return   
            
            await self.__handle_delete_item(
                selected_items = selected_items,
                sender = sender
            )

    def prepare_lease_modal(self, quantity: float):
        
        self.lease_modal.is_quantity_zero = self.utility_calculator.is_zero(quantity)
        
        self.lease_modal.utility_calculator = self.utility_calculator
        
        self.lease_modal.prepare_dropwdown_currencies(self.utility_calculator.available_currencies)
    
    async def _handle_device_btns(self, sender: QPushButton):
        
        self.log.info("Results table is DevicesTable - handling button: %s", sender.text())
        
        if sender is self.add_btn:
            
            self.log.debug("Add button clicked in Devices tab")
            
            if self.emit_result_list is not None:
                
                self.add_devices_modal.update_dropdown_items(self.emit_result_list)
                    
                accepted = await self.add_devices_modal.exec_async()

                if accepted:
                    
                    data = await self.add_devices_modal.get_form_data()
                    
                    confirm_text = (
                        f"You are recording the following item:\n\n"
                        f"Storage:\n{data.storage_id}\n\n"
                        f"Name:\n{data.name}\n\n"
                        f"Type / Serial number:\n{data.manufacture_number}\n\n"
                        f"Quantity:\n{data.quantity}\n\n"
                        f"Manufacturing year:\n{data.manufacture_date.strftime(Config.time.timeformat)}\n\n"
                        f"Commissioning date:\n{data.commissioning_date.strftime(Config.time.timeformat)}\n\n"
                        f"Net unit price:\n{data.price:,.2f}".replace(",", ".") + " HUF\n\n"
                        f"Purchase source:\n{data.purchase_source}\n\n"
                        f"Purchase date:\n{data.purchase_date.strftime(Config.time.timeformat)}\n\n"
                        f"Inspection dates:\n{data.inspection_date.strftime(Config.time.timeformat)}\n"
                        "\n\nBiztosan folytatod?"
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
            
            self.log.debug("Edit button clicked in Devices tab")
            
            selected_data = self.devices_table.get_selected_cache_data()
            
            if not selected_data:
                
                self.log.warning("No item selected for printing")
                
                self.error_labels[sender].setText("Select an item to edit")
                self.error_labels[sender].setVisible(True)

                return

            if len(selected_data) > 1:
                
                self.log.warning("Multiple items selected. Only one item can be edited at a time")
                
                self.error_labels[sender].setText("Select only one item at a time")
                self.error_labels[sender].setVisible(True)

                return

            previous_devices: DeviceData = selected_data[0]
            
            if self.emit_result_list is not None:
                
                self.edit_devices_modal.previous_devices_data = previous_devices
                
                self.edit_devices_modal.update_parameters_from_previous_reference(
                    emit_result_list = self.emit_result_list
                )
                
                accepted = await self.edit_devices_modal.exec_async()  
                
                if accepted:
                    
                    to_data = self.edit_devices_modal.get_form_data()
                
                    name_line = f"{str(previous_devices.name) if previous_devices.name is not None else 'N/A'} --> " \
                                f"{str(to_data.name) if to_data.name is not None else 'N/A'}"

                    quantity_line = f"{previous_devices.quantity:.4f} --> {to_data.quantity:.4f}" \
                        if to_data.quantity != 1e-4 else "N/A"

                    storage_line = f"{str(previous_devices.storage_id) if previous_devices.storage_id is not None else 'N/A'} --> " \
                                f"{str(to_data.storage_id) if to_data.storage_id is not None else 'N/A'}"

                    manufacture_number_line = f"{str(previous_devices.manufacture_number) if previous_devices.manufacture_number is not None else 'N/A'} --> " \
                                            f"{str(to_data.manufacture_number) if to_data.manufacture_number is not None else 'N/A'}"

                    manufacture_date_line = f"{previous_devices.manufacture_date.strftime(Config.time.timeformat) if previous_devices.manufacture_date is not None else 'N/A'} --> " \
                                            f"{to_data.manufacture_date.strftime(Config.time.timeformat) if to_data.manufacture_date is not None else 'N/A'}"

                    commissioning_date_line = f"{previous_devices.commissioning_date.strftime(Config.time.timeformat) if previous_devices.commissioning_date is not None else 'N/A'} --> " \
                                            f"{to_data.commissioning_date.strftime(Config.time.timeformat) if to_data.commissioning_date is not None else 'N/A'}"

                    price_line = (f"{previous_devices.price:,.0f}".replace(",", ".") + " HUF" if previous_devices.price is not None else "N/A") + " --> " + \
                                (f"{to_data.price:,.0f}".replace(",", ".") + " HUF" if to_data.price is not None else "N/A")

                    purchase_source_line = f"{str(previous_devices.purchase_source) if previous_devices.purchase_source is not None else 'N/A'} --> " \
                                        f"{str(to_data.purchase_source) if to_data.purchase_source is not None else 'N/A'}"

                    purchase_date_line = f"{previous_devices.purchase_date.strftime(Config.time.timeformat) if previous_devices.purchase_date is not None else 'N/A'} --> " \
                                        f"{to_data.purchase_date.strftime(Config.time.timeformat) if to_data.purchase_date is not None else 'N/A'}"

                    inspection_date_line = f"{previous_devices.inspection_date.strftime(Config.time.timeformat) if previous_devices.inspection_date is not None else 'N/A'} --> " \
                                        f"{to_data.inspection_date.strftime(Config.time.timeformat) if to_data.inspection_date is not None else 'N/A'}"

                    is_scrap_line = f"{'Yes' if previous_devices.is_scrap else 'No' if previous_devices.is_scrap == False else 'N/A'} --> " \
                                    f"{'Yes' if to_data.is_scrap else 'No' if to_data.is_scrap == False else 'N/A'}"

                    confirm_text = f"""
                    <br>You are modifying the following data:<br><br>
                    Name: {name_line}<br>
                    Quantity: {quantity_line}<br>
                    Storage: {storage_line}<br>
                    Type / Serial number: {manufacture_number_line}<br>
                    Manufacturing year: {manufacture_date_line}<br>
                    Commissioning: {commissioning_date_line}<br>
                    Net unit price: {price_line}<br>
                    Beszerezve: {purchase_source_line}<br>
                    Purchase date: {purchase_date_line}<br>
                    Inspection: {inspection_date_line}<br>
                    Scrap: {is_scrap_line}<br><br>
                    Biztosan folytatod?<br>
                    """

                    self.confirm_action_modal.set_action_message(f"<div align='center'>{confirm_text}</div>")
                    
                    confirm = await self.confirm_action_modal.exec_async()
                    
                    if not confirm:

                        return
                    
                    elif confirm:
                        
                        await self.__handle_edit_data(
                            to_data = to_data,
                            from_data = previous_devices,
                            sender = sender
                        )
        
        elif sender is self.work_add_btn:
            
            self.log.debug("Add to lease button clicked in Devices tab")
            
            selected_data = self.devices_table.get_selected_cache_data()
            
            if not selected_data:
                
                self.log.warning("No item selected for add")
                
                self.error_labels[sender].setText("Select a device to add")
                self.error_labels[sender].setVisible(True)

                return

            if len(selected_data) > 1:
                
                self.log.warning("Multiple items selected. Only one item can be add at a time")
                
                self.error_labels[sender].setText("Select only one item at a time")
                self.error_labels[sender].setVisible(True)

                return

            selected_devices: DeviceData = selected_data[0]

            if selected_devices.is_scrap == True:
                
                self.log.warning("Selected device is scrap and cannot be rented: ID = %s, Name = %s" % (
                    selected_devices.id,
                    selected_devices.name
                    )
                )
                
                self.error_labels[sender].setText("The item is scrapped!")
                self.error_labels[sender].setVisible(True)

                return
            
            self.lease_modal.previous_data = selected_devices
            
            self.prepare_lease_modal(selected_devices.quantity)
            
            accepted = await self.lease_modal.exec_async()
            
            if accepted:
                
                form_data = self.lease_modal.get_form_data(selected_devices)
                # print(form_data)
                
                confirm_text = (
                    "You are adding the following data:\n\n"
                    f"{form_data.quantity:.4f} DB "
                    f"{selected_devices.name if selected_devices.name != '' else 'N/A'} -->\n"
                    f"{str(form_data.tenant_name) if form_data.tenant_name is not None else 'N/A'}\n"
                    f"{form_data.rental_start.strftime(Config.time.timeformat) if form_data.rental_start is not None else 'N/A'}\n"
                    f"{form_data.rental_end.strftime(Config.time.timeformat) if form_data.rental_end is not None else 'N/A'}\n"
                    f"{f'{form_data.rental_price:2f} HUF' if form_data.rental_price is not None else 'N/A'}\n\n"
                    "Biztosan folytatod?"
                )
                
                self.confirm_action_modal.set_action_message(confirm_text)
                
                confirm = await self.confirm_action_modal.exec_async()
                
                if not confirm:

                    return
                
                elif confirm:
                    
                    await self.__handle_add_tenant(
                        selected_item = selected_devices,
                        form_data = form_data,
                        sender = sender
                    )
        
        elif sender is self.qr_code_btn:
            
            self.log.debug("QR code button clicked in Devices tab")
            
            selected_items = self.devices_table.get_selected_cache_data()

            if not selected_items:
                
                self.log.warning("No item selected for printing")
                
                self.error_labels[sender].setText("Select items to print")
                self.error_labels[sender].setVisible(True)

                return
            
            html_content = self.generate_html(selected_items)
                
            self.__print_table(html_content)
            
        elif sender is self.delete_item_btn:
            
            selected_items = self.devices_table.get_selected_cache_data()
            
            if not selected_items:
                
                self.log.warning("No item selected for deleting")
                
                self.error_labels[sender].setText("Select items to delete")
                self.error_labels[sender].setVisible(True)
            
                return   
            
            await self.__handle_delete_item(
                selected_items = selected_items,
                sender = sender
            )

    async def _handle_returnable_btns(self, sender: QPushButton):
        
        self.log.info("Results table is ReturnablePackagingTable - handling button: %s", sender.text())
        
        if sender is self.add_btn:
            
            self.log.debug("Add button clicked in ReturnablePackagings tab")
            
            if self.emit_result_list is not None:
                
                self.add_returnable_packaging_modal.update_dropdown_items(self.emit_result_list)
                    
                accepted = await self.add_returnable_packaging_modal.exec_async()

                if accepted:
                    
                    data = await self.add_returnable_packaging_modal.get_form_data()
                    
                    confirm_text = (
                        f"You are recording the following item:\n\n"
                        f"Storage:\n{data.storage_id}\n\n"
                        f"Name:\n{data.name}\n\n"
                        f"Type / Serial number:\n{data.manufacture_number}\n\n"
                        f"Quantity:\n{data.quantity}\n\n"
                        f"Manufacturing year:\n{data.manufacture_date.strftime(Config.time.timeformat)}\n\n"
                        f"Net unit price:\n{data.price:,.2f}".replace(",", ".") + " HUF\n\n"
                        f"Purchase source:\n{data.purchase_source}\n\n"
                        f"Purchase date:\n{data.purchase_date.strftime(Config.time.timeformat)}\n\n"
                        f"Inspection dates:\n{data.inspection_date.strftime(Config.time.timeformat)}\n"
                        "\n\nBiztosan folytatod?"
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
            
            self.log.debug("Edit button clicked in Returnable tab")
            
            selected_data = self.returnable_table.get_selected_cache_data()
            
            if not selected_data:
                
                self.log.warning("No item selected for printing")
                
                self.error_labels[sender].setText("Select an item to edit")
                self.error_labels[sender].setVisible(True)

                return

            if len(selected_data) > 1:
                
                self.log.warning("Multiple items selected. Only one item can be edited at a time")
                
                self.error_labels[sender].setText("Select only one item at a time")
                self.error_labels[sender].setVisible(True)

                return

            previous_returnable_items: ReturnablePackagingData = selected_data[0]
            
            if self.emit_result_list is not None:
                
                self.edit_returnable_packaging_modal.previous_returnable_packaging_data = previous_returnable_items
                
                self.edit_returnable_packaging_modal.update_parameters_from_previous_reference(
                    emit_result_list = self.emit_result_list
                )
                
                accepted = await self.edit_returnable_packaging_modal.exec_async()  
                
                if accepted:
                    
                    to_data = self.edit_returnable_packaging_modal.get_form_data()
                
                    name_line = f"{str(previous_returnable_items.name) if previous_returnable_items.name is not None else 'N/A'} --> " \
                                f"{str(to_data.name) if to_data.name is not None else 'N/A'}"

                    quantity_line = f"{previous_returnable_items.quantity:.4f} --> {to_data.quantity:.4f}" \
                        if to_data.quantity != 1e-4 else "N/A"

                    storage_line = f"{str(previous_returnable_items.storage_id) if previous_returnable_items.storage_id is not None else 'N/A'} --> " \
                                f"{str(to_data.storage_id) if to_data.storage_id is not None else 'N/A'}"

                    manufacture_number_line = f"{str(previous_returnable_items.manufacture_number) if previous_returnable_items.manufacture_number is not None else 'N/A'} --> " \
                                            f"{str(to_data.manufacture_number) if to_data.manufacture_number is not None else 'N/A'}"

                    manufacture_date_line = f"{previous_returnable_items.manufacture_date.strftime(Config.time.timeformat) if previous_returnable_items.manufacture_date is not None else 'N/A'} --> " \
                                            f"{to_data.manufacture_date.strftime(Config.time.timeformat) if to_data.manufacture_date is not None else 'N/A'}"

                    price_line = (f"{previous_returnable_items.price:,.0f}".replace(",", ".") + " HUF" if previous_returnable_items.price is not None else "N/A") + " --> " + \
                                (f"{to_data.price:,.0f}".replace(",", ".") + " HUF" if to_data.price is not None else "N/A")

                    purchase_source_line = f"{str(previous_returnable_items.purchase_source) if previous_returnable_items.purchase_source is not None else 'N/A'} --> " \
                                        f"{str(to_data.purchase_source) if to_data.purchase_source is not None else 'N/A'}"

                    purchase_date_line = f"{previous_returnable_items.purchase_date.strftime(Config.time.timeformat) if previous_returnable_items.purchase_date is not None else 'N/A'} --> " \
                                        f"{to_data.purchase_date.strftime(Config.time.timeformat) if to_data.purchase_date is not None else 'N/A'}"

                    inspection_date_line = f"{previous_returnable_items.inspection_date.strftime(Config.time.timeformat) if previous_returnable_items.inspection_date is not None else 'N/A'} --> " \
                                        f"{to_data.inspection_date.strftime(Config.time.timeformat) if to_data.inspection_date is not None else 'N/A'}"

                    confirm_text = f"""
                    <br>You are modifying the following data:<br><br>
                    Name: {name_line}<br>
                    Quantity: {quantity_line}<br>
                    Storage: {storage_line}<br>
                    Type / Serial number: {manufacture_number_line}<br>
                    Manufacturing year: {manufacture_date_line}<br>
                    Net unit price: {price_line}<br>
                    Beszerezve: {purchase_source_line}<br>
                    Purchase date: {purchase_date_line}<br>
                    Inspection: {inspection_date_line}<br><br>
                    Biztosan folytatod?<br>
                    """

                    self.confirm_action_modal.set_action_message(f"<div align='center'>{confirm_text}</div>")
                    
                    confirm = await self.confirm_action_modal.exec_async()
                    
                    if not confirm:

                        return
                    
                    elif confirm:
                        
                        await self.__handle_edit_data(
                            to_data = to_data,
                            from_data = previous_returnable_items,
                            sender = sender
                        )
        
        elif sender is self.work_add_btn:
            
            self.log.debug("Add to work button clicked in Returnable tab")
            
            selected_data: ReturnablePackagingCacheData = self.returnable_table.get_selected_cache_data()
            
            if not selected_data:
                
                self.log.warning("No item selected for send back")
                
                self.error_labels[sender].setText("Select an item for return")
                self.error_labels[sender].setVisible(True)

                return

            self.send_back_modal.setup_modal_data(selected_data)
            
            accepted = await self.send_back_modal.exec_async()
            
            if accepted:
                
                form_data = self.send_back_modal.get_form_data()
                # print(form_data)
                
                lines = [f"You are returning the packaging ({len(form_data)} db)\n\n"]
                
                for item in form_data:
                    
                    lines.append(
                        f"{item.name if item.name and item.name.strip() else 'N/A'} | "
                        f"{item.manufacture_number if item.manufacture_number and item.manufacture_number.strip() else 'N/A'} | "
                        f"{item.quantity:.4f} DB"
                    )
                    
                lines.append("\n\nBiztosan folytatod?")
                
                confirm_text = "\n".join(lines)

                self.confirm_action_modal.set_action_message(confirm_text)
                
                confirm = await self.confirm_action_modal.exec_async()
                
                if not confirm:

                    return
                
                elif confirm:
                    
                    await self._handle_send_back(
                        form_data = form_data,
                        sender = sender
                    )
        
        elif sender is self.qr_code_btn:
            
            self.log.debug("QR code button clicked in Devices tab")
            
            selected_items = self.returnable_table.get_selected_cache_data()

            if not selected_items:
                
                self.log.warning("No item selected for printing")
                
                self.error_labels[sender].setText("Select items to print")
                self.error_labels[sender].setVisible(True)

                return
            
            html_content = self.generate_html(selected_items)
                
            self.__print_table(html_content)
            
        elif sender is self.delete_item_btn:
            
            selected_items = self.returnable_table.get_selected_cache_data()
            
            if not selected_items:
                
                self.log.warning("No item selected for deleting")
                
                self.error_labels[sender].setText("Select items to delete")
                self.error_labels[sender].setVisible(True)
            
                return   
            
            await self.__handle_delete_item(
                selected_items = selected_items,
                sender = sender
            )
    
    async def _handle_send_back(self, form_data: t.List[ReturnablePackagingData], sender: QPushButton):
        
        self.log.debug("Processing return of %d [%s]" % (
                len(form_data),
                form_data[0].__class__.__name__
            )
        )
        
        if isinstance(sender, QPushButton):
            
            if len(form_data) > 0:
                
                for data in form_data:
                    
                    zero_quantity = 0.0000
                    
                    if self.utility_calculator.floats_are_equal(data.quantity, zero_quantity) is False:
                        
                        await queries.update_returnable_packaging_returned_by_id(
                            id = data.id,
                            quantity = data.quantity
                        )
                        
                        await self.returnable_cache_service.clear_cache(Config.redis.cache.returnable_packaging.id)
                        
                        await self.load_cache_data(
                            cache_id = Config.redis.cache.returnable_packaging.id, 
                            exp = Config.redis.cache.returnable_packaging.exp
                        )
    
    @asyncSlot()
    async def _handle_menu_click(self, sender: t.Optional[t.Union[QPushButton, QTabBar]]):
      
        try:
            
            self.error_label.setVisible(False) 
            
            if isinstance(sender, QTabBar):
                
                self.log.debug("Tab switched, loading corresponding data")
                
                index = self.tab_bar.currentIndex()

                if index == 0:
                    
                    self.log.info("Switched to Materials tab")
                    
                    self.__set_content(self.materials_table)
                    
                    self.results_table = self.materials_table
                    
                    await self.load_cache_data(
                        cache_id = Config.redis.cache.material.id, 
                        exp = Config.redis.cache.material.exp
                    )
                    
                elif index == 1:
                    
                    self.log.info("Switched to Tools tab")
                    
                    self.__set_content(self.tools_table)
                    
                    self.results_table = self.tools_table
                    
                    await self.load_cache_data(
                        cache_id = Config.redis.cache.tools.id,
                        exp = Config.redis.cache.tools.exp
                    )
                    
                elif index == 2:
   
                    self.log.info("Switched to Devices tab")
                    
                    self.__set_content(self.devices_table)
                    
                    self.results_table = self.devices_table
                    
                    await self.load_cache_data(
                        cache_id = Config.redis.cache.devices.id, 
                        exp = Config.redis.cache.devices.exp
                    )
                    
                elif index == 3:
   
                    self.log.info("Switched to Returnable Packaging tab")
                    
                    self.__set_content(self.returnable_table)
                    
                    self.results_table = self.returnable_table
                    
                    await self.load_cache_data(
                        cache_id = Config.redis.cache.returnable_packaging.id, 
                        exp = Config.redis.cache.returnable_packaging.exp
                    )

                return 
                    
            elif isinstance(sender, QPushButton):
                
                self.log.debug("Button clicked: %s", sender.text())
             
                self.error_labels[sender].setVisible(False)
                
                self.spinner.show(self)

                if self.emit_result_list is None:
                        
                    self.on_cache_data_loaded(self.storage_content.storage_cache_data)
                    
                if isinstance(self.results_table, MaterialsTable):
                    
                    await self._handle_material_btns(sender)
                          
                elif isinstance(self.results_table, ToolsTable):
                    
                    await self._handle_tool_btns(sender)

                elif isinstance(self.results_table, DevicesTable):
                    
                    await self._handle_device_btns(sender)
                
                elif isinstance(self.results_table, ReturnablePackagingTable):
                    
                    await self._handle_returnable_btns(sender)
                          
        except Exception:

            self.log.exception("Unexpected error occurred:")
            
        finally:
            
            self.spinner.hide()

    async def __handle_delete_item(self, 
        selected_items: t.List[t.Union[
            MaterialData, 
            ToolsData, 
            DeviceData, 
            ReturnablePackagingData
            ]
        ], 
        sender: QPushButton
        ):
   
        try:
            
            items_by_type = defaultdict(list)

            for item in selected_items:
                
                if isinstance(item, MaterialData):
                    
                    items_by_type[StorageItemTypeEnum.MATERIAL].append(item.id)
                    
                elif isinstance(item, ToolsData):
                    
                    items_by_type[StorageItemTypeEnum.TOOL].append(item.id)
                    
                elif isinstance(item, DeviceData):
                    
                    items_by_type[StorageItemTypeEnum.DEVICE].append(item.id)
                    
                elif isinstance(item, ReturnablePackagingData):
                    
                    items_by_type[StorageItemTypeEnum.RETURNABLE_PACKAGING].append(item.id)
            
            await queries.delete_items_by_id_from_specified_table(items_by_type)
            
            if StorageItemTypeEnum.MATERIAL in items_by_type:
                
                await self.material_cache_service.clear_cache(Config.redis.cache.material.id)
                
                await self.load_cache_data(
                    cache_id = Config.redis.cache.material.id,
                    exp = Config.redis.cache.material.exp
                )
                
            if StorageItemTypeEnum.TOOL in items_by_type:
                
                await self.tools_cache_service.clear_cache(Config.redis.cache.tools.id)
                
                await self.load_cache_data(
                    cache_id = Config.redis.cache.tools.id,
                    exp = Config.redis.cache.tools.exp
                )
                
            if StorageItemTypeEnum.DEVICE in items_by_type:
                
                await self.devices_cache_service.clear_cache(Config.redis.cache.devices.id)
                
                await self.load_cache_data(
                    cache_id = Config.redis.cache.devices.id,
                    exp = Config.redis.cache.devices.exp
                )
                
            if StorageItemTypeEnum.RETURNABLE_PACKAGING in items_by_type:
                
                await self.returnable_cache_service.clear_cache(Config.redis.cache.returnable_packaging.id)
                
                await self.load_cache_data(
                    cache_id = Config.redis.cache.returnable_packaging.id,
                    exp = Config.redis.cache.returnable_packaging.exp
                )
        
        except ItemCannotBeDeletedWhileRentedError as e:

            self.error_labels[sender].setText(f"In use:\n '{e.items}'")
            self.error_labels[sender].setVisible(True)
            
            self.log.exception(e.message)
            
        except Exception as e:
            
            self.error_labels[sender].setText("Failed to delete the data")
            self.error_labels[sender].setVisible(True)
            
            self.log.exception("Failed to delete items: %s" % str(e))
          
        finally:
            
            self.spinner.hide()    
            
    def check_cache_type(self,
        selected_items: t.List[
            t.Optional[
                t.Union[
                    MaterialCacheData, 
                    ToolsCacheData, 
                    DeviceCacheData
                ]
            ]
        ]) -> str:
        
        for item in selected_items:
     
            if isinstance(item, MaterialData):
                
                return "Anyag"
            
            elif isinstance(item, ToolsData):
                
                return "Tool"
            
            elif isinstance(item, DeviceData):
                
                return "Device"
            
            elif isinstance(item, ReturnablePackagingData):
                
                return "Packaging"
            
            else:
                
                return "Ismeretlen"
        
        return "Ismeretlen"
    
    def generate_html(self, 
        selected_items: t.List[
            t.Optional[
                t.Union[
                    MaterialData, 
                    ToolsData, 
                    DeviceData
                ]
            ]
        ]):

        if len(selected_items) > 0:
   
            type_label = self.check_cache_type(selected_items)
       
            rows_per_page = 3
            
            pages = []
            
            filtered_items = [item for item in selected_items if item is not None]

            for page_start in range(0, len(filtered_items), rows_per_page):
                
                chunk = filtered_items[page_start:page_start + rows_per_page]
                
                table_rows = ""
                
                for _, item in enumerate(chunk, page_start + 1):
                    
                    table_rows += f"""
                    <tr>
                        <td>{type_label}</td>
                        <td>{self.datatable_helper.getAttribute(item, "manufacture_number")}</td>
                        <td>{self.bytes_to_img_html(item.uuid)}</td>
                    </tr>
                    """
                        
                page_html = f"""
                <div style='page-break-after: always;'>
                    <table>
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
    
    def bytes_to_img_html(self, bytes, size = 10):
        
        if bytes != "":
        
            base64_str = base64.b64encode(bytes).decode("utf-8")
            
            return f"<img src='data:image/png;base64,{base64_str}' width='{size}' height='{size}' />"

    def __print_table(self, html_content: str):
        
        if html_content is not None:
      
            export_dir = "exports"
            
            if os.path.exists(export_dir) is False:
                
                os.makedirs(export_dir)
            
            current_timestamp = datetime.now(Config.time.timezone_utc).strftime("%Y%m%d%H%M%S%f")
            
            pdf_file = os.path.join(export_dir, f"qr_codes_{current_timestamp}.pdf")
            
            HTML(string = html_content).write_pdf(pdf_file)
            
            QDesktopServices.openUrl(QUrl.fromLocalFile(pdf_file))
            
    def on_cache_data_loaded(self, storage_cache_data): 
     
        if isinstance(storage_cache_data, StorageCacheData) and isinstance(storage_cache_data.items, list) \
            and all(isinstance(item, StorageData) for item in storage_cache_data.items):
                
                dropdown_items = []
                
                for data in storage_cache_data.items:
                    
                    formatted_str = f"Name: | {data.name} | Location: | {data.location} |"
                    
                    dropdown_items.append((formatted_str, data.id))
                
                self.emit_result_list = dropdown_items if len(dropdown_items) > 0 else [("No displayable data", None)]
        
        else:
            
            self.emit_result_list = [("No displayable data", None)]
            
            self.log.info("Expected StorageCacheData with items, got %s" % (str(storage_cache_data)))
        
    async def __handle_add_tenant(self, 
        selected_item: t.Optional[t.Union[ToolsData, DeviceData]], 
        form_data: t.Optional[t.Union[TenantData, DeviceData]], 
        sender: QPushButton
        ):
        
        if selected_item is not None and form_data is not None:
            
            self.log.debug("Attempting to assign tools '%s' -> to tenant '%s'" % (
                selected_item,
                form_data
                )
            )
            
            try:
                
                async with self.storage_lock:
                    
                    await queries.insert_tenant(
                        item_id = selected_item.id,
                        item_name = selected_item.name,
                        item_type = form_data.item_type,
                        item_quantity = selected_item.quantity, #from storage
                        tenant_quantity = form_data.quantity, #to lease 
                        tenant_name = form_data.tenant_name.capitalize() if form_data.tenant_name is not None else None,
                        rental_start = form_data.rental_start.replace(second = 0, microsecond = 0) if form_data.rental_start else None,
                        rental_end = form_data.rental_end.replace(second = 0, microsecond = 0) if form_data.rental_end else None,
                        rental_price = form_data.rental_price,
                        is_daily_price = False if form_data.rental_end else True
                    )
                    
                tenants_content = self.admin_view.get_tenants_content()
                
                await tenants_content.tenant_datatable_cache.clear_cache(Config.redis.cache.tenants.id)
                
                await tenants_content.load_cache_data(                    
                    cache_id = Config.redis.cache.tenants.id,
                    exp = Config.redis.cache.tenants.exp,
                    update_rental_cache = True
                )
                
                calendar_content = self.main_window.get_calendar_content()
            
                await calendar_content.reminders_cache.clear_cache(calendar_content._create_cache_id())

                await calendar_content.load_cache_data()  
                
                if isinstance(selected_item, ToolsData):
                                    
                    await self.tools_cache_service.clear_cache(Config.redis.cache.tools.id)
                    
                    await self.load_cache_data(
                        cache_id = Config.redis.cache.tools.id, 
                        exp = Config.redis.cache.tools.exp
                    )
                    
                    self.log.info("Tools table refreshed after insert")
                    
                elif isinstance(selected_item, DeviceData):
                    
                    await self.devices_cache_service.clear_cache(Config.redis.cache.devices.id)
                    
                    await self.load_cache_data(
                        cache_id = Config.redis.cache.devices.id, 
                        exp = Config.redis.cache.devices.exp
                    )

                    self.log.info("Devices table refreshed after insert")

                self.error_labels[sender].setVisible(False)
                
            except Exception as e:
                
                self.error_labels[sender].setText("Failed to save the data")
                self.error_labels[sender].setVisible(True)
                
                self.log.exception("Failed to insert tenant data: %s" % str(e))
                
            finally:
                
                self.spinner.hide()
                                
    async def load_cache_data(self, cache_id: str, exp: int):
        
        if isinstance(self.results_table, MaterialsTable):
            
            self.cache_data = await self.material_cache_service.get_material_data_from_cache(
                material_cache_id = cache_id,
                exp = exp
            )
            
        elif isinstance(self.results_table, ToolsTable):
            
            self.cache_data = await self.tools_cache_service.get_tools_data_from_cache(
                tools_cache_id = cache_id,
                exp = exp
            )
            
        elif isinstance(self.results_table, DevicesTable):
            
            self.cache_data = await self.devices_cache_service.get_devices_data_from_cache(
                devices_cache_id = cache_id,
                exp = exp
            )
        
        elif isinstance(self.results_table, ReturnablePackagingTable):
            
            self.cache_data = await self.returnable_cache_service.get_returnable_data_from_cache(
                returnable_packaging_cache_id = cache_id,
                exp = exp
            )
        
        self._emit_cache_data_safe(self.cache_data)

    def on_data_loaded(self, cache_data):
    
        self.results_table.load_data(cache_data)

    async def __handle_add_data(self, 
        data: t.Optional[t.Union[
            MaterialData, 
            ToolsData, 
            DeviceData, 
            ReturnablePackagingData
            ]
        ], 
        sender: QPushButton):
        
        if isinstance(sender, QPushButton):
            
            if isinstance(data, MaterialData):
                
                try:
                    
                    async with self.storage_lock:
                        
                        await queries.insert_material_data(
                            storage_id = data.storage_id,
                            name = data.name,
                            manufacture_number = data.manufacture_number,
                            quantity = data.quantity,
                            unit = data.unit,
                            manufacture_date = data.manufacture_date,
                            price = data.price,
                            purchase_source = data.purchase_source,
                            purchase_date = data.purchase_date,
                            inspection_date = data.inspection_date,
                            is_deleted = data.is_deleted,
                            deleted_date = data.deleted_date,
                            uuid = data.uuid
                        )

                    await self.material_cache_service.clear_cache(Config.redis.cache.material.id)
                    
                    await self.load_cache_data(
                        cache_id = Config.redis.cache.material.id, 
                        exp = Config.redis.cache.material.exp
                    )
                    
                    self.error_labels[sender].setVisible(False)
                    
                    self.log.info("Material table refreshed after insert")

                except Exception as e:
                    
                    self.error_labels[sender].setText("Failed to save the data")
                    self.error_labels[sender].setVisible(True)
                    
                    self.log.exception("Failed to insert material data: %s" % str(e))
                    
                finally:
                    
                    self.spinner.hide()
            
            elif isinstance(data, ToolsData):
                
                try:
                    async with self.storage_lock:
                        
                        await queries.insert_tools_data(
                            storage_id = data.storage_id,
                            name = data.name,
                            manufacture_number = data.manufacture_number,
                            quantity = data.quantity,
                            manufacture_date = data.manufacture_date,
                            price = data.price,
                            commissioning_date = data.commissioning_date,
                            purchase_source = data.purchase_source,
                            purchase_date = data.purchase_date,
                            inspection_date = data.inspection_date,
                            is_scrap = True if data.is_scrap == True else False,
                            is_deleted = data.is_deleted,
                            deleted_date = data.deleted_date,
                            uuid = data.uuid
                        )

                    await self.tools_cache_service.clear_cache(Config.redis.cache.tools.id)
                    
                    await self.load_cache_data(
                        cache_id = Config.redis.cache.tools.id, 
                        exp = Config.redis.cache.tools.exp
                    )
                    
                    self.error_labels[sender].setVisible(False)
                    
                    self.log.info("Tools table refreshed after insert")

                except Exception as e:
                    
                    self.error_labels[sender].setText("Failed to save the data")
                    self.error_labels[sender].setVisible(True)
                    
                    self.log.exception("Failed to insert tools data: %s" % str(e))
                    
                finally:
                    
                    self.spinner.hide()
            
            elif isinstance(data, DeviceData):
                
                try:
                    async with self.storage_lock:
                        
                        await queries.insert_devices_data(
                            storage_id = data.storage_id,
                            name = data.name,
                            manufacture_number = data.manufacture_number,
                            quantity = data.quantity,
                            manufacture_date = data.manufacture_date,
                            price = data.price,
                            commissioning_date = data.commissioning_date,
                            purchase_source = data.purchase_source,
                            inspection_date = data.inspection_date,
                            purchase_date = data.purchase_date,
                            is_scrap = True if data.is_scrap == True else False,
                            is_deleted = data.is_deleted,
                            deleted_date = data.deleted_date,
                            uuid = data.uuid
                        )

                    await self.devices_cache_service.clear_cache(Config.redis.cache.devices.id)
                    
                    await self.load_cache_data(
                        cache_id = Config.redis.cache.devices.id, 
                        exp = Config.redis.cache.devices.exp
                    )
                    
                    self.error_labels[sender].setVisible(False)
                    
                    self.log.info("Devices table refreshed after insert")

                except Exception as e:
                    
                    self.error_labels[sender].setText("Failed to save the data")
                    self.error_labels[sender].setVisible(True)
                    
                    self.log.exception("Failed to insert devices data: %s" % str(e))
                    
                finally:
                    
                    self.spinner.hide()
                    
            elif isinstance(data, ReturnablePackagingData):
                
                try:
                    async with self.storage_lock:
                        
                        await queries.insert_returnable_data( 
                            storage_id = data.storage_id,
                            name = data.name,
                            manufacture_number = data.manufacture_number,
                            quantity = data.quantity,
                            manufacture_date = data.manufacture_date,
                            price = data.price,
                            purchase_source = data.purchase_source,
                            inspection_date = data.inspection_date,
                            purchase_date = data.purchase_date,
                            returned_date = data.returned_date,
                            is_returned = data.is_returned,
                            is_deleted = data.is_deleted,
                            deleted_date = data.deleted_date,
                            uuid = data.uuid
                        )

                    await self.returnable_cache_service.clear_cache(Config.redis.cache.returnable_packaging.id)
                    
                    await self.load_cache_data(
                        cache_id = Config.redis.cache.returnable_packaging.id, 
                        exp = Config.redis.cache.returnable_packaging.exp
                    )
                    
                    self.error_labels[sender].setVisible(False)
                    
                    self.log.info("Returnable packaging table refreshed after insert")

                except Exception as e:
                    
                    self.error_labels[sender].setText("Failed to save the data")
                    self.error_labels[sender].setVisible(True)
                    
                    self.log.exception("Failed to insert devices data: %s" % str(e))
                    
                finally:
                    
                    self.spinner.hide()
                     
    async def __handle_edit_data(
        self, 
        to_data: t.Optional[t.Union[MaterialData, ToolsData, DeviceData, ReturnablePackagingData]], 
        from_data: t.Optional[t.Union[list[MaterialData], list[ToolsData], list[DeviceData], list[ReturnablePackagingData]]],
        sender: QPushButton
        ):
        
        if isinstance(sender, QPushButton):
            
            if isinstance(to_data, MaterialData):
                
                self.log.debug("Edit data material (ID: %s) from: %s -> to: %s" % (
                    str(from_data.id),
                    str(from_data),
                    str(to_data)
                    )
                )
                
                if to_data is not None and isinstance(from_data, MaterialData):
                    # print("Data:", from_data, "->", to_data)
                    
                    current_quantity = from_data.quantity
                    current_price = from_data.price
                    
                    new_quantity = to_data.quantity
                    new_price = to_data.price
                    
                    try:
                        
                        async with self.storage_lock:
                                
                            await queries.update_material_data(
                                id = from_data.id,
                                inspection_date = to_data.inspection_date,
                                storage_id = to_data.storage_id if to_data.storage_id != from_data.storage_id else None,
                                name = to_data.name if to_data.name is not None else None,
                                manufacture_number = to_data.manufacture_number if to_data.manufacture_number is not None else None,
                                quantity = new_quantity if self.utility_calculator.floats_are_equal(current_quantity, new_quantity) is False else None,
                                unit = to_data.unit if to_data.unit is not None else None,
                                manufacture_date = to_data.manufacture_date if to_data.manufacture_date is not None else None,
                                price = new_price if self.utility_calculator.floats_are_equal(current_price, new_price) is False else None,
                                purchase_source = to_data.purchase_source if to_data.purchase_source is not None else None,
                                purchase_date = to_data.purchase_date if to_data.purchase_date is not None else None
                            )

                        await self.material_cache_service.clear_cache(Config.redis.cache.material.id)
                        
                        await self.load_cache_data(
                            cache_id = Config.redis.cache.material.id, 
                            exp = Config.redis.cache.material.exp
                        )
                        
                        self.error_labels[sender].setVisible(False)
                        
                        self.log.info("material table refreshed after update")

                    except Exception as e:
                        
                        self.error_labels[sender].setText("Failed to update the data")
                        self.error_labels[sender].setVisible(True)
                        
                        self.log.exception("Failed to update material data: %s" % str(e))
                        
                    finally:
                        
                        self.spinner.hide()

            elif isinstance(to_data, ToolsData):
                
                self.log.debug("Edit data tools (ID: %s) from: %s -> to: %s" % (
                    str(from_data.id),
                    str(from_data),
                    str(to_data)
                    )
                )  
                
                if to_data is not None and isinstance(from_data, ToolsData):
                    
                    if to_data.is_scrap is False:
                        
                        current_quantity = from_data.quantity
                        current_price = from_data.price
                        
                        new_quantity = to_data.quantity
                        new_price = to_data.price
                        
                        try:
                            
                            async with self.storage_lock:
                                
                                await queries.update_tools_data(
                                    id = from_data.id,
                                    inspection_date = to_data.inspection_date,
                                    storage_id = to_data.storage_id if to_data.storage_id != from_data.storage_id else None,
                                    name = to_data.name if to_data.name is not None else None,
                                    quantity = new_quantity if self.utility_calculator.floats_are_equal(current_quantity, new_quantity) is False else None,
                                    manufacture_number = to_data.manufacture_number if to_data.manufacture_number is not None else None,
                                    manufacture_date = to_data.manufacture_date if to_data.manufacture_date is not None else None,
                                    commissioning_date = to_data.commissioning_date if to_data.commissioning_date is not None else None,
                                    price = new_price if self.utility_calculator.floats_are_equal(current_price, new_price) is False else None,
                                    purchase_source = to_data.purchase_source if to_data.purchase_source is not None else None,
                                    purchase_date = to_data.purchase_date if to_data.purchase_date is not None else None
                                )

                            await self.tools_cache_service.clear_cache(Config.redis.cache.tools.id)
                            
                            await self.load_cache_data(
                                cache_id = Config.redis.cache.tools.id, 
                                exp = Config.redis.cache.tools.exp
                            )

                            self.error_labels[sender].setVisible(False)
                            
                            self.log.info("Tools table refreshed after update")

                        except Exception as e:
                            
                            self.error_labels[sender].setText("Failed to update the data")
                            self.error_labels[sender].setVisible(True)
                            
                            self.log.exception("Failed to update tools data: %s" % str(e))
                            
                        finally:
                            
                            self.spinner.hide()

                    elif to_data.is_scrap is True:
                        
                        try:
                            
                            async with self.storage_lock:
                                
                                await queries.insert_tools_is_scrap(
                                    storage_id = from_data.storage_id,
                                    name = from_data.name,
                                    manufacture_number = from_data.manufacture_number,
                                    quantity = to_data.quantity,
                                    manufacture_date = from_data.manufacture_date,
                                    price = from_data.price,
                                    commissioning_date = from_data.commissioning_date,
                                    purchase_source = from_data.purchase_source,
                                    purchase_date = from_data.purchase_date,
                                    inspection_date = to_data.inspection_date,
                                    is_scrap = to_data.is_scrap,
                                    previous_quantity = from_data.quantity,
                                    is_deleted = from_data.is_deleted,
                                    deleted_date = from_data.deleted_date,
                                    uuid = from_data.uuid
                                )

                            await self.tools_cache_service.clear_cache(Config.redis.cache.tools.id)
                            
                            await self.load_cache_data(
                                cache_id = Config.redis.cache.tools.id, 
                                exp = Config.redis.cache.tools.exp
                            )

                            self.error_labels[sender].setVisible(False)
                            
                            self.log.info("Tools table refreshed after update")
                        
                        except ValueError as e:
                            
                            self.error_labels[sender].setText("You entered an invalid quantity")
                            self.error_labels[sender].setVisible(True)
                            
                            self.log.warning("Failed to update tools data: %s" % str(e))
                                                    
                        except Exception as e:
                            
                            self.error_labels[sender].setText("Failed to update the data")
                            self.error_labels[sender].setVisible(True)
                            
                            self.log.exception("Failed to update tools data: %s" % str(e))
                            
                        finally:
                            
                            self.spinner.hide()

            elif isinstance(to_data, DeviceData):
                
                self.log.debug("Edit data devices (ID: %s) from: %s -> to: %s" % (
                    str(from_data.id),
                    str(from_data),
                    str(to_data)
                    )
                )  
                
                if to_data is not None and isinstance(from_data, DeviceData):
                    
                    if to_data.is_scrap is False:
                        
                        try:
                            
                            current_quantity = from_data.quantity
                            current_price = from_data.price
                            
                            new_quantity = to_data.quantity
                            new_price = to_data.price
                            
                            async with self.storage_lock:
                                
                                await queries.update_devices_data(
                                    id = from_data.id,
                                    inspection_date = to_data.inspection_date,
                                    storage_id = to_data.storage_id if to_data.storage_id != from_data.storage_id else None,
                                    name = to_data.name if to_data.name is not None else None,
                                    quantity = new_quantity if self.utility_calculator.floats_are_equal(current_quantity, new_quantity) is False else None,
                                    manufacture_number = to_data.manufacture_number if to_data.manufacture_number is not None else None,
                                    manufacture_date = to_data.manufacture_date if to_data.manufacture_date is not None else None,
                                    commissioning_date = to_data.commissioning_date if to_data.commissioning_date is not None else None,
                                    price = new_price if self.utility_calculator.floats_are_equal(current_price, new_price) is False else None,
                                    purchase_source = to_data.purchase_source if to_data.purchase_source is not None else None,
                                    purchase_date = to_data.purchase_date if to_data.purchase_date is not None else None
                                )

                            await self.devices_cache_service.clear_cache(Config.redis.cache.devices.id)
                            
                            await self.load_cache_data(
                                cache_id = Config.redis.cache.devices.id, 
                                exp = Config.redis.cache.devices.exp
                            )

                            self.error_labels[sender].setVisible(False)
                            
                            self.log.info("Devices table refreshed after update")

                        except Exception as e:
                            
                            self.error_labels[sender].setText("Failed to update the data")
                            self.error_labels[sender].setVisible(True)
                            
                            self.log.exception("Failed to update devices data: %s" % str(e))
                            
                        finally:
                            
                            self.spinner.hide()

                    elif to_data.is_scrap is True:
                        
                        try:
                            
                            async with self.storage_lock:
                                
                                await queries.insert_devices_is_scrap(
                                    storage_id = from_data.storage_id,
                                    name = from_data.name,
                                    manufacture_number = from_data.manufacture_number,
                                    quantity = to_data.quantity,
                                    manufacture_date = from_data.manufacture_date,
                                    price = from_data.price,
                                    commissioning_date = from_data.commissioning_date,
                                    purchase_source = from_data.purchase_source,
                                    purchase_date = from_data.purchase_date,
                                    inspection_date = to_data.inspection_date,
                                    is_scrap = to_data.is_scrap,
                                    is_deleted = from_data.is_deleted,
                                    deleted_date = from_data.deleted_date,
                                    previous_quantity = from_data.quantity,
                                    uuid = from_data.uuid
                                )

                            await self.tools_cache_service.clear_cache(Config.redis.cache.tools.id)
                            
                            await self.load_cache_data(
                                cache_id = Config.redis.cache.tools.id, 
                                exp = Config.redis.cache.tools.exp
                            )

                            self.error_labels[sender].setVisible(False)
                            
                            self.log.info("Device table refreshed after update")
                        
                        except ValueError as e:
                            
                            self.error_labels[sender].setText("You entered an invalid quantity")
                            self.error_labels[sender].setVisible(True)
                            
                            self.log.warning("Failed to update device data: %s" % str(e))
                        
                        except Exception as e:
                            
                            self.error_labels[sender].setText("Failed to update the data")
                            self.error_labels[sender].setVisible(True)
                            
                            self.log.exception("Failed to update device data: %s" % str(e))
                            
                        finally:
                            
                            self.spinner.hide()
            
            elif isinstance(to_data, ReturnablePackagingData):
                
                self.log.debug("Edit data returnable packaging (ID: %s) from: %s -> to: %s" % (
                    str(from_data.id),
                    str(from_data),
                    str(to_data)
                    )
                )
                
                if to_data is not None and isinstance(from_data, ReturnablePackagingData):
                                            
                        try:
                            
                            current_quantity = from_data.quantity
                            current_price = from_data.price
                            
                            new_quantity = to_data.quantity
                            new_price = to_data.price
                            
                            async with self.storage_lock:
                                
                                await queries.update_returnable_data(
                                    id = from_data.id,
                                    inspection_date = to_data.inspection_date,
                                    storage_id = to_data.storage_id if to_data.storage_id != from_data.storage_id else None,
                                    name = to_data.name if to_data.name is not None else None,
                                    manufacture_number = to_data.manufacture_number if to_data.manufacture_number is not None else None,
                                    manufacture_date = to_data.manufacture_date if to_data.manufacture_date is not None else None,
                                    quantity = new_quantity if self.utility_calculator.floats_are_equal(current_quantity, new_quantity) is False else None,
                                    price = new_price if self.utility_calculator.floats_are_equal(current_price, new_price) is False else None,
                                    purchase_source = to_data.purchase_source if to_data.purchase_source is not None else None,
                                    purchase_date = to_data.purchase_date if to_data.purchase_date is not None else None
                                )

                            await self.returnable_cache_service.clear_cache(Config.redis.cache.returnable_packaging.id)
                            
                            await self.load_cache_data(
                                cache_id = Config.redis.cache.returnable_packaging.id, 
                                exp = Config.redis.cache.returnable_packaging.exp
                            )

                            self.error_labels[sender].setVisible(False)
                            
                            self.log.info("Returnable packaging table refreshed after update")

                        except Exception as e:
                            
                            self.error_labels[sender].setText("Failed to update the data")
                            self.error_labels[sender].setVisible(True)
                            
                            self.log.exception("Failed to update returnable data: %s" % str(e))
                            
                        finally:
                            
                            self.spinner.hide()
                           
    async def __handle_add_accessories(self, 
        selected_work: SelectedWorkData, 
        selected_work_items: list, 
        sender: QPushButton
        ):
        #TODO: Review when work assignment changes are complete - insert work accessories will fail!
        if isinstance(selected_work, SelectedWorkData) and isinstance(selected_work_items, list) \
            and all(isinstance(item, MaterialData) for item in selected_work_items):
            
            description_list = "\n".join(
                f"{selected_work.description} --> {item.name if item.name is not None else 'n.a'}"
                for item in selected_work_items
            )
            
            confirm_text = (
                "The following data will be added:\n\n"
                f"{description_list} "
                "\n\nBiztosan folytatod?"
            )
            
            self.confirm_action_modal.set_action_message(confirm_text)
            
            confirm = await self.confirm_action_modal.exec_async()
            
            if not confirm:
                
                self.spinner.hide()
                
                return
            
            part_ids = [item.id for item in selected_work_items]
 
            try:
                
                async with self.storage_lock:
                        
                    await queries.insert_work_accessories(
                        work_id = selected_work.id,
                        part_ids = part_ids
                    )
                    
                await self.material_cache_service.clear_cache(Config.redis.cache.material.id)
                
                await self.load_cache_data(
                    cache_id = Config.redis.cache.material.id, 
                    exp = Config.redis.cache.material.exp
                )

                self.error_labels[sender].setVisible(False)
                
                self.log.info("Material table refreshed after update")

            except Exception as e:
                
                self.error_labels[sender].setText("Failed to update the data")
                self.error_labels[sender].setVisible(True)
                
                self.log.exception("Failed to insert Material data: %s" % str(e))
                
            finally:
                
                self.spinner.hide()
                
    def __set_content(self, new_view: QWidget):
        
        index = self.stack.indexOf(new_view)
        
        if index == -1:
            
            self.stack.addWidget(new_view)
            
            index = self.stack.indexOf(new_view)

        self.stack.setCurrentIndex(index)
        
        self.results_table = new_view

        if isinstance(new_view, MaterialsTable):
            
            self.search_input_2.setPlaceholderText("Unit search...")
            self.work_add_btn.setText("Add to work")
            
            self.log.debug("Updated search input and work add button for MaterialTable: placeholder: '%s', button_text: '%s'" % (
                self.search_input_2.placeholderText(),
                self.work_add_btn.text()
                )
            )   
                    
        elif isinstance(new_view, ToolsTable):
            
            self.search_input_2.setPlaceholderText("Serial number search...")
            self.work_add_btn.setText("Assign to tenant")
            
            self.log.debug("Updated search input and work add button for ToolsTable: placeholder: '%s', button_text: '%s'" % (
                self.search_input_2.placeholderText(),
                self.work_add_btn.text()
                )
            )
            
        elif isinstance(new_view, DevicesTable):
            
            self.search_input_2.setPlaceholderText("Serial number search...")
            self.work_add_btn.setText("Assign to tenant")
            
            self.log.debug("Updated search input and work add button for DevicesTable: placeholder: '%s', button_text: '%s'" % (
                self.search_input_2.placeholderText(),
                self.work_add_btn.text()
                )
            )
            
        elif isinstance(new_view, ReturnablePackagingTable):
            
            self.search_input_2.setPlaceholderText("Bottle number search...")
            self.work_add_btn.setText("Return")
            
            self.log.debug("Updated search input and work add button for ReturnablePackagingTable: placeholder: '%s', button_text: '%s'" % (
                self.search_input_2.placeholderText(),
                self.work_add_btn.text()
                )
            )

