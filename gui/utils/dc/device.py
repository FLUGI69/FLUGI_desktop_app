import typing as t
from datetime import datetime
from dataclass import DataclassBaseModel

class DeviceData(DataclassBaseModel):
    id: int | None = None
    storage_id: int
    name: str | None = None
    manufacture_number: str | None
    quantity: float 
    manufacture_date: datetime | None = None
    price: float | None = None
    commissioning_date: datetime | None = None
    purchase_source: str | None = None
    purchase_date: datetime | None = None
    inspection_date: datetime
    is_scrap: bool = False
    returned: bool = False
    is_deleted: bool = False
    deleted_date: datetime | None = None
    uuid: bytes | None = None

class DeviceCacheData(DataclassBaseModel):
    items: t.List[DeviceData]