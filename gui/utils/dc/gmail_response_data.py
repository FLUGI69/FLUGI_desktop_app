from datetime import datetime
import typing as t

from dataclass import DataclassBaseModel
from utils.enums.email_status_enum import StatusTypeEnum

class MessagePartBody(DataclassBaseModel):
    attachmentId: str # Attachment ID string marad, mivel nem numerikus (pl. 'ANGjdJ9E') 
    size: int
    data: str

    def __repr__(self):
       
        data_repr = "Str(%d)" % len(self.data) if len(self.data) > 100 else "'%s'" % self.data
        
        return "MessagePartBody(attachmentId='%s', size=%s, data=%s)" % (
            self.attachmentId, 
            self.size, 
            data_repr
        )

class Header(DataclassBaseModel):
    name: str
    value: str

    def __repr__(self):
        
        value_repr = "Str(%d)" % len(self.value) if len(self.value) > 100 else "'%s'" % self.value
       
        return "Header(name='%s', value=%s)" % (
            self.name, 
            value_repr
        )

class MessagePart(DataclassBaseModel):
    part_id: str | None = None
    mime_type: str | None = None
    filename: str | None = None
    headers: t.List[Header] | None = None
    body: MessagePartBody | None = None
    parts: t.List["MessagePart"] | None = None  # Rekurzív MIME támogatás

class Attachments(DataclassBaseModel):
    attachmentId: str
    size: int
    data: str | None = None 

    def __repr__(self):
        
        if self.data is not None and len(self.data) > 100:
            data_repr = "Str(%d)" % len(self.data)
       
        elif self.data is not None:
            data_repr = "'%s'" % self.data
        
        else:
            data_repr = "None"
       
        return "Attachments(attachmentId='%s', size=%s, data=%s)" % (
            self.attachmentId,
            self.size, 
            data_repr
        )

class Message(DataclassBaseModel):
    id: str  # Gmail ID string marad, mivel nem numerikus (pl. '188c4784c5e5c9d1')
    threadId: str | None = None
    labelIds: t.Optional[t.List[StatusTypeEnum]] = None
    snippet: str | None = None
    historyId: int | None = None  # Gmail numerikus stringként jön, de logikailag int
    internalDate: datetime | None = None  # Unix timestamp string → datetime konverzió kell majd
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