from dataclass import DataclassBaseModel

class AdminWorkImage(DataclassBaseModel):
    id: int
    img: bytes
    