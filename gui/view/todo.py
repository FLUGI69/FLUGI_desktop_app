import asyncio
from qasync import asyncSlot
from datetime import datetime
import logging
from pathlib import Path
import sys
import typing as t
import os

from PyQt6.QtWidgets import (
    QWidget, 
    QVBoxLayout, 
    QTableWidget, 
    QHeaderView,
    QSizePolicy,
    QLabel,
    QAbstractScrollArea,
    QDialog,
    QPushButton
)
from PyQt6.QtCore import Qt, QTimer, QSize
from PyQt6.QtGui import QMovie, QPixmap, QIcon, QCursor

from config import Config
from utils.logger import LoggerMixin
from utils.dc.todo_data import TodoBoat, BoatWork
from utils.dc.admin.ship_schedule import ShipSchedule
from .modal.todo import StatusNotesModal, ShowImagesModal
from db import queries

class TodoView(QWidget, LoggerMixin):

    log: logging.Logger

    def __init__(self):
        
        super().__init__()
        
        self.table: QTableWidget = None

        self.__init_view()
        
        self._auto_scroll_timer = QTimer(self)
        
        self._auto_scroll_timer.timeout.connect(self.__auto_scroll_step)
        
        self._departure_timer = QTimer(self)
        
        self._departure_timer.setSingleShot(True)
        
        self._departure_timer.timeout.connect(self._on_refhresh_time_reached)
        
        self._arrival_timer = QTimer(self)
        
        self._arrival_timer.setSingleShot(True)
        
        self._arrival_timer.timeout.connect(self._on_refhresh_time_reached)
        
        self._scroll_direction = 1  
        
        self._pause_counter = 0  
        
        self._pause_duration = 100  
        
        self.todo_boat: t.List[TodoBoat] = []
        
        self.show_imgs_modal = ShowImagesModal(self)
        
        self.status_notes_modal = StatusNotesModal(self)

    @staticmethod
    def icon(name: str) -> QIcon:

        return QIcon(os.path.join(Config.icon.icon_dir, name))
        
    def showEvent(self, event):
        
        super().showEvent(event)

        if not hasattr(self, "_initialized"):
            
            self._initialized = True
            
            asyncio.create_task(self.load_page())
            
    def resizeEvent(self, event):
            
            super().resizeEvent(event)
            
            self.current_window_size = event.size()
            
            self.log.debug("Current window size: %sx%s" % (
                str(self.current_window_size.width()),
                str(self.current_window_size.height())
                )
            )
            
    def __init_view(self):

        self.table = self.set_table()
        self.table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.table)
        
    def set_table(self) -> QTableWidget:
        
        table = QTableWidget()
        table.setObjectName("TodoTable")
        table.setColumnCount(8)
        table.setHorizontalHeaderLabels(["Location", "Ship", "Arrival", "Pontoon", "Departure", "Task", "", ""])
        table.verticalHeader().setVisible(False)
        table.setWordWrap(True)

        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        table.setSizeAdjustPolicy(QAbstractScrollArea.SizeAdjustPolicy.AdjustToContents)

        header = table.horizontalHeader()
        header.setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)
        header.setStretchLastSection(False)

        widths = [200, 200, 200, 200, 200, 1600, 100, 100]
        
        for i in range(table.columnCount()):
            
            header.setSectionResizeMode(i, QHeaderView.ResizeMode.Fixed)
            
            table.setColumnWidth(i, widths[i])

        return table

    def wrap_text(self, text: str, max_len: int = 150) -> str:
        
        return '\n'.join(text[i:i + max_len] for i in range(0, len(text), max_len))

    @staticmethod
    def _to_config_tz(value: datetime) -> datetime:

        if value.tzinfo is None:

            return value.replace(tzinfo = Config.time.timezone_utc)

        return value.astimezone(Config.time.timezone_utc)
    
    async def load_page(self) -> None:

        self.table.setRowCount(0)
        self.table.verticalHeader().setDefaultSectionSize(100)
        
        default_height = self.table.verticalHeader().defaultSectionSize()

        query_result = await queries.select_daily_tasks_from_boats()

        if len(query_result) > 0:
            
            self.todo_boat = [TodoBoat(
                id = row[0].id,
                name = row[0].name,
                flag = row[0].flag,
                mmsi = row[0].mmsi,
                imo = row[0].imo,
                callsign = row[0].callsign,
                type_name = row[0].type_name,
                ship_id = row[0].ship_id,
                schedule = ShipSchedule(
                    schedule_id = row[1].id,
                    location = row[1].location,
                    arrival_date = TodoView._to_config_tz(row[1].arrived_date),
                    ponton = row[1].ponton,
                    leave_date = TodoView._to_config_tz(row[1].leave_date)
                ),
                works = [BoatWork(
                    id = work.id,
                    leader = work.leader,
                    description = work.description,
                    start_date = work.start_date,
                    finished_date = work.finished_date,
                    transfered = work.transfered,
                    is_contractor = work.is_contractor
                    ) for work in row[0].works]
                ) for row in query_result
            ]
      
            next_leave_date = self.todo_boat[0].schedule.leave_date
     
            if next_leave_date:
                
                now = datetime.now(Config.time.timezone_utc)
                
                if next_leave_date.tzinfo is None:
                    
                    next_leave_date = next_leave_date.replace(tzinfo = Config.time.timezone_utc)
          
                time_diff = (next_leave_date - now).total_seconds() * 1000  # ms
          
                if time_diff > 0:
                    
                    self._departure_timer.start(int(time_diff))
                    
                    self.log.info("Departure timer set for %s (in %.1f seconds)" % (
                        next_leave_date, 
                        time_diff/1000
                        )
                    )
                    
                else:
     
                    self._departure_timer.start(100)
                    
                    self.log.info("Departure time already passed, refreshing soon")
            
            await self.__set_arrival_timer()
            
            for row_index, boat in enumerate(self.todo_boat):
                        
                # if hasattr(row, '_fields'):
                #     print("Fields:", row._fields)
                #     print("Values:", tuple(row))

                if hasattr(self, "overlay_label"):
                    
                    self.overlay_label.hide()
                    
                    self.movie.stop()
                    
                self.table.insertRow(row_index)
                
                show_img_btn = QPushButton()
                show_img_btn.setObjectName("WorkBtn")
                show_img_btn.setStyleSheet(Config.styleSheets.work_btn)
                # show_img_btn.setFixedWidth(100)
                show_img_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
                show_img_btn.setProperty("boat", boat)
                show_img_btn.setIcon(TodoView.icon("image.svg"))
                show_img_btn.setIconSize(QSize(20, 20))
                show_img_btn.setToolTip("View images")
                show_img_btn.clicked.connect(lambda _, idx = row_index: self.show_image_for_particular_boat(idx))
                
                show_img_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
                
                show_btn_container = QWidget()
                layout = QVBoxLayout(show_btn_container)
                layout.setContentsMargins(0, 0, 0, 0)
                layout.addWidget(show_img_btn)
                
                self.table.setCellWidget(row_index, 6, show_btn_container)
                
                notes_btn = QPushButton()
                notes_btn.setObjectName("WorkBtn")
                notes_btn.setStyleSheet(Config.styleSheets.work_btn)
                # notes.setFixedWidth(100)
                notes_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
                notes_btn.setProperty("boat", boat)
                notes_btn.setIcon(TodoView.icon("file.svg"))
                notes_btn.setIconSize(QSize(20, 20))
                notes_btn.setToolTip("View notes")
                notes_btn.clicked.connect(lambda _, idx = row_index: self.check_status_notes(idx))
                
                notes_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
                
                notes_container = QWidget()
                layout = QVBoxLayout(notes_container)
                layout.setContentsMargins(0, 0, 0, 0)
                layout.addWidget(notes_btn)

                self.table.setCellWidget(row_index, 7, notes_container)
                
                work_descriptions = ", ".join(f"{idx + 1}: {work.description}" for idx, work in enumerate(boat.works))
                
                values = [
                    boat.schedule.location,
                    boat.name,
                    boat.schedule.arrival_date.strftime(Config.time.timeformat),
                    boat.schedule.ponton,
                    boat.schedule.leave_date.strftime(Config.time.timeformat),
                    work_descriptions
                ]

                max_line_count = 1 
                
                list_hint_height = []
                
                for col_index, value in enumerate(values):
                    
                    wrapped_value = self.wrap_text(value)
                    
                    line_count = wrapped_value.count('\n') + 1
                    
                    max_line_count = max(max_line_count, line_count)

                    label = QLabel(wrapped_value)
                    label.setWordWrap(True)
                    
                    if col_index in [0, 1, 2, 3, 4]:
                        
                        label.setAlignment(Qt.AlignmentFlag.AlignCenter)  # center
                    
                    else:
                        
                        label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)  # left and vertically centered
                    
                    self.table.setCellWidget(row_index, col_index, label)
                    
                    label_width = self.table.columnWidth(col_index) - 12  # padding
                    label.setFixedWidth(label_width)
                    label.adjustSize()
                    
                    hint_height = label.sizeHint().height() # px
                    
                    list_hint_height.append(hint_height)

                if list_hint_height[-1] > default_height:
                    # print("Row:", row_index)
                    self.table.setRowHeight(row_index, list_hint_height[-1])
        
        else:
            
            await self.__centralize_gif()
            
            self.log.info("No records found in the database")
        
        self._auto_scroll_timer.start(50)
    
    @asyncSlot(int)
    async def show_image_for_particular_boat(self, idx: int):
      
        for row_idx in range(self.table.rowCount()):
            
            if row_idx != idx:
                continue
            
            second_last_col_widget = self.table.cellWidget(row_idx, 6)
            
            show_img_btn = self.get_current_col_btn(second_last_col_widget)
           
        if show_img_btn is not None:    
            
            current_row_data: TodoBoat = show_img_btn.property("boat")
            
            self.show_imgs_modal.set_dropdown(current_row_data.works)
            
            await self.show_imgs_modal.exec_async()
            
    @asyncSlot(int)
    async def check_status_notes(self, idx: int):

        for row_idx in range(self.table.rowCount()):
            
            if row_idx != idx:
                continue
            
            last_col_widget = self.table.cellWidget(row_idx, 7)
       
            notes_btn = self.get_current_col_btn(last_col_widget)
            
        if notes_btn is not None:
            
            current_row_data: TodoBoat = notes_btn.property("boat")
            
            self.status_notes_modal.set_dropdown(current_row_data.works)
            
            await self.status_notes_modal.exec_async()
                  
    def get_current_col_btn(self, widget: QWidget) -> QPushButton | None:
    
        if widget is not None and isinstance(widget, QWidget):

            layout = widget.layout()
            
            if layout is not None and layout.count() > 0:
                
                item = layout.itemAt(0).widget()
                
                if isinstance(item, QPushButton):
                    
                    return item    

        return None
        
    async def __centralize_gif(self):
            
        if hasattr(self, "movie") and self.movie is not None:
            
            try:
                
                self.movie.stop()
                self.overlay_label.clear()
                self.overlay_label.deleteLater()
                
                del self.overlay_label
                del self.movie
                
            except Exception as e:
                
                self.log.warning("Failed to remove previous GIF: %s" % str(e))
        
        if getattr(sys, "frozen", False):
            
            path = Path(sys.executable).parent / "_internal" / Config.gif.confused_path
            
        else:
            
            path = Path(Config.gif.confused_path)
             
        self.overlay_label = QLabel(self)
        self.overlay_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.overlay_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

        self.movie = QMovie(str(path))
        
        self.overlay_label.setMovie(self.movie)
        
        self.movie.start()

        await asyncio.sleep(0.05) 

        gif_size = self.movie.currentPixmap().size()
        gif_width = gif_size.width()
        gif_height = gif_size.height()

        self.overlay_label.resize(gif_width, gif_height)
        
        if self.current_window_size is not None:

            self.overlay_label.move(
                self.current_window_size.width() // 2 - gif_width // 2,
                self.current_window_size.height() // 2 - gif_height // 2
            )

            self.overlay_label.show()
            
            self._departure_timer.stop()
            
            self._arrival_timer.stop()
 
    def __auto_scroll_step(self):
        
        scrollbar = self.table.horizontalScrollBar()
        max_val = scrollbar.maximum()
        min_val = scrollbar.minimum()
        current_val = scrollbar.value()

        if self._pause_counter > 0:

            self._pause_counter -= 1
            
            return

        new_val = current_val + self._scroll_direction * 1 
        
        if new_val >= max_val:
            
            new_val = max_val
            
            self._scroll_direction = -1  
            
            self._pause_counter = self._pause_duration
   
        elif new_val <= min_val:
            
            new_val = min_val
            
            self._scroll_direction = 1 
             
            self._pause_counter = self._pause_duration  
            
        scrollbar.setValue(new_val)
        
    async def __set_arrival_timer(self):
        
        next_arrival = await queries.select_min_future_arrival_date()
        
        if next_arrival is not None:
            
            now = datetime.now(Config.time.timezone_utc)

            if next_arrival.tzinfo is None:
                
                next_arrival = next_arrival.replace(tzinfo = Config.time.timezone_utc)
            
            time_diff = (next_arrival - now).total_seconds() * 1000  # ms
            
            if time_diff > 0:
                
                self._arrival_timer.start(int(time_diff))
                
                self.log.info("Pricerival timer set for %s (in %.1f seconds)" % (
                    next_arrival, 
                    time_diff/1000
                    )
                )
                
            else:
                
                self._arrival_timer.start(100)
                
                self.log.info("Pricerival time already passed, refreshing soon")
    
    def _on_refhresh_time_reached(self):

        self.log.info("Refhresh time reached, refreshing table")
        
        asyncio.create_task(self.__handle_refhresh_time_reached())
    
    async def __handle_refhresh_time_reached(self):
        
        await self.__set_arrival_timer()
        
        await self.load_page()
       