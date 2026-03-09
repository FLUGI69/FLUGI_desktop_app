from dataclass import DataclassBaseModel
from datetime import datetime
import typing as t 

from utils.enums.storage_item_type_enum import StorageItemTypeEnum
from .rental_history import RentalHistoryData
from ..tools import ToolsData
from ..device import DeviceData
from .reminder import CalendarData

class CurrentTenant(DataclassBaseModel):
    id: int
    tenant_name: str
    rental_start: datetime
    rental_end: datetime
    rental_price: float
    item_type: StorageItemTypeEnum
    item_id: int 
    returned: bool
    quantity: float
    is_daily_price: bool
    tool: t.Optional[ToolsData]
    device: t.Optional[DeviceData]
    rental_histories: t.Optional[RentalHistoryData]
    tenant_reminders: t.Optional[CalendarData]