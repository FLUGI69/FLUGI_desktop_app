import typing as t
from .bound_wrapper import BoundAsyncWrapper

class AsyncWrapper:
    
    def __init__(self, 
        func: t.Callable,
        endpoint: str,
        method: str | None
        ) -> None:
        
        self.func = func
        
        self.endpoint = endpoint
        
        self.method = method

    def __get__(self, instance: t.Any, owner: t.Type) -> "BoundAsyncWrapper":
        
        return BoundAsyncWrapper(self.func, instance, self.endpoint, self.method)