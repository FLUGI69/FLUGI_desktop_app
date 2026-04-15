import typing as t
import logging

from PyQt6.QtWidgets import (
    QTableWidget, 
    QTableWidgetItem, 
    QSizePolicy,
    QHeaderView,
    QCheckBox,
    QHBoxLayout,
    QWidget
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QCursor

from utils.dc.ship_info import ShipInfo
from utils.logger import LoggerMixin
from config import Config

class MahartPortsTable(QTableWidget, LoggerMixin):
    
    log: logging.Logger
    
    def __init__(self, parent = None):
        
        super().__init__(parent)
        
        self.__init_table()
        
    def __init_table(self):
        
        self.setObjectName("BoatInfoTable")
        
        self.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        
        self.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        
        self.verticalHeader().setVisible(False)
        
        self.setColumnCount(6)
        
        self.setHorizontalHeaderLabels(["", "Név", "Kikötő", "Érkezés", "Ponton", "Távozás"])
        
        self.setColumnWidth(0, 40)  

        header = self.horizontalHeader()
        
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        
        for _header in range(1, 6):
            
            header.setSectionResizeMode(_header, QHeaderView.ResizeMode.Stretch)
        
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def load_data(self, ship_infos: t.List[ShipInfo]):
        
        self.log.debug("Preparing to load %d boat records into the table (first 10: %s)" % (len(ship_infos) if isinstance(ship_infos, list) else 0, str(ship_infos[:10]) if isinstance(ship_infos, list) else "[]"))
        
        self.setUpdatesEnabled(False)
        
        try:
        
            self.clearContents()
            
            self.setRowCount(0)

            if isinstance(ship_infos, list) and all(isinstance(row, ShipInfo) for row in ship_infos):
                
                self.setRowCount(len(ship_infos))

                for row_index, row in enumerate(ship_infos):

                    checkbox = QCheckBox()
                    checkbox.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
                    checkbox.setProperty("ship_info_data", row)
                    
                    checkbox_widget = QWidget()
                    
                    layout = QHBoxLayout(checkbox_widget)
                    layout.addWidget(checkbox)
                    layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    layout.setContentsMargins(0, 0, 0, 0)
                    
                    checkbox_widget.setLayout(layout)
                    
                    self.setCellWidget(row_index, 0, checkbox_widget)

                    fields = [
                        row.name if row.name != "" else "N/A",
                        row.port if row.port != "" else "N/A",
                        row.arrival_date.strftime(Config.time.timeformat) if row.arrival_date else "N/A",
                        row.ponton if row.ponton != "" else "N/A",
                        row.departure_date.strftime(Config.time.timeformat) if row.departure_date else "N/A",
                    ]

                    for col_index, value in enumerate(fields, start = 1):
                    
                        item = QTableWidgetItem(value)
                        item.setForeground(Qt.GlobalColor.white)
                        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    
                        self.setItem(row_index, col_index, item)
        
        finally:
            
            self.setUpdatesEnabled(True)
                
    def uncheck_all(self):
        
        for row_index in range(self.rowCount()):
            
            checkbox_widget = self.cellWidget(row_index, 0)
            
            if checkbox_widget is None:
                
                continue
            
            checkbox = checkbox_widget.findChild(QCheckBox)
            
            if checkbox is not None:
                
                checkbox.setChecked(False)

    def get_selected_ship_data(self) -> list[ShipInfo]:
        
        selected_boats = []
        
        for row_index in range(self.rowCount()):
            
            checkbox_widget = self.cellWidget(row_index, 0)
            
            if checkbox_widget is None:
                
                continue
            
            checkbox = checkbox_widget.findChild(QCheckBox)
            
            if checkbox is not None and checkbox.isChecked():
                
                boat_data = checkbox.property("ship_info_data")
                
                if boat_data:
                    
                    selected_boats.append(boat_data)
                    
                    self.log.debug("Selected boats -> %s" % str(selected_boats))
        
        return selected_boats