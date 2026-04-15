import asyncio
import json
import logging

from db.async_redis import AsyncRedisClient
from utils.dc.admin.fleet import FleetData, FleetCacheData
from db import queries
from utils.logger import LoggerMixin

class FleetCacheService(LoggerMixin):
    
    log: logging.Logger
    
    KEY_PREFIX = "fleet:"
    
    def __init__(self, 
        redis_client: AsyncRedisClient,
        fleet_lock: asyncio.Lock
        ):
        
        self.redis_client = redis_client
        
        self.fleet_lock = fleet_lock

    def _make_key(self, fleet_cache_id: str) -> str:
        
        return f"{self.KEY_PREFIX}{fleet_cache_id}"

    async def get_fleet_from_cache(self, fleet_cache_id: str, exp: int) -> FleetCacheData:
        
        key = self._make_key(fleet_cache_id)
        
        self.log.info("Handling cache key with %s: %s" % (
            self.__class__.__name__, 
            key
            )
        )
        
        cached_data = await self.redis_client.get(key)

        if cached_data is not None:
            
            self.log.debug("Raw cached data for %s: %s" % (fleet_cache_id, self.redis_client.make_readable_cache_log(cached_data)))
            
            try:
                
                decoded = json.loads(cached_data)
                
                if fleet_cache_id in decoded and "items" in decoded[fleet_cache_id]:
                    
                    item_data = decoded[fleet_cache_id]["items"]
                    
                    return FleetCacheData(
                        items = [FleetData(**entry) for entry in item_data]
                    )
                    
                else:
                    
                    self.log.debug("No '%s' key or no items in cache" % fleet_cache_id)
                    
            except Exception as e:
                
                self.log.error("Failed to decode cached fleet data: %s" % str(e))
                
                await self.clear_cache(fleet_cache_id)

        self.log.debug("No valid cache found, querying DB for %s" % fleet_cache_id)

        query_results = await queries.select_fleet()

        if query_results is not None and len(query_results) > 0:
             
            raw_data = [
                FleetData(
                    id = row[0].id,
                    flag = row[0].flag,
                    name = row[0].name,
                    ship_id = row[0].ship_id,
                    imo = row[0].imo,
                    mmsi = row[0].mmsi,
                    callsign = row[0].callsign,
                    type_name = row[0].type_name,
                    view_on_map_href = row[0].view_on_map_href,
                    more_deatails_href = row[0].more_deatails_href,
                    works = row[1]
                ) for row in query_results
            ]

            if raw_data:
                
                wrapped = {
                    fleet_cache_id: {
                        "items": [item.model_dump(mode = "json") for item in raw_data]
                    }
                }
                
                async with self.fleet_lock:
                    await self.redis_client.set(key, json.dumps(wrapped, default = str), ex = exp)
                
                self.log.debug("Fleet data cached for %s" % fleet_cache_id)
                
            else:
                
                self.log.debug("Fleet query returned empty list for %s - not caching" % fleet_cache_id)

            return FleetCacheData(items = raw_data)
        
        elif query_results == []:
            
            self.log.info("No records found in the database")

    async def clear_cache(self, fleet_cache_id: str):
        
        key = self._make_key(fleet_cache_id)
        
        self.log.info("Clearing cache for key: %s" % key)
        
        async with self.fleet_lock:
            await self.redis_client.clear_cache(key)