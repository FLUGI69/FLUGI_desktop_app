import os
import asyncio
import io
import aiofiles
from functools import partial
from qasync import asyncSlot
from datetime import datetime
import logging
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
from PyQt6.QtCore import Qt, pyqtSignal, QDate, QTime, QSize, QTimer
from PyQt6.QtGui import QCursor, QPixmap, QIcon, QFont, QFontMetrics

from utils.logger import LoggerMixin
from ..custom import ImageItemWidget
from config import Config
from ...tables.admin.work_add import AdminAddTable
from ...modal.confirm_action import ConfirmActionModal
from utils.dc.admin.work.boat_search import AdminBoatData
from utils.dc.material import MaterialData, MaterialCacheData
from utils.enums.quantity_range import QuantityRange
from exceptions import ImageNotFound
from db import queries

if t.TYPE_CHECKING:
    
    from .works import AdminWorksContent
    
class AdminAddWorkContent(QWidget, LoggerMixin):
    
    log: logging.Logger
    
    refresh_todo = pyqtSignal(bool)
    
    def __init__(self, 
        parent: 'AdminWorksContent'
        ):
        
        super().__init__(parent)
        
        assert parent is not None, "AdminAddWorkContent requires a parent widget"
        
        self._btn_lock = asyncio.Lock()
        
        self.work_content = parent
        
        self._add_work_lock = parent.storage_lock
        
        self.spinner = parent.spinner
        
        self.utility_calculator = parent.utility_calculator
        
        self.material_cache_service = parent.material_cache_service
        
        self.current_quantity_dict = {}
        
        self.before_quantity_change = {}
        
        self.available_materials: MaterialCacheData = MaterialCacheData(items = [])
        
        self.selected_materials: MaterialCacheData = MaterialCacheData(items = [])
        
        self.table = AdminAddTable(self)
        
        self.confirm_action_modal = ConfirmActionModal(self)
        
        self.attached_images = []
        
        self.row_maximum_col_widths = []
            
        self.all_collumns = None
        
        self.global_max_col_width: int | None = None
        
        self._recalculate_widths = True
        
        self.__init_view()
        
    @staticmethod
    def icon(name: str) -> QIcon:

        return QIcon(os.path.join(Config.icon.icon_dir, name))   
        
    def __init_view(self):
        
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet(Config.styleSheets.work_scroll)

        container = QWidget()
        container.setObjectName("MaterialTableContainer")
        container.setContentsMargins(0, 0, 0, 0)

        container_layout = QVBoxLayout(container)
        container_layout.setSpacing(20)

        self.scroll_area.setWidget(container)

        main_layout = QVBoxLayout(self)
        main_layout.addWidget(self.scroll_area)

        form_frame = QFrame()
        form_frame.setObjectName("WorkFormFrame")

        form_layout = QVBoxLayout(form_frame)
        form_layout.setSpacing(25)

        project_leader_section = self.set_project_leader_section()
        work_description_section = self.set_work_description_section()
        work_pictures_section = self.set_work_puctures_section()
        work_components_section = self.set_work_components_section()
        combobox_is_contractor = self.set_combobox_is_contractor()
        footer_buttons = self.set_footer_buttons()
        
        form_layout.addLayout(project_leader_section)
        form_layout.addLayout(work_description_section)
        form_layout.addLayout(work_pictures_section)
        form_layout.addLayout(work_components_section)
        form_layout.addLayout(combobox_is_contractor)

        container_layout.addWidget(self.table)      
        container_layout.addWidget(form_frame)      
        container_layout.addLayout(footer_buttons)   
        container_layout.addStretch(1)

    def set_project_leader_section(self):

        layout = QVBoxLayout()
        layout.setSpacing(8)

        label = QLabel("Project leader (Assigned person responsible for the work)*")
        label.setObjectName("BoatTitleLabel")

        self.leader_text_edit = QTextEdit()
        self.leader_text_edit.setFixedHeight(60)
        self.leader_text_edit.setStyleSheet(Config.styleSheets.work_text_edit)

        layout.addWidget(label)
        layout.addWidget(self.leader_text_edit)

        return layout

    def set_work_description_section(self):

        layout = QVBoxLayout()
        layout.setSpacing(8)

        label = QLabel("Work description*")
        label.setObjectName("BoatTitleLabel")

        self.description_text_edit = QTextEdit()
        self.description_text_edit.setFixedHeight(300)
        self.description_text_edit.setStyleSheet(Config.styleSheets.work_text_edit)

        layout.addWidget(label)
        layout.addWidget(self.description_text_edit)

        return layout

    def set_work_puctures_section(self):

        section_layout = QVBoxLayout()
        section_layout.setSpacing(10)

        label = QLabel("Add images to the work")
        label.setObjectName("BoatTitleLabel")

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

        section_layout.addWidget(label)
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
        self.refresh_btn.setIcon(AdminAddWorkContent.icon("refresh.svg"))
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
        
        selected_label = QLabel("Selected materials (enter quantity*)")
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

    def set_combobox_is_contractor(self):
        
        section_layout = QHBoxLayout()
        section_layout.setSpacing(10)
        section_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        
        label = QLabel("Subcontractor work")
        label.setObjectName("BoatTitleLabel")
        
        self.dropdown_is_contractor = QComboBox()
        self.dropdown_is_contractor.setObjectName("Dropdown")
        self.dropdown_is_contractor.setStyleSheet(Config.styleSheets.dropdown_style)
        self.dropdown_is_contractor.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.dropdown_is_contractor.addItem("", None)
        self.dropdown_is_contractor.addItem("Yes", True)
        self.dropdown_is_contractor.addItem("No", False)
        self.dropdown_is_contractor.setFixedHeight(35)
        self.dropdown_is_contractor.setFixedWidth(150)
        
        section_layout.addWidget(label)
        section_layout.addWidget(self.dropdown_is_contractor)

        return section_layout

    def set_footer_buttons(self):
        
        v_layout = QVBoxLayout()

        layout = QHBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        confirm_btn = QPushButton("OK")
        confirm_btn.setObjectName("WorkBtn")
        confirm_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        confirm_btn.setFixedHeight(35)
        confirm_btn.setFixedWidth(150)
        confirm_btn.setStyleSheet(Config.styleSheets.work_btn)
        confirm_btn.clicked.connect(lambda: asyncio.ensure_future(self.__btn_callback(0)))

        cancel_btn = QPushButton("Delete")
        cancel_btn.setObjectName("WorkBtn")
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.setFixedHeight(35)
        cancel_btn.setFixedWidth(150)
        cancel_btn.setStyleSheet(Config.styleSheets.work_btn)
        cancel_btn.clicked.connect(lambda: asyncio.ensure_future(self.__btn_callback(1)))

        layout.addWidget(confirm_btn)
        layout.addWidget(cancel_btn)
        
        self.form_error_label = QLabel()
        self.form_error_label.setObjectName("error")
        self.form_error_label.setVisible(False)
        
        font = QFont()
        font.setPointSize(15) 
        font.setBold(True)  
        self.form_error_label.setFont(font)
        self.form_error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
        v_layout.addLayout(layout)
        v_layout.addWidget(self.form_error_label)
        v_layout.setSpacing(10)

        return v_layout
    
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
                
                selected_boat: t.List[AdminBoatData] = self.table.get_selected_boat_data()
                
                validate_fields = self.validate_form(selected_boat)
                
                if validate_fields == True:
                
                    await self.handle_form(
                        boats = selected_boat,
                        leader = self.leader_text_edit.toPlainText().strip(),
                        description = self.description_text_edit.toPlainText().strip()
                    )
                
            elif idx == 1:
                
                await self.reset_form()
                    
            self.spinner.hide()

    def validate_form(self, selected_boat: list):
        
        self.form_error_label.setVisible(False)
        
        if selected_boat == []:
            
            self.form_error_label.setText("You did not select a ship for the work")
            self.form_error_label.setVisible(True)
            
            scroll_bar = self.scroll_area.verticalScrollBar()
            scroll_bar.setValue(scroll_bar.maximum())
            
            self.log.warning("Form validation failed: no 'boat' selected for the work")
            
            return False
        
        if len(selected_boat) > 1:
            
            self.form_error_label.setText("Only one ship can be selected at a time")
            self.form_error_label.setVisible(True)
            
            scroll_bar = self.scroll_area.verticalScrollBar()
            scroll_bar.setValue(scroll_bar.maximum())
            
            self.log.warning("Form validation failed: multiple row selected. Only one 'boat' can be selected at a time")
            
            return False
        
        if self.leader_text_edit.toPlainText().strip() == "":
        
            self.form_error_label.setText("You did not assign a responsible person to the project")
            self.form_error_label.setVisible(True)
            
            scroll_bar = self.scroll_area.verticalScrollBar()
            scroll_bar.setValue(scroll_bar.maximum())
            
            self.log.warning("Form validation failed: 'leader' field is empty")
            
            return False
        
        if self.description_text_edit.toPlainText().strip() == "":
            
            self.form_error_label.setText("No description for the project")
            self.form_error_label.setVisible(True)
            
            scroll_bar = self.scroll_area.verticalScrollBar()
            scroll_bar.setValue(scroll_bar.maximum())
            
            self.log.warning("Form validation failed: 'description' field is empty")
            
            return False
        
        self.log.info("Form successfully validated")
        
        return True
    
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
    
    def _handle_delete_image(self, file_path_to_delete: str):

        self.log.debug("Request to delete image: %s" % file_path_to_delete)
        
        if file_path_to_delete in self.attached_images:
            
            self.attached_images.remove(file_path_to_delete)
            
            asyncio.ensure_future(self._handle_attach_files())
    
    async def handle_form(self,
        boats: t.List[AdminBoatData],
        leader: str,
        description: str
        ):
        
        self.log.debug(
            "Handling form submission - Leader: %s, Description: %s, Image paths: %s ,%s: %s, %s: %s" % (
                leader,
                description,
                [path for path in self.attached_images],
                boats[0].__class__.__name__,
                boats,
                self.selected_materials.items[0].__class__.__name__ if len(self.selected_materials.items) > 0 else "None",
                self.selected_materials.items
            )
        )
        
        async with self._add_work_lock:
            
            try:
                
                await queries.insert_work_by_boat_id(
                    boat_id = boats[0].id,
                    leader = leader,
                    description = description,
                    is_contractor = True if self.dropdown_is_contractor.currentData() is True else False,
                    img_paths = self.attached_images,
                    materials = self.selected_materials.items
                )
                
                self.refresh_todo.emit(True)

                await self.reset_form()
                
            except ImageNotFound as e:
                
                self.log.exception(e)
                
                self.form_error_label.setText("Image not found at the specified path")
                self.form_error_label.setVisible(True)
                
                scroll_bar = self.scroll_area.verticalScrollBar()
                scroll_bar.setValue(scroll_bar.maximum())
                
            except Exception as e:
                
                self.log.exception("Unexpected error occured: %s" % str(e))
                
                self.form_error_label.setText("Something went wrong")
                self.form_error_label.setVisible(True)
                
                scroll_bar = self.scroll_area.verticalScrollBar()
                scroll_bar.setValue(scroll_bar.maximum())
                
        await self.material_cache_service.clear_cache(Config.redis.cache.material.id)
       
        await self.work_content.load_cache_data()
       
    async def reset_form(self):
    
        await self.clear_material_list()

        self.table.clearContents()
        self.table.setRowCount(0)
        
        self.leader_text_edit.clear()
        
        self.description_text_edit.clear()
        
        self.components_search_input.clear()
        
        self.work_content.clear_prev_search() 
        
        for i in range(self.picture_list.count()):
            
            item = self.picture_list.item(i)
                        
            if item is not None and isinstance(item, QListWidgetItem):
                
                widget = self.picture_list.itemWidget(item)
                
                if isinstance(widget, ImageItemWidget):
                    
                    file_path = widget.file_path
                    
                    if file_path != "":
                        
                        self._handle_delete_image(file_path)
        
        self.dropdown_is_contractor.setCurrentIndex(0)
    
    async def _handle_attach_files(self):
        
        self.picture_list.clear()
    
        try:
            
            valid_files = []
    
            for file_path in self.attached_images:

                pixmap = QPixmap(file_path)

                if pixmap.isNull():
                    
                    self.log.warning("Removing non-image: %s" % file_path)
                    
                    continue

                valid_files.append(file_path)

                item = QListWidgetItem()
                item.setSizeHint(QSize(400, 280))

                widget = ImageItemWidget(file_path, self, None)
                
                self.picture_list.addItem(item)
                self.picture_list.setItemWidget(item, widget)

            self.attached_images = valid_files

        except Exception as e:
            
            self.log.exception("Error processing image %s: %s" % (
                os.path.basename(file_path),
                str(e)
                )
            )

        finally:
    
            self.spinner.hide()
    
    def set_value_changed(self, value: t.Any, material: MaterialData):
        
        d_val = Decimal(str(value))
        
        setattr(material, "quantity", d_val.quantize(Decimal('0.0001'), rounding = ROUND_HALF_UP))
        
        self.current_quantity_dict[material.id] = value
    
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
                    # list_item.setSizeHint(QSize(list_item.sizeHint().width(), 35))
                    
                    container = QWidget()
                    container.setFixedHeight(35)
                    
                    edit_btn = QPushButton()
                    edit_btn.setObjectName("TrashButton")
                    edit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
                    edit_btn.setIcon(AdminAddWorkContent.icon("add.svg"))
                    edit_btn.setIconSize(QSize(20, 20))
                    edit_btn.setToolTip("Add")
                    edit_btn.clicked.connect(lambda _, material = data: self._add_material_to_selected(material))
                
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

                    quantity_label = QLabel(quantity.strip())
                    quantity_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                    quantity_label.setFont(font)
                    quantity_label.setToolTip(quantity.strip())

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
                        quantity_label,
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
                
    def populate_work_components_list_selected(self, data_list: t.List[MaterialData]):
        
        scroll_bar = self.work_components_list_bottom.verticalScrollBar()
        scroll_pos = scroll_bar.value()
        
        self.work_components_list_bottom.clear()
    
        if len(data_list) > 0:
            
            self.log.debug("Populating work components selected materials list with %d items of (%s) data" % (
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
                    
                    if data.id not in self.before_quantity_change:
                        
                        self.before_quantity_change[data.id] = data.quantity
                    
                    name = data.name if data.name is not None else "N/A"
                    
                    manufacture_number = data.manufacture_number if data.manufacture_number is not None else "N/A"
                    
                    unit = data.unit if data.unit is not None else "N/A"
                    
                    manufacture_date = data.manufacture_date.strftime(Config.time.timeformat) if data.manufacture_date is not None else "N/A"
                    
                    price = f"{data.price:,.2f}".replace(",", ".") + " HUF" if data.price is not None else "N/A"
                    
                    purchase_source = data.purchase_source if data.purchase_source is not None else "N/A"
                    
                    purchase_date = data.purchase_date.strftime(Config.time.timeformat) if data.purchase_date is not None else "N/A"
                    
                    inspection_date = data.inspection_date.strftime(Config.time.timeformat) if data.inspection_date is not None else "N/A"
                    
                    list_item = QListWidgetItem()
                    list_item.setSizeHint(QSize(list_item.sizeHint().width(), 35))
                    
                    container = QWidget()
                    container.setFixedHeight(35)
                    
                    edit_btn = QPushButton()
                    edit_btn.setObjectName("TrashButton")
                    edit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
                    edit_btn.setIcon(AdminAddWorkContent.icon("trash.svg"))
                    edit_btn.setIconSize(QSize(20, 20))
                    edit_btn.setToolTip("Remove")
                    edit_btn.clicked.connect(lambda _, material = data: self._remove_material_from_selected(material))
                
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
                    
                    input_quantity = QDoubleSpinBox()
                    input_quantity.setDecimals(4)
                    input_quantity.setSingleStep(0.01)
                    input_quantity.setMinimum(0)
                    input_quantity.setMaximum(data.quantity)
                    input_quantity.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
                    input_quantity.setObjectName("input_quantity")
                    
                    if self.current_quantity_dict != {}:
                        
                        value = self.current_quantity_dict.get(data.id, 0)
                        
                        input_quantity.setValue(value)
                    
                    input_quantity.valueChanged.connect(lambda value, material = data: self.set_value_changed(
                        value = value,
                        material = material
                        )
                    )

                    # print("After setattr",self.current_quantity_dict) 
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
                        input_quantity,
                        unit_label,
                        manufacture_date_label,
                        price_label,
                        purchase_source_label,
                        purchase_date_label,
                        inspection_date_label
                    ]
                    
                    for w in widgets:
                        
                        if isinstance(w, QLabel):

                            w.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
                            w.setContentsMargins(0, 0, 0, 0)
                            w.setWordWrap(False)
                    
                        h_layout.addWidget(w)
                    
                    container.setLayout(h_layout)
                
                    list_item.setSizeHint(container.sizeHint())
                    
                    self.work_components_list_bottom.addItem(list_item)
                    self.work_components_list_bottom.setItemWidget(list_item, container)
                    self.work_components_list_bottom.setSpacing(5)
                    
                    list_item.setData(Qt.ItemDataRole.UserRole, data_list)  
                    
                self.calculate_globa_col_width_and_apply_to_relevant_list(self.work_components_list_bottom)
                
                # print("After selected:", data_list)
                QTimer.singleShot(0, lambda: scroll_bar.setValue(scroll_pos))   
            
            else:
                
                self.log.info("Populating work components selected materials list with 0 items")
                
    def get_attribute_list_widget_is_top(self, list_widget) -> bool:
        
        for name, value in self.__dict__.items():
            
            if value is list_widget:
                
                if name == "work_components_list_top":
                   
                    return True
                
                elif name == "work_components_list_bottom":
                    
                    return False
    
    def calculate_globa_col_width_and_apply_to_relevant_list(self, list_widget: QListWidget):
    
        # print(row_maximum_col_widths)
        if len(self.row_maximum_col_widths) > 0:
          
            self.global_max_col_width: int = max(self.row_maximum_col_widths)
            # print("Global max text width:", global_max_width)
            # print("Number of columns:", all_collumns)
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
                                        
                                        is_top = self.get_attribute_list_widget_is_top(list_widget)
                                        
                                        x = 1.5
                                        
                                        if is_top == True:
                                      
                                            if j >= 3 and j <= 4:
                                            
                                                widget.setFixedWidth(int(self.global_max_col_width * x))
                                                
                                            elif j > 4:
                                                
                                                widget.setFixedWidth(self.global_max_col_width)
                                                
                                            else: 
                                            
                                                widget.setFixedWidth(40)  
                                        
                                        elif is_top == False:
                                        
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
                                     
    def _add_material_to_selected(self, material: MaterialData):

        if material in self.selected_materials.items:
            return

        self.available_materials.items = [m for m in self.available_materials.items if m.id != material.id]
        # print(material.id)
        # print("Current quanity:", self.current_quantity_dict)
        # print("Before selected:", self.selected_materials.items)
        
        self.selected_materials.items.append(material)

        self.populate_work_components_list(self.available_materials.items)
        self.populate_work_components_list_selected(self.selected_materials.items)
        
    def _remove_material_from_selected(self, material: MaterialData):

        if material not in self.selected_materials.items:
            return

        self.current_quantity_dict.pop(material.id, 0)
        
        if material.id in self.before_quantity_change:
            
            value = self.before_quantity_change.pop(material.id, None)
            
            if value is not None:
                
                setattr(material, "quantity", value)
        
        self.selected_materials.items = [m for m in self.selected_materials.items if m.id != material.id]

        self.available_materials.items.append(material)

        self.populate_work_components_list(self.available_materials.items)
        self.populate_work_components_list_selected(self.selected_materials.items)
                            
    async def clear_material_list(self):
        
        self.selected_materials.items.clear()
        
        self.available_materials.items.clear()
        
        self.current_quantity_dict.clear()
        
        await self.material_cache_service.clear_cache(Config.redis.cache.material.id)  
        
        await self.work_content.load_cache_data()
        
    def _handle_enter_pressed(self):
                
        text_lower = self.components_search_input.text().strip().lower()
        
        if text_lower == "":
            
            self.work_content.on_data_loaded(self.available_materials.items)
            
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

