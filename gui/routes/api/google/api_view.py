from abc import ABC
import logging
import asyncio
import inspect
import typing as t
from functools import partial

from googleapiclient.http import BatchHttpRequest
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

from .decorator import RuleDecorator
from utils.logger import LoggerMixin
from utils.dc.batch_request import BatchRequestData
from utils.handlers.batch_request import BatchCallbackHandler
from config import Config

class GmailApiView(ABC, LoggerMixin):
    
    endpoint: str = ""
    
    user_id: str
    
    creds: Credentials
    
    log: logging.Logger
    
    _executor = None

    def __init__(self, 
        user_id: str, 
        creds: Credentials
        ) -> None:
        
        self.user_id = user_id
        
        self.creds = creds
        
        self._executor = asyncio.get_running_loop().run_in_executor

    @staticmethod
    def rule(endpoint: str, method: str) -> t.Callable:
        
        return RuleDecorator(endpoint = endpoint, method = method)

    async def user_authenticate(self):
        
        if not isinstance(self.creds, Credentials):
            
            raise TypeError("Provided credentials are not a valid Credentials instance")
        
        if not self.creds.valid:
            
            raise RuntimeError("Invalid or expired credentials for user '%s'" % self.user_id)

    async def _run_blocking(self, func: t.Callable, *args, **kwargs):
        
        loop = asyncio.get_running_loop()
        
        return await loop.run_in_executor(None, partial(func, *args, **kwargs))

    async def execute(self, **kwargs) -> t.Any:
        
        method_name = getattr(self, "method_name_override", None)

        self.log.debug("Executing execute with method_name = '%s', endpoint = '%s', kwargs = %s" % (
            method_name,
            self.endpoint,
            str(kwargs)
            )
        )

        if not isinstance(self.endpoint, str) or not self.endpoint.strip():
            
            self.log.error("Missing or invalid endpoint in GmailApiView for method '%s'" % method_name)
            
            raise ValueError("No endpoint set. Use @rule(...) decorator to define the endpoint")

        try:
            
            svc = await self._run_blocking(
                build,
                Config.google.api_name,
                Config.google.api_version,
                credentials = self.creds,
                cache_discovery = False
            )
            
        except Exception as e:
            
            self.log.error("Failed to build Gmail API service: %s" % str(e))
            
            raise RuntimeError("Failed to initialize Gmail service") from e

        try:
            
            endpoint_resource = getattr(svc.users(), self.endpoint)
            
        except AttributeError as e:
            
            self.log.error("Endpoint '%s' does not exist on Gmail users resource: %s" % (self.endpoint, str(e)))
            
            raise AttributeError("Invalid Gmail API endpoint: '%s'" % self.endpoint) from e

        if method_name is not None:
            
            try:
                
                resource = endpoint_resource()
                
            except TypeError:
                
                resource = endpoint_resource

            try:
                
                method = getattr(resource, method_name)
                
            except AttributeError as e:
                
                self.log.error("Method '%s' not found on resource '%s': %s" % (method_name, self.endpoint, str(e)))
                
                raise AttributeError("Method '%s' not found on endpoint '%s'" % (method_name, self.endpoint)) from e

            if not callable(method):
                
                uri = f"/gmail/v1/users/{self.user_id}/{self.endpoint}/{method_name}"
                
                self.log.error("Method '%s' not callable on Gmail API endpoint '%s'. Tried URI: %s" % (
                    method_name, self.endpoint, uri
                    )
                )
                
                raise AttributeError("Method '%s' not callable on endpoint '%s'. Check URI: %s" % (
                    method_name, 
                    self.endpoint,
                    uri
                    )
                )

            try:

                return await self._run_blocking(method(userId = self.user_id, **kwargs).execute)
         
            except Exception as e:
                
                self.log.error("Error executing Gmail API method '%s' on endpoint '%s': %s" % (
                    method_name, 
                    self.endpoint, 
                    str(e)
                    )
                )
                
                raise RuntimeError("Failed to execute Gmail API method") from e

        elif method_name is None:
            
            if not callable(endpoint_resource):
                
                self.log.error("Endpoint '%s' is not callable and no method provided." % self.endpoint)
                
                raise AttributeError("Endpoint '%s' is not callable and no method provided." % self.endpoint)

            try:

                return await self._run_blocking(endpoint_resource(userId = self.user_id, **kwargs).execute)

            except Exception as e:
                
                self.log.error("Error executing Gmail API endpoint '%s': %s" % (self.endpoint, str(e)))
                
                raise RuntimeError("Failed to execute Gmail API endpoint") from e
            
    def _execute_batch(self, batch, svc, future, loop):
        
        try:
            
            batch.execute(http = svc._http)
            
            loop.call_soon_threadsafe(future.set_result, None)
            
        except Exception as e:
            
            self.log.error("Batch execution failed: %s" % str(e))
            
            loop.call_soon_threadsafe(future.set_exception, e)

    async def execute_batch(self,
        requests: list[BatchRequestData],
        ) -> list:

        svc = await self._run_blocking(
            build,
            Config.google.api_name,
            Config.google.api_version,
            credentials = self.creds,
            cache_discovery = False,
        )

        loop = asyncio.get_running_loop()
        
        future = loop.create_future()

        callback_handler = BatchCallbackHandler()

        batch = BatchHttpRequest(batch_uri = Config.google.batch_uri)

        endpoint_resource = getattr(svc.users(), self.endpoint)
        
        resource = endpoint_resource()

        for item in requests:
            
            try:
                
                method = getattr(resource, item.method_name)
                
                batch.add(
                    method(userId = self.user_id, **item.params),
                    callback = callback_handler.handle
                )
                
            except Exception as e:
                
                self.log.error("Failed to add batch request %s with params %s: %s" % (item.method_name, str(item.params), str(e)))
                
                callback_handler.results.append(None)

        loop.run_in_executor(None, self._execute_batch, batch, svc, future, loop)
        
        await future

        return callback_handler.results

    def parse_response(self, raw: dict) -> t.Any:
        pass
    
    