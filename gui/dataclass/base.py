from pydantic import ConfigDict
import pydantic
from pathlib import Path
import sys
import inspect
import importlib
import pkgutil
import typing as t
import pickle
from enum import Enum
from datetime import datetime

from config import Config

class DataclassBaseModel(pydantic.BaseModel):

    model_config = ConfigDict(
        use_enum_values = True,
        arbitrary_types_allowed = True,
    )
             
    def __post_init__(self): pass

    def model_post_init(self, __context: t.Any):

        # Iterate through model fields
        for field_name, field_value in self.model_fields.items():
            
            # Get the field's type annotation
            field_annotation = field_value.annotation

            if t.get_origin(field_annotation) is t.Union:  # Handles Optional[T]
                
                field_annotation = next((arg for arg in t.get_args(field_annotation) if arg is not type(None)), None)

            # Check if the field's type is an Enum
            if field_annotation and isinstance(field_annotation, type) and issubclass(field_annotation, Enum):
                
                # Convert the string value to the corresponding Enum member if it's a string
                if hasattr(self, field_name):
                    
                    value = getattr(self, field_name)
                    
                    if isinstance(value, int):
                        
                        # Convert the string value to the corresponding Enum member
                        # sys.stderr.write(f"{field_name}: {field_annotation}")
                        converted_enum = field_annotation(value)
                        setattr(self, field_name, converted_enum)

        if hasattr(self, '__post_init__'):
            
            self.__post_init__()

    def dumps(self) -> bytes:

        return pickle.dumps(self)
    
    @classmethod
    def loads(cls, data: bytes) -> 'DataclassBaseModel':

        return pickle.loads(data)

    def as_dict(self) -> dict[str, t.Any]:

        return {k: self._value_to_dict(v) for k, v in super().__dict__.items()}
    
    @classmethod
    def _value_to_dict(cls, value: t.Any) -> t.Any:

        if cls.is_pydantic_dataclass(value):
            
            return {k: cls._value_to_dict(v) for k, v in value.__dict__.items()}
        
        elif isinstance(value, list):
            
            return [cls._value_to_dict(item) for item in value]
        
        elif isinstance(value, tuple):
           
            return tuple([cls._value_to_dict(item) for item in list(value)])
       
        elif isinstance(value, dict):
            
            return {k: cls._value_to_dict(v) for k, v in value.items()}
        
        elif isinstance(value, Enum):
            
            return value.value
        
        else:
            
            return value

    @classmethod
    def is_pydantic_dataclass(cls, obj) -> bool:

        cls = obj if isinstance(obj, type) else type(obj)

        return all(hasattr(cls, item) for item in DataclassBaseModel.__slots__)

    def __str__(self) -> str:
        
        return self.__repr__()
    
    def __repr__(self):
        
        fields = []
        
        for field_name, field_value in self.__dict__.items():

            if field_name.startswith("_") == True:
                continue

            if isinstance(field_value, (bytes, bytearray)):
                
                value = f"Bytes({len(field_value)})"
            
            elif isinstance(field_value, str):
                
                value = f"'{field_value}'"
            
            elif isinstance(field_value, datetime):
                
                try:
                    
                    value = f"datetime({field_value.strftime('%Y-%m-%d %H:%M:%S.%f')}, tz={field_value.tzinfo})"
                
                except:
                    
                    value = f"datetime({field_value})"
            
            elif isinstance(field_value, list) and next((True for item in field_value if self.is_pydantic_dataclass(item.__class__)), False) == True:
                
                list_value = []
                
                for item in field_value:
                   
                    if isinstance(item, str):
                        
                        item = f"'{item}'"
                        
                    elif self.is_pydantic_dataclass(item.__class__) == True:
                        
                        item = str(item)
                    
                    list_value.append(item)

                value = "[%s]" % (str(', '.join(list_value)))

            elif self.is_pydantic_dataclass(field_value.__class__) == True:
                
                value = str(field_value)
            
            else:
                
                value = field_value

            fields.append(f"{field_name}={value}")

        return f"{self.__class__.__name__}({', '.join(fields)})"
    
    @classmethod
    def collect_websocket_models(cls, 
        path: t.Optional[Path] = None, 
        pkg_prefix: t.Optional[str] = None
        ) -> list[type["DataclassBaseModel"]]:
        """
        Recursively collect all DataclassBaseModel subclasses from the websocket folder
        and its subfolders, excluding EXCLUDED_MODELS.
        """
        if path is None:
            
            # Determine websocket folder
            if getattr(sys, "frozen", False) is True:
                
                path = Path(sys.executable).parent / "_internal" / Config.websocket.folder
                
            else:
                
                path = Path(Config.websocket.folder)
                
            pkg_prefix = "utils.dc.websocket"

        if path.exists() is not True:
            
            raise RuntimeError("Websocket folder not found:%s" % str(path))

        models: list[type[DataclassBaseModel]] = []

        for module_info in pkgutil.iter_modules([str(path)]):
            
            full_module_name = f"{pkg_prefix}.{module_info.name}"
            # print(f"Inspecting module: {full_module_name}")
            
            try:
                
                module = importlib.import_module(full_module_name)
                # print(module)
                
            except Exception:
                continue

            # Collect classes
            for name, obj in inspect.getmembers(module, inspect.isclass):
                # print(f"{name}.__module__ = {obj.__module__}, module.__name__ = {module.__name__}")
                # print(name, issubclass(obj, cls))
                
                if cls.is_subclass_of_dataclass_base(obj) and obj is not cls \
                    and name not in Config.websocket.excluded_models:
                            
                    models.append(obj)

            # Recursively process sub-packages
            if module_info.ispkg is True:
                
                sub_path = path / module_info.name
                
                sub_pkg_prefix = f"{pkg_prefix}.{module_info.name}"
                
                models.extend(cls.collect_websocket_models(sub_path, sub_pkg_prefix))
      
        return models
    
    def is_subclass_of_dataclass_base(obj):
        
        return any(base.__name__ == "DataclassBaseModel" for base in obj.__mro__)
    
    @classmethod
    def select_model(cls, data: dict) -> t.Any:
        """
        Iterates through all collected websocket models,
        and instantiates the first one that successfully validates the dict.
        Only the collected models are allowed.
        """
        
        if isinstance(data, dict):
         
            models: list[type[DataclassBaseModel]] = cls.collect_websocket_models()
      
            if len(models) > 0:
                
                class_name = data.get("__class__")   
                     
                for model in models:
                    
                    if model.__name__ == class_name:
                        # print(model, model.__name__)
                        
                        try:
                            
                            return model.model_validate(data)
                        
                        except Exception as e:
                            
                            raise ValueError("Data matches __class__='%s' but validation failed: %s" % (
                                class_name, 
                                e
                                )                
                            )

                raise ValueError("No websocket model found with __class__ = '%s'" % class_name)
        
    def model_dump(self, **kwargs) -> dict:
        """
        Recursively dump the model, including the class name of any nested DataclassBaseModel.
        """
        result = {}
        
        for key, value in self.__dict__.items():
          
            if isinstance(value, DataclassBaseModel):
             
                result[key] = {
                    "__class__": value.__class__.__name__,
                    **value.model_dump(**kwargs)
                }
         
            elif isinstance(value, list):
              
                new_list = []
              
                for item in value:
                   
                    if isinstance(item, DataclassBaseModel):
                       
                        new_list.append({
                            "__class__": item.__class__.__name__,
                            **item.model_dump(**kwargs)
                        })
                    
                    else:
                        
                        new_list.append(item)
                
                result[key] = new_list
            
            else:
                
                result[key] = value

        return result