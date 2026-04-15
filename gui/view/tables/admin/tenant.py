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

from utils.dc.admin.tenant_items import AdminTenantsCacheData
from utils.dc.tenant_data import TenantData
from utils.logger import LoggerMixin
from utils.handlers.data_table import DataTableHelper

class TenantsTable(QTableWidget, LoggerMixin):
    
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
        
        self.setColumnCount(9)
        
        self.setHorizontalHeaderLabels([
            "", 
            "Megnevezés", 
            "Bérlő neve", 
            "Bérlés kezdete", 
            "Bérlés vége", 
            "Visszaadva", 
            "Bérlés ára", 
            "Árazás típusa",
            "Bérelt mennyiség"
        ])
        
        header = self.horizontalHeader()
        
        for col_index in range(self.columnCount()):
            header.setSectionResizeMode(col_index, QHeaderView.ResizeMode.Interactive)

        column_widths = {
            0: 40,
            1: 250,
            2: 250,
            3: 250,
            4: 250,
            5: 250,
            6: 300,
            7: 250,
            8: 250
        }

        for col_index, width in column_widths.items():
            
            self.setColumnWidth(col_index, width)

        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
    def load_data(self, tenant_data: AdminTenantsCacheData):
        
        items = tenant_data.items if hasattr(tenant_data, "items") else []
        
        self.log.debug("Preparing to load %d records into the table (first 10: %s)" % (len(items), str(items[:10])))
        
        self.setUpdatesEnabled(False)
        
        try:
        
            self.clearContents()
            
            self.setRowCount(0)

            if len(items) > 0:
                
                self.setRowCount(len(items))

                for row_index, row in enumerate(items):
            
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
                    
                    price_value = getattr(row, "rental_price", None)
                    
                    formatted_price = "{:,.2f}".format(price_value).replace(",", ".") if price_value is not None else "N/A"

                    formatted_quantity = f"{self.datatable_helper.getAttribute(row, "quantity"):.4f}"
                    
                    rental_end =  "Nincs megadva" if self.datatable_helper.getAttributeDate(row, "rental_end") == self.datatable_helper.getAttributeDate(row, "rental_start") \
                        else self.datatable_helper.getAttributeDate(row, "rental_end")
                    
                    fields = [
                        self.datatable_helper.getAttribute(row, "item_name"),
                        self.datatable_helper.getAttribute(row, "tenant_name"),
                        self.datatable_helper.getAttributeDate(row, "rental_start"),
                        rental_end,
                        "Igen" if getattr(row, "returned", False) is True else "Nem" if getattr(row, "returned", False) is False else "N/A",
                        formatted_price,
                        "Napi ár" if getattr(row, "is_daily_price", True) else "Teljes időszak",
                        formatted_quantity,
                        self.datatable_helper.getAttribute(row, "item_id", None),
                        self.datatable_helper.getAttribute(row, "tenant_id", None),
                    ]
     
                    for col_index, value in enumerate(fields, start = 1):
                    
                        cell = QTableWidgetItem(str(value))
                        cell.setForeground(Qt.GlobalColor.white)
                        cell.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    
                        self.setItem(row_index, col_index, cell)
        
        finally:
            
            self.setUpdatesEnabled(True)

    def get_selected_datatable_items(self) -> list[TenantData]:
        
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
                    