import typing as t

from dataclass import DataclassBaseModel

class WebsocketRequest(DataclassBaseModel):
    success: bool = False
    error: t.Optional[str] = None
    data: t.Optional[DataclassBaseModel] = None 

    def __init__(self, **kwargs):
    
        data = kwargs.get("data")
        
        if data is not None:
         
            if isinstance(data, dict):
          
                kwargs["data"] = self.select_model(data)
                
            elif not isinstance(data, DataclassBaseModel):
                
                raise TypeError("Data must be a DataclassBaseModel instance or dict")
            
        super().__init__(**kwargs)