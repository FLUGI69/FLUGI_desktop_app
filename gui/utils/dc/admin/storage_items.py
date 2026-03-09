import typing as t
from dataclass import DataclassBaseModel

from ..material import MaterialData
from ..device import DeviceData
from ..tools import ToolsData

class AdminStorageItemsCacheData(DataclassBaseModel):
    items: t.List[
        t.Optional[
            t.Union[
                MaterialData, 
                DeviceData, 
                ToolsData
            ]
        ]
    ]