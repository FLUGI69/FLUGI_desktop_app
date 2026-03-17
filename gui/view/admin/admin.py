import logging
import typing as t
import asyncio

from PyQt6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QStackedLayout
)
from PyQt6.QtCore import pyqtSignal

from utils.logger import LoggerMixin
from ..elements.sidebar import HoverSidebar
from .personnel import PersonnelContent
from .works import AdminWorksContent
from .calendar import CalendarContent
from .schedule import ScheduleContent
from .storage import AdminStorageContent
from .login_history import LoginHistoryContent
from .tenant import TenantsContent
from .rental_history import RentalHistoryContent
from .quotation import PriceQuotationContent

if t.TYPE_CHECKING:
    
    from ..main_window import MainWindow

class AdminView(QWidget, LoggerMixin):
    
    log: logging.Logger

    refresh_todo = pyqtSignal(bool)
    
    refresh_other_work_prices = pyqtSignal()

    def __init__(self,
        main_window: 'MainWindow'
        ):
        
        super().__init__()
        
        self.main_window = main_window
        
        self.reminder_worker = main_window.reminder_worker

        self.redis_client = main_window.redis_client
        
        self.rental_worker = main_window.rental_worker
        
        self.rental_end = main_window.rental_end
        
        self.calendar_content: CalendarContent | None = None

        self.admin_works_content: AdminWorksContent | None = None

        self.schedule_content: ScheduleContent | None = None
        
        self.admin_storage_content: AdminStorageContent | None = None
        
        self.tenants_content: TenantsContent | None = None

        self.sidebar = HoverSidebar()
    
        self.sidebar.collapse()
        
        self.__init_view()
        
    def __init_view(self):
        
        main_layout = QHBoxLayout(self)
        main_layout.addWidget(self.sidebar)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        self.content = QWidget()
        self.content.setObjectName("DashboardContainer")
        
        self.stack = QStackedLayout()
        self.content.setLayout(self.stack)
        
        main_layout.addWidget(self.content)
        self.setLayout(main_layout)

        self.sidebar.menu1.clicked.connect(lambda: self.__set_content(self.get_admin_works_content()))
        self.sidebar.menu2.clicked.connect(lambda: self.__set_content(PersonnelContent()))
        self.sidebar.menu3.clicked.connect(lambda: self.__set_content(self.get_calendar_content()))
        self.sidebar.menu4.clicked.connect(lambda: self.__set_content(self.get_schedule_content()))
        self.sidebar.menu5.clicked.connect(lambda: self.__set_content(self.get_admin_storage_content()))
        self.sidebar.menu6.clicked.connect(lambda: self.__set_content(self.get_tenants_content()))
        self.sidebar.menu7.clicked.connect(lambda: self.__set_content(RentalHistoryContent(self)))
        self.sidebar.menu8.clicked.connect(lambda: self.__set_content(LoginHistoryContent(self)))
        self.sidebar.menu9.clicked.connect(self.__open_quotation_content)
        
        self.__set_content(self.get_calendar_content())
        
    def get_tenants_content(self) -> TenantsContent:
        
        if self.tenants_content is not None:
            
            return self.tenants_content
        
        try: 
            
            self.tenants_content = TenantsContent(self)
            
            return self.tenants_content
        
        except Exception as e:
            
            self.log.exception("Failed to create TenantsContent: %s" % str(e))
           
            raise

    def get_schedule_content(self) -> ScheduleContent:

        if self.schedule_content is not None:

            return self.schedule_content

        try:

            self.schedule_content = ScheduleContent(self)
            self.schedule_content.refresh_todo.connect(self.refresh_todo.emit)

            return self.schedule_content

        except Exception as e:

            self.log.exception("Failed to create ScheduleContent: %s" % str(e))

            raise

    def get_admin_works_content(self) -> AdminWorksContent:

        if self.admin_works_content is not None:

            return self.admin_works_content

        try:

            self.admin_works_content = AdminWorksContent(self)
            self.admin_works_content.refresh_todo.connect(self.refresh_todo.emit)

            return self.admin_works_content

        except Exception as e:

            self.log.exception("Failed to create AdminWorksContent: %s" % str(e))

            raise
    
    def get_admin_storage_content(self) -> AdminStorageContent:
        
        if self.admin_storage_content is not None:
            
            return self.admin_storage_content
        
        try: 
            
            self.admin_storage_content = AdminStorageContent(self)
            
            return self.admin_storage_content
        
        except Exception as e:
            
            self.log.exception("Failed to create AdminStorageContent: %s" % str(e))
           
            raise
        
     
    def get_calendar_content(self) -> CalendarContent:
        
        if self.calendar_content is not None:
            
            return self.calendar_content
        
        try:
            
            self.calendar_content = CalendarContent(self)
            
            return self.calendar_content
        
        except Exception as e:
            
            self.log.exception("Failed to create CalendarContent: %s" % str(e))
           
            raise
    
    def get_current_content(self) -> QWidget | None:
        
        return self.stack.currentWidget()
    
    def __open_quotation_content(self):
        
        content = PriceQuotationContent(self)
        
        content.refresh_other_work_prices.connect(self.refresh_other_work_prices.emit)
        
        self.__set_content(content)
    
    def __set_content(self, new_view: QWidget):

        index = self.stack.indexOf(new_view)
        
        if index == -1:
            
            self.stack.addWidget(new_view)
            
            index = self.stack.indexOf(new_view)
        
        self.stack.setCurrentIndex(index)