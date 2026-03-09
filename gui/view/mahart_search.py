from functools import partial
from qasync import asyncSlot
import logging
import typing as t

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
from utils.scraping import WebScraper
from utils.dc.ship_info import ShipInfo
from .tables.mahart_ports import MahartPortsTable
from .modal.confirm_action import ConfirmActionModal
from .modal.select_boat import SelectBoatModal
from utils.dc.mahart_ports.selected_boats import SelectedBoatData
from db import queries

if t.TYPE_CHECKING:
    
    from .main_window import MainWindow

class MahartPortsSearchView(QWidget, LoggerMixin):
    
    log: logging.Logger
    
    refresh_todo = pyqtSignal(bool)
    
    def __init__(self,
        main_window: 'MainWindow'             
        ):

        super().__init__()

        self.spinner = main_window.app.spinner
        
        self.mahart_ports_table = MahartPortsTable()
        
        self.select_boat_modal = SelectBoatModal(self)
        
        self.confirm_action_modal = ConfirmActionModal(self)
           
        self.__init_view()
        
    def __init_view(self):
        
        self.results_table = None
        
        main_layout = QVBoxLayout(self)

        self.search_fields = []
        self.error_labels = []
        self.search_buttons = []
        self.add_buttons = []
        
        self._search_callbacks = [
            self.__search_mahart,
            self._handle_add_mahart_btn,
        ]
        
        search_group = QGroupBox()
        search_layout = QHBoxLayout(search_group)

        col_layout = QVBoxLayout()

        title_label = QLabel("Mahart Ports")
        title_label.setObjectName("BoatTitleLabel")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setFixedHeight(35)
        title_label.setMaximumWidth(380)
        
        self.input_field = QLineEdit()
        self.input_field.setObjectName("BoatSearchInput")
        self.input_field.setPlaceholderText("Search...")
        self.input_field.setFixedHeight(35)
        self.input_field.setMaximumWidth(380)

        self.error_label = QLabel()
        self.error_label.setObjectName("error")
        self.error_label.setVisible(False) 
        self.error_label.setMaximumWidth(380)

        search_btn = QPushButton("Search")
        search_btn.setObjectName("BoatSearchBtn")
        search_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        search_btn.setFixedHeight(35)
        search_btn.setMaximumWidth(380)
        search_btn.clicked.connect(partial(self.__on_btn_clicked, 0))
        
        add_btn = QPushButton("Add")
        add_btn.setObjectName("BoatSearchBtn")
        add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        add_btn.setFixedHeight(35)
        add_btn.setMaximumWidth(380)
        add_btn.clicked.connect(partial(self.__on_btn_clicked, 1))

        col_layout.addWidget(title_label)
        col_layout.addWidget(self.input_field)
        col_layout.addWidget(self.error_label)
        col_layout.addWidget(search_btn)
        col_layout.addWidget(add_btn)

        self.search_fields.append(self.input_field)
        self.error_labels.append(self.error_label)
        self.search_buttons.append(search_btn)
        self.add_buttons.append(add_btn)

        search_layout.addLayout(col_layout)

        main_layout.addWidget(search_group)

        self.content_container = QWidget()
        self.content_container.setObjectName("BoatListContainer")

        self.stack = QStackedLayout()
        self.content_container.setLayout(self.stack)

        main_layout.addWidget(self.content_container)

        self.__set_content(self.mahart_ports_table)
        
    # async def __load_page(self, ship_infos: t.Optional[t.List[ShipInfo]] = None):
        
    #     if not isinstance(ship_infos, list):
            
    #         return

    #     self.results_table.clearContents()
    #     self.results_table.setRowCount(0)

    #     headers = ["Name", "Port", "Arrival", "Pontoon", "Departure"]
    #     self.results_table.setColumnCount(len(headers))
    #     self.results_table.setHorizontalHeaderLabels(headers)

    #     row_index = 0

    #     for inner_list in ship_infos:
            
    #         if not isinstance(inner_list, list):
                
    #             continue

    #         for info in inner_list:
                
    #             if not isinstance(info, ShipInfo):
                    
    #                 continue

    #             self.results_table.insertRow(row_index)

    #             fields = [
    #                 info.name,
    #                 info.port,
    #                 info.arrival_date.strftime("%Y-%m-%d %H:%M"),
    #                 info.ponton,
    #                 info.departure_date.strftime("%Y-%m-%d %H:%M"),
    #             ]

    #             for col_index, value in enumerate(fields):
                    
    #                 item = QTableWidgetItem(value)
    #                 item.setForeground(Qt.GlobalColor.white)
    #                 item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    
    #                 self.results_table.setItem(row_index, col_index, item)

    #             row_index += 1

    #     self.results_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

    #     Spinner.hide()
    
    @asyncSlot()
    async def __on_btn_clicked(self, idx: int):
       
        if self.content_container:
            
            self.spinner.show(self.content_container)
        
        try:
            
            if idx == 1:
            
                await self._handle_add_mahart_btn()
                 
            elif idx < len(self._search_callbacks):
                
                await self._search_callbacks[idx]()
                
        except Exception as e:

            self.log.exception("Search callback failed: %s" % str(e))
        
        finally:
            
            self.spinner.hide()

    async def __search_mahart(self) -> list[ShipInfo]:
        
        if self.results_table is None:
            
            self.log.error("Results table is not initialized")
            
            self.spinner.hide()
            
            return
        
        self.results_table.clearContents()
        
        input_name = self.search_fields[0].text()
        
        if not input_name:
            
            self.log.warning("[MAHART] Empty search input provided, skipping search")
            
            self.error_labels[0].setText("Search field cannot be empty")
            self.error_labels[0].setVisible(True)
            
            self.spinner.hide()
            
            return 
        
        if len(input_name) <= 3:
            
            self.log.warning("[MAHART] Search input is too short, skipping search")
            
            self.error_labels[0].setText("(%s) Too short for search" % (str(input_name)))
            self.error_labels[0].setVisible(True)
            
            self.spinner.hide()
            
            return 

        self.error_labels[0].setVisible(False)
        
        self.log.info("Mahart Ports searching on web: %s" % (str(input_name)))

        # if not matching_original_names:

        #     self.log.warning("[MAHART] No matching ship found for %s" % (str(input_name)))
            
        #     self.error_labels[idx].setText("(%s) Ship not found with this name" % (str(input_name)))
        #     self.error_labels[idx].setVisible(True)
            
        #     Spinner.hide()

        #     return

        try:
            
            result = await WebScraper.search_ship_by_name_on_mahart(
                name = input_name,
                url = Config.web_scraper.mahart_ports.url
            )
            
        except Exception as e:
            
            self.log.error("Search failed: %s" % str(e))
            
            self.error_labels[0].setText("An error occurred during search")
            self.error_labels[0].setVisible(True)
            
            self.spinner.hide()
            
            return

        if result.status != "success" or not result.ship:
            
            self.log.warning("[MAHART] No matching ship found for %s" % (str(input_name)))
            
            self.error_labels[0].setText("(%s) Ship not found with this name" % (str(input_name)))
            self.error_labels[0].setVisible(True)
            
            self.spinner.hide()
            
            return

        self.mahart_ports_table.load_data(result.ship)
        
        self.input_field.clear()
        
        self.spinner.hide()

    async def _handle_add_mahart_btn(self):
        
        selected_ships = self.mahart_ports_table.get_selected_ship_data()
        
        if not selected_ships:
            
            self.log.warning("No boat selected for adding")
            
            self.error_labels[0].setText("You did not select a ship to add")
            self.error_labels[0].setVisible(True)
            
            self.spinner.hide()
            
            return 
        
        selected_list = [
            row for row in selected_ships if isinstance(row, ShipInfo)
        ]
        
        query_results = await queries.select_all_boats()
        
        if len(query_results) > 0:
            
            boats = [SelectedBoatData(
                boat_id = row.id,
                name = row.name,
                flag = row.flag,
                mmsi = row.mmsi,
                imo = row.imo,
                ship_id = row.ship_id
            ) for row in query_results]
            
            self.select_boat_modal.set_boats(boats)
            
            accepted = await self.select_boat_modal.exec_async() 
            
            if not accepted:
                
                self.spinner.hide()
                
                return

            elif accepted:
                
                if len(selected_list) > 0:
                    
                    selected_boat = self.select_boat_modal.get_selected_boat()
                    
                    if isinstance(selected_boat, SelectedBoatData):
                        
                        confirm_text_lines = [
                            f"{selected_boat.name.capitalize()} -> Arrival: {row.arrival_date} Pontoon: {row.ponton} Departure: {row.departure_date}" for row in selected_list
                        ]
                        
                        confirm_text = (
                            "Add schedule:\n\n"
                            + "\n".join(confirm_text_lines)
                            + "\n\nBiztosan folytatod?"
                        )
                        
                        self.confirm_action_modal.set_action_message(confirm_text)
                
                        if self.confirm_action_modal.exec() != QDialog.DialogCode.Accepted:
                            
                            self.spinner.hide()
                            
                            return
                        
                        await self.__add_data_from_mahart(
                            selected_boat_data = selected_boat,
                            ship_schedule_data = selected_ships
                        )

        elif query_results == []:
            
            self.log.info("No records found in the database")
                
            self.error_labels[0].setText("No result found in the database")
            self.error_labels[0].setVisible(True)  
                
    async def __add_data_from_mahart(self, selected_boat_data: SelectedBoatData, ship_schedule_data: list[ShipInfo],):
        
        schedule_str = ", ".join(
            "%s - %s - %s - %s" % (row.port, row.arrival_date, row.ponton, row.departure_date)
            for row in ship_schedule_data
        )

        self.log.debug("Adding ship schedule data from Mahart. Selected Boat: %s | Schedule: %s" % (
            str(selected_boat_data),
            schedule_str
            )
        )
        
        for row in ship_schedule_data:
            
            await queries.insert_boat_schedule(
                boat_id = selected_boat_data.boat_id,
                location = row.port,
                arrived_date = row.arrival_date,
                ponton = row.ponton,
                leave_date = row.departure_date
            )

        self.refresh_todo.emit(True)
        
    def __set_content(self, new_view: QWidget):
        
        index = self.stack.indexOf(new_view)
        
        if index == -1:
            
            self.stack.addWidget(new_view)
            
            index = self.stack.indexOf(new_view)

        self.stack.setCurrentIndex(index)
        
        self.results_table = new_view

