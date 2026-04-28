import asyncio
import json
import logging
from datetime import datetime
import time

from db.async_redis import AsyncRedisClient
from utils.dc.admin.storage_items import AdminStorageItemsCacheData
from utils.dc.material import MaterialData
from utils.dc.tools import ToolsData
from utils.dc.device import DeviceData
from db import queries
from utils.logger import LoggerMixin 
from config import Config

class AdminStorageItemsCacheService(LoggerMixin):
    
    log: logging.Logger
    
    KEY_PREFIX = "storage_items:"
    
    def __init__(self, 
        redis_client: AsyncRedisClient,
        admin_storage_lock: asyncio.Lock
        ):
        
        self.redis_client = redis_client
        
        self.admin_storage_lock = admin_storage_lock
             
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
        return Config.redis.cache.storage_items.execution_lock

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
                
                self.log.error("Failed to decode cached Admin Storage Items data: %s" % str(e))
                
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
                
                await self._handle_cache_race_condition(
                    method = "set",
                    key = key, 
                    data = wrapped,
                    exp = exp
                )
                
                self.log.debug("Admin Storage Items data cached for %s" % storage_cache_id)
                
            else:
                
                self.log.debug("Admin Storage Items query returned empty list for %s - not caching" % storage_cache_id)

            return AdminStorageItemsCacheData(items = raw_data)
        
        elif query_results == []:
            
            self.log.info("No records found in the database")
            
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
                    
                    self.log.info("Admin Storage Items cache worker stopped while waiting for lock")
                    
                    break
                
                elif acquired == True:
                    
                    try:
                        
                        async with self.admin_storage_lock:
                            
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
                        
                        self.log.exception("Exception during Admin Storage Items execution lock (lock key: '%s'): %s" % (
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
                    
                    self.log.info("Acquired Admin Storage Items execution lock (lock key: '%s') after wait -> Lock begin" % self._lock_key())
                    
                else:
                    
                    self.log.info("Acquired Admin Storage Items execution lock (lock key: '%s') -> Lock begin" % self._lock_key())
                
                return True
            
            elif acquired[0] == False:
                
                now = time.monotonic()
                
                if waited == False or now - last_log >= 5:
                    
                    current_holder = await self.redis_client.client.get(self._lock_key())
                    
                    self.log.debug("Waiting for Admin Storage Items execution lock (lock key: '%s') to be released, held by %s -> Lock wait" % (
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

    async def clear_cache(self, storage_cache_id: str):
        
        key = self._make_key(storage_cache_id)
        
        self.log.info("Clearing cache for key: %s" % key)
        
        await self._handle_cache_race_condition(
            method = "delete",
            key = key, 
            data = None,
            exp = None
        )