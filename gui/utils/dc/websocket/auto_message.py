from dataclass import DataclassBaseModel
import typing as t 

class AutoMessage(DataclassBaseModel):
    message: str