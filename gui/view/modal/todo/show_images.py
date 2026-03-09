import asyncio
import logging
from qasync import asyncSlot
import typing as t

from PyQt6.QtWidgets import (
    QDialog, 
    QVBoxLayout,
    QLabel, 
    QDialogButtonBox, 
    QWidget, 
    QHBoxLayout,
    QComboBox,
    QListWidget,
    QSizePolicy,
    QListWidgetItem
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QCursor, QPixmap

from utils.dc.todo_data import BoatWork
from view.admin.custom.modal_image_item import ImageItemWidget
from utils.logger import LoggerMixin
from utils.dc.admin.work.images import AdminWorkImage
from config import Config
from db import queries

class ShowImagesModal(QDialog, LoggerMixin):

    log: logging.Logger

    def __init__(self, parent = None):
        
        super().__init__(parent)
        
        self._future = None
        
        self.setWindowTitle("Attached images")
        
        self.setModal(True)
        
        self.setMinimumWidth(500)

        self.__init_modal()
        
        self.adjustSize()
            
    def __init_modal(self):
        
        self.setObjectName("ConfirmModal")

        self.message_label = QLabel("Select a work to view images:")
        self.message_label.setObjectName("ConfirmModalLabel")
        self.message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
 
        self.combo_box = QComboBox(self)
        self.combo_box.setFixedHeight(35)
        self.combo_box.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        
        self.combo_box.currentIndexChanged.connect(self._on_combo_changed)
        
        work_pictures_section = self.set_work_puctures_section()
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(20, 20, 20, 20)
        self.layout.setSpacing(15)
        
        self.layout.addWidget(self.message_label)
        self.layout.addWidget(self.combo_box)
        
        self.layout.addLayout(work_pictures_section)
  
        self.button_container = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        
        self.button_container.setObjectName("ConfirmModalButtonBox")
        self.button_container.setFixedHeight(60)

        for button in self.button_container.buttons():
            
            button.setFixedHeight(35)
            button.setFixedWidth(90)
            button.setObjectName("ConfirmModalButton")
            button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

        self.button_container.accepted.connect(self.accept)

        button_widget = QWidget()
        button_layout = QHBoxLayout(button_widget)
        button_layout.setContentsMargins(0, 0, 0, 0)
        button_layout.setSpacing(0)
        button_layout.addStretch()
        button_layout.addWidget(self.button_container, alignment = Qt.AlignmentFlag.AlignCenter)
        button_layout.addStretch()

        self.layout.addWidget(button_widget)

    def set_work_puctures_section(self):

        section_layout = QVBoxLayout()
        section_layout.setSpacing(10)

        label = QLabel("Attached images")
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
        self.picture_list.setFixedHeight(550)
        self.picture_list.setDragDropMode(QListWidget.DragDropMode.NoDragDrop)
        self.picture_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.picture_list.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.picture_list.setStyleSheet(Config.styleSheets.work_form_list)

        h_layout.addWidget(self.picture_list)

        section_layout.addLayout(h_layout)

        return section_layout

    @asyncSlot(int)
    async def _on_combo_changed(self, index):
        
        self.picture_list.clear()
        
        work: BoatWork = self.combo_box.itemData(index)
        
        if work is not None:
            
            work_imgs = await self.select_work_images_by_id(work.id)
            
            if len(work_imgs) > 0:
                
                for image in work_imgs:
                    
                    item = QListWidgetItem()
                    item.setSizeHint(QSize(550, 550))

                    widget = ImageItemWidget(image.img, self)
                    
                    self.picture_list.addItem(item)
                    self.picture_list.setItemWidget(item, widget)
                    
                    self.log.info("Image item added to the list successfully")
                    
            else:
                
                placeholder_widget = QWidget()
                
                layout = QVBoxLayout(placeholder_widget)
                layout.setContentsMargins(0, 0, 0, 0)
                
                label = QLabel("No image attached to this work")
                label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                label.setStyleSheet(Config.styleSheets.label)
                
                layout.addWidget(label)
                
                item = QListWidgetItem()
                item.setSizeHint(QSize(550, 550)) 
                
                self.picture_list.addItem(item)
                self.picture_list.setItemWidget(item, placeholder_widget)
                
                self.log.info("No images found for the selected work")

    async def  select_work_images_by_id(self, id: int) -> t.List[AdminWorkImage]:
        
        if id is not None:
            
            try:
                
                query_results = await queries.select_work_images_by_work_id(id)
                
                images = [AdminWorkImage(
                    id = image.id,
                    img = image.img
                    ) for image in query_results
                ]
                
                self.log.debug("Query executed successfully. Retrieved: %s" % str(images))
                
                return images
                
            except Exception as e:
                
                self.log.exception("Unexpected error occured durring select all images: %s" % str(e))
        
    def set_dropdown(self, works: list[BoatWork]):
        
        self.log.debug("Setting selected works:\n%s" % "\n".join(str(work) for work in works))
        
        self.combo_box.clear()

        for work in works:
            
            display_text = f"Lead: {work.leader} | Description: {work.description}"
            
            self.combo_box.addItem(display_text, work)
    
    def exec_async(self) -> asyncio.Future:
        
        self._future = asyncio.get_event_loop().create_future()
        
        self.log.info("Starting asynchronous modal execution, future created and modal opened")
        
        self.accepted.connect(self._on_accepted)
        
        self.open()
        
        return self._future

    def _on_accepted(self):
        
        if self._future and not self._future.done():
            
            self.log.info("Modal accepted by the user; setting future result to True")
            
            self._future.set_result(True)
            
        else:
            
            self.log.warning("Accepted signal received, but future is already done or missing")
        
        self._disconnect_signals()
        
        self.log.info("Disconnected accepted and rejected signals after acceptance")

    def _disconnect_signals(self):
        
        try:
            
            self.accepted.disconnect(self._on_accepted)
            
            self.log.debug("Successfully disconnected modal signals")
            
        except TypeError:
            
            self.log.warning("Attempted to disconnect signals that were not connected")

    def closeEvent(self, event):
        
        if self._future and not self._future.done():
            
            self.log.info("Modal closed without explicit accept/reject; setting future result to False")
            
            self._future.set_result(False)
        
        self._disconnect_signals()
        
        self.log.info("Modal closed; signals disconnected and closing event propagated")
        
        super().closeEvent(event)