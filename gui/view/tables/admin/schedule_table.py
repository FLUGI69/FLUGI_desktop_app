import typing as t
import logging
from copy import deepcopy
from datetime import datetime
import os

from PyQt6.QtWidgets import (
    QTableWidget, 
    QTableWidgetItem, 
    QSizePolicy,
    QHeaderView,
    QCheckBox,
    QHBoxLayout,
    QWidget,
    QPushButton
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QSize
from PyQt6.QtGui import QCursor, QIcon

from utils.dc.mahart_ports.selected_boats import SelectedBoatData
from utils.dc.admin.ship_schedule import ShipSchedule
from utils.logger import LoggerMixin
from exceptions import InvalidDateFormatError
from config import Config

class ScheduleTable(QTableWidget, LoggerMixin):
    
    log: logging.Logger
    
    row_modified_data = pyqtSignal(tuple)
    
    def __init__(self, parent = None):
        
        super().__init__(parent)
        
        self.__init_table()
        
    def __init_table(self):

        self.setObjectName("BoatInfoTable")
        
        self.setEditTriggers(QTableWidget.EditTrigger.DoubleClicked | QTableWidget.EditTrigger.SelectedClicked)
        
        self.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        
        self.verticalHeader().setVisible(False)
        
        self.setColumnCount(7)
        
        self.setHorizontalHeaderLabels(["#", "Name", "Port", "Arrival", "Pontoon", "Departure", ""])

        header = self.horizontalHeader()

        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        
        self.setColumnWidth(0, 40)

        for _header in range(1, 6):
            header.setSectionResizeMode(_header, QHeaderView.ResizeMode.Stretch)

        header.setSectionResizeMode(6, QHeaderView.ResizeMode.Fixed)
        
        self.setColumnWidth(6, 100)
        
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
    
    @staticmethod
    def icon(name: str) -> QIcon:
  
        return QIcon(os.path.join(Config.icon.icon_dir, name))
   
    def _emit_data_safe(self, 
        data: tuple
        ):
        
        QTimer.singleShot(0, lambda: self.row_modified_data.emit(data))

    def load_data(self, boat_data: t.List[SelectedBoatData]):

        self.log.debug("Preparing to load the following boat records into the table: %s" % str(boat_data))
        
        self.clearContents()
        
        self.setRowCount(0)
        
        row_index = 0

        if isinstance(boat_data, list) and all(isinstance(row, SelectedBoatData) for row in boat_data):
            
            for boat in boat_data:
                
                schedules = boat.schedule
                
                for row_index, row in enumerate(schedules):

                    self.insertRow(row_index)

                    self.setRowHeight(row_index, 50)
                    
                    edit_btn = QPushButton()
                    edit_btn.setObjectName("WorkBtn")
                    edit_btn.setStyleSheet(Config.styleSheets.work_btn)
                    edit_btn.setFixedWidth(100)
                    edit_btn.setFixedHeight(50)
                    edit_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
                    edit_btn.setProperty("ship_schedule", row)
                    edit_btn.setIcon(ScheduleTable.icon("edit.svg"))
                    edit_btn.setIconSize(QSize(20, 20))
                    edit_btn.setToolTip("Edit")
                    edit_btn.clicked.connect(lambda _, idx = row_index: self.get_selected_and_modified_schedules(idx))
                    
                    self.setCellWidget(row_index, 6, edit_btn)

                    fields = [
                        str(boat.boat_id) if row_index == 0 else "",
                        boat.name if (row_index == 0 and boat.name != "") else "",
                        row.location if row.location != "" else "N/A",
                        row.arrival_date.strftime(Config.time.timeformat) if row.arrival_date else "N/A",
                        row.ponton if row.ponton != "" else "N/A",
                        row.leave_date.strftime(Config.time.timeformat) if row.leave_date else "N/A",
                    ]

                    for col_index, value in enumerate(fields):
                        
                        item = QTableWidgetItem(value)
                        item.setForeground(Qt.GlobalColor.white)
                        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                        
                        self.setItem(row_index, col_index, item)

                    row_index += 1
                
    def get_selected_and_modified_schedules(self, row_idx: int) -> t.Tuple[list[ShipSchedule], list[ShipSchedule]]:
        
        location = None
        arrival_date = None
        ponton = None
        leave_date = None
        
        selected_boats = []
        
        modified_boats = []
        
        for row_index in range(self.rowCount()):
         
            edit_btn = self.cellWidget(row_index, 6)
            # print(edit_btn)
            # print(type(edit_btn))
            if row_index != row_idx:
                continue
            
            if edit_btn is not None and isinstance(edit_btn, QPushButton):

                prev_ship_schedule: ShipSchedule = edit_btn.property("ship_schedule")
               
                if prev_ship_schedule:
    
                    selected_boats.append(prev_ship_schedule)
                    
                    modified = deepcopy(prev_ship_schedule)
                    
                    try:
                    
                        location = self.item(row_index, 2).text().strip().lower()
                        
                        arrival_date = self.validate_date_format(self.item(row_index, 3).text().strip())
                        
                        ponton = self.item(row_index, 4).text().strip().lower()
                        
                        leave_date = self.validate_date_format(self.item(row_index, 5).text().strip())
                        
                    except InvalidDateFormatError as e:
                        
                        self._emit_data_safe((None, e))
                    
                    changed = False
                    
                    if location is not None and location != prev_ship_schedule.location.lower():
                        
                        setattr(modified, "location", location.capitalize())
                        
                        changed = True
                    
                    if arrival_date is not None and arrival_date != prev_ship_schedule.arrival_date:
    
                        setattr(modified, "arrival_date", arrival_date)
                        
                        changed = True

                    if ponton is not None and ponton != prev_ship_schedule.ponton.lower():
    
                        setattr(modified, "ponton", ponton.capitalize())
                        
                        changed = True
                        
                    if leave_date is not None and leave_date != prev_ship_schedule.leave_date:
                        
                        setattr(modified, "leave_date", leave_date)
                        
                        changed = True
                    
                    if changed == True:
                        
                        modified_boats.append(modified)        

        if len(modified_boats) > 0:

            selected_boats = [
                selected for selected in selected_boats
                if any(selected.schedule_id == modified.schedule_id for modified in modified_boats)
            ]
            
            self.log.debug("Preparing to emit event with the following data - Previous state: %s | Current State: %s" % (
                str(selected_boats),
                str(modified_boats)
                )
            )
            
            self._emit_data_safe((selected_boats, modified_boats))
        
        else: 
            
            self.log.info("No changes were made to the selected boat schedule list")
            
    def validate_date_format(self, value: str) -> datetime:

        if value != "":
    
            try:
                
                return datetime.strptime(value, Config.time.timeformat)
            
            except ValueError:
            
                raise InvalidDateFormatError(value)

