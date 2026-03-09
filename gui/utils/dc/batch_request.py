from dataclass import DataclassBaseModel

class BatchRequestData(DataclassBaseModel):
    method_name: str
    params: dict