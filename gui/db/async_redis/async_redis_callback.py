import inspect
import logging
import typing as t

from utils.logger import LoggerMixin
from utils.dc.websocket.redis_event import RedisEvent

if t.TYPE_CHECKING:
    
    from .async_redis import AsyncRedisClient
    
class AsyncRedisCallback(LoggerMixin):
    
    log: logging.Logger
    
    def __init__(self, redis_client: 'AsyncRedisClient') -> None:
        
        self.redis_client = redis_client

    async def __call__(self, key: str, ex: int) -> RedisEvent:
        
        self.log.debug("AsyncRedisCallback -> BEGIN")
        
        try:
            
            service, owner, attr_name = self._detect_service_with_owner()

            if service is not None:
                
                if owner is not None:
                    
                    self.log.debug("Detected service with prefix key: %s - '%s' in owner: %s as attribute: %s" % (
                        type(service).__name__, 
                        key,
                        type(owner).__name__, 
                        attr_name
                        )
                    )
                    
                    cache_id = key.split(":")[-1]
                
                    for name, _ in inspect.getmembers(owner, predicate = inspect.iscoroutinefunction):
                       
                        if name == "load_cache_data":
                            
                            return RedisEvent(
                                service_name = type(service).__name__,
                                class_name = type(owner).__name__,
                                method_name = name,
                                cache_id = cache_id,
                                exp = ex
                            )
                            
        except Exception as e:
            
            self.log.exception("Error in AsyncRedisCallback: %s" % str(e))
        
        finally:
            
            self.log.debug("AsyncRedisCallback -> END")

    def _detect_service_with_owner(self):
        """
        Searches the call stack for the service instance and identifies the object (owner)
        that contains this service as an attribute.

        Returns:
            service_instance: the found service instance
            owner_instance: the object that holds the service (None if not found)
            attribute_name: the name of the attribute through which the service is accessible in the owner
        """
        
        for frame_info in inspect.stack()[2:]:
            
            possible_service = frame_info.frame.f_locals.get("self")

            if possible_service is not None and possible_service is not self.redis_client:
                
                if "Service" in type(possible_service).__name__:
                    service_instance = possible_service

                    for frame_info2 in inspect.stack()[2:]:
                        
                        possible_owner = frame_info2.frame.f_locals.get("self")
                        
                        if possible_owner is not None and possible_owner is not self.redis_client and hasattr(possible_owner, "__dict__"):
           
                            for attribute_name, attribute_value in vars(possible_owner).items():
                                
                                if attribute_value is service_instance:
                                    return service_instance, possible_owner, attribute_name

                    return service_instance, None, None

        return None, None, None