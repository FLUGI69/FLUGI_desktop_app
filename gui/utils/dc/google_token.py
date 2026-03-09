from dataclass import DataclassBaseModel
from datetime import datetime

class GoogleToken(DataclassBaseModel):
    token: str
    refresh_token: str
    token_uri: str
    client_id: str
    client_secret: str
    scopes: list[str]
    expiry: str
    universe_domain: str
    