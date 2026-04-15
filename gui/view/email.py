import asyncio
from pathlib import Path
import os, sys
from qasync import asyncSlot
import logging
from functools import partial
import typing as t 

from PyQt6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QListWidget,
    QPushButton,
    QToolButton,
    QLineEdit,
    QSizePolicy,
    QFrame,
    QLabel,
    QListWidgetItem,
    QCheckBox,
    QMessageBox
)
from PyQt6.QtCore import Qt, QSize, QTimer
from PyQt6.QtGui import QIcon, QFont, QMovie

from config import Config
from db import queries
from utils.logger import LoggerMixin
from utils.dc.gmail_response_data import EmailHeaders, Message
from view.modal.email_modal import EmailModal
from view.modal.new_email import NewEmailModal
from utils.handlers.email_content import EmailContentHandler
from utils.enums.email_status_enum import StatusTypeEnum
from .elements.email import HoverSidebar
from routes.api.google import EmailMessagesView
from routes.api.google import EmailHeadersView
from routes.api.google import EmailMessageView
from routes.api.google import UserProfileView

if t.TYPE_CHECKING:
    
    from .main_window import MainWindow

class EmailView(QWidget, LoggerMixin):
    
    log: logging.Logger
    
    def __init__(self, main_window: 'MainWindow'):
        
        super().__init__()
        
        self.main_window = main_window
        
        self.spinner = main_window.app.spinner

        self.page_size = Config.google.page_size
        
        self.email_modal = EmailModal()
        
        self.new_email_modal = NewEmailModal(
            main_window = main_window, 
            parent = self
        )
        
        self.email_content_handler = EmailContentHandler()
        
        self.sidebar = HoverSidebar()
        
        self.sidebar.collapse()
        
        self.user_client = main_window.user_client
        
        self.gmail_login_window = main_window.gmail_login_window
        
        self.email_messages = EmailMessagesView(
            user_id = self.user_client.user_id,
            creds = self.user_client.creds 
        )
        
        self.email_headers = EmailHeadersView(
            user_id = self.user_client.user_id,
            creds = self.user_client.creds 
        )
        
        self.email_message = EmailMessageView(
            user_id = self.user_client.user_id,
            creds = self.user_client.creds 
        )
        
        self.user = UserProfileView(
            user_id = self.user_client.user_id,
            creds = self.user_client.creds 
        ) 
        
        self.user_profile_data = None
        
        self._next_page_token: str | None = None
        
        self._prev_tokens: list[str] = []
        
        self._current_page_token: str | None = None
        
        self._search_query: str | None = None
        
        self._label_filter: list[str] | None = None

        self.__init_view()
        
        asyncio.create_task(self._load_page(None))

    @staticmethod
    def icon(name: str) -> QIcon:
  
        return QIcon(os.path.join(Config.icon.icon_dir, name))

    def __init_view(self):
        
        topbar = self.set_topbar()
        
        self.message_list = self.set_message_list()
        self.message_list.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.message_list.setCursor(Qt.CursorShape.PointingHandCursor)
        
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 9, 9, 9)
      
        self.sidebar.menu1.clicked.connect(lambda: asyncio.create_task(self.load_inbox()))
        self.sidebar.menu2.clicked.connect(lambda: asyncio.create_task(self.load_starred()))
        self.sidebar.menu3.clicked.connect(lambda: asyncio.create_task(self.load_draft()))
        self.sidebar.menu4.clicked.connect(lambda: asyncio.create_task(self.load_sent()))
        self.sidebar.menu5.clicked.connect(lambda: asyncio.create_task(self.load_important()))
        self.sidebar.menu6.clicked.connect(lambda: asyncio.create_task(self.load_spam()))
        self.sidebar.menu7.clicked.connect(lambda: asyncio.create_task(self.load_trash()))
        self.sidebar.menu8.clicked.connect(lambda: asyncio.create_task(self.logout()))
        
        # Email content layout
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        content_layout.addWidget(topbar)
        content_layout.addWidget(self.message_list)

        main_layout.addWidget(self.sidebar)
        main_layout.addLayout(content_layout)

    def set_topbar(self) -> QWidget:
        
        topbar = QWidget()
        topbar.setObjectName("Topbar")
        
        self._select_all_checkbox = QCheckBox()
        self._select_all_checkbox.setCursor(Qt.CursorShape.PointingHandCursor)

        self.prev_btn = QToolButton()
        self.prev_btn.setArrowType(Qt.ArrowType.LeftArrow)
        self.prev_btn.setAutoRaise(True)
        self.prev_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.prev_btn.setFixedSize(25, 25)

        self.next_btn = QToolButton()
        self.next_btn.setArrowType(Qt.ArrowType.RightArrow)
        self.next_btn.setAutoRaise(True)
        self.next_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.next_btn.setFixedSize(25, 25)

        self.refresh_btn = QToolButton()
        self.refresh_btn.setObjectName("refresh")
        self.refresh_btn.setIcon(EmailView.icon("refresh.svg"))
        self.refresh_btn.setToolTip("Frissítés")
        self.refresh_btn.setAutoRaise(True)
        self.refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.refresh_btn.setIconSize(QSize(25, 25))

        self.search_box = QLineEdit()
        self.search_box.setObjectName("SearchBox")
        self.search_box.setPlaceholderText("Search mail…")
        self.search_box.setFixedHeight(35)
        self.search_box.setMaximumWidth(380)
        self.search_box.setClearButtonEnabled(True)
        self.search_box.returnPressed.connect(self.search_emails)
        self.search_box.textChanged.connect(self.on_search_text_changed)
        
        self._select_all_checkbox.stateChanged.connect(self._toggle_select_all)
        
        self.prev_btn.clicked.connect(self._prev_page)
        self.next_btn.clicked.connect(self._next_page)
        
        self.refresh_btn.clicked.connect(lambda: asyncio.create_task(self._load_page(self._current_page_token)))

        self.compose_btn = QPushButton()
        self.compose_btn.setObjectName("TrashButton")
        self.compose_btn.setIcon(EmailView.icon("add.svg"))
        self.compose_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.compose_btn.setIconSize(QSize(25, 25))
        self.compose_btn.setToolTip("Levél írás")
        self.compose_btn.clicked.connect(self.open_compose_modal)

        self.delete_selected_btn = QPushButton()
        self.delete_selected_btn.setObjectName("TrashButton")
        self.delete_selected_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.delete_selected_btn.setIcon(EmailView.icon("trash.svg"))
        self.delete_selected_btn.setIconSize(QSize(20, 20))
        self.delete_selected_btn.setToolTip("Kiválasztottak törlése")
        self.delete_selected_btn.clicked.connect(lambda: asyncio.create_task(self.delete_selected()))

        self.email_label = QLabel()
        self.email_label.setObjectName("EmailLabel")
        
        self.message_count_label = QLabel()
        self.message_count_label.setObjectName("MessageCountLabel")
        
        count_email_box = QWidget()
        count_email_layout = QHBoxLayout(count_email_box)
        count_email_layout.setContentsMargins(0, 0, 0, 0)
        count_email_layout.setSpacing(8)
        count_email_layout.addWidget(self.email_label)
        count_email_layout.addWidget(self.message_count_label)
        
        layout = QHBoxLayout(topbar)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)
        layout.addWidget(self._select_all_checkbox)
        layout.addWidget(self.prev_btn)
        layout.addWidget(self.next_btn)
        layout.addWidget(self.refresh_btn)
        layout.addSpacing(8)
        layout.addWidget(self.search_box)
        layout.addSpacing(10)
        layout.addWidget(count_email_box)
        layout.addStretch()
        layout.addWidget(self.compose_btn)
        layout.addWidget(self.delete_selected_btn)

        return topbar

    def start_message_count_animation(self, target_count: int):
        
        self.current_count = 0
        self.target_count = target_count
        self._count_step = max(1, target_count // 312)
        self._animation_pending = True

        if self.isVisible():
            self._begin_count_animation()

    def _begin_count_animation(self):
        
        if hasattr(self, 'timer') and self.timer.isActive():
            self.timer.stop()
            
        self.current_count = 0
        self.timer = QTimer()
        self.timer.setInterval(16)  # ~60fps
        self.timer.timeout.connect(self.update_message_count)
        self.timer.start()
        self._animation_pending = False

    def showEvent(self, event):
        
        super().showEvent(event)
        
        if getattr(self, '_animation_pending', False) and self.target_count > 0:
            self._begin_count_animation()

    def update_message_count(self):
        
        if self.current_count < self.target_count:
            
            self.current_count = min(self.current_count + self._count_step, self.target_count)
            
            self.message_count_label.setText(f"Összes üzenet: {self.current_count}")
            
        else:
            
            self.timer.stop()
    
    def set_message_list(self) -> QListWidget:
        
        message_list = QListWidget()
        message_list.setObjectName("MessageList")
        message_list.setFrameShape(QFrame.Shape.NoFrame)
        message_list.setMouseTracking(True)
        message_list.itemClicked.connect(self.on_message_item_clicked)
        
        return message_list
        
    async def _load_page(self, page_token: str | None) -> None:
        
        self.user_profile_data = await self.user.get_user_profile_data()
        
        if self.user_profile_data is not None:
            
            self.start_message_count_animation(self.user_profile_data.messagesTotal)
            
            self.email_label.setText(self.user_profile_data.emailAddress)
        
        self.message_list.clear()
        
        self.spinner.show(parent_widget = self)
        
        self.prev_btn.setEnabled(False)
        self.next_btn.setEnabled(False)
        
        self._select_all_checkbox.setChecked(False)
        
        try:
            
            response = await self.email_messages.list_user_messages(
                q = self._search_query,
                labelIds = self._label_filter,
                pageToken = page_token,
                maxResults = self.page_size,
            )
     
            if response is not None:
                
                headers = await self.email_headers.list_email_headers_batch(response.messages)
                
                if headers is not None:
                    
                    self.populate_message_list(headers)
                    
                    self._current_page_token = page_token
                    
                    self._next_page_token = response.nextPageToken
                    
                    self.next_btn.setEnabled(self._next_page_token is not None)
                    
                    self.prev_btn.setEnabled(self._current_page_token is not None)
            
            if hasattr(self, "overlay_label") and self.overlay_label is not None:
                
                self.overlay_label.deleteLater()
                
                self.overlay_label = None

            if self.message_list.count() == 0:
                
                self.log.info("Mailbox is empty")

                if getattr(sys, "frozen", False):
                    
                    path = Path(sys.executable).parent / "_internal" / Config.gif.empty_mailbox
                    
                else:
                    
                    path = Path(Config.gif.empty_mailbox)

                self.overlay_label = QLabel(self)
                self.overlay_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                self.overlay_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

                self.movie = QMovie(str(path))
                
                self.overlay_label.setMovie(self.movie)
                
                self.movie.start()

                await asyncio.sleep(0.05) 

                gif_size = self.movie.currentPixmap().size()
                gif_width = gif_size.width()
                gif_height = gif_size.height()

                self.overlay_label.resize(gif_width, gif_height)

                center = self.rect().center()
                
                self.overlay_label.move(
                    center.x() - gif_width // 2,
                    center.y() - gif_height // 2
                )

                self.overlay_label.show()
            
        except Exception as e:
            
            self.log.exception("Error loading page: %s" % str(e))
            
        finally:
            
            self.spinner.hide()
                
    @asyncSlot()
    async def _toggle_important_btn(self, header: EmailHeaders, btn: QPushButton):
        
        if header is not None:
            
            try:
                
                if header.is_important == True:
                    
                    await self.email_headers.modify_important_label(
                        Message(id = header.id),
                        body = {"removeLabelIds": [StatusTypeEnum.IMPORTANT.value]}
                    )
                    
                    header.is_important = False
                    
                    btn.setIcon(EmailView.icon("important_unchecked.svg"))

                elif header.is_important == False:
                    
                    await self.email_headers.modify_important_label(
                        Message(id = header.id),
                        body = {"addLabelIds": [StatusTypeEnum.IMPORTANT.value]}
                    )
                    
                    header.is_important = True
                    
                    btn.setIcon(EmailView.icon("important_checked.svg"))

                else:
                    
                    self.log.error("Unexpected is_important value: %s" % (str(header.is_important)))

            except Exception as e:
                
                self.log.error("Failed to toggle important: %s" % str(e))

    def populate_message_list(self, headers: EmailHeaders) -> None:
        
        if headers is not None:
            
            self.message_list.setUpdatesEnabled(False)
            self.message_list.clear()
            self.message_list.setUniformItemSizes(True)
            
            font = QFont()
            font.setPointSize(10)
            
            for header in headers:
                
                list_item = QListWidgetItem()
                
                container = QWidget()

                sender_label = QLabel(header.sender)
                sender_label.setFont(font)

                subject_label = QLabel(header.subject)
                subject_label.setFont(font)

                snippet_label = QLabel(header.snippet if hasattr(header, "snippet") else "")
                snippet_label.setFont(font)
                
                date_str = header.date.strftime(Config.time.timeformat)
                
                date_label = QLabel(date_str)
                date_label.setFont(font)
                date_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

                # Example read/unread: bold if unread
                label_style = "read" if getattr(header, "is_read", False) else "unread"
                
                sender_label.setObjectName(label_style)
                
                subject_label.setObjectName(label_style)
                
                date_label.setObjectName(label_style)
                    
                important_btn = QPushButton()
                important_btn.setObjectName("ImportantButton")
                important_btn.setCursor(Qt.CursorShape.PointingHandCursor)
                
                is_important = getattr(header, "is_important", False)
                
                important_icon = EmailView.icon("important_checked.svg" if is_important == True else "important_unchecked.svg" if is_important == False else "")
                important_btn.setIcon(important_icon)
                important_btn.setToolTip("Fontos")
                important_btn.setIconSize(QSize(20, 20))
                
                important_btn.clicked.connect(partial(self._toggle_important_btn, header, important_btn))

                trash_btn = QPushButton()
                trash_btn.setObjectName("TrashButton")
                trash_btn.setCursor(Qt.CursorShape.PointingHandCursor)
                trash_btn.setIcon(EmailView.icon("trash.svg"))
                trash_btn.setIconSize(QSize(20, 20))
                trash_btn.setToolTip("Törlés")
                
                trash_btn.clicked.connect(lambda checked, item = list_item: self.on_delete_clicked(item))
                
                select_cb = QCheckBox()
                select_cb.setCursor(Qt.CursorShape.PointingHandCursor)
                
                list_item.setData(Qt.ItemDataRole.UserRole + 1, select_cb)

                h_layout = QHBoxLayout(container)
                h_layout.addWidget(select_cb)
                h_layout.addWidget(important_btn)
                h_layout.addWidget(sender_label, 1)
                h_layout.addWidget(subject_label, 2)
                h_layout.addWidget(snippet_label, 3)
                h_layout.addWidget(date_label)
                h_layout.addWidget(trash_btn)
                
                container.setLayout(h_layout)

                list_item.setSizeHint(container.sizeHint())
                
                self.message_list.addItem(list_item)
                self.message_list.setItemWidget(list_item, container)
                self.message_list.setSpacing(0)
                
                list_item.setData(Qt.ItemDataRole.UserRole, header)

            self.message_list.setUpdatesEnabled(True)

    def _toggle_select_all(self, state):
        
        checked = state == Qt.CheckState.Checked.value
        
        for i in range(self.message_list.count()):
            
            item = self.message_list.item(i)
            
            cb = item.data(Qt.ItemDataRole.UserRole + 1)
            
            if cb:
                
                cb.setChecked(checked)
                
    # move to bin first
    async def delete_selected(self):

        items_to_delete = []
        
        for i in range(self.message_list.count()):
            
            item = self.message_list.item(i)
            
            cb = item.data(Qt.ItemDataRole.UserRole + 1)
            
            if cb and cb.isChecked():
                
                items_to_delete.append(item)

        if not items_to_delete:
            
            QMessageBox.information(self, "No Selection", "Please select at least one email to delete.")
        
            return
        
        for item in items_to_delete:
            
            await self.on_delete_clicked(item)

    @asyncSlot()
    async def search_emails(self) -> None:
        
        query = self.search_box.text().strip()
        
        self._search_query = query if query != "" else None
        
        self._prev_tokens.clear()
        
        self._current_page_token = None
        
        await self._load_page(None)

    def on_search_text_changed(self, text: str):
        
        if text == "":
            
            asyncio.create_task(self.clear_search())

    async def clear_search(self):
        
        self._search_query = None
        
        self.search_box.clear()
        
        self._prev_tokens.clear()
        
        self._current_page_token = None
        
        await self._load_page(None)
        
    @asyncSlot()
    async def open_compose_modal(self):
        
        if self.new_email_modal is not None:

            accepted = await self.new_email_modal.exec_async()

            if accepted:
                            
                data = self.new_email_modal.get_form_data()
                print(data)

    # async def _send_email(self, to_email, subject, body, is_html):
        
    #     try:
            
    #         await self.user.send_message(
    #             from_email = ,
    #             to_email = to_email, 
    #             subject = subject, 
    #             body_text = body, is_html)
            
       
            
    #     except Exception as e:
    #         print(e)
     

    @asyncSlot(QListWidgetItem)
    async def on_message_item_clicked(self, item: QListWidgetItem):
        
        header: EmailHeaders = item.data(Qt.ItemDataRole.UserRole)
    
        if header is not None:
            
            self.log.info("Clicked header with subject: (%s)" % header.subject)
            
            try:
                
                message: Message = await self.email_message.get_message_by_id(header.id)
                
                if message is not None:
                 
                    await self.email_message.modify_as_read(header)
                    
                    header.is_read = True
                    
                    to_show = self.email_content_handler.get_body_to_show(message.payload)
                    
                    self.email_modal.load_html(to_show)

                    await self.email_modal.exec_async()

            except Exception as e:
                
                self.log.exception("Error opening email: %s" % str(e))

    @asyncSlot(QListWidgetItem)
    async def on_delete_clicked(self, list_item: QListWidgetItem):
        
        header: EmailHeaders = list_item.data(Qt.ItemDataRole.UserRole)
        
        if not header:
            
            return
        
        try:
            
            await self.email_message.move_to_bin(header)
            
            row = self.message_list.row(list_item)
            
            self.message_list.takeItem(row)
            
        except Exception as e:
            
            self.log.error("Failed to delete email: %s" % str(e))

    @asyncSlot()
    async def _next_page(self) -> None:
        
        if self._next_page_token:
            
            self._prev_tokens.append(self._current_page_token)
            
            await self._load_page(self._next_page_token)

    @asyncSlot()
    async def _prev_page(self) -> None:
        
        if self._prev_tokens:
            
            token = self._prev_tokens.pop()
            
            await self._load_page(token)
            
    async def load_inbox(self):
        
        self._label_filter = None
        
        await self._load_page(None)

    async def load_important(self):
        
        self._label_filter = [StatusTypeEnum.IMPORTANT.value]
        
        await self._load_page(None)
        
    async def load_starred(self):
        
        self._label_filter = [StatusTypeEnum.STARRED.value]
        
        await self._load_page(None)

    async def load_draft(self):
        
        self._label_filter = [StatusTypeEnum.DRAFT.value]
        
        await self._load_page(None)
        
    async def load_sent(self):
        
        self._label_filter = [StatusTypeEnum.SENT.value]
        
        await self._load_page(None)
                
    async def load_spam(self):
        
        self._label_filter = [StatusTypeEnum.SPAM.value]
        
        await self._load_page(None)
        
    async def load_trash(self):
        
        self._label_filter = [StatusTypeEnum.TRASH.value]
        
        await self._load_page(None)
        
    async def logout(self):
        
        if self.user_client.is_authorized is True:
            
            self.log.info("Logging out %s and deactivating token for device: %s" % (
                self.user_profile_data.emailAddress, 
                self.user_client.user_device.guid
                )
            )
            
            await queries.update_user_token_active_by_guid(
                guid = self.user_client.user_device.guid,
                is_active = False
            )
            
            self.user_client.is_authorized = False
            
            self.main_window.hide()
            
            self.gmail_login_window.show()

        if getattr(self.gmail_login_window, "status_label", None) is not None:
            
            self.gmail_login_window.status_label.setObjectName("info")
            self.gmail_login_window.status_label.setText("Sikeres kijelentkezés...")
            self.gmail_login_window.status_label.style().unpolish(self.gmail_login_window.status_label)
            self.gmail_login_window.status_label.style().polish(self.gmail_login_window.status_label)