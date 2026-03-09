from dataclass import DataclassBaseModel
from datetime import datetime
import typing as t

from .boat_search import AdminBoatData
from .accessories import AdminWorkAccessorie
from .images import AdminWorkImage
from .status import AdminWorkStatus

class AdminEditWorkData(DataclassBaseModel):
    work_id: int
    leader: str
    description: str | None = None
    start_date: datetime | None = None
    finished_date: datetime | None = None
    transfered: bool = False
    is_contractor: bool = False
    boat: AdminBoatData
    work_accessories: t.List[AdminWorkAccessorie] = []
    images: t.List[AdminWorkImage] = []
    status: AdminWorkStatus | None = None
