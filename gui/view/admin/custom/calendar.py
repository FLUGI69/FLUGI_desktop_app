import logging
import typing as t

from PyQt6.QtWidgets import (
    QWidget, 
    QCalendarWidget
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPainter, QPalette, QPen, QColor
from PyQt6.QtCore import QDate, QPoint

from utils.logger import LoggerMixin
from utils.dc.admin.reminder import CalendarData, CalendarCacheData
from utils.dc.admin.tenant_items import AdminTenantsCacheData
from utils.dc.tenant_data import TenantData

class CustomCalendar(QCalendarWidget, LoggerMixin):
    
    log: logging.Logger
    
    def __init__(self, 
        marked_date: CalendarData = None, 
        *args, **kwargs
        ):
        
        super().__init__(*args, **kwargs)
        
        self.marked_date = marked_date
        
        self.marked_dates = set()
        
        self.selected_date = None 
        
        self.setMouseTracking(True)
        
        self.setHorizontalHeaderFormat(QCalendarWidget.HorizontalHeaderFormat.LongDayNames)
        
        calendar_view = self.findChild(QWidget, "qt_calendar_calendarview")
        
        if calendar_view:
            
            calendar_view.setMouseTracking(True)
            
    def set_marked_dates(self, cache_data: t.Union[CalendarCacheData, AdminTenantsCacheData]): 

        self.marked_dates.clear()

        if (isinstance(cache_data, CalendarCacheData) and cache_data.items 
            and all(isinstance(item, CalendarData) for item in cache_data.items)
            ):
            
            dates_str = ", ".join(item.date.strftime("%Y-%m-%d") for item in cache_data.items)
            
            self.log.debug("Marked dates: %s" % dates_str)

            for item in cache_data.items:
                
                date = QDate(item.date.year, item.date.month, item.date.day)
                
                self.marked_dates.add(date)

        if (isinstance(cache_data, AdminTenantsCacheData) and cache_data.items 
            and all(isinstance(item, TenantData) for item in cache_data.items)
            ):

            for item in cache_data.items:
                
                if item.rental_end is not None:
                    
                    dates_str = ", ".join(item.rental_end.strftime("%Y-%m-%d"))
            
                    date = QDate(item.rental_end.year, item.rental_end.month, item.rental_end.day)
                
                    self.marked_dates.add(date)
                    
            self.log.debug("Marked dates: %s" % dates_str)

        self.updateCells()

    def paintCell(self, painter: QPainter, rect, date: QDate):

        if date.month() == self.monthShown():
            
            super().paintCell(painter, rect, date)
            
        else:
            
            painter.save()
            
            bg_color = self.palette().color(QPalette.ColorRole.Base).lighter(130)
            
            painter.fillRect(rect, bg_color)
            
            text_color = self.palette().color(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text)
           
            painter.setPen(QPen(text_color))
            painter.drawText(rect, int(Qt.AlignmentFlag.AlignCenter), str(date.day()))
            painter.restore()

        if hasattr(self, 'marked_dates') and date in self.marked_dates:
            
            painter.save()
            
            pen = QPen(QColor("#4285f4"), 2)
            
            painter.setPen(pen)
            
            diameter = min(rect.width(), rect.height()) - 50
            
            center = rect.center()
            
            painter.drawEllipse(center, diameter // 2, diameter // 2)
            painter.restore()
    
    def mouseMoveEvent(self, event):
        
        super().mouseMoveEvent(event)
        
        pos = event.position().toPoint()
        
        date = self.hitTest(pos)
        
        if date and date.isValid():
            
            self.setCursor(Qt.CursorShape.PointingHandCursor)
            
        else:
            
            self.setCursor(Qt.CursorShape.ArrowCursor)

    def hitTest(self, pos: QPoint):

        cell_width = self.geometry().width() / 7
        cell_height = (self.geometry().height() - self.navigationBarHeight()) / 6

        y = pos.y() - self.navigationBarHeight()
        
        if y < 0:
            
            return None

        col = int(pos.x() // cell_width)
        row = int(y // cell_height)

        first_day_of_month = QDate(self.yearShown(), self.monthShown(), 1)
        first_day_weekday = first_day_of_month.dayOfWeek()

        index = row * 7 + col
        offset = first_day_weekday - 1 

        day_number = index - offset + 1

        if day_number < 1 or day_number > first_day_of_month.daysInMonth():
            
            return None

        return QDate(self.yearShown(), self.monthShown(), day_number)

    def navigationBarHeight(self):
        
        nav_bar = self.findChild(QWidget, "qt_calendar_navigationbar")
        
        if nav_bar:
            
            return nav_bar.height()
        
        return 0