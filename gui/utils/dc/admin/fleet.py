import typing as t
from datetime import datetime

from dataclass import DataclassBaseModel

class FleetData(DataclassBaseModel):
    id: int
    flag: str | None = None
    name: str
    ship_id: int
    imo: int | None = None
    mmsi: int | None = None
    callsign: str | None = None
    type_name: str | None = None
    view_on_map_href: str | None = None
    more_deatails_href: str | None = None
    works: int

class FleetCacheData(DataclassBaseModel):
    items: t.List[FleetData]