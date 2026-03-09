import logging
import typing as t

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

from utils.dc.admin.storage_items import AdminStorageItemsCacheData
from utils.dc.material import MaterialData
from utils.dc.tools import ToolsData
from utils.dc.device import DeviceData
from utils.logger import LoggerMixin
from utils.handlers.data_table import DataTableHelper

class StorageTable(QTableWidget, LoggerMixin):
    
    log: logging.Logger
    
    def __init__(self, parent = None):
        
        super().__init__(parent)
        
        self.datatable_helper: DataTableHelper = parent.datatable_helper
        
        self.__init_table()
        
    def __init_table(self):
        
        self.setObjectName("workscontenttable")
        
        self.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        
        self.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        
        self.verticalHeader().setVisible(False)
        
        self.setColumnCount(12)
        
        self.setHorizontalHeaderLabels([
            "", 
            "Name", 
            "Serial number", 
            "Quantity", 
            "Unit", 
            "Manufacturing year", 
            "Price", 
            "Commissioning date", 
            "Purchase source", 
            "Purchase date",
            "Inspection dates", 
            "Scrapezve"
        ])
        
        header = self.horizontalHeader()
        
        for col_index in range(self.columnCount()):
            header.setSectionResizeMode(col_index, QHeaderView.ResizeMode.Interactive)

        column_widths = {
            0: 40,
            1: 220,
            2: 220,
            3: 150,
            4: 200,
            5: 200,
            6: 100,
            7: 250,
            8: 180,
            9: 185,
            10: 350,
            11: 150
        }

        for col_index, width in column_widths.items():
            
            self.setColumnWidth(col_index, width)

        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
    def load_data(self, storage_data: AdminStorageItemsCacheData):
        
        self.log.debug("Preparing to load the following records into the table: %s" % str(storage_data))
        
        self.clearContents()
        
        self.setRowCount(0)

        if hasattr(storage_data, "items"):

            for row_index, row in enumerate(storage_data.items):
                
                self.insertRow(row_index)
            
                checkbox = QCheckBox()
                checkbox.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
                checkbox.setProperty("check", row)
                
                checkbox_widget = QWidget()
                
                layout = QHBoxLayout(checkbox_widget)
                layout.addWidget(checkbox)
                layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
                layout.setContentsMargins(0, 0, 0, 0)
                
                checkbox_widget.setLayout(layout)
                
                self.setCellWidget(row_index, 0, checkbox_widget)
                
                price_value = getattr(row, "price", None)
                
                formatted_price = "{:,.2f}".format(price_value).replace(",", ".") if price_value is not None else "N/A"

                formatted_quantity = f"{self.datatable_helper.getAttribute(row, "quantity"):.4f}"
                
                fields = [
                    self.datatable_helper.getAttribute(row, "name"),
                    self.datatable_helper.getAttribute(row, "manufacture_number"),
                    formatted_quantity,
                    self.datatable_helper.getAttribute(row, "unit"),
                    self.datatable_helper.getAttributeDate(row, "manufacture_date"),
                    formatted_price,
                    self.datatable_helper.getAttributeDate(row, "commissioning_date"),
                    self.datatable_helper.getAttribute(row, "purchase_source"),
                    self.datatable_helper.getAttributeDate(row, "purchase_date"),
                    self.datatable_helper.getAttributeDate(row, "inspection_date"),
                    "Yes" if getattr(row, "is_scrap", False) is True else "No" if getattr(row, "is_scrap", False) is False else "N/A",
                    self.datatable_helper.getAttribute(row, "id", None),
                    self.datatable_helper.getAttribute(row, "storage_id", None)
                ]
     
                for col_index, value in enumerate(fields, start = 1):
                    
                    cell = QTableWidgetItem(str(value))
                    cell.setForeground(Qt.GlobalColor.white)
                    cell.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    
                    self.setItem(row_index, col_index, cell)
  
    def get_selected_datatable_items(self) -> list[t.Union[MaterialData, ToolsData, DeviceData]]:
        
        selected_data = []
        
        for row_index in range(self.rowCount()):
            
            checkbox_widget = self.cellWidget(row_index, 0)
            
            if checkbox_widget is None:
                
                continue
            
            checkbox = checkbox_widget.findChild(QCheckBox)
            
            if checkbox is not None and checkbox.isChecked():
                
                boat_data = checkbox.property("check")
                
                if boat_data:
                    
                    selected_data.append(boat_data)
                    
                    self.log.debug("Selected data -> %s" % str(selected_data))
        
        return selected_data
                    

