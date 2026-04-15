import asyncio
import json
import logging

from db.async_redis import AsyncRedisClient
from utils.dc.returnable_packaging import ReturnablePackagingData, ReturnablePackagingCacheData
from db import queries
from utils.logger import LoggerMixin

class ReturnablePackagingCacheService(LoggerMixin):
    
    log: logging.Logger
    
    KEY_PREFIX = "returnable_packaging:"
    
    def __init__(self, 
        redis_client: AsyncRedisClient,
        storage_lock: asyncio.Lock
        ):
        
        self.redis_client = redis_client
        
        self.storage_lock = storage_lock

    def _make_key(self, returnable_packaging_cache_id: str) -> str:
        
        return f"{self.KEY_PREFIX}{returnable_packaging_cache_id}"

    async def get_returnable_data_from_cache(self, returnable_packaging_cache_id: str, exp: int) -> ReturnablePackagingCacheData:
        
        key = self._make_key(returnable_packaging_cache_id)
        
        self.log.info("Handling cache key with %s: %s" % (
            self.__class__.__name__, 
            key
            )
        )
        
        cached_data = await self.redis_client.get(key)

        if cached_data is not None:
            
            self.log.debug("Raw cached data for %s: %s" % (returnable_packaging_cache_id, self.redis_client.make_readable_cache_log(cached_data)))
            
            try:
                
                decoded_json = json.loads(cached_data)
                
                if returnable_packaging_cache_id in decoded_json and "items" in decoded_json[returnable_packaging_cache_id]:
                    
                    item_data = decoded_json[returnable_packaging_cache_id]["items"]
                    
                    return ReturnablePackagingCacheData(
                        items = [ReturnablePackagingData(**entry) for entry in item_data]
                    )
                    
                else:
                    
                    self.log.debug("No '%s' key or no items in cache" % returnable_packaging_cache_id)
                    
            except Exception as e:
                
                self.log.error("Failed to decode cached returnable packaging data: %s" % str(e))
                
                await self.clear_cache(returnable_packaging_cache_id)

        self.log.debug("No valid cache found, querying DB for %s" % returnable_packaging_cache_id)

        query_results = await queries.select_returnable_packaging_data()

        if len(query_results) > 0:
             
            raw_data = [
                ReturnablePackagingData(
                    id = row.id,
                    storage_id = row.storage_id,
                    name = row.name,
                    manufacture_number = row.manufacture_number,
                    quantity = row.quantity,
                    manufacture_date = row.manufacture_date,
                    price = row.price,
                    purchase_source = row.purchase_source,
                    purchase_date = row.purchase_date,
                    inspection_date = row.inspection_date,
                    returned_date = row.returned_date,
                    is_returned = row.is_returned,
                    is_deleted = row.is_deleted,
                    deleted_date = row.deleted_date,
                    uuid = row.uuid
                ) for row in query_results]

            if raw_data:
                
                wrapped = {
                    returnable_packaging_cache_id: {
                        "items": [
                            item.model_dump(mode = "json")
                            for item in raw_data
                        ]
                    }
                }
                
                async with self.storage_lock:
                    await self.redis_client.set(key, json.dumps(wrapped, default = str), ex = exp)
                
                self.log.debug("Returnable packaging data cached for %s" % returnable_packaging_cache_id)
                
            else:
                
                self.log.debug("Returnable packaging query returned empty list for %s - not caching" % returnable_packaging_cache_id)

            return ReturnablePackagingCacheData(items = raw_data)
        
        elif query_results == []:
            
            self.log.info("No records found in the database")

    async def clear_cache(self, returnable_packaging_cache_id: str):
        
        key = self._make_key(returnable_packaging_cache_id)
        
        self.log.info("Clearing cache for key: %s" % key)
        
        async with self.storage_lock:
            await self.redis_client.clear_cache(key)