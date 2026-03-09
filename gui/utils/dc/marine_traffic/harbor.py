from dataclass import DataclassBaseModel
import typing as t

class Harbor(DataclassBaseModel):
    name: t.Optional[str] = None
    lat: t.Optional[float]
    lon: t.Optional[float]
