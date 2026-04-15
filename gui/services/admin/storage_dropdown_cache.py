import asyncio
import json
import logging

from db.async_redis import AsyncRedisClient
from utils.dc.admin.storage import StorageCacheData, StorageData
from db import queries
from utils.logger import LoggerMixin

class StorageCacheService(LoggerMixin):
    
    log: logging.Logger
        
    KEY_PREFIX = "storage:"
    
    def __init__(self, 
        redis_client: AsyncRedisClient,
        admin_storage_lock: asyncio.Lock
        ):
        
        self.redis_client = redis_client
        
        self.admin_storage_lock = admin_storage_lock

    def _make_key(self, storage_cache_id: str) -> str:
        
        return f"{self.KEY_PREFIX}{storage_cache_id}"

    async def get_storage_data_from_cache(self, storage_cache_id: str, exp: int) -> StorageCacheData:
        
        key = self._make_key(storage_cache_id)
        
        self.log.info("Handling cache key with %s: %s" % (
            self.__class__.__name__, 
            key
            )
        )
        
        cached_data = await self.redis_client.get(key)

        if cached_data is not None:
            
            self.log.debug("Raw cached data for %s: %s" % (storage_cache_id, self.redis_client.make_readable_cache_log(cached_data)))
            
            try:
                
                decoded = json.loads(cached_data)
                
                if storage_cache_id in decoded and "items" in decoded[storage_cache_id]:
                    
                    item_data = decoded[storage_cache_id]["items"]
                    
                    return StorageCacheData(
                        items = [StorageData(**entry) for entry in item_data]
                    )
                    
                else:
                    
                    self.log.debug("No '%s' key or no items in cache" % storage_cache_id)
                    
            except Exception as e:
                
                self.log.exception("Failed to decode cached storage data: %s" % str(e))
                
                await self.clear_cache(storage_cache_id)

        self.log.debug("No valid cache found, querying DB for %s" % storage_cache_id)

        query_results = await queries.select_all_storage()
     
        if query_results is not None or len(query_results) > 0:

            raw_data = [
                StorageData(
                    id = row.id,
                    name = row.name,
                    location = row.location
                ) for row in query_results]

            if raw_data:
                
                wrapped = {
                    storage_cache_id: {
                        "items": [item.model_dump(mode = "json") for item in raw_data]
                    }
                }
                
                async with self.admin_storage_lock:
                    await self.redis_client.set(key, json.dumps(wrapped, default = str), ex = exp)
                
                self.log.debug("Storage data cached for %s" % storage_cache_id)
                
            else:
                
                self.log.debug("Storage query returned empty list for %s - not caching" % storage_cache_id)

            return StorageCacheData(items = raw_data)
        
        elif query_results == []:
            
            self.log.info("No records found in the database")

    async def clear_cache(self, storage_cache_id: str):
        
        key = self._make_key(storage_cache_id)
        
        self.log.info("Clearing cache for key: %s" % key)
        
        async with self.admin_storage_lock:
            await self.redis_client.clear_cache(key)