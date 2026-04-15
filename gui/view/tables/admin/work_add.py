import logging

from PyQt6.QtWidgets import (
    QSizePolicy,
    QTableWidget,
    QHeaderView,
    QTableWidgetItem,
    QCheckBox,
    QHBoxLayout,
    QWidget
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QCursor

from utils.dc.admin.work.boat_search import AdminBoatData
from utils.logger import LoggerMixin

class AdminAddTable(QTableWidget, LoggerMixin):
    
    log: logging.Logger
    
    def __init__(self, parent = None):
        
        super().__init__(parent)
        
        self.__init_table()
        
    def __init_table(self):
        
        self.setObjectName("workscontenttable")
        
        self.setFixedHeight(550)
        
        self.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        
        self.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        
        self.verticalHeader().setVisible(False)
        
        self.setColumnCount(5)
        
        self.setHorizontalHeaderLabels(["", "Hajó", "Zászló", "IMO", "MMSI"])
        
        self.setColumnWidth(0, 40)  

        header = self.horizontalHeader()
        
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        
        for i in range(1, 5):
            
            header.setSectionResizeMode(i, QHeaderView.ResizeMode.Stretch)

        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
    def load_data(self, admin_boat_data: list[AdminBoatData]):
        
        self.log.debug("Preparing to load %d boat records into the table (first 10: %s)" % (len(admin_boat_data) if isinstance(admin_boat_data, list) else 0, str(admin_boat_data[:10]) if isinstance(admin_boat_data, list) else "[]"))
        
        self.setUpdatesEnabled(False)
        
        try:
        
            if isinstance(admin_boat_data, list) and all(isinstance(row, AdminBoatData) for row in admin_boat_data):
                
                self.clearContents()
                
                self.setRowCount(0)
                
                self.setRowCount(len(admin_boat_data))

                for row_index, row in enumerate(admin_boat_data):
            
                    checkbox = QCheckBox()
                    checkbox.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
                    checkbox.setProperty("add_table_data", row)
                    
                    checkbox_widget = QWidget()
                    
                    layout = QHBoxLayout(checkbox_widget)
                    layout.addWidget(checkbox)
                    layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    layout.setContentsMargins(0, 0, 0, 0)
                    
                    checkbox_widget.setLayout(layout)
                    
                    self.setCellWidget(row_index, 0, checkbox_widget)
                    
                    fields = [
                        row.name if row.name != "" else "N/A",
                        row.flag if row.flag != "" else "N/A",
                        row.imo if row.imo is not None else "N/A",
                        row.mmsi if row.mmsi is not None else "N/A"
                    ]
                    
                    for col_index, value in enumerate(fields, start = 1):
                    
                        cell = QTableWidgetItem(str(value))
                        cell.setForeground(Qt.GlobalColor.white)
                        cell.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    
                        self.setItem(row_index, col_index, cell)
        
        finally:
            
            self.setUpdatesEnabled(True)
    
    def get_selected_boat_data(self) -> list[AdminBoatData]:
        
        selected_boats = []
        
        for row_index in range(self.rowCount()):
            
            checkbox_widget = self.cellWidget(row_index, 0)
            
            if checkbox_widget is None:
                
                continue
            
            checkbox = checkbox_widget.findChild(QCheckBox)
            
            if checkbox is not None and checkbox.isChecked():
                
                boat_data = checkbox.property("add_table_data")
                
                if boat_data:
                    
                    selected_boats.append(boat_data)
                    
                    self.log.debug("Selected boats -> %s" % str(selected_boats))
        
        return selected_boats
                    