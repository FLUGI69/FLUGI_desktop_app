# import typing as t

# from ..marine_traffic_client import MarineClientBase
# from utils.enums.ship_type_enum import ShipTypeEnum
# from utils.dc.marine_traffic.search_data import MarineTrafficData
# from config import Config

# class SearchBoatByName(MarineClientBase):
    
#     # api_key = Config.marine_traffic.search.api_key
    
#     prefix = "/shipsearch"  

#     async def get(self, ship_name: str, shiptype: t.Optional[ShipTypeEnum] = None) -> t.Any:
        
#         if shiptype is not None:
            
#             try:
        
#                 ship_type = self.map_shiptype_to_int(shiptype)

#                 self.log.debug("Filtering by shiptype: %s" % shiptype.upper())
            
#             except KeyError:
                
#                 self.log.error("Unknown shiptype: %s" % shiptype)
        
#         params: t.Dict[str, t.Any] = {
#             "shipname": ship_name,
#             "shiptype": ship_type,
#             "protocol": "json"
#         }

#         try:
            
#             return await self._request(params)
            
#         except Exception as e:
            
#             self.log.error("Search Failed: %s" % str(e))
            
#             raise
        
#     def parse_response(self, json_data: t.Any) -> list[MarineTrafficData]:
        
#         parsed_data = []

#         for idx, item in enumerate(json_data):
            
#             try:
         
#                 data = MarineTrafficData(
#                     ship_name = item[0],
#                     MMSI = int(item[1]) if item[1] else None,
#                     IMO = int(item[2]) if item[2] else None,
#                     ship_id = int(item[3]) if item[3] else None,
#                     callsign = item[4],
#                     type_name = item[5] or "",
#                     dwt = item[6] or "",
#                     flag = item[7] or "",
#                     country = item[8] or "",
#                     year_built = item[9] or "",
#                     url = item[10] or ""
#                 )
                
#                 parsed_data.append(data)
                
#             except Exception as e:
                
#                 self.log.warning("Failed to parse ship at index %d: %s" % (idx, str(e)))

#         return parsed_data
        
#     def map_shiptype_to_int(self, shiptype: str) -> int:
        
#         mapping: dict[str, int] = {
#             "FISHING": 2,
#             "HIGH_SPEED_CRAFT": 4,
#             "PASSENGER": 6,
#             "CARGO": 7,
#             "TANKER": 8,
#         }

#         return mapping[shiptype.upper()]