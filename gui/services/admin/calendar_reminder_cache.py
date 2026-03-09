import json
import logging

from db.async_redis import AsyncRedisClient
from utils.dc.admin.reminder import CalendarCacheData, CalendarData
from db import queries
from utils.logger import LoggerMixin

class CalendarReminderCacheService(LoggerMixin):
    
    log: logging.Logger
    
    def __init__(self, redis_client: AsyncRedisClient):
        
        self.redis_client = redis_client
    
    KEY_PREFIX = "reminders:"

    def _make_key(self, calendar_cache_id: str) -> str:
        
        return f"{self.KEY_PREFIX}{calendar_cache_id}"

    async def get_reminders_from_cache(self, calendar_cache_id: str, exp: int) -> CalendarCacheData:
        
        key = self._make_key(calendar_cache_id)
        
        self.log.info("Handling cache key with %s: %s" % (
            self.__class__.__name__, 
            key
            )
        )
        
        cached_data = await self.redis_client.get(key)

        if cached_data is not None:
            
            self.log.debug("Raw cached data for %s: %s" % (calendar_cache_id, self.redis_client.make_readable_cache_log(cached_data)))
            
            try:
                
                decoded = json.loads(cached_data)
                
                if calendar_cache_id in decoded and "items" in decoded[calendar_cache_id]:
                    
                    item_data = decoded[calendar_cache_id]["items"]
                    
                    return CalendarCacheData(
                        items = [CalendarData(**entry) for entry in item_data]
                    )
                    
                else:
                    
                    self.log.debug("No '%s' key or no items in cache" % calendar_cache_id)
                    
            except Exception as e:
                
                self.log.error("Failed to decode cached reminders data: %s" % str(e))
                
                await self.clear_cache(calendar_cache_id)

        self.log.debug("No valid cache found, querying DB for %s" % calendar_cache_id)

        query_results = await queries.select_reminders_data()

        if query_results is not None and len(query_results) > 0:
             
            raw_data = [
                CalendarData(
                    calendar_cache_id = calendar_cache_id,
                    id = row.id,
                    note = row.note,
                    date = row.reminder_date,
                    used = row.used
                )
                for row in query_results]

            if raw_data:

                wrapped = {
                    calendar_cache_id: {
                        "items": [item.model_dump(mode = "json") for item in raw_data]
                    }
                }
                
                await self.redis_client.set(key, json.dumps(wrapped, default = str), ex = exp)
                
                self.log.debug("Calendar data cached for %s" % calendar_cache_id)
                
            else:
                
                self.log.debug("Reminder query returned empty list for %s - not caching" % calendar_cache_id)

            return CalendarCacheData(items = raw_data)
        
        elif query_results == []:
            
            self.log.info("No records found in the database")

    async def clear_cache(self, calendar_cache_id: str):
        
        key = self._make_key(calendar_cache_id)
        
        self.log.info("Clearing cache for key: %s" % key)
        
        await self.redis_client.clear_cache(key)