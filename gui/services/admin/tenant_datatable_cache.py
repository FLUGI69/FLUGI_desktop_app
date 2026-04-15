import asyncio
import json
import logging

from db.async_redis import AsyncRedisClient
from utils.dc.admin.tenant_items import AdminTenantsCacheData
from utils.dc.tenant_data import TenantData
from db import queries
from utils.logger import LoggerMixin 

class AdminTenantsCacheService(LoggerMixin):
    
    log: logging.Logger
    
    KEY_PREFIX = "tenant_items:"
    
    def __init__(self, 
        redis_client: AsyncRedisClient, 
        rental_lock: asyncio.Lock
        ):
        
        self.redis_client = redis_client
        
        self.rental_lock = rental_lock

    def _make_key(self, tenant_cache_id: str) -> str:
        
        return f"{self.KEY_PREFIX}{tenant_cache_id}"

    async def get_tenant_datatable_data_from_cache(self, tenant_cache_id: str, exp: int) -> AdminTenantsCacheData:
        
        key = self._make_key(tenant_cache_id)
        
        self.log.info("Handling cache key with %s: %s" % (
            self.__class__.__name__, 
            key
            )
        )
        
        cached_data = await self.redis_client.get(key)

        if cached_data is not None:
            
            self.log.debug("Raw cached data for %s: %s" % (tenant_cache_id, self.redis_client.make_readable_cache_log(cached_data)))
            
            try:
                
                decoded = json.loads(cached_data)
                
                if tenant_cache_id in decoded and "items" in decoded[tenant_cache_id]:
                    
                    item_data = decoded[tenant_cache_id]["items"]
                    
                    return AdminTenantsCacheData(
                        items = [TenantData(**entry) for entry in item_data]
                    )
                    
                else:
                    
                    self.log.debug("No '%s' key or no items in cache" % tenant_cache_id)
                       
            except Exception as e:
                
                self.log.error("Failed to decode cached storage data: %s" % str(e))
                
                await self.clear_cache(tenant_cache_id)

        self.log.debug("No valid cache found, querying DB for %s" % tenant_cache_id)

        query_results = await queries.select_all_tenant()

        if len(query_results) > 0:
                
            raw_data = [
                TenantData(
                    tenant_id = row.id,
                    item_type = row.item_type,
                    item_id = row.item_id,
                    item_name = (row.tool.name if row.tool else row.device.name if row.device else "N/A"),
                    quantity = row.quantity,
                    tenant_name = row.tenant_name,
                    rental_start = row.rental_start,
                    rental_end = row.rental_end,
                    returned = row.returned,
                    rental_price = row.rental_price,
                    is_daily_price = row.is_daily_price
                ) for row in query_results if row.tool or row.device]
        
            if isinstance(raw_data, list) and len(raw_data) > 0:
                
                wrapped = {
                    tenant_cache_id: {
                        "items": [
                            {**item.model_dump(mode = "json"), "type": item.__class__.__name__} for item in raw_data
                        ]
                    }
                }
                
                async with self.rental_lock:
                    await self.redis_client.set(key, json.dumps(wrapped, default = str), ex = exp)
                
                self.log.debug("Tenant data cached for %s" % tenant_cache_id)
                
            else:
                
                self.log.debug("Tenant query returned empty list for %s - not caching" % tenant_cache_id)

            return AdminTenantsCacheData(items = raw_data)
        
        elif query_results == []:
            
            self.log.info("No records found in the database")

    async def clear_cache(self, tenant_cache_id: str):
        
        key = self._make_key(tenant_cache_id)
        
        self.log.info("Clearing cache for key: %s" % key)
        
        async with self.rental_lock:
            await self.redis_client.clear_cache(key)