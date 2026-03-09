from datetime import datetime

from dataclass import DataclassBaseModel

class ShipSchedule(DataclassBaseModel):
    schedule_id: int | None = None
    location: str
    arrival_date: datetime
    ponton: str
    leave_date: datetime