from dataclass import DataclassBaseModel
import typing as t
from ..marine_traffic.single_vessel_data import MarineTrafficSingleVesselData

class AdminSingleBoatCacheData(DataclassBaseModel):
    items: t.List[MarineTrafficSingleVesselData]