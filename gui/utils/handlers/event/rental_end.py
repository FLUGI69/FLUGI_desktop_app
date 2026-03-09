from PyQt6.QtCore import QObject, pyqtSignal

class RentalEnd(QObject):
    
    rental_end_event = pyqtSignal(object)
