from datetime import datetime
import typing as t

from dataclass import DataclassBaseModel
from utils.dc.tenant_data import TenantData

class RentalHistoryData(DataclassBaseModel):
    is_paid: bool
    tenant: t.Optional[TenantData] = None
    
class RentalHistoryCacheData(DataclassBaseModel):
    items: t.List[RentalHistoryData]