from PyQt6.QtWidgets import QLabel, QWidget
from PyQt6.QtGui import QMovie
from PyQt6.QtCore import Qt, QPoint, QMetaObject, pyqtSignal, Q_ARG

from pathlib import Path
import sys
from shiboken6 import isValid
import logging
import typing as t

from utils.logger import LoggerMixin

class Spinner(QWidget, LoggerMixin):
    
    log: logging.Logger
    
    show_signal = pyqtSignal(QWidget)
    
    hide_signal = pyqtSignal()
    
    def __init__(self, 
        gif_path: str,
        ):
        
        super().__init__()
                
        self._parent_widget: t.Optional[QWidget] = None
        
        self._is_visible: bool = False
        
        self.show_signal.connect(self._show_impl)
        
        self.hide_signal.connect(self._hide_impl)

        if getattr(sys, "frozen", False):
            
            self.path = Path(sys.executable).parent / "_internal" / gif_path
            
        else:
            
            self.path = Path(gif_path)
            
        self.__init_view()

    def __init_view(self):

        if not self.path.exists():
            
            self.log.error("Spinner GIF not found at: %s" % str(self.path))
            
            return

        self._label = QLabel()
        self._label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self._label.setStyleSheet("background-color: transparent;")
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._label.setScaledContents(False)

        self._movie = QMovie(str(self.path))
        
        if not self._movie.isValid():
            
            self.log.error("Invalid QMovie: %s" % str(self.path))
            
            return

        self._label.setMovie(self._movie)
    
    def show(self, parent_widget: QWidget):

        self.show_signal.emit(parent_widget)

    def hide(self):
        
        self.hide_signal.emit()
        
    def _show_impl(self, parent_widget: QWidget):
    
        if not isValid(parent_widget):
            
            self.log.warning("Spinner.show() skipped: parent_widget is invalid or deleted")
            
            return

        if not isValid(self._label):
            
            self.log.warning("Spinner.show() skipped: _label is invalid or deleted")
        
        if self._parent_widget != parent_widget:
            
            self.log.info("New parent widget detected: %s" % type(parent_widget).__name__)
            
            self._parent_widget = parent_widget
            
            self._label.setParent(parent_widget)

        if self._movie.state() == QMovie.MovieState.Running:
            
            self.log.info("Spinner movie is currently running, stopping it before restart")
            
            self._movie.stop()
        
        self.log.info("Spinner movie -> START")
        
        self._movie.start()
        
        gif_size = self._movie.currentImage().size()
        
        self._label.resize(gif_size)

        parent_size = parent_widget.size()
        
        self.log.debug("Parent widget size: width: %d, height: %d" % (parent_size.width(), parent_size.height()))
        
        center_point = QPoint(
            (parent_size.width() - self._label.width()) // 2,
            (parent_size.height() - self._label.height()) // 2
        )
        
        self.log.debug("Calculated center point for spinner: x = %d, y = %d" % (
            center_point.x(), 
            center_point.y()
            )
        )
        
        self._label.move(center_point)

        self._label.raise_()
        self._label.setVisible(True)
        self._label.update()
        
        self._is_visible = True
        
        self.log.debug("Spinner state after show(): _is_visible -> %s, _parent_widget: %s, _movie_running: %s" % (
            self._is_visible,
            str(self._parent_widget),
            self._movie.state() == QMovie.MovieState.Running
            )
        )

    def _hide_impl(self):
        
        if self._is_visible is False:
            
            return

        try:
            
            if self._label is not None:
                
                if self._movie.state() == QMovie.MovieState.Running:
                    
                    self.log.info("Spinner movie -> STOP")
                    
                    self._movie.stop()

                self._label.hide()
                
                self._is_visible = False
                
                self.log.debug("Spinner state after hide(): _is_visible -> %s, _parent_widget: %s, _movie_running: %s" % (
                    self._is_visible,
                    str(self._parent_widget),
                    self._movie.state() == QMovie.MovieState.Running
                    )
                )
                
        except RuntimeError as e:
            
            self.log.exception("Tried to hide deleted QLabel: %s" % str(e))
