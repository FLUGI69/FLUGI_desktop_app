import json
import logging
import asyncio

from db.async_redis import AsyncRedisClient
from utils.dc.material import MaterialCacheData, MaterialData
from db import queries
from utils.logger import LoggerMixin

class MaterialCacheService(LoggerMixin):
    
    log: logging.Logger
    
    KEY_PREFIX = "material:"
    
    def __init__(self, 
        redis_client: AsyncRedisClient,
        storage_lock: asyncio.Lock
        ):
        
        self.redis_client = redis_client
        
        self.storage_lock = storage_lock

    def _make_key(self, material_cache_id: str) -> str:
        
        return f"{self.KEY_PREFIX}{material_cache_id}"

    async def get_material_data_from_cache(self, material_cache_id: str, exp: int) -> MaterialCacheData:
        
        key = self._make_key(material_cache_id)
        
        self.log.info("Handling cache key with %s: %s" % (
            self.__class__.__name__, 
            key
            )
        )
        
        cached_data = await self.redis_client.get(key)
        
        if cached_data is not None:
            # print(type(cached_data))
            
            self.log.debug("Raw cached data for %s: %s" % (material_cache_id, self.redis_client.make_readable_cache_log(cached_data)))
           
            try:
                
                decoded_json = json.loads(cached_data)
                
                if material_cache_id in decoded_json and "items" in decoded_json[material_cache_id]:
                    
                    item_data = decoded_json[material_cache_id]["items"]
                 
                    return MaterialCacheData(
                        items = [MaterialData(**entry) for entry in item_data]
                    )
                    
                else:
                    
                    self.log.debug("No '%s' key or no items in cache" % material_cache_id)
                    
            except Exception as e:
                
                self.log.error("Failed to decode cached warehouse data: %s" % str(e))
                
                await self.clear_cache(material_cache_id)

        self.log.debug("No valid cache found, querying DB for %s" % material_cache_id)

        query_results = await queries.select_material_data()

        if len(query_results) > 0:
             
            raw_data = [
                MaterialData(
                    id = row.id,
                    storage_id = row.storage_id,
                    name = row.name,
                    manufacture_number = row.manufacture_number,
                    quantity = row.quantity,
                    unit = row.unit,
                    manufacture_date = row.manufacture_date,
                    price = row.price,
                    purchase_source = row.purchase_source,
                    purchase_date = row.purchase_date,
                    inspection_date = row.inspection_date,
                    is_deleted = row.is_deleted,
                    deleted_date = row.deleted_date,
                    uuid = row.uuid
                )
                for row in query_results]
        
            if raw_data:
                
                wrapped = {
                    material_cache_id: {
                        "items": [
                            item.model_dump(mode = "json")
                            for item in raw_data
                        ]
                    }
                }
                
                async with self.storage_lock:
                    await self.redis_client.set(key, json.dumps(wrapped, default = str), ex = exp)
                
                self.log.debug("Material data cached for %s" % material_cache_id)
                
            else:
                
                self.log.debug("Material query returned empty list for %s - not caching" % material_cache_id)

            return MaterialCacheData(items = raw_data)
        
        elif query_results == []:
            
            self.log.info("No records found in the database")

    async def clear_cache(self, material_cache_id: str):
        
        key = self._make_key(material_cache_id)
        
        self.log.info("Clearing cache for key: %s" % key)
        
        async with self.storage_lock:
            await self.redis_client.clear_cache(key)