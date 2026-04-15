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
from PyQt6.QtCore import Qt, pyqtSignal

from utils.dc.returnable_packaging import ReturnablePackagingData, ReturnablePackagingCacheData
from config import Config
from utils.handlers.math import UtilityCalculator
from utils.logger import LoggerMixin

class ReturnablePackagingTable(QTableWidget, LoggerMixin):
    
    log: logging.Logger
    
    header_clicked = pyqtSignal(int)
    
    def __init__(self, 
        utility_calculator = None, 
        parent = None
        ):
        
        super().__init__(parent)
        
        self.utility_calculator: UtilityCalculator = utility_calculator
        
        self.__init_table()
        
    def __init_table(self):
        
        self.setObjectName("MaterialTable")
        
        self.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        
        self.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        
        self.verticalHeader().setVisible(False)
        
        self.setColumnCount(8)
        
        self.setHorizontalHeaderLabels(["", "Megnevezés", "Mennyiség", "Palackszám", "Visszaküldve", "Beszerzés időpontja", "Nettó egységár", "Összesített ár"])
        
        self.setColumnWidth(0, 40)
    
        header = self.horizontalHeader()
        
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        
        for col in range(1, self.columnCount()):
            
            header.setSectionResizeMode(col, QHeaderView.ResizeMode.Interactive)
            
            self.setColumnWidth(col, 300)
        
        header.setStretchLastSection(False)
        
        header.sectionClicked.connect(self.header_clicked.emit)
        
        header.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self.setHorizontalScrollMode(QTableWidget.ScrollMode.ScrollPerPixel)
        self.setVerticalScrollMode(QTableWidget.ScrollMode.ScrollPerPixel)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        self.setWordWrap(False)  
              
    def load_data(self, returnable_packaging_cache: ReturnablePackagingCacheData):
        
        items = returnable_packaging_cache.items if hasattr(returnable_packaging_cache, "items") else []
        
        self.log.debug("Preparing to load %d returnable packaging records into the table (first 10: %s)" % (len(items), str(items[:10])))
        
        self.setUpdatesEnabled(False)
        
        try:
        
            self.clearContents()
            
            self.setRowCount(0)

            if hasattr(returnable_packaging_cache, "items"):
                
                visible_items = [item for item in returnable_packaging_cache.items if item is not None and item.is_deleted == False]
                
                self.setRowCount(len(visible_items))
                
                for row_index, item in enumerate(visible_items):

                    checkbox = QCheckBox()
                    checkbox.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
                    checkbox.setProperty("returnable_packaging_data", item)
                    
                    checkbox_widget = QWidget()
                    
                    layout = QHBoxLayout(checkbox_widget)
                    layout.addWidget(checkbox)
                    layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    layout.setContentsMargins(0, 0, 0, 0)
                    
                    checkbox_widget.setLayout(layout)
                    
                    self.setCellWidget(row_index, 0, checkbox_widget)
                    
                    if self.utility_calculator and item.price is not None and item.quantity is not None:
                        
                        raw_total = float(self.utility_calculator.arithmetic_decimal(item.price, item.quantity, "multiply", 2))
                        total_price = f"{raw_total:,.2f}".replace(",", ".") + " HUF"
                   
                    else:
                        
                        total_price = "N/A"

                    fields = [
                        item.name if item.name != "" else "N/A",
                        f"{item.quantity:.4f}" if item.quantity is not None else "N/A",
                        item.manufacture_number if item.manufacture_number is not None else "N/A",
                        "Igen" if item.is_returned == True else "Nem" if item.is_returned == False else "N/A",
                        item.purchase_date.strftime(Config.time.timeformat) if item.purchase_date is not None else "N/A",
                        f"{item.price:,.2f}".replace(",", ".") + " HUF" if item.price is not None else "N/A",
                        total_price,
                        item.id
                    ]

                    for col_index, value in enumerate(fields, start = 1):
                        
                        cell = QTableWidgetItem(value)
                        cell.setForeground(Qt.GlobalColor.white)
                        cell.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                        self.setItem(row_index, col_index, cell)
        
        finally:
            
            self.setUpdatesEnabled(True)
                        
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