from datetime import datetime
from datetime import datetime

from dataclass import DataclassBaseModel

class LoginHistory(DataclassBaseModel):
    username: str | None = None
    guid: str
    device_name: str | None = None
    os: str | None = None
    ip_address: str | None = None
    location: str | None = None
    login_time: datetime
    success: bool