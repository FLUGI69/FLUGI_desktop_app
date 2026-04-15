import asyncio
import json
import typing as t
import logging

from db.async_redis import AsyncRedisClient
from utils.dc.marine_traffic.search_data import MarineTrafficData, MarineSearchCacheData
from utils.logger import LoggerMixin

class MarineTrafficCacheService(LoggerMixin):
    
    log: logging.Logger
        
    KEY_PREFIX = "marine_search:"
    
    def __init__(self, 
        redis_client: AsyncRedisClient,
        marine_traffic_lock: asyncio.Lock
        ):
        
        self.redis_client = redis_client
        
        self.marine_traffic_lock = marine_traffic_lock

    def _make_key(self, marine_cache_id: str) -> str:
        
        return f"{self.KEY_PREFIX}{marine_cache_id}"

    async def cache_marine_search_data(self, marine_cache_id: str, exp: int, raw_data: t.List[MarineTrafficData])-> MarineSearchCacheData:
        
        key = self._make_key(marine_cache_id)
        
        self.log.info("Handling cache key with %s: %s" % (
            self.__class__.__name__, 
            key
            )
        )
        
        if raw_data:
           
            wrapped = {
                marine_cache_id: {
                    "items": [item.model_dump(mode = "json") for item in raw_data]
                }
            }
            
            async with self.marine_traffic_lock:
                await self.redis_client.set(key, json.dumps(wrapped, default = str), ex = exp)
            
            self.log.debug("MarineTrafficData cached for %s" % marine_cache_id)
            
        else:
            
            self.log.debug("MarineTrafficData returned empty list for %s - not caching" % marine_cache_id)

        return MarineSearchCacheData(items = raw_data)
        
    async def get_prev_search_data_from_cache(self, marine_cache_id: str) -> MarineSearchCacheData:
        
        key = self._make_key(marine_cache_id)    
        
        cached_data = await self.redis_client.get(key)

        if cached_data is not None:
            
            self.log.debug("Raw cached data for %s: %s" % (marine_cache_id, self.redis_client.make_readable_cache_log(cached_data)))
            
            try:
                
                decoded = json.loads(cached_data)
                
                if marine_cache_id in decoded and "items" in decoded[marine_cache_id]:
                    
                    item_data = decoded[marine_cache_id]["items"]
                    
                    return MarineSearchCacheData(
                        items = [MarineTrafficData(**entry) for entry in item_data]
                    )
                    
                else:
                    
                    self.log.debug("No '%s' key or no items in cache" % marine_cache_id)
                    
            except Exception as e:
                
                self.log.error("Failed to decode cached marine traffic data: %s" % str(e))
                
                await self.clear_cache(marine_cache_id)

    async def clear_cache(self, marine_cache_id: str):
        
        key = self._make_key(marine_cache_id)
        
        self.log.info("Clearing cache for key: %s" % key)
        
        async with self.marine_traffic_lock:
            await self.redis_client.clear_cache(key)