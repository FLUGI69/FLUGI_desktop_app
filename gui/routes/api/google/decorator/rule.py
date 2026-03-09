import typing as t
from .wrapper import AsyncWrapper

class RuleDecorator:
    
    def __init__(self, 
        endpoint: str, 
        method: str | None = None
        ) -> None:
        
        self.endpoint = endpoint
        
        self.method = method

    def __call__(self, func: t.Callable) -> "AsyncWrapper":
        
        return AsyncWrapper(func, self.endpoint, self.method)