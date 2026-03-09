import typing as t
from datetime import datetime

from dataclass import DataclassBaseModel

class SelectedWorkData(DataclassBaseModel):
    id: int
    boat_id: int
    description: str | None = None
    start_date: datetime | None = None
    finished_date: datetime | None = None
    transfered: bool | None = None
    is_contractor: bool | None = None
    img: bytes | None = None
    boat_name: str | None = None