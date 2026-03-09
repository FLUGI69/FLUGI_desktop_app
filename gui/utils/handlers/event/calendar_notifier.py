from PyQt6.QtCore import QObject, pyqtSignal

class CalendarNotifier(QObject):
    
    reminder_warning = pyqtSignal(object)
