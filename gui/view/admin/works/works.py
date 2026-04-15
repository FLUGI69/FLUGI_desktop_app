import asyncio
from functools import partial
from qasync import asyncSlot
from datetime import datetime
import logging
import typing as t

from PyQt6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QTabBar,
    QPushButton,
    QLineEdit,
    QLineEdit,
    QLabel,
    QTextEdit,
    QComboBox,
    QDateTimeEdit,
    QFileDialog,
    QStackedWidget,
    QSizePolicy
)
from PyQt6.QtCore import Qt, QDateTime, QDate, QTime, QTimer, pyqtSignal
from PyQt6.QtGui import QCursor

from utils.logger import LoggerMixin
from utils.dc.admin.work.boat_search import AdminBoatData
from utils.dc.admin.work.edit import AdminEditWorkData 
from utils.dc.admin.work.accessories import AdminWorkAccessorie
from utils.dc.admin.work.images import AdminWorkImage
from utils.dc.admin.work.status import AdminWorkStatus
from utils.dc.admin.work.status_note import AdminWorkStatusNote
from utils.dc.material import MaterialData, MaterialCacheData
from .add_work import AdminAddWorkContent
from .edit_work import AdminEditWorkContent
from config import Config
from db import queries

if t.TYPE_CHECKING:
    
    from ..admin import AdminView

