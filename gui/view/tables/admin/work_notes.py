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

class AdminEditWorkNotes(QTableWidget, LoggerMixin):
    
    note_changed = pyqtSignal(object)
    
    log: logging.Logger
    
    def __init__(self, parent = None):
        
        super().__init__(parent)
        
        self._prev_note_values = {} 
        
        self.__init_table()
        
    def __init_table(self):

        self.setObjectName("workscontenttable")
        
        self.setFixedHeight(550)

        self.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        
        self.verticalHeader().setVisible(False)
        
        self.setColumnCount(3)
        
        self.setHorizontalHeaderLabels(["#", "Jegyzet", "Kelt"])
        
        self.setColumnWidth(0, 40)  

        header = self.horizontalHeader()
        
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        
        for _header in range(1, 3):
            
            header.setSectionResizeMode(_header, QHeaderView.ResizeMode.Stretch)
        
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        self.setEditTriggers(
            QTableWidget.EditTrigger.DoubleClicked |
            QTableWidget.EditTrigger.SelectedClicked
        )

        self.itemChanged.connect(self.table_cell_changed)

    def load_data(self, admin_boat_data: list[AdminEditWorkData]):
        
        self.log.debug("Preparing to load the following boat records into the table: %s" % str(admin_boat_data))
        
        self.clearContents()
        
        self.setRowCount(0)

        if isinstance(admin_boat_data, list) and all(isinstance(row, AdminEditWorkData) for row in admin_boat_data):
            
            for _, work in enumerate(admin_boat_data):
                
                if work.status is not None:
                    
                    if len(work.status.notes) > 0:
                        
                        for row_index, note in enumerate(work.status.notes):
                            
                            self.insertRow(row_index)
                            
                            fields = [
                                note.id,
                                note.note,
                                note.created_at
                            ]

                            for col_index, value in enumerate(fields):
                    
                                cell = QTableWidgetItem(str(value))
                                cell.setForeground(Qt.GlobalColor.white)
                                cell.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

                            
                                if col_index == 1:
                                    
                                    cell.setFlags(
                                        Qt.ItemFlag.ItemIsSelectable |
                                        Qt.ItemFlag.ItemIsEnabled |
                                        Qt.ItemFlag.ItemIsEditable
                                    )
                                    
                                    cell.setData(Qt.ItemDataRole.UserRole, note)
                                    
                                    self._prev_note_values[note.id] = note.note
                                    
                                else:
                                    
                                    cell.setFlags(
                                        Qt.ItemFlag.ItemIsSelectable |
                                        Qt.ItemFlag.ItemIsEnabled
                                    )

                                self.setItem(row_index, col_index, cell)
                            
                            self.resizeRowsToContents()
                            
    def table_cell_changed(self, item: QTableWidgetItem):

        if item.column() != 1:
            return

        note: AdminWorkStatusNote = item.data(Qt.ItemDataRole.UserRole)
        
        new_note_text = item.text().strip()

        if note.id is not None:
            
            prev_note_text = self._prev_note_values.get(note.id, "")

            if prev_note_text != new_note_text:
                
                self.log.debug("Note with ID (%d) previous value has been changed from: '%s' -> '%s'" % (
                    note.id,
                    prev_note_text,
                    new_note_text
                    )    
                )
                
                self._prev_note_values[note.id] = new_note_text

                setattr(note, "note", new_note_text)
                
                self.note_changed.emit(note)
                            