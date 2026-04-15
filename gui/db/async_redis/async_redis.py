import asyncio
import base64
from datetime import datetime
import uuid
from redis.asyncio import Redis, ConnectionPool
from redis.exceptions import ConnectionError as RedisConnectionError
import json
import socket
import os
import typing as t
import types
import logging
import time

from utils.logger import LoggerMixin
from ..network.connections import SSHTunnelConnections, SSHTunnelConnection
from ..network.reconnect_service import SSHTunnelReconnectService
from ..network.sshtunnel import SSHTunnel
from .async_redis_callback import AsyncRedisCallback
from websocket.ws_client import QtApplicationSocketClient
from config import Config

class AsyncRedisClient(LoggerMixin):
    
    log: logging.Logger
    
    def __init__(self) -> None:
        
        self.callback = AsyncRedisCallback(self)
    
        self.websocket_client: QtApplicationSocketClient = None
        
        self.client = None
        
        self.ssh_tunnel = None
        
        self.ssh_tunnel_reconnect_service = None
        
        self.host = None
        
        self.port = None
        
        self.db = None
        
        self.password = None
        
    def _make_lock_token(self) -> str:
        return "%s:%s:%s" % (socket.gethostname(), os.getpid(), uuid.uuid4().hex)
    
    async def _release_owned_lock(self, lock_key: str, token: str) -> bool:
        
        result = await self.client.eval(
            Config.redis.cache.lock_release_script,
            1,
            lock_key,
            token
        )
        
        return result == 1
        
    def encode_for_cache(self, value: t.Any) -> t.Any:
        """
        Recursively encode bytes values for JSON caching.
        
        - bytes -> "B64:<base64 string>"
        - dict -> encode each value
        - list/tuple -> encode each element
        - other types -> returned as-is
        """
        if isinstance(value, bytes):
            
            return "B64:" + base64.b64encode(value).decode("utf-8")
        
        if isinstance(value, dict):
            
            return {k: self.encode_for_cache(v) for k, v in value.items()}
        
        if isinstance(value, list):
            
            return [self.encode_for_cache(v) for v in value]
        
        if isinstance(value, tuple):
            
            return tuple(self.encode_for_cache(v) for v in value)
        
        return value

    def decode_from_cache(self, value: t.Any) -> t.Any:
        """
        Recursively decode values from JSON cache.
        
        - "B64:<base64 string>" -> bytes
        - dict -> decode each value
        - list/tuple -> decode each element
        - other types -> returned as-is
        """
        if isinstance(value, str) and value.startswith("B64:"):
            
            return base64.b64decode(value[4:])
        
        if isinstance(value, dict):
            
            return {k: self.decode_from_cache(v) for k, v in value.items()}
        
        if isinstance(value, list):
            
            return [self.decode_from_cache(v) for v in value]
        
        if isinstance(value, tuple):
            
            return tuple(self.decode_from_cache(v) for v in value)
        
        return value
    
    def make_readable_cache_log(self, cached_data, max_len: int = 30, max_items: int = 10) -> str:
        
        if cached_data is not None:

            if isinstance(cached_data, bytes):
                
                try:
                    
                    decoded = cached_data.decode("utf-8")
                    
                except UnicodeDecodeError:
                    
                    escaped = repr(cached_data)
                    
                    return escaped[:max_len] + "..." if len(escaped) > max_len else escaped
                
            elif isinstance(cached_data, str):
                
                decoded = cached_data
                
            else:
        
                return repr(cached_data)[:max_len] + "..."

            try:
                
                data = json.loads(decoded)
                
            except json.JSONDecodeError:
                
                return decoded[:max_len] + "..." if len(decoded) > max_len else decoded

            if isinstance(data, dict):
                
                for value in data.values():
                    
                    if isinstance(value, dict) and "items" in value and isinstance(value["items"], list):
                        
                        total_items = len(value["items"])
                        
                        value["items"] = value["items"][:max_items]
                        
                        for item in value["items"]:
                            
                            if isinstance(item, dict):
                                
                                for key, val in item.items():
                                    
                                    if isinstance(val, str) and len(val) > max_len:
                                        
                                        bval = val.encode("utf-8")
                                        
                                        bin_str = ''.join(f'{b:08b}' for b in bval)
                                        
                                        item[key] = bin_str[:max_len] + "..." if len(bin_str) > max_len else bin_str
                        
                        value["total_count"] = total_items

            return json.dumps(data, ensure_ascii = False)

        else:
            
            return "None"
        
    async def is_ready(self) -> bool:
        
        if not self.client:
            
            return False
        
        try:
            
            return await self.client.ping()
        
        except Exception as e:
            
            self.log.exception("Ping failed, client not ready %s" % str(e))
            
            return False

    async def setup_redis(self,
        host: str = None,
        port: int = None,
        db: int = None,
        password: str = None,
        sshtunnel_host: str = None,
        sshtunnel_port: int = None,
        sshtunnel_user: str = None,
        sshtunnel_pass: str = None,
        sshtunnel_private_key_path: str = None
        ):

        if sshtunnel_host is not None and sshtunnel_port is not None:
            
            db_host = "127.0.0.1"

            self.ssh_tunnel = SSHTunnel(
                name = "Redis-SSH",
                ssh_host = sshtunnel_host,
                ssh_port = sshtunnel_port,
                ssh_user = sshtunnel_user,
                ssh_pass = sshtunnel_pass,
                ssh_private_key_ppk_path = sshtunnel_private_key_path,
                sql_hostname = host,
                sql_port = port,
            )

            self.ssh_tunnel_reconnect_service = SSHTunnelReconnectService(tunnel = self.ssh_tunnel)

            SSHTunnelConnections.add_connection(SSHTunnelConnection(ssh_tunnel = self.ssh_tunnel))
            
            self.ssh_tunnel_reconnect_service.start()

            host = db_host
            
            port = self.ssh_tunnel_reconnect_service.local_bind_port

            self.log.debug("Redis SSH-tunnel -> Host: %s, Port: %s" % (host, port))
            
        else:
            
            self.log.debug("Redis direct -> Host: %s, Port: %s" % (host, port))

        await self._connect(
            host = host,
            port = port,
            db = db,
            password = password
        )
    
    async def _connect(self,
        host: str,
        port: int,
        db: int,
        password: str | None
        ):

        self.host = host
        self.port = port
        self.db = db
        self.password = password
        
        self.client = Redis(
            connection_pool = ConnectionPool(
                host = host,
                port = port,
                db = db,
                password = password,
                max_connections = 10,
                decode_responses = False
            )
        )

        try:
            
            ping = await self.client.ping()
            
            self.log.info("Redis client connection %s" % ("successful" if ping is True else "returned unexpected response: %s" % str(ping)))
            
        except Exception as e:
            
            self.log.error("Failed to connect to Redis: %s" % str(e))
            
            self.client = None
            
    async def reconnect(self):
        
        self.log.info("Reconnecting Redis client...")

        if self.client is not None:
            
            try:
                
                await self.client.close()
                
            except Exception as e:
                
                self.log.warning("Error while closing Redis client: %s" % str(e))

        await self._connect(            
            host = self.host,
            port = self.port,
            db = self.db,
            password = self.password
        )

    async def get(self, key, retries = 3, delay = 2):
        
        return await self._with_retry("get", key, retries = retries, delay = delay)

    async def set(self, key, value, ex = None, retries = 3, delay = 2):
        
        result = await self._with_retry("set", key, value, ex = ex, retries = retries, delay = delay)
        
        if result is not False and self.websocket_client is not None:
            
            redis_event = await self.callback(key, ex)
            
            await self.websocket_client.redis_refresh(redis_event)
        
        return result

    async def clear_cache(self, key, retries = 3, delay = 2):
        
        return await self._with_retry("delete", key, retries = retries, delay = delay)

    async def close(self):
        
        if not self.client:
            
            raise RuntimeError("Redis client is not initialized")
            
        if self.client is not None:
            
            await self.client.close()
    
    async def _with_retry(self, 
        method_name, 
        *args, 
        retries = 3, 
        delay = 1, 
        **kwargs
        ):
        
        if not self.client:
            
            raise RuntimeError("Redis client is not initialized")

        for attempt in range(1, retries + 2):
            
            try:
                
                method = getattr(self.client, method_name)
                
                if isinstance(method, types.MethodType):
                    
                    self.log.debug("Redis '%s' attempt %s with args = %s, kwargs = %s" % (
                        method_name, 
                        str(attempt), 
                        str(self.make_readable_cache_log(args)), 
                        str(kwargs)
                        )
                    )
                    
                    function_name = method.__name__
                    
                    if function_name in ["set", "delete"]:
   
                        lock_key = f"lock:{args[0]}"
                        lock_token = self._make_lock_token()
    
                        last_log = time.monotonic()
                        first_wait = True

                        while True:
                            
                            lock_acquired = await self.client.set(
                                lock_key, 
                                lock_token, 
                                ex = 10, 
                                nx = True
                            )
                                                        
                            if lock_acquired == True:
                                
                                self.log.debug("Acquired lock for key %s (lock key: '%s') performing %s operation -> Lock begin" % (
                                    str(self.make_readable_cache_log(args)), 
                                    lock_key,
                                    function_name
                                ))
                                
                                try: 
                                    
                                    filtered_kwargs = dict(kwargs)
                                    
                                    if function_name == "set" and "nx" in filtered_kwargs:
                                        filtered_kwargs["nx"] = True
                                        
                                    else:
                                        filtered_kwargs.pop("nx", None)
                                    
                                    return await method(*args, **filtered_kwargs)
                                
                                except Exception as e:
                                    
                                    self.log.exception("Exception in handle_racing_condition: %s" % str(e))
                                    raise
                                
                                finally:
                                    
                                    released = await self._release_owned_lock(
                                        lock_key, lock_token
                                    )
 
                                    self.log.info("Released lock for key %s (lock key: '%s' released=%s) -> Lock end" % (
                                        str(self.make_readable_cache_log(args)), 
                                        lock_key,
                                        str(released)
                                    ))
                                    
                            else:
                                
                                now = time.monotonic()
                                
                                if first_wait == True or now - last_log >= 5:
                                    
                                    self.log.debug("Waiting for lock on key %s (lock key: '%s') to be released -> Lock wait" % (
                                        str(self.make_readable_cache_log(args)), 
                                        lock_key
                                    ))
                                    
                                    last_log = now
                                    first_wait = False
                                
                                await asyncio.sleep(0.1)

                    else:     
                           
                        return await method(*args, **kwargs)

            except (RedisConnectionError, ConnectionResetError) as e:
                
                self.log.warning("Redis '%s' failed on attempt %s: %s" % (
                    method_name, 
                    str(attempt),
                    str(e)
                    )
                )

                if attempt == retries + 1:
                    
                    self.log.error("Redis '%s' permanently failed after %s retries" % (
                        method_name, str(retries)
                    ))
                    
                    raise

                await self.reconnect()
                
                backoff = min(delay * (2 ** (attempt - 1)), 30)
                
                await asyncio.sleep(backoff)

            except Exception as e:
                
                self.log.error("Unexpected Redis error in '%s': %s" % (
                    method_name, 
                    str(e)
                    )
                )
                
                raise
            
    def serialize_datetimes(self, obj):
        
        if isinstance(obj, dict):
            
            return {k: self.serialize_datetimes(v) for k, v in obj.items()}
        
        elif isinstance(obj, list):
            
            return [self.serialize_datetimes(i) for i in obj]
        
        elif isinstance(obj, datetime):
            
            return obj.isoformat()
        
        return obj