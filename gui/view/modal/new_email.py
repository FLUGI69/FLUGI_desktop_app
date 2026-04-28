import logging
import asyncio
from qasync import asyncSlot
import os
import re
import typing as t

from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout, 
    QLineEdit, 
    QTextEdit, 
    QPushButton, 
    QLabel, 
    QComboBox,
    QHBoxLayout,
    QFileDialog,
    QDialogButtonBox,
    QWidget
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QIcon, QCursor

from utils.handlers.email_content.translate import OpenapiTranslate
from utils.dc.google.new_email_data import NewEmailData
from config import Config
from utils.logger import LoggerMixin

if t.TYPE_CHECKING:
    
    from ..main_window import MainWindow

class NewEmailModal(QDialog, LoggerMixin):
    
    log: logging.Logger
    
    def __init__(self, 
        main_window: 'MainWindow',
        parent = None
        ):
    
        super().__init__(parent)
        
        self.openai_helper = OpenapiTranslate(main_window)
        
        self._future = None
    
        self.attachment_path = None
        
        self.file_path = None
        
        self.files_list = []
        
        self.__init_modal()
        
    @staticmethod
    def icon(name: str) -> QIcon:
        
        return QIcon(os.path.join(Config.icon.icon_dir, name))
    
    def __init_modal(self):
        
        self.setWindowTitle("Új levél küldése")
        
        self.resize(600, 500)

        main_layout = QVBoxLayout(self)

        header_layout = QHBoxLayout()
        
        self.translation_label = QLabel("Fordítás:")
        self.language_dropdown = QComboBox()
        self.language_dropdown.addItem("")
        self.language_dropdown.addItems([
            "Angol", 
            "Német", 
            "Román", 
            "Szerb", 
            "Francia", 
            "Spanyol", 
            "Olasz", 
            "Lengyel", 
            "Szlovák", 
            "Magyar"
        ])
        self.language_dropdown.currentIndexChanged.connect(self.on_language_selected)

        self.attach_button = QPushButton()
        self.attach_button.setObjectName("attach_file")
        self.attach_button.setIcon(NewEmailModal.icon("attach_email.svg"))
        self.attach_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.attach_button.setIconSize(QSize(25, 25))
        self.attach_button.setToolTip("File csatolás")
        self.attach_button.clicked.connect(self.__on_file_button_clicked)

        header_layout.addStretch()
        header_layout.addWidget(self.translation_label)
        header_layout.addWidget(self.language_dropdown)
        header_layout.addWidget(self.attach_button)

        main_layout.addLayout(header_layout)

        self.label_to_input = QLabel("Címzett:")
        self.to_input = QLineEdit()
        self.to_input.setObjectName("input_unit")
        self.to_input.setPlaceholderText("example@email.com")
        self.to_input.setFixedHeight(35)

        self.label_subject_input = QLabel("Tárgy:")
        self.subject_input = QLineEdit()
        self.subject_input.setObjectName("input_unit")
        self.subject_input.setFixedHeight(35)

        self.label_body_input = QLabel("Üzenet:")
        self.body_input = QTextEdit()
        self.body_input.setAcceptRichText(False)
        self.body_input.setObjectName("TranslateInputField")
        self.body_input.setMinimumHeight(70)

        self.to_error_label = QLabel()
        self.to_error_label.setObjectName("error")
        self.to_error_label.setVisible(False)

        self.subject_error_label = QLabel()
        self.subject_error_label.setObjectName("error")
        self.subject_error_label.setVisible(False)

        self.body_error_label = QLabel()
        self.body_error_label.setObjectName("error")
        self.body_error_label.setVisible(False)
        
        self.button_container = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.button_container.setObjectName("ConfirmModalButtonBox")
        self.button_container.setFixedHeight(60)

        for button in self.button_container.buttons():
            
            role = self.button_container.buttonRole(button)
            
            button.setFixedHeight(35)
            button.setFixedWidth(90)
            button.setObjectName("ConfirmModalButton")
            button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

            if role == QDialogButtonBox.ButtonRole.AcceptRole:
                
                button.setText("Küldés")
                
            elif role == QDialogButtonBox.ButtonRole.RejectRole:
                
                button.setText("Törlés")

        self.button_container.accepted.connect(self.on_send_clicked)
        self.button_container.rejected.connect(self.reject)

        main_layout.addWidget(self.label_to_input)
        main_layout.addWidget(self.to_error_label)
        main_layout.addWidget(self.to_input)
        main_layout.addWidget(self.label_subject_input)
        main_layout.addWidget(self.subject_error_label)
        main_layout.addWidget(self.subject_input)
        main_layout.addWidget(self.label_body_input)
        main_layout.addWidget(self.body_error_label)
        main_layout.addWidget(self.body_input)

        
        button_widget = QWidget()
        button_layout = QHBoxLayout(button_widget)
        button_layout.addStretch()
        button_layout.addWidget(self.button_container)
        button_layout.addStretch()
        button_layout.setContentsMargins(0, 0, 0, 0)
        button_layout.setSpacing(10)
        
        main_layout.addWidget(button_widget)

    @staticmethod
    def is_valid_email(email: str) -> bool:
        
        if email is not None:

            pattern = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
            
            return re.match(pattern, email) is not None
        
        return False
    
    @asyncSlot(int)
    async def on_language_selected(self, index: int):
        
        selected_language = self.language_dropdown.itemText(index)
        
        if selected_language.strip() != "" and self.body_input.toPlainText().strip() != "":
            
            self.log.info("Language selected: %s" % selected_language)
            
            text_results = await self.openai_helper.translate_language(
                text = self.body_input.toPlainText().strip(),
                language = selected_language.strip()
            )

            if text_results is not None:
                
                self.body_input.setPlainText(text_results)
        
    def __on_file_button_clicked(self):
    
        file_path, _ = QFileDialog.getOpenFileName(self, "Fájl kiválasztása")

        if file_path:
            
            self.file_path = file_path
            
            self.log.debug("Selected file path: %s" % file_path)
            
            self.files_list.append(self.file_path)
            # asyncio.ensure_future(self._handle_attach_file(file_path))
            
    def on_send_clicked(self):
        
        self.to_error_label.setVisible(False)
        self.subject_error_label.setVisible(False)
        self.body_error_label.setVisible(False)
        
        to_email = self.to_input.text().strip() if self.to_input.text().strip() != "" else None
        subject = self.subject_input.text().strip() if self.subject_input.text().strip() != "" else None
        body = self.body_input.toPlainText().strip() if self.body_input.toPlainText().strip() != "" else None

        has_error = False
        
        if to_email is None:
            
            self.to_error_label.setText("E-mail cím megadása kötelező")
            self.to_error_label.setVisible(True)
            
            self.log.warning("Email address is required")
            
            has_error = True
            
        elif self.is_valid_email(to_email) == False:
            
            self.to_error_label.setText("Érvénytelen e-mail cím formátum")
            self.to_error_label.setVisible(True)
            
            self.log.warning("Invalid email address format")
            
            has_error = True

        if subject is None:
            
            self.subject_error_label.setText("Tárgy megadása kötelező")
            self.subject_error_label.setVisible(True)
            
            self.log.warning("Subject is required")
            
            has_error = True

        if body is None:
            
            self.body_error_label.setText("Üzenet megadása kötelező")
            self.body_error_label.setVisible(True)
            
            self.log.warning("Body is required")
            
            has_error = True

        if has_error == False:
            
            self.accept()

    def get_form_data(self) -> NewEmailData:
        
        data = NewEmailData(
            to = self.to_input.text().strip() if self.to_input.text().strip() != "" else None,
            subject = self.subject_input.text().strip() if self.subject_input.text().strip() != "" else None,
            body = self.body_input.toPlainText().strip() if self.body_input.toPlainText().strip() != "" else None,
            attachments = self.files_list if len(self.files_list) > 0 else None
        )
                
        self.log.debug("Form data: %s" % data)
        
        return data
        
    def exec_async(self) -> asyncio.Future:
        
        self._future = asyncio.get_event_loop().create_future()
        
        self.language_dropdown.setCurrentIndex(0)
        self.to_input.clear()
        self.subject_input.clear()
        self.body_input.clear()
        
        self.to_error_label.setVisible(False)
        self.subject_error_label.setVisible(False)
        self.body_error_label.setVisible(False)
        
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
