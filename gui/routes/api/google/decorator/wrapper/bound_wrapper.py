import typing as t 

class BoundAsyncWrapper:
    
    def __init__(self, 
        func: t.Callable, 
        instance: t.Any, 
        endpoint: str, 
        method: str | None
        ) -> None:
        
        self.func = func
        
        self.instance = instance
        
        self.endpoint = endpoint
        
        self.method = method

    async def __call__(self, *args, **kwargs) -> t.Any:
        
        self.instance.endpoint = self.endpoint
        
        self.instance.method_name_override = self.method
        
        return await self.func(self.instance, *args, **kwargs)