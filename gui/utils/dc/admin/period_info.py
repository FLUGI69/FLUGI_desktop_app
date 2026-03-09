from datetime import datetime

from dataclass import DataclassBaseModel

class PeriodInfo(DataclassBaseModel):
    full_period_days: int
    extension_days: int
    daily_base_price: float
    daily_new_price: float
    price_changed: bool
    quantity_changed: bool
    extended: bool
    elapsed_days: int
    remaining_days: int
    total_days: int
    period_end: datetime | None = None