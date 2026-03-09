from dataclass import DataclassBaseModel
import typing as t 

class WebsocketClient(DataclassBaseModel):
    authenticated: bool = False
    name: str
    auth_token: t.Optional[str]
