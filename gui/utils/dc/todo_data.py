import typing as t
from datetime import datetime
from dataclass import DataclassBaseModel
from .admin.ship_schedule import ShipSchedule

class BoatWork(DataclassBaseModel):
    id: int
    leader: str
    order_date: datetime
    description: str | None = None
    start_date: datetime | None = None
    finished_date: datetime | None = None
    transfered: bool = False
    is_contractor: bool = False

class TodoBoat(DataclassBaseModel):
    id: int
    name: str
    flag: t.Optional[str]
    mmsi: t.Optional[int]
    imo: t.Optional[int]
    callsign: t.Optional[str]
    type_name: t.Optional[str]
    ship_id: t.Optional[int]
    schedule: ShipSchedule
    works: t.List[BoatWork]