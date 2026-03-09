import asyncio
import logging

from PyQt6.QtWidgets import (
    QDialog, 
    QVBoxLayout,
    QLabel, 
    QDialogButtonBox, 
    QWidget, 
    QHBoxLayout,
    QComboBox,
    QLineEdit,
    QDateTimeEdit
)
from PyQt6.QtCore import Qt, pyqtSignal, QDateTime, QDate, QTime
from PyQt6.QtGui import QCursor

from utils.dc.marine_traffic.search_data import MarineTrafficData
from utils.dc.admin.ship_schedule import ShipSchedule
from utils.logger import LoggerMixin

class AddSceduleModal(QDialog, LoggerMixin):

    log: logging.Logger

    def __init__(self, parent = None):
        
        super().__init__(parent)
        
        self._future = None
        
        self.selected_boat: MarineTrafficData = None
        
        self.setWindowTitle("Selection")
        
        self.setModal(True)
        
        self.setMinimumWidth(500)

        self.__init_modal()
        
        self.adjustSize()
            
    def __init_modal(self):
        
        self.setObjectName("ConfirmModal")

        self.message_label = QLabel("Select the boat from your fleet you want to add to:")
        self.message_label.setObjectName("ConfirmModalLabel")
        self.message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
 
        self.combo_box = QComboBox(self)
        self.combo_box.setFixedHeight(35)
        self.combo_box.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        
        self.label_location = QLabel("Location:")
        self.input_location = QLineEdit()
        self.input_location.setPlaceholderText("Budapest / Esztergom")
        self.input_location.setObjectName("input_unit")
        self.input_location.setFixedHeight(35)

        self.input_location_error = QLabel()
        self.input_location_error.setObjectName("error")
        self.input_location_error.setVisible(False)
        
        self.min_datetime = QDateTime.currentDateTime()

        self.label_arrival_date = QLabel("Arrival ideje:")
        self.arrival_date = QDateTimeEdit()
        self.arrival_date.setFixedHeight(35)
        self.arrival_date.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.arrival_date.setCalendarPopup(True)
        self.arrival_date.setMinimumDateTime(QDateTime(QDate(2000, 1, 1), QTime(0, 0)))
        self.arrival_date.setDateTime(self.min_datetime)

        self.arrival_date_error = QLabel()
        self.arrival_date_error.setObjectName("error")
        self.arrival_date_error.setVisible(False)
        
        self.label_ponton = QLabel("Pontoon:")
        self.input_ponton = QLineEdit()
        self.input_ponton.setPlaceholderText("International I")
        self.input_ponton.setObjectName("input_unit")
        self.input_ponton.setFixedHeight(35)

        self.input_ponton_error = QLabel()
        self.input_ponton_error.setObjectName("error")
        self.input_ponton_error.setVisible(False)
        
        self.label_leave_date = QLabel("Departure ideje:")
        self.leave_date = QDateTimeEdit()
        self.leave_date.setFixedHeight(35)
        self.leave_date.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.leave_date.setCalendarPopup(True)
        self.leave_date.setMinimumDateTime(QDateTime(QDate(2000, 1, 1), QTime(0, 0)))
        self.leave_date.setDateTime(self.min_datetime)

        self.leave_date_error = QLabel()
        self.leave_date_error.setObjectName("error")
        self.leave_date_error.setVisible(False)
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(20, 20, 20, 20)
        self.layout.setSpacing(15)
        
        self.layout.addWidget(self.message_label)
        self.layout.addWidget(self.combo_box)
        
        self.layout.addWidget(self.label_location)
        self.layout.addWidget(self.input_location)
        self.layout.addWidget(self.input_location_error)
        
        self.layout.addWidget(self.label_arrival_date)
        self.layout.addWidget(self.arrival_date)
        self.layout.addWidget(self.arrival_date_error)
                        
        self.layout.addWidget(self.label_ponton)
        self.layout.addWidget(self.input_ponton)
        self.layout.addWidget(self.input_ponton_error)
        
        self.layout.addWidget(self.label_leave_date)
        self.layout.addWidget(self.leave_date)
        self.layout.addWidget(self.leave_date_error)
  
        self.button_container = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        
        self.button_container.setObjectName("ConfirmModalButtonBox")
        self.button_container.setFixedHeight(60)

        for button in self.button_container.buttons():
            
            button.setFixedHeight(35)
            button.setFixedWidth(90)
            button.setObjectName("ConfirmModalButton")
            button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

        self.button_container.accepted.connect(self.__handle_accept)
        self.button_container.rejected.connect(self.reject)

        button_widget = QWidget()
        button_layout = QHBoxLayout(button_widget)
        button_layout.addStretch()
        button_layout.addWidget(self.button_container)
        button_layout.addStretch()
        button_layout.setContentsMargins(0, 0, 0, 0)
        button_layout.setSpacing(10)

        self.layout.addWidget(button_widget)

    def set_boats(self, boats: list[MarineTrafficData]):
        
        self.log.debug("Setting selected boats:\n%s" % "\n".join(str(boat) for boat in boats))
        
        self.combo_box.clear()

        for boat in boats:
            
            flag_emoji = self.country_flag_emoji(boat.flag if boat.flag is not None else "n.a")
            
            display_text = f"{boat.ship_name if boat.ship_name is not None else "n.a"} {flag_emoji} – {boat.type_name if boat.type_name is not None else "n.a"} (MMSI: {boat.mmsi if boat.mmsi is not None else 'n.a.'})"
            
            self.combo_box.addItem(display_text, boat)

    def country_flag_emoji(self, country_code: str) -> str:
        
        if len(country_code) != 2:
            
            return ""
        
        return chr(127397 + ord(country_code[0].upper())) + chr(127397 + ord(country_code[1].upper()))

    def __handle_accept(self):
        
        self.selected_boat = self.combo_box.currentData()
        
        has_error = self.validate_fields()
        
        if has_error is False:
            
            self.accept()

    def validate_fields(self):
        
        has_error = False
        
        current_time = self.min_datetime.toPyDateTime()
        
        location = self.input_location.text().strip()
        arrival_date = self.arrival_date.dateTime()
        ponton = self.input_ponton.text().strip()
        leave_date = self.leave_date.dateTime()
        print(arrival_date)
        print(leave_date)
        if location == "":

            self.input_location_error.setText("You did not provide a location")
            self.input_location_error.setVisible(True)

            self.log.warning("Input validation failed: 'location' field is empty")

            has_error = True

        else:

            self.input_location_error.setVisible(False)
            
        if arrival_date == current_time:
            
            self.arrival_date_error.setText("Arrival time cannot be exactly the current time")
            self.arrival_date_error.setVisible(True)
            
            self.log.warning("Input validation failed: 'arrival_date' equals current time")
            
            has_error = True

        elif arrival_date < QDateTime(QDate(2000, 1, 1), QTime(0, 0)):
            
            self.arrival_date_error.setText("Arrival year must be at least 2000")
            self.arrival_date_error.setVisible(True)
            
            self.log.warning("Input validation failed: 'arrival_date' field is invalid")
            
            has_error = True

        else:
            
            self.arrival_date_error.setVisible(False)
            
        if ponton == "":

            self.input_ponton_error.setText("You did not provide meg Pontoont")
            self.input_ponton_error.setVisible(True)

            self.log.warning("Input validation failed: 'ponton' field is empty")

            has_error = True

        else:

            self.input_ponton_error.setVisible(False)
            
        if leave_date == current_time:
            
            self.leave_date_error.setText("Departure time cannot be exactly the current time")
            self.leave_date_error.setVisible(True)
            
            self.log.warning("Input validation failed: 'leave_date' equals current time")
            
            has_error = True

        elif leave_date < QDateTime(QDate(2000, 1, 1), QTime(0, 0)):
            
            self.leave_date_error.setText("Departure year must be at least 2000")
            self.leave_date_error.setVisible(True)
            
            self.log.warning("Input validation failed: 'leave_date' field is invalid")
            
            has_error = True

        else:
            
            self.leave_date_error.setVisible(False)
            
        return has_error
    
    def get_selected_boat(self):
        
        return self.selected_boat
    
    def get_fields_data(self):
  
        data = ShipSchedule(
            schedule_id = None,
            location = self.input_location.text().strip().capitalize(),
            arrival_date = self.arrival_date.dateTime().toPyDateTime(),
            ponton = self.input_ponton.text().strip().capitalize(),
            leave_date = self.leave_date.dateTime().toPyDateTime()
        )
        
        self.log.debug("Form data: %s" % data)
        
        return data
        
    def exec_async(self) -> asyncio.Future:
        
        self._future = asyncio.get_event_loop().create_future()
        
        self.input_location.clear()
        self.arrival_date.setDateTime(self.min_datetime)
        self.input_ponton.clear()
        self.leave_date.setDateTime(self.min_datetime)
        

        self.input_location_error.setVisible(False)
        self.arrival_date_error.setVisible(False)
        self.input_ponton_error.setVisible(False)
        self.leave_date_error.setVisible(False)
        
        self.log.info("Starting asynchronous modal execution, future created and modal opened")
        
        self.accepted.connect(self._on_accepted)
        self.rejected.connect(self._on_rejected)
        
        self.open()
        
        return self._future

    def _on_accepted(self):
        
        if self._future and not self._future.done():
            
            self.log.info("Modal accepted by the user; setting future result to True")
            
            self._future.set_result(True)
            
        else:
            
            self.log.warning("Accepted signal received, but future is already done or missing")
        
        self._disconnect_signals()
        
        self.log.info("Disconnected accepted and rejected signals after acceptance")

    def _on_rejected(self):
        
        if self._future and not self._future.done():
            
            self.log.info("Modal rejected by the user; setting future result to False")
            
            self._future.set_result(False)
            
        else:
            
            self.log.warning("Rejected signal received, but future is already done or missing")
        
        self._disconnect_signals()
        
        self.log.info("Disconnected accepted and rejected signals after rejection")

    def _disconnect_signals(self):
        
        try:
            
            self.accepted.disconnect(self._on_accepted)
            self.rejected.disconnect(self._on_rejected)
            
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

