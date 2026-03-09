import json
import re
import logging

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QKeyEvent, QGuiApplication, QKeySequence
from PyQt6.QtWidgets import (
    QDialog,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QWidget,
    QScrollArea
)

from utils.logger import LoggerMixin

class WorkInformationModal(QDialog, LoggerMixin):
    
    log: logging.Logger
    
    finished_signal = pyqtSignal()
    
    def __init__(self, 
        json_data, 
        parent = None
        ):
        
        super().__init__(parent)
        
        self.__init_modal(json_data)
        
    def closeEvent(self, event):
        
        self.finished_signal.emit()
        
        super().closeEvent(event)

    def __init_modal(self, json_data):
        
        self.setWindowTitle("PDF Data Table")
        self.resize(1024, 768)

        if isinstance(json_data, str):
            
            json_data = json.loads(json_data)
            
        if not isinstance(json_data, dict):
            
            json_data = {}

        main_widget = QWidget(self)
        main_widget.setObjectName("ModalWidget")
        main_layout = QHBoxLayout(main_widget)

        for main_key, main_value in json_data.items():
         
            vbox = QVBoxLayout()

            label = QLabel(self.format_label(main_key))
            
            vbox.addWidget(label)

            table = QTableWidget()
            table.setObjectName("ModalTable")
            table.setColumnCount(2)
            table.setHorizontalHeaderLabels(["Category", "Content"])
            table.horizontalHeader().setStretchLastSection(True)
            table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
            table.verticalHeader().setVisible(False)
            table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
            table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectItems)
            table.setSelectionMode(QTableWidget.SelectionMode.ExtendedSelection)

            table.setFixedWidth(1024)
            
            rows = []
            
            self.extract_data_from_json(main_value, rows)
            
            table.setRowCount(len(rows))
            
            for i, (key, value) in enumerate(rows):
                
                key_item = QTableWidgetItem(self.format_label(key))
                value_item = QTableWidgetItem(str(value))
                
                key_item.setToolTip(key_item.text())
                value_item.setToolTip(value_item.text())
                
                table.setItem(i, 0, key_item)
                table.setItem(i, 1, value_item)
            
            vbox.addWidget(table)
            main_layout.addLayout(vbox)

        scroll_area = QScrollArea(self)
        scroll_area.setObjectName("ScrollModal")
        scroll_area.setWidgetResizable(True) 
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)  
        scroll_area.setWidget(main_widget)
        
        self.setLayout(QVBoxLayout())
        self.layout().addWidget(scroll_area)  

    def extract_data_from_json(self, data, output, prefix = "", is_top_level = True):
        
        if isinstance(data, dict):
            
            for key, value in data.items():
                
                new_prefix = f"{prefix}.{key}" if prefix else key
                
                if isinstance(value, (dict, list)):
                    
                    self.extract_data_from_json(value, output, prefix = new_prefix, is_top_level = False)
                    
                else:
                    
                    output.append((new_prefix, value))
                    
        elif isinstance(data, list):
            
            for item in data:
                
                if isinstance(item, dict):
                    
                    self.extract_data_from_json(item, output, prefix = prefix, is_top_level = False)
                    
                else:
                    
                    output.append((prefix, item))
        
        else:
            
            output.append((prefix, data))
        
        if is_top_level:
            
            self.log.debug(
                "Extracted data from JSON:\n%s" %
                "\n".join(f"{key} = {value}" for key, value in output)
            )

    def format_label(self, raw_key: str) -> str:
        
        raw_key = raw_key.replace("_", " ")
        raw_key = re.sub(r'(?<!^)(?=[A-Z])', ' ', raw_key)
        raw_key = raw_key.replace(".", ": ")
        
        return raw_key.title()
    
    def keyPressEvent(self, event: QKeyEvent):
        
        if event.matches(QKeySequence.StandardKey.Copy):
            
            focus_widget = self.focusWidget()
            
            if isinstance(focus_widget, QTableWidget):
                
                selected_ranges = focus_widget.selectedRanges()
                
                if selected_ranges:
                    
                    copied_text = ""
                    
                    for r in selected_ranges:
                        
                        for row in range(r.topRow(), r.bottomRow() + 1):
                            
                            row_data = []
                            
                            for col in range(r.leftColumn(), r.rightColumn() + 1):
                                
                                item = focus_widget.item(row, col)
                                
                                row_data.append(item.text() if item else "")
                                
                            copied_text += "\t".join(row_data) + "\n"
                            
                    QGuiApplication.clipboard().setText(copied_text.strip())
        
        else:
            
            super().keyPressEvent(event)
