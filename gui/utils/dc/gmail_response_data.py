from datetime import datetime
import typing as t

from dataclass import DataclassBaseModel
from utils.enums.email_status_enum import StatusTypeEnum

class MessagePartBody(DataclassBaseModel):
    attachmentId: str 
    size: int
    data: str

class Header(DataclassBaseModel):
    name: str
    value: str

class MessagePart(DataclassBaseModel):
    part_id: str | None = None
    mime_type: str | None = None
    filename: str | None = None
    headers: t.List[Header] | None = None
    body: MessagePartBody | None = None
    parts: t.List["MessagePart"] | None = None  # Recursive MIME support

class Attachments(DataclassBaseModel):
    attachmentId: str
    size: int
    data: str | None = None 

class Message(DataclassBaseModel):
    id: str 
    threadId: str | None = None
    labelIds: t.Optional[t.List[StatusTypeEnum]] = None
    snippet: str | None = None
    historyId: int | None = None  # Gmail sends as numeric string, but logically int
    internalDate: datetime | None = None  # Unix timestamp string → datetime conversion needed
    payload: MessagePart | None = None
    sizeEstimate: int | None = None
    raw: str | None = None

class ListMessages(DataclassBaseModel):
    messages: t.List[Message]
    nextPageToken: str | None = None
    resultSizeEstimate: int | None = None
    
class EmailHeaders(Message): 
    sender: str | None = None
    subject: str | None = None
    date: datetime | None = None
    is_read: bool = False
    is_important: bool = False