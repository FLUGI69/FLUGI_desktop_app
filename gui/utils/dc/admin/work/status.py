from dataclass import DataclassBaseModel

import typing as t 

from .status_note import AdminWorkStatusNote

class AdminWorkStatus(DataclassBaseModel):
    id: int
    delivered_back: bool = False
    notes: t.List[AdminWorkStatusNote] = []