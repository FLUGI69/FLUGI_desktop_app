import typing as t
from datetime import datetime

from dataclass import DataclassBaseModel

class MaterialData(DataclassBaseModel):
    id: int | None = None
    storage_id: int
    name: str | None = None
    manufacture_number: str | None = None
    quantity: float
    unit: str | None = None
    manufacture_date: datetime | None = None
    price: float | None = None
    purchase_source: str | None = None
    purchase_date: datetime | None = None
    inspection_date: datetime
    is_deleted: bool = False
    deleted_date: datetime | None = None
    uuid: bytes | None = None

class MaterialCacheData(DataclassBaseModel):
    items: t.List[MaterialData]