import os
import asyncio
import io
import aiofiles
from functools import partial
from qasync import asyncSlot
from datetime import datetime
import logging
import copy
import typing as t
from decimal import Decimal, ROUND_HALF_UP

from PyQt6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QTabBar,
    QPushButton,
    QComboBox,
    QLineEdit,
    QLineEdit,
    QLabel,
    QTextEdit,
    QComboBox,
    QDateTimeEdit,
    QFileDialog,
    QListWidget,
    QTableWidget,
    QDoubleSpinBox,
    QToolButton,
    QScrollArea,
    QFrame,
    QSizePolicy,
    QListWidgetItem
)
from PyQt6.QtCore import Qt, pyqtSignal, QDate, QTime, QSize, QTimer, QDateTime
from PyQt6.QtGui import QCursor, QPixmap, QIcon, QFont, QFontMetrics

from utils.logger import LoggerMixin
from ..custom import ImageItemWidget
from utils.dc.admin.work.edit import AdminEditWorkData
from utils.dc.admin.work.accessories import AdminWorkAccessorie
from utils.dc.admin.work.status_note import AdminWorkStatusNote
from utils.dc.material import MaterialData, MaterialCacheData
from config import Config
from ...tables.admin.work_edit import AdminEditTable
from ...tables.admin.work_notes import AdminEditWorkNotes
from ...modal.confirm_action import ConfirmActionModal
from utils.enums.quantity_range import QuantityRange
from db import queries

if t.TYPE_CHECKING:
    
    from .works import AdminWorksContent
    
