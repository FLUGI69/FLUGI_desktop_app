from dataclass import DataclassBaseModel
import typing as t

class MarineTrafficData(DataclassBaseModel):
    id: int | None = None
    ship_name: str
    more_deatails_href: t.Optional[str] = None
    view_on_map_href: t.Optional[str] = None
    ship_id: t.Optional[int] = None
    type_name: t.Optional[str] = None
    flag: t.Optional[str] = None
    mmsi: t.Optional[int] = None
    callsign: t.Optional[str] = None
    imo: t.Optional[int] = None
    reported_destination: t.Optional[str] = None
    matched_destination: t.Optional[str] = None
    
# class MarineTrafficData(DataclassBaseModel):
#     ship_name: str
#     MMSI: int | None = None
#     IMO: int | None = None
#     ship_id: int | None = None
#     callsign: str
#     type_name: t.Optional[str] = None
#     dwt: t.Optional[str] = None
#     flag: t.Optional[str] = None
#     country: t.Optional[str] = None
#     year_built: t.Optional[str] = None
#     url: t.Optional[str] = None
    
class MarineSearchCacheData(DataclassBaseModel):
    items: t.List[MarineTrafficData]