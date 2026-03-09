from dataclass import DataclassBaseModel
import typing as t

class VesselPosition(DataclassBaseModel):
    ship_name: t.Optional[str]
    lat: t.Optional[float]
    lon: t.Optional[float]
