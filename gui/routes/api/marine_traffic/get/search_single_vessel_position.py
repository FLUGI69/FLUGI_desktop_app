# import typing as t
# from datetime import datetime

# from ..marine_traffic_client import MarineClientBase
# from utils.dc.marine_traffic.single_vessel_data import MarineTrafficSingleVesselData
# from config import Config

# class SearchSingleVesselByID(MarineClientBase):
    
#     # api_key = Config.marine_traffic.vessel_tracking.api_key
    
#     prefix = "/exportvessel"  

#     async def get(self, ship_id: int, version: int, timespan: int) -> t.Any:
        
#         params: t.Dict[str, t.Any] = {
#             "v": version,
#             "shipid": ship_id,
#             "timespan": timespan,
#             "protocol": "jsono"
#         }

#         try:
            
#             return await self._request(params)
            
#         except Exception as e:
            
#             self.log.error("Search Failed: %s" % str(e))
            
#             raise
        
#     def parse_response(self, json_data: t.Any) -> list[MarineTrafficSingleVesselData]:

#         parsed_data = []

#         for idx, item in enumerate(json_data):
            
#             try:
                
#                 data = MarineTrafficSingleVesselData(
#                     ship_name = None,
#                     mmsi = int(item["MMSI"]) if item.get("MMSI") and item["MMSI"] != "0" else None,
#                     imo = int(item["IMO"]) if item.get("IMO") and item["IMO"] != "0" else None,
#                     ship_id = int(item["SHIP_ID"]) if item.get("SHIP_ID") else None,
#                     lat = float(item["LAT"]) if item.get("LAT") else None,
#                     lon = float(item["LON"]) if item.get("LON") else None,
#                     speed = float(item["SPEED"]) if item.get("SPEED") else None,
#                     heading = int(item["HEADING"]) if item.get("HEADING") and item["HEADING"] != "511" else None,
#                     course = float(item["COURSE"]) if item.get("COURSE") else None,
#                     status = int(item["STATUS"]) if item.get("STATUS") else None,
#                     timestamp = datetime.fromisoformat(item["TIMESTAMP"].replace("Z", "+00:00")) if item.get("TIMESTAMP") else None,
#                     dsrc = item.get("DSRC"),
#                     utc_seconds = int(item["UTC_SECONDS"]) if item.get("UTC_SECONDS") else None,
#                 )
                
#                 parsed_data.append(data)
                
#             except Exception as e:
                
#                 self.log.warning("Failed to parse ship at index %d: %s" % (idx, str(e)))

#         return parsed_data
