from PyQt6.QtWidgets import  QFrame, QVBoxLayout, QPushButton
from PyQt6.QtCore import QPropertyAnimation, QEasingCurve, QEvent
from PyQt6.QtCore import Qt

class HoverSidebar(QFrame):
    
    def __init__(self, parent = None):
        
        super().__init__(parent)

        self.collapsed_width = 3
        self.expanded_width = 250
        
        self.setMinimumWidth(self.collapsed_width)
        self.setMaximumWidth(self.expanded_width)
        self.resize(self.collapsed_width, self.height())

        self.menu1 = QPushButton("Works")
        self.menu1.setObjectName("DashboardMenuBtn")
        self.menu1.setCursor(Qt.CursorShape.PointingHandCursor)
        
        self.menu2 = QPushButton("Employees")
        self.menu2.setObjectName("DashboardMenuBtn")
        self.menu2.setCursor(Qt.CursorShape.PointingHandCursor)
        
        self.menu3 = QPushButton("Calendar")
        self.menu3.setObjectName("DashboardMenuBtn")
        self.menu3.setCursor(Qt.CursorShape.PointingHandCursor)
        
        self.menu4 = QPushButton("Schedule")
        self.menu4.setObjectName("DashboardMenuBtn")
        self.menu4.setCursor(Qt.CursorShape.PointingHandCursor)
        
        self.menu5 = QPushButton("Manage storages")
        self.menu5.setObjectName("DashboardMenuBtn")
        self.menu5.setCursor(Qt.CursorShape.PointingHandCursor)
        
        self.menu6 = QPushButton("Tenants")
        self.menu6.setObjectName("DashboardMenuBtn")
        self.menu6.setCursor(Qt.CursorShape.PointingHandCursor)
        
        self.menu7 = QPushButton("Rental history")
        self.menu7.setObjectName("DashboardMenuBtn")
        self.menu7.setCursor(Qt.CursorShape.PointingHandCursor)
        
        self.menu8 = QPushButton("Logins")
        self.menu8.setObjectName("DashboardMenuBtn")
        self.menu8.setCursor(Qt.CursorShape.PointingHandCursor)
        
        self.menu9 = QPushButton("Quotation")
        self.menu9.setObjectName("DashboardMenuBtn")
        self.menu9.setCursor(Qt.CursorShape.PointingHandCursor)
        
        self.menu1.hide()
        self.menu2.hide()
        self.menu3.hide()
        self.menu4.hide()
        self.menu5.hide()
        self.menu6.hide()
        self.menu7.hide()
        self.menu8.hide()

        layout = QVBoxLayout()
        layout.addWidget(self.menu1)
        layout.addWidget(self.menu2)
        layout.addWidget(self.menu3)
        layout.addWidget(self.menu4)
        layout.addWidget(self.menu5)
        layout.addWidget(self.menu6)
        layout.addWidget(self.menu7)
        layout.addWidget(self.menu9)
        layout.addStretch()
        layout.addWidget(self.menu8)
        
        self.setLayout(layout)

        self.animation = QPropertyAnimation(self, b"maximumWidth")
        self.animation.setDuration(300)
        self.animation.setEasingCurve(QEasingCurve.Type.OutCubic)

        self.setMouseTracking(True)
        self.installEventFilter(self)

    def eventFilter(self, source, event):
        
        if event.type() == QEvent.Type.Enter:
            
            self.expand()
            
        elif event.type() == QEvent.Type.Leave:
            
            self.collapse()
            
        return super().eventFilter(source, event)

    def expand(self):
        
        self.animation.stop()
        self.animation.setStartValue(self.width())
        self.animation.setEndValue(self.expanded_width)
        self.animation.start()

        self.menu1.show()
        self.menu2.show()
        self.menu3.show()
        self.menu4.show()
        self.menu5.show()
        self.menu6.show()
        self.menu7.show()
        self.menu9.show()
        self.menu8.show()

    def collapse(self):
        
        self.animation.stop()
        self.animation.setStartValue(self.width())
        self.animation.setEndValue(self.collapsed_width)
        self.animation.start()

        self.menu1.hide()
        self.menu2.hide()
        self.menu3.hide()
        self.menu4.hide()
        self.menu5.hide()
        self.menu6.hide()
        self.menu7.hide()
        self.menu9.show()
        self.menu8.hide()
