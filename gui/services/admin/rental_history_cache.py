import asyncio
import json
import logging

from db.async_redis import AsyncRedisClient
from utils.dc.admin.rental_history import RentalHistoryData, RentalHistoryCacheData
from utils.dc.tenant_data import TenantData
from db import queries
from utils.logger import LoggerMixin

class RentalHistoryCacheService(LoggerMixin):
    
    log: logging.Logger
    
    KEY_PREFIX = "rental_history:"
    
    def __init__(self, 
        redis_client: AsyncRedisClient,
        rental_lock: asyncio.Lock
        ):
        
        self.redis_client = redis_client
        
        self.rental_lock = rental_lock

    def _make_key(self, rentals_cache_id: str) -> str:
        
        return f"{self.KEY_PREFIX}{rentals_cache_id}"

    async def get_rentals_from_cache(self, rentals_cache_id: str, exp: int) -> RentalHistoryCacheData:
        
        key = self._make_key(rentals_cache_id)
        
        self.log.info("Handling cache key with %s: %s" % (
            self.__class__.__name__, 
            key
            )
        )
        
        cached_data = await self.redis_client.get(key)

        if cached_data is not None:
            
            self.log.debug("Raw cached data for %s: %s" % (rentals_cache_id, self.redis_client.make_readable_cache_log(cached_data)))
            
            try:
                
                decoded = json.loads(cached_data)
                
                if rentals_cache_id in decoded and "items" in decoded[rentals_cache_id]:
                    
                    item_data = decoded[rentals_cache_id]["items"]
                    
                    return RentalHistoryCacheData(
                        items = [RentalHistoryData(
                            is_paid = entry["is_paid"],
                            tenant = TenantData(**entry["tenant"])
                        ) for entry in item_data]
                    )
                    
                else:
                    
                    self.log.debug("No '%s' key or no items in cache" % rentals_cache_id)
                    
            except Exception as e:
                
                self.log.error("Failed to decode cached rentals data: %s" % str(e))
                
                await self.clear_cache(rentals_cache_id)

        self.log.debug("No valid cache found, querying DB for %s" % rentals_cache_id)

        query_results = await queries.select_all_rental_history()

        if query_results is not None and len(query_results) > 0:
             
            raw_data = [
                RentalHistoryData(
                    is_paid = row.is_paid,
                    tenant = TenantData(
                        tenant_id = row.tenant.id,
                        item_type = row.tenant.item_type,
                        item_id = row.tenant.item_id,
                        item_name = (
                            row.tenant.tool.name if row.tenant.tool is not None 
                            else row.tenant.device.name if row.tenant.device is not None 
                            else None
                        ),                        
                        quantity = row.tenant.quantity,
                        tenant_name = row.tenant.tenant_name,
                        rental_start = row.tenant.rental_start,
                        rental_end = row.tenant.rental_end,
                        returned = row.tenant.returned,
                        rental_price = row.tenant.rental_price,
                        is_daily_price = row.tenant.is_daily_price
                    )
                ) for row in query_results
            ]

            if raw_data:
                
                wrapped = {
                    rentals_cache_id: {
                        "items": [item.model_dump(mode = "json") for item in raw_data]
                    }
                }
                
                async with self.rental_lock:
                    await self.redis_client.set(key, json.dumps(wrapped, default = str), ex = exp)
                
                self.log.debug("Calendar data cached for %s" % rentals_cache_id)
                
            else:
                
                self.log.debug("Rentals query returned empty list for %s - not caching" % rentals_cache_id)

            return RentalHistoryCacheData(items = raw_data)
        
        elif query_results == []:
            
            self.log.info("No records found in the database")

    async def clear_cache(self, rentals_cache_id: str):
        
        key = self._make_key(rentals_cache_id)
        
        self.log.info("Clearing cache for key: %s" % key)
        
        async with self.rental_lock:
            await self.redis_client.clear_cache(key)