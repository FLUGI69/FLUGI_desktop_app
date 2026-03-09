from dataclass import DataclassBaseModel

import typing as t 
from datetime import datetime

class AdminWorkStatusNote(DataclassBaseModel):
    id: int
    note: str
    created_at: datetime