import asyncio
import logging
import typing as t

from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QLabel,
    QDialogButtonBox,
    QWidget,
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QScrollArea,
    QDoubleSpinBox
)
from PyQt6.QtCore import Qt, QDateTime, QDate, QTime
from PyQt6.QtGui import QCursor, QFont


from utils.dc.returnable_packaging import ReturnablePackagingData
from utils.logger import LoggerMixin
from config import Config

class SendBackModal(QDialog, LoggerMixin):
    
    log: logging.Logger

    def __init__(self, parent = None):
        
        super().__init__(parent)
        
        self._future = None
        
        self.item_quantity = None
        
        self.setWindowTitle("Visszaküldés")
        
        self.setModal(True)
        
        self.setMinimumWidth(800)

        self.__init_modal()
        
        self.adjustSize()
            
    def __init_modal(self):
        
        self.setObjectName("AddToolsModal")
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        self.label = QLabel("Göngyöleg visszaküldése")
        self.label.setObjectName("BoatTitleLabel")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setWordWrap(True)
        
        self.list_widget = QListWidget()
        self.list_widget.setObjectName("MessageList")
        self.list_widget.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self.list_widget.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.list_widget.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.list_widget.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.list_widget.setMinimumHeight(250)

        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.button_box.setObjectName("ConfirmModalButtonBox")
        self.button_box.setFixedHeight(60)

        for btn in self.button_box.buttons():
            
            btn.setFixedHeight(35)
            btn.setFixedWidth(90)
            btn.setObjectName("ConfirmModalButton")
            btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

        footer = QWidget()
        
        footer_layout = QHBoxLayout(footer)
        footer_layout.addStretch()
        footer_layout.addWidget(self.button_box)
        footer_layout.addStretch()
        footer_layout.setContentsMargins(0, 0, 0, 0)

        main_layout.addWidget(self.label)
        main_layout.addWidget(self.list_widget, stretch = 1)
        main_layout.addWidget(footer)
        
    def setup_modal_data(self, returnable_list: t.List[ReturnablePackagingData]):
        
        self.list_widget.clear()
        
        self.log.debug("Populating returnable packaging list with %d items of (%s) data" % (
            len(returnable_list),
            returnable_list[0].__class__.__name__
            )
        )
        
        self.list_widget.setUniformItemSizes(True)
        
        font = QFont()
        font.setPointSize(10)
        font.setBold(True)
        
        for returnable in returnable_list:
            
            if returnable.is_returned == False and returnable.is_deleted == False:
            
                name = returnable.name if returnable.name is not None else "N/A"
                
                manufacture_number = returnable.manufacture_number if returnable.manufacture_number is not None else "N/A"
                
                quantity = returnable.quantity if returnable.quantity is not None else 0.0000
                            
                price = f"{returnable.price:.2f}" if returnable.price is not None else "N/A"
            
                purchase_source = returnable.purchase_source if returnable.purchase_source else "N/A"
                
                purchase_date = returnable.purchase_date.strftime(Config.time.timeformat) if returnable.purchase_date else "N/A"
                        
                list_item = QListWidgetItem()
        
                container = QWidget()
                container.setFixedHeight(35)
                
                self.input_quantity = QDoubleSpinBox()
                self.input_quantity.setDecimals(4)
                self.input_quantity.setSingleStep(1)
                self.input_quantity.setMinimum(0)
                self.input_quantity.setMaximum(quantity)
                self.input_quantity.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
                self.input_quantity.setObjectName("input_quantity")
                self.input_quantity.setFixedHeight(35)
                
                self.input_quantity.setValue(0)
                
                labels = {
                    "Name": name,
                    "Manufacture": manufacture_number,
                    "Price": price,
                    "Purchase Source": purchase_source,
                    "Purchase Date": purchase_date
                }

                h_layout = QHBoxLayout(container)
                h_layout.setContentsMargins(5, 2, 5, 2)
                h_layout.setSpacing(10)

                for _, value in labels.items():
                    
                    lbl = QLabel(f" {value} ")
                    lbl.setFont(font)
                    
                    h_layout.addWidget(lbl)
                    h_layout.addStretch(5)
                    
                h_layout.addWidget(self.input_quantity, alignment = Qt.AlignmentFlag.AlignRight)
                
                container.setLayout(h_layout)
                
                list_item.setSizeHint(container.sizeHint())
                
                self.list_widget.addItem(list_item)
                self.list_widget.setItemWidget(list_item, container)
                self.list_widget.setSpacing(0)
                
                list_item.setData(Qt.ItemDataRole.UserRole, returnable)

            if len(returnable_list) > 10:
                
                self.list_widget.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
                
            else:
                
                self.list_widget.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
    
    def get_form_data(self) -> t.List[ReturnablePackagingData]:
        
        data: t.List[ReturnablePackagingData] = []

        for index in range(self.list_widget.count()):
            
            list_item = self.list_widget.item(index)
            container = self.list_widget.itemWidget(list_item)
            
            returnable: ReturnablePackagingData = list_item.data(Qt.ItemDataRole.UserRole)
            
            spin_box: QDoubleSpinBox = container.findChild(QDoubleSpinBox, "input_quantity")
            
            if spin_box:
                
                returnable.quantity = spin_box.value()
            
            data.append(returnable)
        
        self.log.debug("Form data: %s" % data)
        
        return data
    
    def exec_async(self) -> asyncio.Future:
        
        self._future = asyncio.get_event_loop().create_future()
        
        self.log.info("Starting asynchronous modal execution, future created and modal opened")
        
        self.accepted.connect(self._on_accepted)
        self.rejected.connect(self._on_rejected)
        
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