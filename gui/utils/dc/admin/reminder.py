from datetime import datetime
import typing as t

from dataclass import DataclassBaseModel

class CalendarData(DataclassBaseModel):
    calendar_cache_id: str | None = None
    id: int | None = None
    note: str
    date: datetime
    used: bool
    
class CalendarCacheData(DataclassBaseModel):
    items: t.List[CalendarData]
