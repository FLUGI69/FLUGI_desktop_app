import typing as t

from dataclass import DataclassBaseModel
from ..tenant_data import TenantData

class AdminTenantsCacheData(DataclassBaseModel):
    items: t.List[TenantData]