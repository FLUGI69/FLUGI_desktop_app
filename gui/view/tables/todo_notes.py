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
from utils.dc.admin.work.status_note import AdminWorkStatusNote
from utils.logger import LoggerMixin

class TodoNotesTable(QTableWidget, LoggerMixin):
    
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
        
        self.setColumnWidth(0, 40)  

        header = self.horizontalHeader()
        
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        
        for _header in range(1, 3):
            
            header.setSectionResizeMode(_header, QHeaderView.ResizeMode.Stretch)
        
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def load_data(self, admin_status_notes: list[AdminWorkStatusNote]):
        
        self.log.debug("Preparing to load %d note records into the table (first 10: %s)" % (len(admin_status_notes) if isinstance(admin_status_notes, list) else 0, str(admin_status_notes[:10]) if isinstance(admin_status_notes, list) else "[]"))
        
        self.clearContents()
        
        self.setRowCount(0)

        if admin_status_notes == []:
            
            self.setRowCount(1)
            self.setColumnCount(1)
            
            self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            
            self.horizontalHeader().setStretchLastSection(True)
            
            item = QTableWidgetItem("Nincsenek jegyzetek ehhez a munkához")
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.setItem(0, 0, item)
            
            self.resizeRowsToContents()
            
            return
        
        self.setColumnCount(3)
        self.setHorizontalHeaderLabels(["#", "Jegyzet", "Kelt"])

        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        self.setUpdatesEnabled(False)
        
        try:
        
            if isinstance(admin_status_notes, list) and all(isinstance(row, AdminWorkStatusNote) for row in admin_status_notes):
                
                self.setRowCount(len(admin_status_notes))
                        
                for row_idx, note in enumerate(admin_status_notes):

                    fields = [
                        note.id,
                        note.note,
                        note.created_at
                    ]

                    for col_idx, value in enumerate(fields):

                        cell = QTableWidgetItem(str(value))
                        cell.setForeground(Qt.GlobalColor.white)
                        cell.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

                        self.setItem(row_idx, col_idx, cell)

                self.resizeRowsToContents()
        
        finally:
            
            self.setUpdatesEnabled(True)                      