from PyQt6.QtWidgets import (
    QWidget
)
from PyQt6.QtCore import Qt, QPointF
from PyQt6.QtGui import QColor, QPainter, QBrush, QRadialGradient

from utils.dc.admin.reminder import CalendarData

class ReminderDay(QWidget):
    
    def __init__(self, 
        parent = None
        ):
        
        super().__init__(parent)
        
        self.reminders: list[CalendarData] = []
        
        self.setMinimumWidth(300)
        
        self.setMinimumHeight(600)

    def update_reminders(self, reminders: list[CalendarData]):
        
        self.reminders = reminders

        self.update()

    def paintEvent(self, event):
        
        # print(f"Painting {len(self.reminders)} reminders")
        
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        center_point = QPointF(self.rect().center())
        
        gradient = QRadialGradient(center_point, self.width() / 2)
        gradient.setColorAt(0, QColor("#6e6e6e"))
        gradient.setColorAt(1, QColor("#3e3e3e"))
        
        painter.setBrush(QBrush(gradient))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(self.rect(), 10, 10)

        total_height = self.height()
        
        hour_height = total_height / 24.0

        label_width = 50
        
        content_margin = 5

        painter.setPen(QColor("#000000"))
        
        font_metrics = painter.fontMetrics()
        
        for hour in range(24):
            
            y = int(hour * hour_height)
            
            time_label = f"{hour:02d}:00"
            
            painter.drawText(5, y + font_metrics.ascent() + 2, time_label)
            painter.drawLine(label_width, y, self.width(), y)

        for reminder in self.reminders:
            
            dt = reminder.date
            
            hour_fraction = dt.hour + dt.minute / 60
            
            y = int(hour_fraction * hour_height)
            
            block_height = int(hour_height * 0.8)

            painter.setBrush(QBrush(QColor("#5AA9E6")))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRect(label_width + content_margin, y + 1, self.width() - label_width - 2 * content_margin, block_height)

            text = f"{dt.strftime('%H:%M')} - {reminder.note[:30]}"
            
            painter.setPen(Qt.GlobalColor.black)
            painter.drawText(label_width + content_margin + 5, y + 15, text)