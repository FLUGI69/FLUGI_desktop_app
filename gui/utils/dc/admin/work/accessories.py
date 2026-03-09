from dataclass import DataclassBaseModel

class AdminWorkAccessorie(DataclassBaseModel):
    component_id: int
    quantity: float
    