class AdminEditWorkContent(QWidget, LoggerMixin):
    
    log: logging.Logger
    
    refresh_todo = pyqtSignal(bool)
    
    def __init__(self, 
        parent: 'AdminWorksContent'
        ):
        
        super().__init__(parent)
        
        assert parent is not None, "AdminEditWorkContent requires a parent widget"
        
        self._btn_lock = asyncio.Lock()
        
        self.work_content = parent
        
        self.current_work_id = None
        
        self._edit_work_lock = parent.storage_lock
        
        self.spinner = parent.spinner
        
        self.utility_calculator = parent.utility_calculator
        
        self.material_cache_service = parent.material_cache_service
        
        self.changed_notes: t.List[AdminWorkStatusNote] = []
        
        self.row_maximum_col_widths = []
        
        self.deleted_img_bytes: dict = {}
        
        self.image_map: dict = {}
        
        self.available_materials: MaterialCacheData = MaterialCacheData(items = [])
        
        self.work_accessories: MaterialCacheData = MaterialCacheData(items = [])
        
        self.table = AdminEditTable(self)
        
        self.previous_admin_work_data: AdminEditWorkData | None = None
        
        self.notes_table = AdminEditWorkNotes(self)
        
        self.confirm_action_modal = ConfirmActionModal(self)
        
        self.attached_images: t.List[t.Union[str, int]] = []
        
        self._recalculate_widths = True
        
        self.all_collumns = None
        
        self.__init_view()
        
        self.table.boat_selected.connect(self._handle_toogle_selected)
        
        self.notes_table.note_changed.connect(self._handle_note_changed)

    @staticmethod
    def icon(name: str) -> QIcon:

        return QIcon(os.path.join(Config.icon.icon_dir, name))   
    
    def __init_view(self):

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(Config.styleSheets.work_scroll)

        container = QWidget()
        container.setObjectName("MaterialTableContainer")
        container.setContentsMargins(0, 0, 0, 0)

        container_layout = QVBoxLayout(container)
        container_layout.setSpacing(20)

        scroll.setWidget(container)

        main_layout = QVBoxLayout(self)
        main_layout.addWidget(scroll)

        form_frame = QFrame()
        form_frame.setObjectName("WorkFormFrame")

        form_layout = QVBoxLayout(form_frame)
        form_layout.setSpacing(25)

        project_leader_section = self.set_project_leader_section()
        work_description_section = self.set_work_description_section()
        work_pictures_section = self.set_work_puctures_section()
        work_components_section = self.set_work_components_section()
        missing_data_section = self.set_missing_data_section()
        self.status_notes_section = self.set_status_notes_section()

        self.status_notes_section.setVisible(False)
        
        footer_buttons = self.set_footer_buttons()
        
        form_layout.addLayout(project_leader_section)
        form_layout.addLayout(work_description_section)
        form_layout.addLayout(work_pictures_section)
        form_layout.addLayout(work_components_section)
        form_layout.addLayout(missing_data_section)
        form_layout.addWidget(self.status_notes_section)

        container_layout.addWidget(self.table)      
        container_layout.addWidget(form_frame)      
        container_layout.addLayout(footer_buttons)   
        container_layout.addStretch(1)
        
    @asyncSlot(AdminEditWorkData)
    async def _handle_toogle_selected(self, work: AdminEditWorkData | None = None):
   
        await self.reset_form(True)

        if work is not None:
            
            self.previous_admin_work_data = work
  
    @asyncSlot(AdminWorkStatusNote)
    async def _handle_note_changed(self, note: AdminWorkStatusNote):
        
        self.changed_notes.append(note)
    
    def set_project_leader_section(self):

        layout = QVBoxLayout()
        layout.setSpacing(8)

        label = QLabel("Project leader (Assigned person responsible for the work)")
        label.setObjectName("BoatTitleLabel")

        self.leader_text_edit = QTextEdit()
        self.leader_text_edit.setFixedHeight(60)
        self.leader_text_edit.setPlaceholderText("John Smith (Salary deduction)")
        self.leader_text_edit.setStyleSheet(Config.styleSheets.work_text_edit)

        layout.addWidget(label)
        layout.addWidget(self.leader_text_edit)

        return layout

    def set_work_description_section(self):

        layout = QVBoxLayout()
        layout.setSpacing(8)

        label = QLabel("Work description")
        label.setObjectName("BoatTitleLabel")

        self.description_text_edit = QTextEdit()
        self.description_text_edit.setPlaceholderText("The AC broke on one of our valued client's ships")
        self.description_text_edit.setFixedHeight(300)
        self.description_text_edit.setStyleSheet(Config.styleSheets.work_text_edit)

        layout.addWidget(label)
        layout.addWidget(self.description_text_edit)

        return layout

    def set_work_puctures_section(self):

        section_layout = QVBoxLayout()
        section_layout.setSpacing(10)

        label = QLabel("Work-related images")
        label.setObjectName("BoatTitleLabel")
        
        section_layout.addWidget(label)

        h_layout = QHBoxLayout()
        h_layout.setSpacing(15)

        self.picture_list = QListWidget()
        self.picture_list.setObjectName("FormItemList")
        self.picture_list.setViewMode(QListWidget.ViewMode.IconMode)
        self.picture_list.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.picture_list.setFlow(QListWidget.Flow.LeftToRight)
        self.picture_list.setWrapping(False)
        self.picture_list.setFixedHeight(300)
        self.picture_list.setDragDropMode(QListWidget.DragDropMode.NoDragDrop)
        self.picture_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.picture_list.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.picture_list.setStyleSheet(Config.styleSheets.work_form_list)

        h_layout.addWidget(self.picture_list)

        upload_button = QPushButton("Upload image")
        upload_button.setObjectName("SelectFormItem")
        upload_button.setFixedHeight(35)
        upload_button.setFixedWidth(200)
        upload_button.setCursor(Qt.CursorShape.PointingHandCursor)
        upload_button.setStyleSheet(Config.styleSheets.work_storage_items)
        
        upload_button.clicked.connect(self._handle_attach_file_btn)
        h_layout.addWidget(upload_button, stretch = 1, alignment = Qt.AlignmentFlag.AlignBottom)

        section_layout.addLayout(h_layout)

        return section_layout

    def set_work_components_section(self):

        layout = QVBoxLayout()
        layout.setSpacing(8)

        label = QLabel("Work components (available materials in storage)")
        label.setObjectName("BoatTitleLabel")
        
        self.components_search_input = QLineEdit()
        self.components_search_input.setPlaceholderText("Search...")
        self.components_search_input.setObjectName("WorkSearch")
        self.components_search_input.setStyleSheet(Config.styleSheets.work_add_components_search)
        self.components_search_input.returnPressed.connect(self._handle_enter_pressed)
        
        self.refresh_btn = QToolButton()
        self.refresh_btn.setObjectName("refresh")
        self.refresh_btn.setIcon(AdminEditWorkContent.icon("refresh.svg"))
        self.refresh_btn.setToolTip("Refresh")
        self.refresh_btn.setAutoRaise(True)
        self.refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.refresh_btn.setIconSize(QSize(25, 25))
        self.refresh_btn.clicked.connect(lambda: asyncio.ensure_future(self.clear_material_list()))
        
        label_search_h = QHBoxLayout()
        label_search_h.addWidget(label)
        label_search_h.setSpacing(10)
        label_search_h.addWidget(self.components_search_input)
        label_search_h.setSpacing(10)
        label_search_h.addWidget(self.refresh_btn)

        v_box = QVBoxLayout()
        v_box.setSpacing(5)
        
        self.work_components_list_top = QListWidget()
        self.work_components_list_top.setObjectName("FormItemList")
        self.work_components_list_top.setFixedHeight(300)
        self.work_components_list_top.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.work_components_list_top.setHorizontalScrollMode(QListWidget.ScrollMode.ScrollPerPixel)
        self.work_components_list_top.setStyleSheet(Config.styleSheets.work_form_list)
        
        selected_label = QLabel("Materials used for work")
        selected_label.setObjectName("BoatTitleLabel")
        
        self.work_components_list_bottom = QListWidget()
        self.work_components_list_bottom.setObjectName("FormItemList")
        self.work_components_list_bottom.setFixedHeight(300)
        self.work_components_list_bottom.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.work_components_list_bottom.setHorizontalScrollMode(QListWidget.ScrollMode.ScrollPerPixel)
        self.work_components_list_bottom.setStyleSheet(Config.styleSheets.work_form_list)
    
        v_box.addWidget(self.work_components_list_top)
        v_box.addStretch(10)
        v_box.addWidget(selected_label)
        v_box.addStretch(10)
        v_box.addWidget(self.work_components_list_bottom)
    
        layout.addLayout(label_search_h)
        layout.addLayout(v_box)

        return layout
    
    def set_missing_data_section(self):
        
        section_layout = QHBoxLayout()
        section_layout.setSpacing(10)
        section_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        
        transfered_label = QLabel("In progress (required for writing notes - 'yes'*):")
        transfered_label.setObjectName("BoatTitleLabel")
        
        self.dropdown_transfered = QComboBox()
        self.dropdown_transfered.setObjectName("Dropdown")
        self.dropdown_transfered.setStyleSheet(Config.styleSheets.dropdown_style)
        self.dropdown_transfered.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.dropdown_transfered.addItem("", None)
        self.dropdown_transfered.addItem("Yes", True)
        self.dropdown_transfered.addItem("No", False)
        self.dropdown_transfered.setFixedHeight(35)
        self.dropdown_transfered.setFixedWidth(100)
        
        is_contractor_label = QLabel("Subcontractor work:")
        is_contractor_label.setObjectName("BoatTitleLabel")
        
        self.dropdown_is_contractor = QComboBox()
        self.dropdown_is_contractor.setObjectName("Dropdown")
        self.dropdown_is_contractor.setStyleSheet(Config.styleSheets.dropdown_style)
        self.dropdown_is_contractor.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.dropdown_is_contractor.addItem("", None)
        self.dropdown_is_contractor.addItem("Yes", True)
        self.dropdown_is_contractor.addItem("No", False)
        self.dropdown_is_contractor.setFixedHeight(35)
        self.dropdown_is_contractor.setFixedWidth(100)
        
        self.min_dt = QDateTime(QDate(2000, 1, 1), QTime(0, 0))
        
        work_start_date_label = QLabel("Start (Optional):")
        work_start_date_label.setObjectName("BoatTitleLabel")
        
        self.work_start_date = QDateTimeEdit()
        self.work_start_date.setObjectName("Date")
        self.work_start_date.setStyleSheet(Config.styleSheets.date_time_select)
        self.work_start_date.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.work_start_date.setCalendarPopup(True)
        self.work_start_date.setFixedHeight(35)
        self.work_start_date.setFixedWidth(150)
        self.work_start_date.setMinimumDateTime(self.min_dt)
        
        work_finished_date_label = QLabel("End (Optional):")
        work_finished_date_label.setObjectName("BoatTitleLabel")
        
        self.work_finished_date = QDateTimeEdit()
        self.work_finished_date.setObjectName("Date")
        self.work_finished_date.setStyleSheet(Config.styleSheets.date_time_select)
        self.work_finished_date.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.work_finished_date.setCalendarPopup(True)
        self.work_finished_date.setFixedHeight(35)
        self.work_finished_date.setFixedWidth(150)
        self.work_finished_date.setMinimumDateTime(self.min_dt)
        
        section_layout.addWidget(transfered_label)
        section_layout.addWidget(self.dropdown_transfered)
        section_layout.addWidget(is_contractor_label)
        section_layout.addWidget(self.dropdown_is_contractor)
        section_layout.addWidget(work_start_date_label)
        section_layout.addWidget(self.work_start_date)
        section_layout.addWidget(work_finished_date_label)
        section_layout.addWidget(self.work_finished_date)

        return section_layout
    
    def set_status_notes_section(self):
        
        status_notes_container = QWidget()
    
        v_layout = QVBoxLayout()

        label = QLabel("Work process notes")
        label.setObjectName("BoatTitleLabel")

        self.notes_text_edit = QTextEdit()
        self.notes_text_edit.setPlaceholderText("E.g.: Delivered. Botond started the refurbishment. The part has been ordered.")
        self.notes_text_edit.setFixedHeight(60)
        self.notes_text_edit.setStyleSheet(Config.styleSheets.work_text_edit)
        
        v_layout.addWidget(label)
        v_layout.addWidget(self.notes_text_edit)
        v_layout.addWidget(self.notes_table)

        status_notes_container.setLayout(v_layout)
        
        return status_notes_container
    
    def set_footer_buttons(self):

        layout = QHBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        confirm_btn = QPushButton("OK")
        confirm_btn.setObjectName("WorkBtn")
        confirm_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        confirm_btn.setFixedHeight(35)
        confirm_btn.setFixedWidth(200)
        confirm_btn.setStyleSheet(Config.styleSheets.work_btn)
        confirm_btn.clicked.connect(lambda: asyncio.ensure_future(self.__btn_callback(0)))

        cancel_btn = QPushButton("Delete")
        cancel_btn.setObjectName("WorkBtn")
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.setFixedHeight(35)
        cancel_btn.setFixedWidth(200)
        cancel_btn.setStyleSheet(Config.styleSheets.work_btn)
        cancel_btn.clicked.connect(lambda: asyncio.ensure_future(self.__btn_callback(1)))

        layout.addWidget(confirm_btn)
        layout.addWidget(cancel_btn)

        return layout
    
    def set_fields_data_from_prev_reference(self):

        if self.previous_admin_work_data is not None:
            
            if self.previous_admin_work_data.transfered is True:
                
                self.status_notes_section.setVisible(True)
            
            self.current_work_id = self.previous_admin_work_data.work_id
            leader = self.previous_admin_work_data.leader
            description = self.previous_admin_work_data.description if self.previous_admin_work_data.description is not None else ""
            start_date = self.previous_admin_work_data.start_date if self.previous_admin_work_data.start_date is not None else self.min_dt
            finished_date = self.previous_admin_work_data.finished_date if self.previous_admin_work_data.finished_date is not None else self.min_dt
            transfered = self.previous_admin_work_data.transfered
            is_contractor = self.previous_admin_work_data.is_contractor
            status = self.previous_admin_work_data.status if self.previous_admin_work_data.status is not None else None
            
            if self.previous_admin_work_data.images != []:
                
                for image in self.previous_admin_work_data.images:
                    
                    if image.id not in self.image_map:
                        
                        self.image_map[image.id] = image.img
                    
                    self.attached_images.append(image.id)
                    
                asyncio.ensure_future(self._handle_attach_files())
            
            self.leader_text_edit.setText(leader)
            
            self.description_text_edit.setText(description)
            
            transfered_index = self.dropdown_transfered.findData(transfered)
            self.dropdown_transfered.setCurrentIndex(transfered_index if transfered_index != -1 else 0)
            
            is_contractor_index = self.dropdown_is_contractor.findData(is_contractor)
            self.dropdown_is_contractor.setCurrentIndex(is_contractor_index if is_contractor_index != -1 else 0)
            
            self.work_start_date.setDateTime(start_date)
            
            self.work_finished_date.setDateTime(finished_date)
            
            if self.previous_admin_work_data.work_accessories != []:
                
                for accessorie in self.previous_admin_work_data.work_accessories:
                
                    for material in self.available_materials.items:
                    
                        if accessorie.component_id == material.id:

                            material_copy = copy.deepcopy(material)
                            
                            material_copy.quantity = accessorie.quantity
                            
                            self.work_accessories.items.append(material_copy)
                
            if status is not None:
                
                self.notes_table.load_data([self.previous_admin_work_data])

    async def reset_form(self, partial_reset: bool):
                       
        await self.clear_material_list()
        
        self.status_notes_section.setVisible(False)
     
        self.previous_admin_work_data = None
        
        self.current_work_id = None
        
        self.changed_notes.clear()

        if partial_reset == False: 
            
            self.table.clearContents()
            self.table.setRowCount(0)
            
        self.leader_text_edit.clear()

        self.deleted_img_bytes.clear()
        
        self.description_text_edit.clear()
        
        self.components_search_input.clear()
        
        self.dropdown_transfered.setCurrentIndex(0)

        self.dropdown_is_contractor.setCurrentIndex(0)
        
        self.work_start_date.setDateTime(self.min_dt)
        
        self.work_finished_date.setDateTime(self.min_dt)
        
        self.work_content.clear_prev_search() 
        
        self.notes_text_edit.clear()
        
        self.notes_table.clearContents()
        self.notes_table.setRowCount(0)
        
        for i in range(self.picture_list.count()):
            
            item = self.picture_list.item(i)
                        
            if item is not None and isinstance(item, QListWidgetItem):
                
                widget = self.picture_list.itemWidget(item)

                if isinstance(widget, ImageItemWidget):
                    
                    if widget.file_path is not None or widget.file_path != "":
                        
                        file = widget.file_path
                    
                    if widget.image_id is not None:
                        
                        file = widget.image_id
                        
                    if file:
                        
                        self._handle_delete_image(file)

    @asyncSlot()
    async def __btn_callback(self, idx: int):
        
        parent_widget = self

        if parent_widget:
            
            self.spinner.show(parent_widget)
        
        if self._btn_lock.locked():
            
            self.log.warning("Button callback ignored because another operation is running")
            
            return

        async with self._btn_lock:
            
            if idx == 0:
            
                await self.compare_fields_data_with_previous_reference()

            elif idx == 1:
                
                await self.reset_form(False)
                    
            self.spinner.hide()
    
    def compare_str_field(self, prev_data, text: str) -> str | None:
        
        if text != prev_data:
            
            return text

        return None
    
    async def compare_fields_data_with_previous_reference(self):
      
        if self.previous_admin_work_data is not None:
            
            min_date = self.min_dt.toPyDateTime()
                
            leader_field = self.leader_text_edit.toPlainText().strip()
            description_field = self.description_text_edit.toPlainText().strip()
            start_date_field = self.work_start_date.dateTime().toPyDateTime()
            finished_date_field = self.work_finished_date.dateTime().toPyDateTime()
            new_note_field = self.notes_text_edit.toPlainText().strip()
            transfered_field = self.dropdown_transfered.currentData()
            is_contractor_field = self.dropdown_is_contractor.currentData()

            leader = self.compare_str_field(self.previous_admin_work_data.leader, leader_field)
            
            description = self.compare_str_field(self.previous_admin_work_data.description, description_field)

            transfered = True if transfered_field is True else False
            
            is_contractor = None if is_contractor_field is None or \
                is_contractor_field == self.previous_admin_work_data.is_contractor else bool(is_contractor_field)
            
            start_date = None
            if start_date_field != min_date or start_date != self.previous_admin_work_data.start_date:
                
                start_date = start_date_field
                
            finished_date = None
            if finished_date_field != min_date:
                
                finished_date = finished_date_field
                
            new_note = None
            if new_note_field != "":
                
                new_note = new_note_field

            attached_images_path = [
                img for img in self.attached_images if isinstance(img, str)
            ]
            
            work_accessories = self.filtering_list_with_reference_data(
                check_deleted = False,
                previous_data = self.previous_admin_work_data,
                modified_list = self.work_accessories.items
            )
           
            deleted_work_material = self.filtering_list_with_reference_data(
                check_deleted = True,
                previous_data = self.previous_admin_work_data,
                modified_list = self.work_accessories.items
            )
          
            previous_available_material = await self.material_cache_service.get_material_data_from_cache(
                material_cache_id = Config.redis.cache.material.id,
                exp = Config.redis.cache.material.exp
            )
            
            available_materials = self.filtering_list_with_reference_data(
                check_deleted = False,
                previous_data = previous_available_material.items,
                modified_list = self.available_materials.items
            )
          
            deleted_available_material = self.filtering_list_with_reference_data(
                check_deleted = True,
                previous_data = previous_available_material.items,
                modified_list = self.available_materials.items
            )

            await self.handle_update_work(
                leader = leader,
                description = description,
                prev_transfered = self.previous_admin_work_data.transfered,
                transfered = transfered,
                is_contractor = is_contractor,
                start_date = start_date,
                finished_date = finished_date,
                new_note = new_note,
                attached_images_path = attached_images_path,
                work_accessories = work_accessories,
                deleted_work_material = deleted_work_material,
                available_materials = available_materials,
                deleted_available_material = deleted_available_material,
                changed_notes = self.changed_notes,
                deleted_img_bytes = self.deleted_img_bytes
            )

    def getattr_id(self, obj: object) -> int:
        
        if isinstance(obj, MaterialData):
            
            return obj.id
        
        elif isinstance(obj, AdminWorkAccessorie):
            
            return obj.component_id
    
    def filtering_list_with_reference_data(self,
        check_deleted: bool, 
        previous_data: t.Union[t.List[MaterialData], t.List[AdminEditWorkData]], 
        modified_list: t.List[MaterialData]
        ) -> t.List[MaterialData]: # list can be empty
        # print(check_deleted)
        # print(type(previous_data))
        # print(modified_list)
        
        if all(isinstance(prev, MaterialData) for prev in previous_data):
            
            iterable = previous_data
            
        elif isinstance(previous_data, AdminEditWorkData):
                
            iterable = previous_data.work_accessories

        if check_deleted == False:
            
            results = [
                material for material in modified_list
                if not any(self.getattr_id(previous) == material.id and 
                    self.utility_calculator.floats_are_equal(
                        previous.quantity, 
                        material.quantity
                    )
                    for previous in iterable 
                )
            ]
      
            return results
        
        elif check_deleted == True:
            
            results = [
                prev_material for prev_material in iterable
                if not any(current_material.id == self.getattr_id(prev_material)
                    for current_material in modified_list
                )
            ]
       
            return results
    
    async def handle_update_work(self,
        leader: str | None,
        description: str | None,
        prev_transfered: bool,
        transfered: bool,
        is_contractor: bool | None,
        start_date: datetime | None,
        finished_date: datetime | None,
        new_note: str | None,
        attached_images_path: t.List[str],
        work_accessories: t.List[MaterialData],
        deleted_work_material: t.List[MaterialData],
        available_materials: t.List[MaterialData],
        deleted_available_material: t.List[MaterialData],
        changed_notes: t.List[AdminWorkStatusNote] = [],
        deleted_img_bytes: dict = {}
        ):
 
        self.log.debug("Before updating work, final parameters are: leader - %s, description: %s, transferred / in progress: %s, is_contractor: %s, start_date: %s, finished_date: %s, new_note: %s, attached_images: %s, work_accessories: %s, deleted_work_material: %s, available_materials: %s, deleted_available_material: %s, changed_notes: %s, deleted_image_ids: %s" % (
            str(leader), 
            str(description), 
            str(transfered), 
            str(is_contractor), 
            str(start_date), 
            str(finished_date), 
            str(new_note), 
            str(attached_images_path), 
            str(work_accessories), 
            str(deleted_work_material), 
            str(available_materials), 
            str(deleted_available_material), 
            str(changed_notes), 
            ", ".join(str(img_id) for img_id, _ in deleted_img_bytes.items())
            )
        )
        
        confirm_text = f"""
        <br>You are modifying the following data:<br><br>
        Project lead: {leader if leader is not None else "No changes"}<br>
        Work description: {description if description is not None else "No changes"}<br>
        Delivered: {"Yes" if transfered is True else "No"}<br>
        Handled by subcontractor: {"Yes" if is_contractor is True else "No" if is_contractor is False else "No changes"}<br>
        Munka kezdete: {start_date.strftime(Config.time.timeformat) if start_date is not None else "Not assigned yet"}<br>
        Work completion: {finished_date.strftime(Config.time.timeformat) if finished_date is not None else "Not assigned yet" }<br>
        New event: {new_note if new_note is not None else "No new note"}<br>
        New image attached: {len(attached_images_path)} pcs<br>
        {self.format_material_list_for_txt(work_accessories, "Work accessories")}
        {self.format_material_list_for_txt(deleted_work_material, "Deleted work materials")}
        {self.format_material_list_for_txt(available_materials, "Available materials")}
        {self.format_material_list_for_txt(deleted_available_material, "Deleted materials")}
        <br>Biztosan folytatod?<br>
        """
        
        self.confirm_action_modal.set_action_message(f"<div align='center'>{confirm_text}</div>")

        confirm = await self.confirm_action_modal.exec_async()
        
        if not confirm:

            return
        
        elif confirm:
            
            try:
                
                if self.current_work_id is not None:
                    
                    await queries.update_work_by_id(
                        work_id = self.current_work_id,
                        leader = leader,
                        description = description,
                        prev_transfered = prev_transfered,
                        transfered = transfered,
                        is_contractor = is_contractor,
                        start_date = start_date,
                        finished_date = finished_date,
                        new_note = new_note,
                        new_imgs = attached_images_path,
                        work_accessories = work_accessories,
                        deleted_work_material = deleted_work_material,
                        available_materials = available_materials,
                        deleted_available_material = deleted_available_material,
                        changed_notes = changed_notes,
                        deleted_img_bytes = deleted_img_bytes
                    )

                    self.refresh_todo.emit(True)

                    await self.reset_form(False)
                    
            except Exception as e:
                
                self.log.exception("An unexpected error occurred during the update %s" % str(e))
            
    def format_material_list_for_txt(self, materials: t.List[MaterialData], title: str) -> str:
        
        if len(materials) > 0:
            
            formatted_items = ", ".join(
                f"{m.name}[{m.manufacture_number}]" if m.name or m.manufacture_number else "N/A"
                for m in materials
            )
            
            return f"{title}: {formatted_items}<br>"

        return f"{title}: No changes<br>"
    
    def _handle_attach_file_btn(self):
    
        parent_widget = self
    
        if parent_widget:
            
            self.spinner.show(parent_widget)
        
        file_paths, _ = QFileDialog.getOpenFileNames(
            self, 
            "Select files"
            "Select images",
            "",
            "Images (*.png *.jpg *.jpeg *.bmp *.webp)"
        )

        if len(file_paths) == 0:
            
            self.log.warning("No file selected for attaching")
            
            self.spinner.hide()
            
            return
        
        for file_path in file_paths:
            
            self.log.debug("Selected file path: %s" % file_path)
            
            self.attached_images.append(file_path)
        
        if len(self.attached_images) > 0:
            
            asyncio.ensure_future(self._handle_attach_files())
    
    def _handle_delete_image(self, file_path_to_delete: t.Union[str, int]):
        # print("Type", type(file_path_to_delete))
        # print("Attached images", self.attached_images)
        # for i in self.attached_images:
        #     print(i, type(i))
            
        if isinstance(file_path_to_delete, str):
            
            text = file_path_to_delete
            
        elif isinstance(file_path_to_delete, int):
            
            byte = self.image_map.get(file_path_to_delete, None)
            
            text = f"Bytes({len(byte)})"
    
            self.deleted_img_bytes[file_path_to_delete] = byte
            
            self.image_map.pop(file_path_to_delete)
        
        self.log.debug("Request to delete image: %s" % text)
            
        if file_path_to_delete in self.attached_images:
            
            self.attached_images.remove(file_path_to_delete)
   
            asyncio.ensure_future(self._handle_attach_files())
            
    async def _handle_attach_files(self):
        
        self.picture_list.clear()
    
        try:
            
            valid_files = []
    
            for file_path in self.attached_images:
                
                image_id = None
                
                if isinstance(file_path, str):
                    
                    pixmap = QPixmap(file_path)

                    if pixmap.isNull():
                        
                        self.log.warning("Removing non-image: %s", file_path)
                        
                        continue

                    valid_files.append(file_path)

                elif isinstance(file_path, int):
                    # filepath = image.id
                    
                    for key, value in self.image_map.items():
                        
                        for k, _ in self.deleted_img_bytes.items():
                            
                            if file_path == k:
                                
                                self.image_map.pop(k)
                                
                                self.attached_images.remove(k)
                            
                        if key == file_path:
                            
                            file_path = value
                            
                            image_id = key
                            
                            valid_files.append(key)
                
                item = QListWidgetItem()
                item.setSizeHint(QSize(400, 280))

                widget = ImageItemWidget(file_path, self, image_id)
                
                self.picture_list.addItem(item)
                self.picture_list.setItemWidget(item, widget)

            self.attached_images = valid_files
            
            # print("ATTACHED", self.attached_images)
            # for k, _ in self.deleted_img_bytes.items():
            #     print("DELETED", k)
            # for k, _ in self.image_map.items():
            #     print("KEY MAP", k)
                
        except Exception as e:
            
            self.log.exception("Error processing image %s: %s" % (
                os.path.basename(file_path),
                str(e)
                )
            )

        finally:
    
            self.spinner.hide()

    # Available in storage
    def populate_work_components_list(self, data_list: t.List[MaterialData]):
        
        if self._recalculate_widths is True:
            
            self.row_maximum_col_widths.clear()
        
        scroll_bar = self.work_components_list_top.verticalScrollBar()
        scroll_pos = scroll_bar.value()
        
        self.work_components_list_top.clear()

        if len(data_list) > 0:
            
            self.log.debug("Populating work components available in storage list with %d items of (%s) data" % (
                len(data_list),
                data_list[0].__class__.__name__
                )
            )
        
            self.work_components_list_top.setUniformItemSizes(False)
            
            font = QFont()
            font.setPointSize(10)
            font.setBold(True)

            if isinstance(data_list[0], MaterialData):
                
                for data in data_list:
            
                    if data.is_deleted == True:
                        continue
                    
                    name = data.name if data.name is not None else "N/A"
                    
                    manufacture_number = data.manufacture_number if data.manufacture_number is not None else "N/A"
                    
                    quantity = f"{data.quantity:.4f}" if data.quantity is not None else "N/A"
                    
                    unit = data.unit if data.unit is not None else "N/A"
                    
                    manufacture_date = data.manufacture_date.strftime(Config.time.timeformat) if data.manufacture_date is not None else "N/A"
                    
                    price = f"{data.price:,.2f}".replace(",", ".") + " HUF" if data.price is not None else "N/A"
                    
                    purchase_source = data.purchase_source if data.purchase_source is not None else "N/A"
                    
                    purchase_date = data.purchase_date.strftime(Config.time.timeformat) if data.purchase_date is not None else "N/A"
                    
                    inspection_date = data.inspection_date.strftime(Config.time.timeformat) if data.inspection_date is not None else "N/A"
                    
                    list_item = QListWidgetItem()
                    
                    container = QWidget()
                    container.setFixedHeight(35)
                    
                    edit_btn = QPushButton()
                    edit_btn.setObjectName("TrashButton")
                    edit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
                    edit_btn.setIcon(AdminEditWorkContent.icon("add.svg"))
                    edit_btn.setIconSize(QSize(20, 20))
                    edit_btn.setToolTip("Add")
                
                    id_label = QLabel(str(data.id).strip())
                    id_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
                    id_label.setFont(font)
                    id_label.setToolTip(str(data.id).strip())

                    storage_id_label = QLabel(str(data.storage_id).strip())
                    storage_id_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
                    storage_id_label.setFont(font)
                    storage_id_label.setToolTip(str(data.storage_id).strip())

                    name_label = QLabel(name.strip())
                    name_label.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
                    name_label.setFont(font)
                    name_label.setToolTip(name.strip())

                    manufacture_number_label = QLabel(manufacture_number.strip())
                    manufacture_number_label.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
                    manufacture_number_label.setFont(font)
                    manufacture_number_label.setToolTip(manufacture_number.strip())

                    self.in_storage_label = QLabel("In storage: " + quantity.strip())
                    self.in_storage_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                    self.in_storage_label.setFont(font)
                    self.in_storage_label.setToolTip(quantity.strip())
                    
                    add_to_quantity_sb = QDoubleSpinBox()
                    add_to_quantity_sb.setDecimals(4)
                    add_to_quantity_sb.setSingleStep(0.01)
                    add_to_quantity_sb.setMinimum(0)
                    add_to_quantity_sb.setMaximum(data.quantity)
                    add_to_quantity_sb.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
                    add_to_quantity_sb.setObjectName("input_quantity")
                    
                    edit_btn.clicked.connect(lambda _, material = data, spin_box = add_to_quantity_sb, is_on_work_btn = False: 
                        self._handle_current_material(material, spin_box, is_on_work_btn)
                    )
                    
                    unit_label = QLabel(unit.strip())
                    unit_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                    unit_label.setFont(font)
                    unit_label.setToolTip(unit.strip())

                    manufacture_date_label = QLabel(manufacture_date.strip())
                    manufacture_date_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                    manufacture_date_label.setFont(font)
                    manufacture_date_label.setToolTip(manufacture_date.strip())

                    price_label = QLabel(price.strip())
                    price_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                    price_label.setFont(font)
                    price_label.setToolTip(price.strip())

                    purchase_source_label = QLabel(purchase_source.strip())
                    purchase_source_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                    purchase_source_label.setFont(font)
                    purchase_source_label.setToolTip(purchase_source.strip())

                    purchase_date_label = QLabel(purchase_date.strip())
                    purchase_date_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                    purchase_date_label.setFont(font)
                    purchase_date_label.setToolTip(purchase_date.strip())

                    inspection_date_label = QLabel(inspection_date.strip())
                    inspection_date_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                    inspection_date_label.setFont(font)
                    inspection_date_label.setToolTip(inspection_date.strip())
                    
                    quantity_range = self.utility_calculator.check_quantity(data.quantity)
                    
                    if quantity_range == QuantityRange.ZERO_TO_THREE:
                        
                        container.setStyleSheet(Config.styleSheets.failed)
                        
                    elif quantity_range == QuantityRange.THREE_TO_FIVE:
                        
                        container.setStyleSheet(Config.styleSheets.warning)
                        
                    else: 
                        
                        container.setStyleSheet(Config.styleSheets.success)
                        
                    h_layout = QHBoxLayout(container)
                    h_layout.setContentsMargins(0, 0, 0, 0)
                    
                    widgets = [
                        edit_btn,
                        id_label,
                        storage_id_label,
                        name_label,
                        manufacture_number_label,
                        self.in_storage_label,
                        add_to_quantity_sb,
                        unit_label,
                        manufacture_date_label,
                        price_label,
                        purchase_source_label,
                        purchase_date_label,
                        inspection_date_label
                    ]
                    
                    if self.all_collumns is None:
                        
                        self.all_collumns = len(widgets)

                    if self._recalculate_widths is True:
                
                        current_row_max_col_width = max([QFontMetrics(w.font()).horizontalAdvance(w.text()) 
                            for w in widgets if isinstance(w, QLabel)])
                        
                        self.row_maximum_col_widths.append(current_row_max_col_width + 10)
                    
                    for w in widgets:
                        
                        if isinstance(w, QLabel):

                            w.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
                            w.setContentsMargins(0, 0, 0, 0)
                            w.setWordWrap(False)
                    
                        h_layout.addWidget(w)
                
                    list_item.setSizeHint(container.sizeHint())
                    
                    self.work_components_list_top.addItem(list_item)
                    self.work_components_list_top.setItemWidget(list_item, container)
                    self.work_components_list_top.setSpacing(5)
                    
                    list_item.setData(Qt.ItemDataRole.UserRole, data_list)
                
                self.calculate_globa_col_width_and_apply_to_relevant_list(self.work_components_list_top)
                
                # print("Available list:", data_list)  
                QTimer.singleShot(0, lambda: scroll_bar.setValue(scroll_pos))

        else: 
            
            self.log.info("Populating work components available in storage list with 0 items")
            
    # Work accessories
    def populate_work_components_list_on_work(self, data_list: t.List[MaterialData]):
        
        if self._recalculate_widths is True:
            
            self.row_maximum_col_widths.clear()
        
        scroll_bar = self.work_components_list_bottom.verticalScrollBar()
        scroll_pos = scroll_bar.value()
        
        self.work_components_list_bottom.clear()

        if len(data_list) > 0:
            
            self.log.debug("Populating work components available on work list with %d items of (%s) data" % (
                len(data_list),
                data_list[0].__class__.__name__
                )
            )
        
            self.work_components_list_bottom.setUniformItemSizes(False)
            
            font = QFont()
            font.setPointSize(10)
            font.setBold(True)
            
            if isinstance(data_list[0], MaterialData):
                
                for data in data_list:
                    
                    if data.is_deleted == True:
                        continue
                    
                    name = data.name if data.name is not None else "N/A"
                    
                    manufacture_number = data.manufacture_number if data.manufacture_number is not None else "N/A"
                    
                    quantity = f"{data.quantity:.4f}" if data.quantity is not None else "N/A"
                    
                    unit = data.unit if data.unit is not None else "N/A"
                    
                    manufacture_date = data.manufacture_date.strftime(Config.time.timeformat) if data.manufacture_date is not None else "N/A"
                    
                    price = f"{data.price:,.2f}".replace(",", ".") + " HUF" if data.price is not None else "N/A"
                    
                    purchase_source = data.purchase_source if data.purchase_source is not None else "N/A"
                    
                    purchase_date = data.purchase_date.strftime(Config.time.timeformat) if data.purchase_date is not None else "N/A"
                    
                    inspection_date = data.inspection_date.strftime(Config.time.timeformat) if data.inspection_date is not None else "N/A"
                    
                    list_item = QListWidgetItem()
                    
                    container = QWidget()
                    container.setFixedHeight(35)
                    
                    edit_btn = QPushButton()
                    edit_btn.setObjectName("TrashButton")
                    edit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
                    edit_btn.setIcon(AdminEditWorkContent.icon("trash.svg"))
                    edit_btn.setIconSize(QSize(20, 20))
                    edit_btn.setToolTip("Add")
                
                    id_label = QLabel(str(data.id).strip())
                    id_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
                    id_label.setFont(font)
                    id_label.setToolTip(str(data.id).strip())

                    storage_id_label = QLabel(str(data.storage_id).strip())
                    storage_id_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
                    storage_id_label.setFont(font)
                    storage_id_label.setToolTip(str(data.storage_id).strip())

                    name_label = QLabel(name.strip())
                    name_label.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
                    name_label.setFont(font)
                    name_label.setToolTip(name.strip())

                    manufacture_number_label = QLabel(manufacture_number.strip())
                    manufacture_number_label.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
                    manufacture_number_label.setFont(font)
                    manufacture_number_label.setToolTip(manufacture_number.strip())

                    self.in_storage_label = QLabel("Added to work: " + quantity.strip())
                    self.in_storage_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                    self.in_storage_label.setFont(font)
                    self.in_storage_label.setToolTip(quantity.strip())
                    
                    remove_work_quantity_sb = QDoubleSpinBox()
                    remove_work_quantity_sb.setDecimals(4)
                    remove_work_quantity_sb.setSingleStep(0.01)
                    remove_work_quantity_sb.setMinimum(0)
                    remove_work_quantity_sb.setMaximum(data.quantity)
                    remove_work_quantity_sb.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
                    remove_work_quantity_sb.setObjectName("input_quantity")
                    
                    edit_btn.clicked.connect(lambda _, material = data, spin_box = remove_work_quantity_sb, is_on_work_btn = True: 
                        self._handle_current_material(material, spin_box, is_on_work_btn)
                    )

                    unit_label = QLabel(unit.strip())
                    unit_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                    unit_label.setFont(font)
                    unit_label.setToolTip(unit.strip())

                    manufacture_date_label = QLabel(manufacture_date.strip())
                    manufacture_date_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                    manufacture_date_label.setFont(font)
                    manufacture_date_label.setToolTip(manufacture_date.strip())

                    price_label = QLabel(price.strip())
                    price_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                    price_label.setFont(font)
                    price_label.setToolTip(price.strip())

                    purchase_source_label = QLabel(purchase_source.strip())
                    purchase_source_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                    purchase_source_label.setFont(font)
                    purchase_source_label.setToolTip(purchase_source.strip())

                    purchase_date_label = QLabel(purchase_date.strip())
                    purchase_date_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                    purchase_date_label.setFont(font)
                    purchase_date_label.setToolTip(purchase_date.strip())

                    inspection_date_label = QLabel(inspection_date.strip())
                    inspection_date_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                    inspection_date_label.setFont(font)
                    inspection_date_label.setToolTip(inspection_date.strip())

                    h_layout = QHBoxLayout(container)
                    h_layout.setContentsMargins(0, 0, 0, 0)
                    
                    widgets = [
                        edit_btn,
                        id_label,
                        storage_id_label,
                        name_label,
                        manufacture_number_label,
                        self.in_storage_label,
                        remove_work_quantity_sb,
                        unit_label,
                        manufacture_date_label,
                        price_label,
                        purchase_source_label,
                        purchase_date_label,
                        inspection_date_label
                    ]
                    
                    if self.all_collumns is None:
                        
                        self.all_collumns = len(widgets)

                    if self._recalculate_widths is True:
                
                        current_row_max_col_width = max([QFontMetrics(w.font()).horizontalAdvance(w.text()) 
                            for w in widgets if isinstance(w, QLabel)])
                        
                        self.row_maximum_col_widths.append(current_row_max_col_width + 10)
                    
                    for w in widgets:
                        
                        if isinstance(w, QLabel):

                            w.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
                            w.setContentsMargins(0, 0, 0, 0)
                            w.setWordWrap(False)
                    
                        h_layout.addWidget(w)
                
                    list_item.setSizeHint(container.sizeHint())
                    
                    self.work_components_list_bottom.addItem(list_item)
                    self.work_components_list_bottom.setItemWidget(list_item, container)
                    self.work_components_list_bottom.setSpacing(5)
                    
                    list_item.setData(Qt.ItemDataRole.UserRole, data_list)
                
                self.calculate_globa_col_width_and_apply_to_relevant_list(self.work_components_list_bottom)
                
                # print("Available list:", data_list)  
                QTimer.singleShot(0, lambda: scroll_bar.setValue(scroll_pos))
                
            else:
                
                self.log.info("Populating work components available on work list with 0 items")
                
    def _handle_current_material(self, material: MaterialData, spin_box: QDoubleSpinBox, is_on_work_btn: bool):
        """
        Adds or removes a quantity of a material between the warehouse and work lists.

        This method moves a quantity of the specified `material` object between two lists:
        - `self.available_materials.items` (warehouse)
        - `self.work_accessories.items` (materials assigned to the work)

        The direction of the operation is determined by the `is_on_work_btn` flag:
        - True  → remove material from the work list and return it to the warehouse
                (work_accessories.items → available_materials.items)
        - False → add material to the work list
                (available_materials.items → work_accessories.items)

        Important notes about the `material` parameter:
        - This is the exact MaterialData object stored in the source list (either warehouse or work list),
        depending on the button that triggered the operation.
        - Modifying its attributes (e.g., `quantity`) will directly affect the source list.
        - If a separate instance is needed for the target list to avoid shared state, make a copy
        (e.g., via `copy.deepcopy(material)`).

        Behavior:
        - If the material is not yet in the target list, it will be added with the quantity
        specified in the spin_box.
        - If the material already exists in the target list, only its quantity will be updated.
        - The source list's quantity is always reduced accordingly.
        - If the quantity in the source list reaches 0, the material is removed from that list.

        Parameters
        ----------
        material : MaterialData
            The MaterialData object corresponding to the clicked row.
            This object comes from either `available_materials.items` or `work_accessories.items`,
            depending on the button clicked.
        
        spin_box : QDoubleSpinBox
            The spin box associated with the current row, determining the quantity to transfer.

        is_on_work_btn : bool
            Determines the direction of transfer:
            - True  → move material from work list to warehouse
            - False → move material from warehouse to work list
        """
        current_quantity = spin_box.value()
        
        if self.utility_calculator.is_zero(current_quantity) == True:
            
            self.log.debug("Move operation skipped because quantity is zero: %s" % current_quantity)
            
            return
        
        material_to_move = copy.deepcopy(material)
        
        setattr(material_to_move, "quantity", current_quantity)
        
        self.log.debug("Starting material move. Material ID: %s | Quantity to move: %s | Direction: %s" % (
            material_to_move.id,
            current_quantity,
            "WORK -> AVAILABLE" if is_on_work_btn else "AVAILABLE -> WORK"
            )
        )
        
        if is_on_work_btn == True:
            
            found_work_accessori_index = -1
            
            for i, work_accessori in enumerate(self.work_accessories.items):
                
                if work_accessori.id == material_to_move.id:
                    
                    found_work_accessori_index = i
                    
                    break
            
            if found_work_accessori_index != -1:
                
                work_accessori_in_list = self.work_accessories.items[found_work_accessori_index]
                # print(work_accessori_in_list)
                
                before_quantity = work_accessori_in_list.quantity
                
                remaining_quantity = self.utility_calculator.arithmetic_decimal(
                    work_accessori_in_list.quantity,
                    current_quantity,
                    "subtract"
                )
                
                setattr(work_accessori_in_list, "quantity", float(remaining_quantity))
                
                self.log.debug("WORK subtract material ID %s quantity changed: %s -> %s" % (
                        work_accessori_in_list.id,
                        before_quantity,
                        work_accessori_in_list.quantity
                    )
                )
                
                if self.utility_calculator.is_zero(work_accessori_in_list.quantity):
                            
                    self.log.debug("Material ID %s removed from WORK list because quantity became zero." % (
                         material_to_move.id
                        )
                    )
                    
                    self.work_accessories.items.pop(found_work_accessori_index)
            
            found_available_material = None
            
            for available_material in self.available_materials.items:
                
                if available_material.id == material_to_move.id:
                    
                    found_available_material = available_material
                    
                    break
            
            if found_available_material is not None:
                
                before_quantity = found_available_material.quantity
                
                new_quantity = self.utility_calculator.arithmetic_decimal(
                    found_available_material.quantity,
                    current_quantity,
                    "add"
                )
                
                setattr(found_available_material, "quantity", float(new_quantity))
                
                self.log.debug("AVAILABLE add material ID %s quantity changed: %s -> %s" % (
                    found_available_material.id,
                    before_quantity,
                    found_available_material.quantity
                    )
                )
                
            else:
                
                self.available_materials.items.append(material_to_move)
                
                self.log.debug("Material ID %s added to AVAILABLE list with quantity: %s" % (
                    material_to_move.id,
                    material_to_move.quantity
                    )
                )
            
        elif is_on_work_btn == False:
            
            found_available_material_index = -1
            
            for i, available_material in enumerate(self.available_materials.items):
                
                if available_material.id == material_to_move.id:
                    
                    found_available_material_index = i
                    
                    break
            
            if found_available_material_index != -1:
                
                available_material_in_list = self.available_materials.items[found_available_material_index]
                
                before_quantity = available_material_in_list.quantity
                
                remaining_quantity = self.utility_calculator.arithmetic_decimal(
                    available_material_in_list.quantity,
                    current_quantity,
                    "subtract"
                )
                
                setattr(available_material_in_list, "quantity", float(remaining_quantity))
                
                self.log.debug("AVAILABLE subtract material ID %s quantity changed: %s -> %s" % (
                    available_material_in_list.id,
                    before_quantity,
                    available_material_in_list.quantity
                    )
                )
                
                if self.utility_calculator.is_zero(available_material_in_list.quantity):
                    
                    self.available_materials.items.pop(found_available_material_index)
                    
                    self.log.debug("Material ID %s removed from AVAILABLE list because quantity became zero." % (
                        material_to_move.id
                        )
                    )
            
            found_work_accessorie = None
            
            for work_accessorie in self.work_accessories.items:
                
                if work_accessorie.id == material_to_move.id:
                    
                    found_work_accessorie = work_accessorie
                    
                    break
            
            if found_work_accessorie is not None:
                
                before_quantity = found_work_accessorie.quantity
                
                new_quantity = self.utility_calculator.arithmetic_decimal(
                    found_work_accessorie.quantity,
                    current_quantity,
                    "add"
                )
                
                setattr(found_work_accessorie, "quantity", float(new_quantity))
                
                self.log.debug("WORK add material ID %s quantity changed: %s -> %s" % (
                    found_work_accessorie.id,
                    before_quantity,
                    found_work_accessorie.quantity
                    )
                )
            
            else:
                
                self.work_accessories.items.append(material_to_move) 
                
                self.log.debug("Material ID %s added to WORK list with quantity: %s" % (
                    material_to_move.id,
                    material_to_move.quantity
                    )
                )           
            
        # print(self.available_materials.items)
        # print(self.work_accessories.items)
        self.populate_work_components_list(self.available_materials.items)
        self.populate_work_components_list_on_work(self.work_accessories.items)
                                
    def calculate_globa_col_width_and_apply_to_relevant_list(self, list_widget: QListWidget):
    
        if len(self.row_maximum_col_widths) > 0:
          
            self.global_max_col_width: int = max(self.row_maximum_col_widths)

            if self.global_max_col_width is not None:
                    
                if self.all_collumns is not None:
                    
                    for i in range(list_widget.count()):
                        
                        row_width = self.global_max_col_width * self.all_collumns
                        
                        item = list_widget.item(i)
                        
                        if item is not None:
                            
                            container = list_widget.itemWidget(item)

                            container.setFixedWidth(row_width)
                            
                            item.setSizeHint(QSize(row_width, item.sizeHint().height()))
                            
                            layout = container.layout()
                            
                            for j in range(layout.count()):
                                
                                child = layout.itemAt(j)
                                
                                if child is not None:
                                
                                    widget = child.widget()
                                    
                                    if widget is not None:
                                        
                                        x = 1.5
                                        
                                        if isinstance(widget, QDoubleSpinBox):
                                            
                                            widget.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                                            widget.setFixedWidth(50)
                                    
                                        if j >= 3 and j <= 4:
                                        
                                            widget.setFixedWidth(int(self.global_max_col_width * x))
                                            
                                        elif j > 4:
                                            
                                            widget.setFixedWidth(self.global_max_col_width)
                                            
                                        else: 
                                        
                                            widget.setFixedWidth(40)  
  
            self._recalculate_widths = False 

    async def clear_material_list(self):
       
        self.work_accessories.items.clear()
        
        self.available_materials.items.clear()
        
        await self.material_cache_service.clear_cache(Config.redis.cache.material.id) 

        await self.work_content.load_cache_data()
            
    def _handle_enter_pressed(self):
                
        text_lower = self.components_search_input.text().strip().lower()
        
        if text_lower == "":
            
            self.work_content.on_data_loaded(self.available_materials)
        
            return
        
        filtered_items = [
            material for material in self.available_materials.items 
            if material.is_deleted == False
            if (
                (material.id is not None and text_lower in str(material.id).lower()) or
                (text_lower in str(material.storage_id).lower()) or
                (material.name and text_lower in material.name.lower()) or
                (material.manufacture_number and text_lower in material.manufacture_number.lower()) or
                (material.quantity is not None and text_lower in f"{material.quantity:.4f}") or
                (material.unit and text_lower in material.unit.lower()) or
                (material.manufacture_date and text_lower in str(material.manufacture_date).lower()) or
                (material.price is not None and text_lower in f"{material.price:.2f}") or
                (material.purchase_source and text_lower in material.purchase_source.lower()) or
                (material.purchase_date and text_lower in str(material.purchase_date).lower()) or
                (material.inspection_date and text_lower in str(material.inspection_date).lower())
            )
        ]
        
        self.log.debug("Filtering materials with text '%s'. %d items matched: %s" % (
            text_lower, 
            len(filtered_items), 
            filtered_items
            )
        )
        
        self.work_content.on_data_loaded(MaterialCacheData(items = filtered_items))
    