class AdminWorksContent(QWidget, LoggerMixin):
    
    log: logging.Logger
    
    refresh_todo = pyqtSignal(bool)
    
    def __init__(self,
        admin_view: 'AdminView'
        ):
        
        super().__init__()
        
        self.utility_calculator = admin_view.main_window.app.utility_calculator
        
        if admin_view.main_window.storage_view is not None:
            
            self.storage_view = admin_view.main_window.storage_view

            self.material_cache_service = admin_view.main_window.storage_view.material_cache_service
            
        else:
            
            self.storage_view = admin_view.main_window.get_storage_view()
 
            self.material_cache_service = self.storage_view.material_cache_service
        
        self.spinner = admin_view.main_window.app.spinner
        
        self.openai = admin_view.main_window.app.openai
        
        self.openapi_lock = admin_view.main_window.app.openapi_lock
        
        self.previous_add_text = ""
        
        self.previous_edit_text = ""
    
        self.add_work_widget = AdminAddWorkContent(self)
        
        self.edit_work_widget = AdminEditWorkContent(self)

        self.add_work_widget.refresh_todo.connect(self.refresh_todo.emit)
        self.edit_work_widget.refresh_todo.connect(self.refresh_todo.emit)
        
        self.__init_view()
        
        asyncio.ensure_future(self.load_cache_data())
        
        self.storage_view.data_loaded.connect(self.on_data_loaded)
        
    def __init_view(self): 
        
        main_layout = QHBoxLayout(self)
        
        widget = QWidget()
        
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(0, 0, 0, 0)

        search_layout = self.set_search_layout()
        
        content_layout.addLayout(search_layout)
        
        self.content_container = QWidget()
        self.content_container.setObjectName("MaterialTableContainer")
        self.content_container.setLayout(QVBoxLayout())
        self.content_container.layout().setContentsMargins(0, 0, 0, 0)
        
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.stack = QStackedWidget()
        
        self.content_container.layout().addWidget(self.stack)
        
        content_layout.addWidget(self.content_container)
        
        main_container = QWidget()
        
        main_container.setLayout(content_layout)
        
        main_layout.addWidget(main_container)
        
        self.__set_content(self.add_work_widget)

        self.results_widget = self.add_work_widget
    
    def clear_prev_search(self):
        
        self.previous_add_text = ""
        self.previous_edit_text = ""
    
    def on_data_loaded(self, data):
   
        if isinstance(data, MaterialCacheData) and hasattr(data, "items"):
            
            if self.add_work_widget and isinstance(self.results_widget, AdminAddWorkContent):
 
                self.add_work_widget.available_materials.items = [
                    material for material in data.items 
                    if material.is_deleted == False and material not in self.add_work_widget.selected_materials.items
                ]
                
                self.add_work_widget.populate_work_components_list(self.add_work_widget.available_materials.items)
                self.add_work_widget.populate_work_components_list_selected(self.add_work_widget.selected_materials.items)
            
            if self.edit_work_widget is not None and isinstance(self.edit_work_widget, AdminEditWorkContent):
                
                self.edit_work_widget.available_materials.items = [
                    material for material in data.items if material.is_deleted == False
                ]
                
                self.edit_work_widget.set_fields_data_from_prev_reference()
                
                self.edit_work_widget.populate_work_components_list(self.edit_work_widget.available_materials.items) 
                self.edit_work_widget.populate_work_components_list_on_work(self.edit_work_widget.work_accessories.items) 

    async def load_cache_data(self):
        
        if self.results_widget is not None:
            
            self.add_work_widget._recalculate_widths = True
            self.edit_work_widget._recalculate_widths = True
       
        await self.storage_view.load_cache_data(
            cache_id = Config.redis.cache.material.id,
            exp = Config.redis.cache.material.exp
        )
        
    def set_search_layout(self):
        
        self.tab_bar = QTabBar()
        self.tab_bar.setExpanding(False)
        self.tab_bar.setCursor(Qt.CursorShape.PointingHandCursor)
        self.tab_bar.setShape(QTabBar.Shape.RoundedNorth)
        self.tab_bar.setElideMode(Qt.TextElideMode.ElideNone) 
        self.tab_bar.setFixedHeight(50)
        self.tab_bar.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        self.tab_bar.addTab("Munka hozzáadás")      
        self.tab_bar.addTab("Munkák módosítása")     
        self.tab_bar.setCurrentIndex(0) 
        self.tab_bar.currentChanged.connect(lambda index, tab_bar = self.tab_bar: self._handle_selected_tab(tab_bar, index))

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Keresés...")
        self.search_input.setObjectName("WarehouseSearchInput")
        self.search_input.returnPressed.connect(self._handle_enter_pressed)
        
        self.search_error_label = QLabel()
        self.search_error_label.setObjectName("error")
        self.search_error_label.setVisible(False) 
        self.search_error_label.setMaximumWidth(380)
        
        search_input_h = QVBoxLayout()
        
        search_input_h.addWidget(self.search_input)
        search_input_h.addWidget(self.search_error_label)
        
        search_layout = QHBoxLayout()
        search_layout.addWidget(self.tab_bar)
        search_layout.addLayout(search_input_h)
        
        return search_layout
     
    @asyncSlot()
    async def _handle_selected_tab(self, tab_bar: QTabBar, idx: int):
        
        tab_text = tab_bar.tabText(idx)
        
        if tab_text == "Munka hozzáadás":
            
            self.__set_content(self.add_work_widget)
            
        elif tab_text == "Munkák módosítása":
            
            self.__set_content(self.edit_work_widget)
    
    @asyncSlot()    
    async def _handle_enter_pressed(self):
        
        self.search_error_label.setVisible(False) 
        
        text = self.search_input.text().strip().lower()
        
        self.search_input.clear()
        
        if isinstance(self.results_widget, AdminAddWorkContent):
        
            if text == self.previous_add_text:
                
                self.log.info("Same search input as before, skipping query")
                
                self.spinner.hide()
                
                return
            
            self.previous_add_text = text
            
            if text != "":
                
                query_result = await queries.select_boat_by_name(text)
            
                if len(query_result) > 0:
                    
                    result = [AdminBoatData(
                        id = row.id,
                        boat_id = row.ship_id,
                        name = row.name,
                        flag = row.flag,
                        imo = row.imo,
                        mmsi = row.mmsi
                        ) for row in query_result
                    ]
                    
                    if self.results_widget is not None and isinstance(self.results_widget, AdminAddWorkContent):
                        self.results_widget.table.load_data(result)
                
                elif query_result == []:
                    
                    self.log.info("No records found in the database")
                    
                    self.search_error_label.setVisible(True)
                    
                    self.search_error_label.setText("Nincs megjeleníthető adat '%s' kapcsolódóan" % text)
        
        elif isinstance(self.results_widget, AdminEditWorkContent):
            
            if text == self.previous_edit_text:
                
                self.log.info("Same search input as before, skipping query")
                
                self.spinner.hide()
                
                return
            
            self.previous_edit_text = text
            
            if text != "":
                
                query_result = await queries.select_boat_work_by_boat_name(text)
                # for i in query_result:
                #     print(i.accessories.__dir__())
                #     for j in i.accessories:
                #         print(type(j))
                #         print(j.__class__.__name__)
                        
                if len(query_result) > 0:
                    
                    result = [AdminEditWorkData(
                        work_id = row.id,
                        leader = row.leader,
                        order_date = row.order_date,
                        description = row.description if row.description is not None else None,
                        start_date = row.start_date if row.start_date is not None else None,
                        finished_date = row.finished_date if row.finished_date is not None else None,
                        transfered = True if row.transfered is True else False,
                        is_contractor = True if row.is_contractor is True else False,
                        boat = AdminBoatData(
                            id = row.boat.id,
                            boat_id = row.boat.ship_id,
                            name = row.boat.name,
                            flag = row.boat.flag,
                            imo = row.boat.imo,
                            mmsi = row.boat.mmsi
                        ),
                        work_accessories = [
                            AdminWorkAccessorie(
                                component_id = accessori.component_id,
                                quantity = accessori.quantity
                            ) for accessori in row.work_accessories
                        ] if len(row.work_accessories) > 0 else [],
                        images = [
                            AdminWorkImage(
                                id = image.id,
                                img = image.img
                            ) for image in row.images
                        ] if len(row.images) > 0 else [],
                        status = AdminWorkStatus(
                            id = row.status.id,
                            delivered_back = True if row.status.delivered_back else False,
                            notes = [
                                AdminWorkStatusNote(
                                    id = note_text.id,
                                    note = note_text.note,
                                    created_at = note_text.created_at
                                ) for note_text in row.status.notes
                            ] if len(row.status.notes) > 0 else []
                        ) if row.transfered == True and row.status is not None else None,
                    ) for row in query_result]
                    
                    if self.results_widget is not None and isinstance(self.results_widget, AdminEditWorkContent):    
                        self.results_widget.table.load_data(result)
                    
                elif query_result == []:
                    
                    self.log.info("No records found in the database")
                    
                    self.search_error_label.setVisible(True)
                    
                    self.search_error_label.setText("Nincs megjeleníthető adat '%s' kapcsolódóan" % text)
                
    def __set_content(self, new_view: QWidget):
        
        index = self.stack.indexOf(new_view)
        
        if index == -1:
            
            self.stack.addWidget(new_view)
            
            index = self.stack.indexOf(new_view)

        self.stack.setCurrentIndex(index)
        
        self.results_widget = new_view