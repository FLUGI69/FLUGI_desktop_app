import requests
import logging
import typing as t

from config import Config
from utils.logger import LoggerMixin

class GeocodingAPI(LoggerMixin):
    
    log: logging.Logger

    def reverse_geocode(self, lat: float, lon: float) -> t.Optional[str]:
        
        address = self._get_nominatim_address(lat, lon)
        
        if address is None:
            
            return None
        
        parts = []
        
        country = address.get("country")
        
        county = address.get("county")
        
        settlement = None
        
        for field in Config.marine_traffic.geocoding.nominatim_address_fields:
            
            value = address.get(field)
            
            if value is not None:
                
                settlement = value
                
                break
        
        if country is not None:
            
            parts.append(country)
        
        if county is not None:
            
            parts.append(county)
        
        if settlement is not None:
            
            parts.append(settlement)
        
        if len(parts) > 0:
            
            result = " - ".join(parts)
            
            self.log.debug("Geocode result for (%.5f, %.5f): %s" % (lat, lon, result))
            
            return result
        
        return None

    def _get_nominatim_address(self, lat: float, lon: float) -> t.Optional[dict]:
        
        try:
            
            response = requests.get(
                Config.marine_traffic.geocoding.nominatim_url,
                params = {
                    "lat": lat,
                    "lon": lon,
                    "format": "json",
                    "zoom": 10,
                    "addressdetails": 1
                },
                headers = {
                    "User-Agent": "FlugiCompanyApp/1.0"
                },
                timeout = 3
            )
            
            if response.status_code == 200:
                
                return response.json().get("address")
            
        except Exception as e:
            
            self.log.warning("Nominatim request failed: %s" % str(e))
        
        return None
