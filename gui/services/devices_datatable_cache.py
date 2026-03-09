import json
import logging
import base64

from db.async_redis import AsyncRedisClient
from utils.dc.device import DeviceData, DeviceCacheData
from db import queries
from utils.logger import LoggerMixin

class DevicesCacheService(LoggerMixin):
    
    log: logging.Logger
    
    def __init__(self, redis_client: AsyncRedisClient):
        
        self.redis_client = redis_client
    
    KEY_PREFIX = "devices:"

    def _make_key(self, devices_cache_id: str) -> str:
        
        return f"{self.KEY_PREFIX}{devices_cache_id}"

    async def get_devices_data_from_cache(self, devices_cache_id: str, exp: int) -> DeviceCacheData:
        
        key = self._make_key(devices_cache_id)
        
        self.log.info("Handling cache key with %s: %s" % (
            self.__class__.__name__, 
            key
            )
        )
        
        cached_data = await self.redis_client.get(key)

        if cached_data is not None:
            
            self.log.debug("Raw cached data for %s: %s" % (devices_cache_id, self.redis_client.make_readable_cache_log(cached_data)))
            
            try:
                
                decoded_json = json.loads(cached_data)
                
                if devices_cache_id in decoded_json and "items" in decoded_json[devices_cache_id]:
                    
                    item_data = self.redis_client.decode_from_cache(decoded_json[devices_cache_id]["items"])
                    
                    return DeviceCacheData(
                        items = [DeviceData(**entry) for entry in item_data]
                    )
                    
                else:
                    
                    self.log.debug("No '%s' key or no items in cache" % devices_cache_id)
                    
            except Exception as e:
                
                self.log.error("Failed to decode cached devices data: %s" % str(e))
                
                await self.clear_cache(devices_cache_id)

        self.log.debug("No valid cache found, querying DB for %s" % devices_cache_id)

        query_results = await queries.select_devices_data()

        if len(query_results) > 0:
             
            raw_data = [
                DeviceData(
                    id = row.id,
                    storage_id = row.storage_id,
                    name = row.name,
                    manufacture_number = row.manufacture_number,
                    quantity = row.quantity,
                    manufacture_date = row.manufacture_date,
                    price = row.price,
                    commissioning_date = row.commissioning_date,
                    purchase_source = row.purchase_source,
                    purchase_date = row.purchase_date,
                    inspection_date = row.inspection_date,
                    is_scrap = row.is_scrap,
                    returned = all(t.returned for t in row.tenant),
                    is_deleted = row.is_deleted,
                    deleted_date = row.deleted_date,
                    uuid = row.uuid
                ) for row in query_results]

            if raw_data:
                
                wrapped = {
                    devices_cache_id: {
                        "items": [
                            self.redis_client.encode_for_cache(item.model_dump())
                            for item in raw_data
                        ]
                    }
                }
                
                await self.redis_client.set(key, json.dumps(wrapped, default = str), ex = exp)
                
                self.log.debug("Devices data cached for %s" % devices_cache_id)
                
            else:
                
                self.log.debug("Devcices query returned empty list for %s - not caching" % devices_cache_id)

            return DeviceCacheData(items = raw_data)
        
        elif query_results == []:
            
            self.log.info("No records found in the database")

    async def clear_cache(self, devices_cache_id: str):
        
        key = self._make_key(devices_cache_id)
        
        self.log.info("Clearing cache for key: %s" % key)
        
        await self.redis_client.clear_cache(key)