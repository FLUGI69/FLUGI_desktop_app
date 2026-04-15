import asyncio
import json
import logging

from db.async_redis import AsyncRedisClient
from utils.dc.admin.storage_items import AdminStorageItemsCacheData
from utils.dc.material import MaterialData
from utils.dc.tools import ToolsData
from utils.dc.device import DeviceData
from db import queries
from utils.logger import LoggerMixin 

class AdminStorageItemsCacheService(LoggerMixin):
    
    log: logging.Logger
    
    KEY_PREFIX = "storage_items:"
    
    def __init__(self, 
        redis_client: AsyncRedisClient,
        admin_storage_lock: asyncio.Lock
        ):
        
        self.redis_client = redis_client
        
        self.admin_storage_lock = admin_storage_lock

    def _make_key(self, storage_cache_id: str) -> str:
        
        return f"{self.KEY_PREFIX}{storage_cache_id}"

    async def get_storage_datatable_data_from_cache(self, storage_cache_id: str, exp: int) -> AdminStorageItemsCacheData:
        
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
                    
                    items_raw = decoded[storage_cache_id]["items"]
                    
                    items = []

                    for entry in items_raw:
                        
                        item_type = entry.get("type")
                        
                        data = {key: value for key, value in entry.items() if key != "type"}

                        if item_type == "MaterialData":
                            
                            items.append(MaterialData(**data))
                            
                        elif item_type == "ToolsData":
                            
                            items.append(ToolsData(**data))
                            
                        elif item_type == "DeviceData":
                            
                            items.append(DeviceData(**data))
                            
                        else:
                            
                            self.log.warning("Unknown item type in cache: %s" % item_type)

                    return AdminStorageItemsCacheData(items = items)
                    
                else:
                    
                    self.log.debug("No '%s' key or no items in cache" % storage_cache_id)
                    
            except Exception as e:
                
                self.log.error("Failed to decode cached storage data: %s" % str(e))
                
                await self.clear_cache(storage_cache_id)

        self.log.debug("No valid cache found, querying DB for %s" % storage_cache_id)

        query_results = await queries.select_all_storage_items()

        if len(query_results) > 0:
                
            raw_data = []

            for storage in query_results:
            
                for item in storage.materials:
                    
                    raw_data.append(MaterialData(
                        id = item.id,
                        storage_id = item.storage_id,
                        name = item.name,
                        manufacture_number = item.manufacture_number,
                        quantity = item.quantity,
                        unit = item.unit,
                        manufacture_date = item.manufacture_date,
                        price = item.price,
                        purchase_source = item.purchase_source,
                        purchase_date = item.purchase_date,
                        inspection_date = item.inspection_date,
                        uuid = item.uuid
                    ))

                for item in storage.tools:
                
                    raw_data.append(ToolsData(
                        id = item.id,
                        storage_id = item.storage_id,
                        name = item.name,
                        manufacture_number = item.manufacture_number,
                        quantity = item.quantity,
                        manufacture_date = item.manufacture_date,
                        price = item.price,
                        commissioning_date = item.commissioning_date,
                        purchase_source = item.purchase_source,
                        purchase_date = item.purchase_date,
                        inspection_date = item.inspection_date,
                        is_scrap = item.is_scrap,
                        returned = True if any(tenant.returned for tenant in item.tenant) is True else False,
                        uuid = item.uuid
                    ))
                  
                for item in storage.devices:
                    
                    raw_data.append(DeviceData(
                        id = item.id,
                        storage_id = item.storage_id,
                        name = item.name,
                        manufacture_number = item.manufacture_number,
                        quantity = item.quantity,
                        manufacture_date = item.manufacture_date,
                        price = item.price,
                        commissioning_date = item.commissioning_date,
                        purchase_source = item.purchase_source,
                        purchase_date = item.purchase_date,
                        inspection_date = item.inspection_date,
                        is_scrap = item.is_scrap,
                        returned = True if any(tenant.returned for tenant in item.tenant) is True else False,
                        uuid = item.uuid
                    ))
                   
            if isinstance(raw_data, list) and len(raw_data) > 0:
                
                wrapped = {
                    storage_cache_id: {
                        "items": [
                            {**item.model_dump(mode = "json"), "type": item.__class__.__name__} for item in raw_data
                        ]
                    }
                }
                
                async with self.admin_storage_lock:
                    await self.redis_client.set(key, json.dumps(wrapped, default = str), ex = exp)
                
                self.log.debug("Storage data cached for %s" % storage_cache_id)
                
            else:
                
                self.log.debug("Storage query returned empty list for %s - not caching" % storage_cache_id)

            return AdminStorageItemsCacheData(items = raw_data)
        
        elif query_results == []:
            
            self.log.info("No records found in the database")

    async def clear_cache(self, storage_cache_id: str):
        
        key = self._make_key(storage_cache_id)
        
        self.log.info("Clearing cache for key: %s" % key)
        
        async with self.admin_storage_lock:
            await self.redis_client.clear_cache(key)