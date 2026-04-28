import asyncio
from datetime import datetime
import json
import typing as t
import logging
import time

from db.async_redis import AsyncRedisClient
from utils.dc.marine_traffic.search_data import MarineTrafficData, MarineSearchCacheData
from utils.logger import LoggerMixin
from config import Config

class MarineTrafficCacheService(LoggerMixin):
    
    log: logging.Logger
        
    KEY_PREFIX = "marine_search:"
    
    def __init__(self, 
        redis_client: AsyncRedisClient,
        marine_traffic_lock: asyncio.Lock
        ):
        
        self.redis_client = redis_client
        
        self.marine_traffic_lock = marine_traffic_lock
        
        self._wake_event = asyncio.Event()
        
        self.interval = 5000 / 1000
        
        self._lock_token = None
        
        self._execution_locked = False
        
        self.__should_start_waiting = False
        
    @property
    def _should_start_waiting(self) -> bool:
        return self.__should_start_waiting is True
    
    @_should_start_waiting.setter
    def _should_start_waiting(self, value: bool):
        self.__should_start_waiting = value
        
    def _lock_key(self) -> str:
        return Config.redis.cache.marine_traffic.execution_lock
        
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
            
            await self._handle_cache_race_condition(
                method = "set",
                key = key, 
                data = wrapped,
                exp = exp
            )
            
            self.log.debug("MarineTrafficData cached for %s" % marine_cache_id)
            
        else:
            
            self.log.debug("MarineTrafficData returned empty list for %s - not caching" % marine_cache_id)

        return MarineSearchCacheData(items = raw_data)
    
    async def _handle_cache_race_condition(self, 
        method: str, 
        key: str, 
        data: dict | None = None,
        exp: int | None = None
        ):
        
        self.__should_start_waiting = True
        
        try:
            
            while self._should_start_waiting == True:
                
                acquired = await self._wait_for_lock_or_acquire()
 
                if acquired == False:
                    
                    self.log.info("Marine Traffic cache worker stopped while waiting for lock")
                    
                    break
                
                elif acquired == True:
                    
                    try:
                        
                        async with self.marine_traffic_lock:
                            
                            if method == "set":
                                
                                await self.redis_client.set(key, json.dumps(data, default = str), ex = exp)
                                
                                if self._lock_token is not None:
                                    await self.redis_client.release_execution_lock(
                                        lock_key = self._lock_key(),
                                        token = self._lock_token
                                    )
                                
                                self.__should_start_waiting = False
                                self._lock_token = None
                                self._execution_locked = False
                                self._wake_event.set()   
                                
                            elif method == "delete":

                                await self.redis_client.clear_cache(key)
                                
                                if self._lock_token is not None:
                                    await self.redis_client.release_execution_lock(
                                        lock_key = self._lock_key(),
                                        token = self._lock_token
                                    )
                                
                                self.__should_start_waiting = False
                                self._lock_token = None
                                self._execution_locked = False
                                self._wake_event.set()   

                    except Exception as e:
                        
                        self.log.exception("Exception during Marine Traffic execution lock (lock key: '%s'): %s" % (
                            self._lock_key(),
                            str(e)
                        ))
                        raise

        except asyncio.CancelledError:
            raise
        
        finally:
            
            if self.__should_start_waiting == True:
                self.__should_start_waiting = False
            
            if self._lock_token is not None:
                self._lock_token = None
            
            if self._execution_locked == True:
                self._execution_locked = False
            
            if self._wake_event.is_set() == False:
                self._wake_event.set()    

    async def _wait_for_lock_or_acquire(self) -> bool:
        
        waited = False
        last_log = time.monotonic()
        
        while self._should_start_waiting == True:
            
            acquired = await self.redis_client.try_acquire_execution_lock(
                lock_key = self._lock_key()
            )

            if acquired[0] == True:
                
                self._lock_token = acquired[1]
                self._execution_locked = True
                
                if waited == True:
                    
                    self.log.info("Acquired Marine Traffic execution lock (lock key: '%s') after wait -> Lock begin" % self._lock_key())
                    
                else:
                    
                    self.log.info("Acquired Marine Traffic execution lock (lock key: '%s') -> Lock begin" % self._lock_key())
                
                return True
            
            elif acquired[0] == False:
            
                now = time.monotonic()
                
                if waited == False or now - last_log >= 5:
                    
                    current_holder = await self.redis_client.client.get(self._lock_key())
                    
                    self.log.debug("Waiting for Marine Traffic execution lock (lock key: '%s') to be released, held by %s -> Lock wait" % (
                        self._lock_key(),
                        current_holder.decode("utf-8") if isinstance(current_holder, bytes) else str(current_holder)
                    ))
                    
                    last_log = now
                    waited = True
                
                self._wake_event.clear()
                
                try:
                    
                    await asyncio.wait_for(self._wake_event.wait(), timeout = 5)
                    
                except asyncio.TimeoutError:
                    pass

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
        
        await self._handle_cache_race_condition(
            method = "delete",
            key = key, 
            data = None,
            exp = None
        )