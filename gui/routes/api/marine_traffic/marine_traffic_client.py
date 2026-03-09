# from abc import ABC, abstractmethod
# from pydantic import BaseModel
# import httpx
# import typing as t
# import logging

# from config import Config
# from utils.logger import LoggerMixin

# class MarineClientBase(ABC, LoggerMixin):
    
#     log: logging.Logger
    
#     # base_url = Config.marine_traffic.base_url
    
#     api_key: str

#     prefix: str  

#     def __init__(self):
        
#         self.client = httpx.AsyncClient()

#     async def _request(self,
#         params: t.Optional[t.Dict[str, t.Any]] = None
#         ) -> t.Type['get_response_body']:
        
#         self.log.debug("START -> MarineClient request")
        
#         params = params or {}

#         self.log.debug("Request params: %s" % str(params))
        
#         url = f"{self.base_url}{self.prefix}/{self.api_key}"
        
#         self.log.debug("Request URL: %s" % str(url))

#         try:
            
#             async with httpx.AsyncClient() as client:
                
#                 response = await client.get(url, params = params)
             
#                 response.raise_for_status()
                
#                 response_json = response.json()
                
#                 self.log.debug("Response json: %s" % response_json)
                
#                 if isinstance(response_json, dict):
                    
#                     parsed_data = self.parse_response(list(response_json.values()))
                
#                 elif isinstance(response_json, list):
                   
#                     parsed_data = self.parse_response(response_json)
               
#                 else:
                    
#                     raise ValueError("Unexpected response format: expected a list or dict")

#                 result = get_response_body(
#                     status= response.status_code,
#                     data = parsed_data,
#                     error = ""
#                 )

#                 self.log.debug("GET response body: %s" % str(result))
                
#                 return result

#         except httpx.HTTPStatusError as http_err:
            
#             self.log.error("HTTP error occurred: %s" % str(http_err))
            
#             return get_response_body(
#                 status = response.status_code,
#                 data = [], 
#                 error = str(http_err)
#             )

#         except Exception as e:
            
#             self.log.exception("MarineClient request failed:")
            
#             return get_response_body(
#                 status = response.status_code, 
#                 data = [], 
#                 error = str(e)
#             )

#         finally:
            
#             self.log.debug("END -> MarineClient request")

#     @abstractmethod
#     async def get(self, *args, **kwargs) -> t.Any:
#         pass
    
#     @abstractmethod
#     def parse_response(self, json_data: t.Any) -> t.Any:
#         pass
    
# class get_response_body(BaseModel):
#     status: int  
#     data: t.Optional[t.Any] = None
#     error: t.Optional[str] = None