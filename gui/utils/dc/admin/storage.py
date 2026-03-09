import typing as t

from dataclass import DataclassBaseModel

class StorageData(DataclassBaseModel):
    id: int | None = None
    name: str | None = None
    location: str | None = None
    
class StorageCacheData(DataclassBaseModel):
    items: t.List[StorageData]