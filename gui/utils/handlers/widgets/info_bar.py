from PyQt6.QtWidgets import QLabel, QScrollArea, QFrame
from PyQt6.QtGui import QWheelEvent
from PyQt6.QtCore import Qt, QTimer

class InfoBar(QScrollArea):
    
    def __init__(self, *args, **kwargs):
        
        super().__init__(*args, **kwargs)
        
        self.setObjectName("InfoBarLabel")
        self.setWidgetResizable(True)
        self.setMaximumHeight(60)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setCursor(Qt.CursorShape.ArrowCursor)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        self.label = QLabel()
        self.label.setObjectName("BoatTitleLabel")
        self.label.setContentsMargins(1, 1, 1, 1)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)
        self.label.setWordWrap(True)
        self.label.setCursor(Qt.CursorShape.ArrowCursor)

        self.setWidget(self.label)

    def addText(self, text: str):
        """
        Adds new text to the existing content in the QLabel.
        If there is already text, the new text will be added on a new line.
        
        Args:
            text (str): The text to be added.
        """

        current_text = self.label.text().strip()
        
        if current_text != "":
            
            self.label.setText(current_text + "\n" + text)
            
        else:
            
            self.label.setText(text)
            
        QTimer.singleShot(0, lambda: self.verticalScrollBar().setValue(self.verticalScrollBar().maximum()))

    def clearText(self):
        """
        Clears all text currently displayed in the QLabel,
        leaving the InfoBar completely empty.
        """
        
        self.label.setText("")
        
    def wheelEvent(self, event: QWheelEvent):
        """
        Scrolls one line per wheel step.
        """
        scrollbar = self.verticalScrollBar()
        
        line_height = self.label.fontMetrics().height()
        
        steps = event.angleDelta().y() // 120

        if steps != 0:
            
            new_value = scrollbar.value() - steps * line_height
            
            scrollbar.setValue(max(0, min(scrollbar.maximum(), new_value)))
            
            event.accept()
            
        else:
            
            super().wheelEvent(event)