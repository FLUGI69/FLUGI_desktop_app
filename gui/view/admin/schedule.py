from functools import partial
from qasync import asyncSlot
import logging
import typing as t
from datetime import datetime

from PyQt6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QPushButton,
    QLineEdit,
    QLineEdit,
    QLabel,
    QGroupBox,
    QDialog,
    QStackedLayout
)
from PyQt6.QtCore import Qt, pyqtSignal

from config import Config
from utils.logger import LoggerMixin
from ..tables.admin.schedule_table import ScheduleTable
from utils.dc.mahart_ports.selected_boats import SelectedBoatData
from utils.dc.marine_traffic.search_data import MarineTrafficData
from utils.dc.admin.ship_schedule import ShipSchedule
from ..modal.confirm_action import ConfirmActionModal
from ..modal.admin.add_schedule import AddSceduleModal
from ..admin.custom.line_edit import SearchLineEdit
from exceptions import InvalidDateFormatError
from db import queries

if t.TYPE_CHECKING:
    
    from .admin import AdminView

class ScheduleContent(QWidget, LoggerMixin):
    
    log: logging.Logger
    
    refresh_todo = pyqtSignal(bool)

    def __init__(self, 
        admin_view: 'AdminView'             
        ):

        super().__init__()

        self.spinner = admin_view.main_window.app.spinner
        
        self.schedule_table = ScheduleTable(self)
        
        self.add_schedule_modal = AddSceduleModal(self)

        self.confirm_action_modal = ConfirmActionModal(self)
           
        self.__init_view()
        
        self.schedule_table.row_modified_data.connect(self.handle_update_boat_schedule)
        
    def __init_view(self):
        
        self.results_table = None
        
        main_layout = QVBoxLayout(self)

        search_group = QGroupBox()
        search_layout = QHBoxLayout(search_group)

        col_layout = QVBoxLayout()

        title_label = QLabel("Mentett Menetrend")
        title_label.setObjectName("BoatTitleLabel")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setFixedHeight(35)
        title_label.setMaximumWidth(380)
        
        self.input_field = SearchLineEdit(btn_callback = self.__on_btn_clicked)
        self.input_field.setObjectName("BoatSearchInput")
        self.input_field.setPlaceholderText("Menetrend keresés...")
        self.input_field.setFixedHeight(35)
        self.input_field.setMaximumWidth(380)

        self.error_label = QLabel()
        self.error_label.setObjectName("error")
        self.error_label.setVisible(False)
        
        self.success_label = QLabel()
        self.success_label.setObjectName("success")
        self.success_label.setVisible(False)

        schedule_add_btn = QPushButton("Menetrend Hozzáadása")
        schedule_add_btn.setObjectName("BoatSearchBtn")
        schedule_add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        schedule_add_btn.setFixedHeight(35)
        schedule_add_btn.setMaximumWidth(380)
        schedule_add_btn.clicked.connect(partial(self.__on_btn_clicked, 1))
        
        col_layout.addWidget(title_label)
        col_layout.addWidget(self.input_field)
        col_layout.addWidget(self.error_label)
        col_layout.addWidget(self.success_label)
        col_layout.addWidget(schedule_add_btn)

        search_layout.addLayout(col_layout)

        main_layout.addWidget(search_group)

        self.content_container = QWidget()
        self.content_container.setObjectName("BoatListContainer")

        self.stack = QStackedLayout()
        self.content_container.setLayout(self.stack)

        main_layout.addWidget(self.content_container)

        self.__set_content(self.schedule_table)
    
    @asyncSlot()
    async def __on_btn_clicked(self, idx: int):
        
        self.error_label.setVisible(False)
        self.success_label.setVisible(False)
        
        if self.content_container:
            
            self.spinner.show(self.content_container)
        
        try:
            
            if idx == 0:
                
                await self.load_table()
            
            elif idx == 1:
                
                query_results = await queries.select_all_boats()
                
                if len(query_results) > 0:
                    
                    boats = [
                        MarineTrafficData(
                            id = row.id,
                            ship_name = row.name,
                            more_deatails_href = row.more_deatails_href,
                            view_on_map_href = row.view_on_map_href,
                            ship_id = row.ship_id,
                            type_name = row.type_name,
                            flag = row.flag,
                            mmsi = row.mmsi,
                            callsign = row.callsign,
                            imo = row.imo,
                            reported_destination = None,
                            matched_destination = None
                        ) for row in query_results
                    ]
                    
                    self.add_schedule_modal.set_boats(boats)
                    
                    accepted = await self.add_schedule_modal.exec_async() 
                    
                    if not accepted:
                        return
                        
                    elif accepted:
                        
                        boat = self.add_schedule_modal.get_selected_boat()
                        schedule =  self.add_schedule_modal.get_fields_data()
         
                        await self.__insert_schedule_for_particular_ship(
                            boat_id = boat.id,
                            location = schedule.location,
                            arrival_date = schedule.arrival_date,
                            ponton = schedule.ponton,
                            leave_date = schedule.leave_date
                        )
         
        except Exception as e:

            self.log.exception("Search callback failed: %s" % str(e))
        
        finally:
            
            self.spinner.hide()

    async def load_table(self):
        
        boat_name = self.input_field.text().strip()
        
        query_results = await queries.select_schedule_by_boat_name(boat_name)
        # for row in query_results:
        #     print(row.__dir__())
        
        boats = [SelectedBoatData(
            boat_id = row.id,
            name = row.name,
            flag = row.flag,
            mmsi = row.mmsi,
            imo = row.imo,
            ship_id = row.ship_id,
            schedule = [ShipSchedule(
                schedule_id = schedule.id,
                location = schedule.location,
                arrival_date = schedule.arrived_date,
                ponton = schedule.ponton,
                leave_date = schedule.leave_date
                ) for schedule in row.schedule]
            ) for row in query_results
        ]
        
        self.schedule_table.load_data(boats)
    
    @asyncSlot(tuple)
    async def handle_update_boat_schedule(self, data: tuple):
        
        self.error_label.setVisible(False)
        
        previous, modified = data
        
        if previous is None and isinstance(modified, InvalidDateFormatError):
            
            self.log.warning(modified.message)
            
            self.error_label.setVisible(True)
            self.error_label.setText(f"Nem megfelelő dátum formátum: '{modified.str_date}' megfelelő: 'ÉÉÉÉ-HH-NN OO:PP'")
            
            return
    
        else:
            
            if len(previous) > 0:
                
                values_to_update = {}
                
                if previous[0].location != modified[0].location:
                    
                    values_to_update["location"] = modified[0].location
                    
                if previous[0].arrival_date != modified[0].arrival_date:
                    
                    values_to_update["arrived_date"] = modified[0].arrival_date
                    
                if previous[0].ponton != modified[0].ponton:
                    
                    values_to_update["ponton"] = modified[0].ponton

                if previous[0].leave_date != modified[0].leave_date:
                    
                    values_to_update["leave_date"] = modified[0].leave_date
                
                try:

                    await queries.update_schedule_by_id(
                        id = modified[0].schedule_id,
                        values_to_update = values_to_update
                    )

                    self.success_label.setVisible(True)
                    self.success_label.setText(f"Sikeresen frissítetted menetrendet")

                    self.refresh_todo.emit(True)
                    
                    await self.load_table()
                    
                except Exception as e:
                    
                    self.log.exception("Unexpected error occured during the update %s" % str(e))
                    
                    self.error_label.setVisible(True)
                    self.error_label.setText(f"Valami hiba történt")

    async def __insert_schedule_for_particular_ship(self,
        boat_id: int,
        location: str,
        arrival_date: datetime,
        ponton: str,
        leave_date: datetime
        ):

        try:

            await queries.insert_boat_schedule(
                boat_id = boat_id,
                schedules = [{
                    "location": location,
                    "arrived_date": arrival_date,
                    "ponton": ponton,
                    "leave_date": leave_date
                }]
            )
            
            self.success_label.setVisible(True)
            self.success_label.setText(f"Sikeresen rögzítetted az adatokat")

            self.refresh_todo.emit(True)
            
            await self.load_table()
            
        except Exception as e:
            
            self.log.exception("Unexpected error occured during the insertion %s" % str(e))
            
            self.error_label.setVisible(True)
            self.error_label.setText(f"Valami hiba történt")

    def __set_content(self, new_view: QWidget):
        
        index = self.stack.indexOf(new_view)
        
        if index == -1:
            
            self.stack.addWidget(new_view)
            
            index = self.stack.indexOf(new_view)

        self.stack.setCurrentIndex(index)
        
        self.results_table = new_view