import typing as t
import logging
import os

from PyQt6.QtWidgets import (
    QTableWidget, 
    QTableWidgetItem, 
    QSizePolicy,
    QHeaderView,
    QCheckBox,
    QHBoxLayout,
    QWidget,
    QLabel
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QCursor, QPixmap

from utils.dc.marine_traffic.search_data import MarineTrafficData
from utils.logger import LoggerMixin
from config import Config

class MarineTrafficTable(QTableWidget, LoggerMixin):
    
    log: logging.Logger
    
    def __init__(self, parent = None):
        
        super().__init__(parent)
        
        self.__init_table()
     
    def __init_table(self):
        
        self.setObjectName("BoatInfoTable")
        
        self.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        
        self.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        
        self.verticalHeader().setVisible(False)
        
        self.setColumnCount(8)
        
        self.setHorizontalHeaderLabels(["", "Név", "Zászló", "MMSI", "IMO", "Hajó ID", "Típus", "Ország"])
        
        self.setColumnWidth(0, 40)
    
        header = self.horizontalHeader()
        
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        
        for col in range(1, 8):
            
            header.setSectionResizeMode(col, QHeaderView.ResizeMode.Stretch)

        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self.setHorizontalScrollMode(QTableWidget.ScrollMode.ScrollPerPixel)
        self.setVerticalScrollMode(QTableWidget.ScrollMode.ScrollPerPixel)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        self.setWordWrap(False)

    def load_data(self, data: t.List[MarineTrafficData]):
        
        self.log.debug("Preparing to load %d boat records into the table (first 10: %s)" % (len(data) if isinstance(data, list) else 0, str(data[:10]) if isinstance(data, list) else "[]"))
        
        self.setUpdatesEnabled(False)
        
        try:
        
            self.clearContents()
            
            self.setRowCount(0)
            
            if isinstance(data, list) and all(isinstance(row, MarineTrafficData) for row in data):
                
                self.setRowCount(len(data))

                for row_index, row in enumerate(data):
                
                    self.setRowHeight(row_index, 40) 

                    checkbox = QCheckBox()
                    checkbox.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
                    checkbox.setProperty("marine_traffic_data", row)
                    
                    checkbox_widget = QWidget()
                    
                    layout = QHBoxLayout(checkbox_widget)
                    layout.addWidget(checkbox)
                    layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    layout.setContentsMargins(0, 0, 0, 0)
                    
                    checkbox_widget.setLayout(layout)
                    
                    self.setCellWidget(row_index, 0, checkbox_widget)
                    
                    flag_label = QLabel()
                    flag_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

                    flag_code = row.flag.lower() if row.flag else "nan"

                    pixmap = QPixmap(os.path.join(Config.flags.flag_dir, f"{flag_code}.png"))

                    if not pixmap.isNull():
        
                        scaled_pixmap = pixmap.scaled(QSize(32, 20), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                        
                        flag_label.setPixmap(scaled_pixmap)
                
                    else:
                        
                        self.log.error("Could not load flag image for code %s" % flag_code)

                    self.setCellWidget(row_index, 2, flag_label)
                    
                    fields = [
                        row.ship_name if row.ship_name != "" else "N/A",
                        row.flag if row.flag != "" else "N/A",
                        str(row.MMSI) if row.MMSI is not None else "N/A",
                        str(row.IMO) if row.IMO is not None else "N/A",
                        str(row.ship_id) if row.ship_id is not None else "N/A",
                        row.type_name.capitalize() if row.type_name != "" else "N/A",
                        row.country if row.country != "" else "N/A"
                    ]

                    for col_index, value in enumerate(fields, start = 1):
                    
                        if col_index == 2:
                            continue
                    
                        item = QTableWidgetItem(value)
                        item.setForeground(Qt.GlobalColor.white)
                        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    
                        self.setItem(row_index, col_index, item)
        
        finally:
            
            self.setUpdatesEnabled(True)
                
    def get_selected_ship_data(self) -> list[MarineTrafficData]:
        
        selected_boats = []
        
        for row_index in range(self.rowCount()):
            
            checkbox_widget = self.cellWidget(row_index, 0)
            
            if checkbox_widget is None:
                
                continue
            
            checkbox = checkbox_widget.findChild(QCheckBox)
            
            if checkbox is not None and checkbox.isChecked():
                
                boat_data = checkbox.property("marine_traffic_data")
                
                if boat_data:
                    
                    selected_boats.append(boat_data)
                    
                    self.log.debug("Selected boats -> %s" % str(selected_boats))
        
        return selected_boats