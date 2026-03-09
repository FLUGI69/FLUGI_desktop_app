import asyncio
import os
from qasync import asyncSlot
from html import escape
from openai import OpenAIError
import fitz 
import mimetypes
import json
import re
import logging
import typing as t

from PyQt6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QPushButton,
    QTextEdit,
    QFileDialog
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QIcon, QTextCursor

from config import Config
from utils.logger import LoggerMixin
from .modal.work_information import WorkInformationModal
from .admin.custom.text_edit import ChatTextEdit

if t.TYPE_CHECKING:
    
    from .main_window import MainWindow

class TranslateView(QWidget, LoggerMixin):
    
    log: logging.Logger
    
    def __init__(self, 
        main_window: 'MainWindow'
        ):
        
        super().__init__()

        self.spinner = main_window.app.spinner
        
        self._lock = main_window.app.openapi_lock
        
        self._btn_lock = asyncio.Lock()
        
        self.openai = main_window.app.openai
     
        self.conversation_history = [
            {"role": "system", "content": "You are the assistant of Example Company Ltd. \
                You help with daily tasks, especially in topics related to shipping \
                and the related parts. You are familiar with refrigerants, \
                as well as their industrial applications. Your answers should be thoughtful, reliable, and \
                based on information from real sources."}
        ]

        self.__init_view()
        
    @staticmethod
    def icon(name: str) -> QIcon:
        
        return QIcon(os.path.join(Config.icon.icon_dir, name))
    
    def __init_view(self):
        
        self._search_callbacks = [
            self.send_message
        ]

        layout = QVBoxLayout(self)

        self.chat_display = QTextEdit()
        self.chat_display.setObjectName("TranslateChatDisplay")
        self.chat_display.setReadOnly(True)
        
        layout.addWidget(self.chat_display)

        input_layout = QHBoxLayout()

        self.file_button = QPushButton()
        self.file_button.setObjectName("TranslateFileButton")
        self.file_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.file_button.setIcon(self.icon("paperclip.svg")) 
        self.file_button.setFixedSize(200, 100)
        self.file_button.setIconSize(QSize(28, 28))
        self.file_button.clicked.connect(self.__on_file_button_clicked)
        
        input_layout.addWidget(self.file_button)

        self.input_field = ChatTextEdit(btn_callback = self.__btn_callback)
        self.input_field.setObjectName("TranslateInputField")
        self.input_field.setPlaceholderText("Type your message...")
        self.input_field.setMaximumHeight(100)
        self.input_field.setMaximumWidth(1500)
        
        input_layout.addWidget(self.input_field, stretch = 1)

        self.send_button = QPushButton()
        self.send_button.setObjectName("TranslateSendButton")
        self.send_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.send_button.setIcon(self.icon("anchor.svg"))  
        self.send_button.setFixedSize(200, 100)
        self.send_button.setIconSize(QSize(28, 28))
        self.send_button.clicked.connect(lambda: asyncio.ensure_future(self.__btn_callback(1)))
        
        input_layout.addWidget(self.send_button)

        layout.addLayout(input_layout)
        
    def __on_file_button_clicked(self):
    
        parent_widget = self.chat_display
    
        if parent_widget:
            
            self.spinner.show(parent_widget)
        
        file_path, _ = QFileDialog.getOpenFileName(self, "Select file")

        if file_path:
            
            self.log.debug("Selected file path: %s" % file_path)
            
            asyncio.ensure_future(self._handle_attach_file(file_path))
        
    @asyncSlot()
    async def __btn_callback(self, idx: int):
        
        if self._btn_lock.locked():
            
            self.log.warning("Button callback ignored because another operation is running")
            
            return

        async with self._btn_lock:
            
            parent_widget = self.chat_display

            if parent_widget:
                
                self.spinner.show(parent_widget)

            if idx == 1:
                
                try:
                    
                    await self.send_message()
                    
                except Exception as e:
                    
                    self.log.error("Error while running send_message: %s" % str(e))
                    
            self.spinner.hide()
            
    async def _handle_attach_file(self, file_path: str):
        
        try:
            
            text = self.__handle_file_preview(file_path)

            result_dict = await self.__handle_pdf_information(text)

            self.spinner.hide()

            dialog = WorkInformationModal(
                result_dict, 
                parent = self
            )

            dialog.finished_signal.connect(lambda: self.log.debug("Modal closed"))
            
            dialog.open()

        except Exception as e:
            
            self.log.error("Unexpected error while attaching file: %s" % str(e))
     
    async def __handle_pdf_information(self, text) -> str:
        
        try:
        
            async with self._lock:    
                
                response = await self.openai.chat.completions.create(
                    model = "gpt-5.1",  
                    messages = [
                        {"role": "system", "content": "Analyze the text, highlight the key information, \
                            and categorize the data in a well-structured tabular JSON format. Respond with only one valid \
                            JSON object, without any additional explanation or text. \
                            Translate all textual content of the JSON into Hungarian."},
                        {"role": "user", "content": text}
                    ],
                )
            
            result = response.choices[0].message.content.strip()

            self.log.debug("ChatGPT result: %s" % (str(result)))

            cleaned_result = self.__clean_json_response(result)

            result_dict = json.loads(cleaned_result)
            
            self.log.debug("JSON dict results: %s" % (str(result_dict)))
            
            return result_dict

        except OpenAIError as e: 
            
            self.log.error("OpenAI API error while handle PDF information: %s" % (str(e)))

    def __clean_json_response(self, text):

        cleaned = re.sub(r"^```json\s*", "", text)
        
        cleaned = re.sub(r"\s*```$", "", cleaned)
        
        return cleaned.strip()
                
    def __read_pdf_file(self, file_path) -> str:
        
        try:
            
            doc = fitz.open(file_path)
            
            text = ""
            
            for page in doc:
                
                text += page.get_text()
                
            return text
        
        except Exception as e:
            
            self.log.error("Failed to read PDF file: %s" % (str(e)))
            
            return f"<span style='color:red;'>❌ PDF read error: {e}</span>"
        
    def __read_text_file(self, file_path):
        
        try:
            
            with open(file_path, "r", encoding = "utf-8") as f:
                
                return f"<pre>{f.read()}</pre>"
            
        except UnicodeDecodeError:
            
            with open(file_path, "r", encoding = "latin1") as f:
                
                return f"<pre>{f.read()}</pre>"

    def __handle_file_preview(self, file_path):
        
        mime_type, _ = mimetypes.guess_type(file_path)

        if mime_type:
            
            if mime_type.startswith("text"):
                
                return self.__read_text_file(file_path)
            
            elif mime_type == "application/pdf":
                
                return self.__read_pdf_file(file_path)
            
            elif mime_type.startswith("image/"):
                
                self.log.info("Image file detected, no processing needed for preview: %s" % (os.path.basename(file_path)))                
                
                return None

            else:
                
                self.log.warning("Unsupported MIME type for preview: %s" % (str(mime_type)))
                
                return f"ℹ️ A(z) <b>{os.path.basename(file_path)}</b> file type ({mime_type}) cannot be displayed."
        
        else:
            
            self.log.error("Unknown MIME type, cannot preview file: %s" % (str(file_path)))
            
            return f"❓ Unknown file type: {os.path.basename(file_path)}"
       
    @asyncSlot()    
    async def send_message(self) -> str:
        
        message = self.input_field.toPlainText().strip()
        
        if message is not None:
            
            self.input_field.clear()
            
            try:
                
                self.conversation_history.append({"role": "user", "content": message})
                
                async with self._lock:
                        
                    response = await self.openai.chat.completions.create(
                        model = "gpt-5.1",  
                        messages = self.conversation_history,
                    )
                
                self.spinner.hide()
                
                result = response.choices[0].message.content.strip()
                
                self.conversation_history.append({"role": "assistant", "content": result})
                
                self.log.debug("ChatGPT result: %s" % (str(result)))

                converted_message = self.convert_markdown_bold(message)

                converted_result = self.convert_markdown_bold(result)
                
                formatted = f"""
                <div style="margin: 10px 0; padding: 0 10px; max-width: 70%;">
                    <div style="color:#4285f4; font-weight: bold; text-align: left; margin-bottom: 5px;">👤 You:</div>
                    <div style="text-align: left; white-space: pre-wrap;">
                        {escape(converted_message)}
                    </div>
                </div>

                <div style="margin: 10px 0; padding: 0 10px; max-width: 70%;">
                    <div style="color:#4285f4; font-weight: bold; text-align: left; margin-bottom: 5px;">🧠 Example Company GPT:</div>
                    <div style="text-align: left; white-space: pre-wrap;">
                        {converted_result}
                    </div>
                </div>
                """
                
                cursor = self.chat_display.textCursor()
                cursor.movePosition(QTextCursor.MoveOperation.End)
                
                self.chat_display.setTextCursor(cursor)
                self.chat_display.insertHtml(formatted)
                self.chat_display.insertPlainText("\n")

            except OpenAIError as e: 
                
                self.log.error("OpenAI API error while handle information: %s" % (str(e)))
                
    def convert_markdown_bold(self, text):
        
        text = re.sub(r'###### (.+)', r'<h6>\1</h6>', text)
        text = re.sub(r'##### (.+)', r'<h5>\1</h5>', text)
        text = re.sub(r'#### (.+)', r'<h4>\1</h4>', text)
        text = re.sub(r'### (.+)', r'<h3>\1</h3>', text)
        text = re.sub(r'## (.+)', r'<h2>\1</h2>', text)
        text = re.sub(r'# (.+)', r'<h1>\1</h1>', text)

        # Bold conversion
        text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)

        return text    
