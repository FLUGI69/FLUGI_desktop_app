from dataclass import DataclassBaseModel

class NewEmailData(DataclassBaseModel):
    to: str | None = None
    subject: str | None = None
    body: str | None = None 
    attachments: list | None = None