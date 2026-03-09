from dataclass import DataclassBaseModel
import typing as t

from ..admin.ship_schedule import ShipSchedule

class SelectedBoatData(DataclassBaseModel):
    boat_id: int
    name: str
    flag: t.Optional[str]
    mmsi: t.Optional[int]
    imo: t.Optional[int]
    ship_id: t.Optional[int]
    schedule: t.List[ShipSchedule] = []