import logging

from PyQt6.QtWidgets import (
    QTableWidget,
    QHeaderView,
    QTableWidgetItem,
    QSizePolicy,
    QCheckBox,
    QWidget,
    QHBoxLayout
)
from PyQt6.QtGui import QCursor
from PyQt6.QtCore import Qt

from utils.dc.returnable_packaging import ReturnablePackagingData, ReturnablePackagingCacheData
from config import Config
from utils.logger import LoggerMixin

class ReturnablePackagingTable(QTableWidget, LoggerMixin):
    
    log: logging.Logger
    
    def __init__(self, parent = None):
        
        super().__init__(parent)
        
        self.__init_table()
        
    def __init_table(self):
        
        self.setObjectName("MaterialTable")
        
        self.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        
        self.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        
        self.verticalHeader().setVisible(False)
        
        self.setColumnCount(6)
        
        self.setHorizontalHeaderLabels(["", "Name", "Quantity", "Bottle number", "Returned", "Price"])
        
        self.setColumnWidth(0, 40)
    
        header = self.horizontalHeader()
        
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        
        for col in range(1, 6):
            
            header.setSectionResizeMode(col, QHeaderView.ResizeMode.Stretch)

        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self.setHorizontalScrollMode(QTableWidget.ScrollMode.ScrollPerPixel)
        self.setVerticalScrollMode(QTableWidget.ScrollMode.ScrollPerPixel)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        self.setWordWrap(False)  
              
    def load_data(self, returnable_packaging_cache: ReturnablePackagingCacheData):
        
        self.log.debug("Preparing to load the following returnable packaging records into the table: %s" % str(returnable_packaging_cache))
        
        self.clearContents()
        
        self.setRowCount(0)

        if hasattr(returnable_packaging_cache, "items"):
            
            for row_index, item in enumerate(returnable_packaging_cache.items):
                
                if item is not None and item.is_deleted == False:
                    
                    self.insertRow(row_index)

                    checkbox = QCheckBox()
                    checkbox.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
                    checkbox.setProperty("returnable_packaging_data", item)  # full item attached 
                    
                    checkbox_widget = QWidget()
                    
                    layout = QHBoxLayout(checkbox_widget)
                    layout.addWidget(checkbox)
                    layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    layout.setContentsMargins(0, 0, 0, 0)
                    
                    checkbox_widget.setLayout(layout)
                    
                    self.setCellWidget(row_index, 0, checkbox_widget)
                    
                    fields = [
                        item.name if item.name != "" else "N/A",
                        f"{item.quantity:.4f}" if item.quantity is not None else "N/A",
                        item.manufacture_number if item.manufacture_number is not None else "N/A",
                        "Yes" if item.is_returned == True else "No" if item.is_returned == False else "N/A",
                        f"{item.price:,.2f}".replace(",", ".") + " HUF" if item.price is not None else "N/A",
                        item.id
                    ]

                    for col_index, value in enumerate(fields, start = 1):
                        
                        cell = QTableWidgetItem(value)
                        cell.setForeground(Qt.GlobalColor.white)
                        cell.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                        self.setItem(row_index, col_index, cell)
                        
    def get_selected_cache_data(self) -> list[ReturnablePackagingCacheData]:
        
        selected_data = []
        
        for row_index in range(self.rowCount()):
            
            checkbox_widget = self.cellWidget(row_index, 0)
            
            if checkbox_widget is None:
                
                continue
            
            checkbox = checkbox_widget.findChild(QCheckBox)
            
            if checkbox is not None and checkbox.isChecked():
                
                boat_data = checkbox.property("returnable_packaging_data")
                
                if boat_data:
                    
                    selected_data.append(boat_data)
                    
                    self.log.debug("Selected data -> %s" % str(selected_data))
                    
        return selected_data
