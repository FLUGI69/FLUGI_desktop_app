from dataclass import DataclassBaseModel

class RedisEvent(DataclassBaseModel):
    service_name: str
    class_name: str
    method_name: str
    cache_id: str
    exp: int