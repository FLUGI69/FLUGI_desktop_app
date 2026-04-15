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
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QCursor

from utils.dc.admin.work.edit import AdminEditWorkData
from utils.logger import LoggerMixin

class AdminEditTable(QTableWidget, LoggerMixin):
    
    boat_selected = pyqtSignal(object)
    
    log: logging.Logger
    
    def __init__(self, parent = None):
        
        super().__init__(parent)
        
        self.__init_table()
        
    def __init_table(self):
        
        self._checkboxes = []
        
        self.setObjectName("workscontenttable")
        
        self.setFixedHeight(550)
        
        self.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        
        self.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        
        self.verticalHeader().setVisible(False)
        
        self.setColumnCount(4)
        
        self.setHorizontalHeaderLabels(["", "Hajó", "Munkák", "Felelős"])
        
        self.setColumnWidth(0, 40)  

        header = self.horizontalHeader()
        
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        
        for _header in range(1, 4):
            
            header.setSectionResizeMode(_header, QHeaderView.ResizeMode.Stretch)
        
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def load_data(self, admin_boat_data: list[AdminEditWorkData]):
        
        self.log.debug("Preparing to load %d boat records into the table (first 10: %s)" % (len(admin_boat_data) if isinstance(admin_boat_data, list) else 0, str(admin_boat_data[:10]) if isinstance(admin_boat_data, list) else "[]"))
        
        self._checkboxes.clear()
        
        self.setUpdatesEnabled(False)
        
        try:

            if isinstance(admin_boat_data, list) and all(isinstance(row, AdminEditWorkData) for row in admin_boat_data):
                
                self.clearContents()
                
                self.setRowCount(0)
                
                self.setRowCount(len(admin_boat_data))

                for row_index, row in enumerate(admin_boat_data):
                
                    checkbox = QCheckBox()
                    checkbox.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
                    checkbox.setProperty("edit_table_data", row)
                    checkbox.stateChanged.connect(self._on_checkbox_toggled)
                    
                    self._checkboxes.append(checkbox)
                    
                    checkbox_widget = QWidget()
                    
                    layout = QHBoxLayout(checkbox_widget)
                    layout.addWidget(checkbox)
                    layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    layout.setContentsMargins(0, 0, 0, 0)
                    
                    checkbox_widget.setLayout(layout)
                    
                    self.setCellWidget(row_index, 0, checkbox_widget)
                
                    fields = [
                        row.boat.name if row.boat.name != "" else "N/A",
                        row.description if row.description != "" else "N/A",
                        row.leader if row.leader != "" else "N/A",
                    ]
                
                    for col_index, value in enumerate(fields, start = 1):
          
                        cell = QTableWidgetItem(str(value))
                        cell.setForeground(Qt.GlobalColor.white)
                        cell.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    
                        self.setItem(row_index, col_index, cell)
                
                self.resizeRowsToContents()
        
        finally:
            
            self.setUpdatesEnabled(True)
                 
    def _on_checkbox_toggled(self, state):
        
        sender_checkbox = self.sender()
        
        if state == Qt.CheckState.Checked.value:

            for cb in self._checkboxes:
                
                if cb is not sender_checkbox:
                    
                    cb.blockSignals(True)
                    cb.setChecked(False)
                    cb.blockSignals(False)
            
            boat_data = sender_checkbox.property("edit_table_data")
            
            if boat_data is not None:
                
                self.boat_selected.emit(boat_data)
                
        elif state == Qt.CheckState.Unchecked.value:
         
            self.boat_selected.emit(None)