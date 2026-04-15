from dataclass import DataclassBaseModel

class ReminderEvent(DataclassBaseModel):
    reminder_id: int
    action: str
    calendar_cache_id: str
