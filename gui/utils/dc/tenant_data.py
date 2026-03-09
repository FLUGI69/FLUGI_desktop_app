import typing as t
from datetime import datetime

from dataclass import DataclassBaseModel
from utils.enums.storage_item_type_enum import StorageItemTypeEnum

class TenantData(DataclassBaseModel):
    tenant_id: int | None = None
    item_type: StorageItemTypeEnum
    item_id: int
    item_name: str | None = None
    quantity: float | None = None
    tenant_name: str | None = None
    rental_start: datetime | None = None
    rental_end: datetime | None = None
    returned: bool | None = None
    rental_price: float | None = None
    is_daily_price: bool = False