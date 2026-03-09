import typing as t

from dataclass import DataclassBaseModel

class WebsocketRequestResponse(DataclassBaseModel):
    success: bool = False
    error: t.Optional[str] = None
    event: t.Optional[str] = None