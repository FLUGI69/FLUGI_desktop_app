import asyncio
import logging
from qasync import asyncSlot
import typing as t 

from PyQt6.QtWidgets import (
    QDialog, 
    QVBoxLayout,
    QLabel, 
    QDialogButtonBox, 
    QWidget, 
    QHBoxLayout,
    QComboBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QCursor

from utils.dc.todo_data import BoatWork
from utils.dc.admin.work.status import AdminWorkStatus
from utils.dc.admin.work.status_note import AdminWorkStatusNote
from utils.logger import LoggerMixin
from view.tables.todo_notes import TodoNotesTable
from db import queries

class StatusNotesModal(QDialog, LoggerMixin):

    log: logging.Logger

    def __init__(self, parent = None):
        
        super().__init__(parent)
        
        self._future = None
        
        self.setWindowTitle("Munka jegyzetek")
        
        self.setModal(True)
        
        self.setMinimumWidth(500)

        self.notes_table = TodoNotesTable(self)

        self.__init_modal()
        
        self.adjustSize()
            
    def __init_modal(self):
        
        self.setObjectName("ConfirmModal")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        self.message_label = QLabel("Válaszd ki a munkát a jegyzetek megtekintéséhez:")
        self.message_label.setObjectName("ConfirmModalLabel")
        self.message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
 
        self.combo_box = QComboBox(self)
        self.combo_box.setFixedHeight(35)
        self.combo_box.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        
        self.combo_box.currentIndexChanged.connect(self._on_combo_changed)
        
        status_notes_section = self.set_status_notes_section()
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(20, 20, 20, 20)
        self.layout.setSpacing(15)
        
        self.layout.addWidget(self.message_label)
        self.layout.addWidget(self.combo_box)
        
        self.layout.addWidget(status_notes_section)
  
        self.button_container = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        
        self.button_container.setObjectName("ConfirmModalButtonBox")
        self.button_container.setFixedHeight(60)

        for button in self.button_container.buttons():
            
            button.setFixedHeight(35)
            button.setFixedWidth(90)
            button.setObjectName("ConfirmModalButton")
            button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

        self.button_container.accepted.connect(self.accept)

        button_widget = QWidget()
        button_layout = QHBoxLayout(button_widget)
        button_layout.setContentsMargins(0, 0, 0, 0)
        button_layout.setSpacing(0)
        button_layout.addStretch()
        button_layout.addWidget(self.button_container, alignment = Qt.AlignmentFlag.AlignCenter)
        button_layout.addStretch()

        self.layout.addWidget(button_widget)
    
    @asyncSlot(int)
    async def _on_combo_changed(self, index):
        
        work: BoatWork = self.combo_box.itemData(index)
        
        if work is not None and work.transfered == True:
            
            work_status = await self.select_work_status_notes_by_id(work.id)

            if work_status is not None:
                
                self.notes_table.load_data(work_status.notes)
            
            else:
                
                self.notes_table.load_data([])
                
                self.log.info("No work_status or notes found for work - %s" % work.description)
                
        else:
            
            self.notes_table.load_data([])
            
            self.log.debug("Work '%s' is not marked as transferred. Skipping notes loading." % (
                str(work)
                )
            )
            
    async def select_work_status_notes_by_id(self, id: int) -> AdminWorkStatus | None:
        
        if id is not None:
            
            try:

                query_result = await queries.select_work_status_by_work_id(id)
                
                if query_result is not None:
                    
                    work_status = AdminWorkStatus(
                        id = query_result.id,
                        delivered_back = query_result.delivered_back,
                        notes = [AdminWorkStatusNote(
                            id = note.id,
                            note = note.note,
                            created_at = note.created_at
                        ) for note in query_result.notes]
                    )
                    
                    self.log.debug("Retrieved work_status for work_id: %d with %s obj." % (
                        id,
                        str(work_status)
                        )
                    )
                
                    return work_status
                
                return None
            
            except Exception as e:
                
                self.log.exception("Unexpected erro occured during the notes selection %s" % str(e))
                
    def set_status_notes_section(self):
        
        status_notes_container = QWidget()
    
        v_layout = QVBoxLayout()

        label = QLabel("Munka folyamatának jegyzetei")
        label.setObjectName("BoatTitleLabel")

        v_layout.addWidget(label)
        v_layout.addWidget(self.notes_table)

        status_notes_container.setLayout(v_layout)
        
        return status_notes_container

    def set_dropdown(self, works: list[BoatWork]):
        
        self.log.debug("Setting selected works:\n%s" % "\n".join(str(work) for work in works))
        
        self.combo_box.clear()

        for work in works:
            
            display_text = f"Vezető: {work.leader} | Leírás: {work.description}"
            
            self.combo_box.addItem(display_text, work)

    def exec_async(self) -> asyncio.Future:
        
        self._future = asyncio.get_event_loop().create_future()
        
        self.log.info("Starting asynchronous modal execution, future created and modal opened")
        
        self.accepted.connect(self._on_accepted)
        
        self.open()
        
        return self._future

    def _on_accepted(self):
        
        if self._future and not self._future.done():
            
            self.log.info("Modal accepted by the user setting future result to True")
            
            self._future.set_result(True)
            
        else:
            
            self.log.warning("Accepted signal received, but future is already done or missing")
        
        self._disconnect_signals()
        
        self.log.info("Disconnected accepted and rejected signals after acceptance")

    def _on_rejected(self):
        
        if self._future and not self._future.done():
            
            self.log.info("Modal rejected by the user setting future result to False")
            
            self._future.set_result(False)
            
        else:
            
            self.log.warning("Rejected signal received, but future is already done or missing")
        
        self._disconnect_signals()
        
        self.log.info("Disconnected accepted and rejected signals after rejection")

    def _disconnect_signals(self):
        
        try:
            
            self.accepted.disconnect(self._on_accepted)
            
            self.log.debug("Successfully disconnected modal signals")
            
        except TypeError:
            
            self.log.warning("Attempted to disconnect signals that were not connected")

    def closeEvent(self, event):
        
        if self._future and not self._future.done():
            
            self.log.info("Modal closed without explicit accept/reject; setting future result to False")
            
            self._future.set_result(False)
        
        self._disconnect_signals()
        
        self.log.info("Modal closed; signals disconnected and closing event propagated")
        
        super().closeEvent(event)