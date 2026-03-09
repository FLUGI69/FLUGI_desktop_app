from datetime import datetime

from dataclass import DataclassBaseModel

class ShipInfo(DataclassBaseModel):
    name: str
    arrival_date: datetime
    port: str
    ponton: str
    departure_date: datetime