from dataclass import DataclassBaseModel

class AdminBoatData(DataclassBaseModel):
    id: int
    boat_id: int
    name: str
    flag: str | None = None
    imo: int | None = None
    mmsi: int | None = None