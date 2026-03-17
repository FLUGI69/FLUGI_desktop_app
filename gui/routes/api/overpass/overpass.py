import requests
import logging
import typing as t

from config import Config
from utils.logger import LoggerMixin
from utils.dc.marine_traffic.harbor import Harbor

if t.TYPE_CHECKING:
    
    from async_loop import QtApplication
    
class OverpassAPI(LoggerMixin):
    
    log: logging.Logger
    
    def __init__(self,
        app: 'QtApplication'
        ):
        
        self.utility_calculator = app.utility_calculator

    def get_nearest_harbor(self, lat: float, lon: float) -> t.Tuple[Harbor | None, float | None, str | None]:
        """
        Finds the nearest harbor to the given latitude and longitude, and calculates the distance 
        to the nearest harbor with a name.

        Pricegs:
            lat (float): Latitude of the reference point.
            lon (float): Longitude of the reference point.

        Returns:
            Tuple | 
            None:
                - nearest_harbor (Harbor | None): The closest harbor (even if it has no name).
                - distance_km (float | None): Distance in kilometers from nearest_harbor to the closest named harbor.
                - nearest_named_name (str | None): Name of the nearest harbor that has a name.
            Returns (None, None, None) if no harbors are found or an error occurs.
        """
        delta = Config.marine_traffic.overpass.delta

        bbox = f"{lat - delta},{lon - delta},{lat + delta},{lon + delta}"
        
        query_params = f"""
        [out:json][timeout:25];
        (
        node["harbour"]({bbox});
        way["harbour"]({bbox});
        relation["harbour"]({bbox});

        node["amenity"="marina"]({bbox});
        way["amenity"="marina"]({bbox});
        relation["amenity"="marina"]({bbox});

        node["man_made"="pier"]({bbox});
        way["man_made"="pier"]({bbox});
        relation["man_made"="pier"];

        node["man_made"="jetty"]({bbox});
        way["man_made"="jetty"]({bbox});
        relation["man_made"="jetty"];

        node["man_made"="dock"]({bbox});
        way["man_made"="dock"]({bbox});
        relation["man_made"="dock"];
        );
        out center;
        """
        try:
            
            response = None
            
            for url in Config.marine_traffic.overpass.urls:
                
                try:
                    
                    response = requests.post(
                        url, 
                        data = {"data": query_params}, 
                        timeout = 15
                    )
                    
                    if response.status_code == 200:
                        
                        break
                        
                except requests.exceptions.RequestException as req_err:
                    
                    self.log.warning("Overpass request failed for %s: %s" % (url, str(req_err)))
                    
                    continue
            
            if response is not None and response.status_code == 200:
           
                data = response.json()
                
                elements = data.get("elements")
                
                if isinstance(elements, list):
                    
                    harbors = [Harbor(
                        name = element.get("tags", {}).get("name"),
                        lat = center.get("lat"),
                        lon = center.get("lon")
                        ) for element in elements 
                        if isinstance(center := element.get("center"), dict) 
                        and isinstance(center.get("lat"), float)
                        and isinstance(center.get("lon"), float)
                    ]
                    
                    nearest_harbor = min(
                        harbors,
                        key = lambda harbor: self.utility_calculator.haversine_formula(
                            lat1 = lat, 
                            lon1 = lon, 
                            lat2 = harbor.lat, 
                            lon2 = harbor.lon
                        )
                    )
                 
                    distance_km, nearest_named = self.find_distance_to_nearest_named_harbor(
                        nearest_harbor = nearest_harbor,
                        harbors = harbors
                    )

                    return nearest_harbor, distance_km, nearest_named

        except Exception as e:
            
            self.log.exception("Unexpected error occured: %s" % str(e))
            
            return None, None, None
    
    def find_distance_to_nearest_named_harbor(self, nearest_harbor: Harbor, harbors: t.List[Harbor]) -> t.Tuple[float, str] | None:
        """
        Finds the nearest harbor with a name relative to the given nearest_harbor,
        and returns the distance in kilometers and the harbor's name.

        Pricegs:
            nearest_harbor (Harbor): The reference harbor (the nearest one, even if it has no name).
            harbors (List[Harbor]): List of available harbors.

        Returns:
            Tuple[float, str] |
            None:
                - distance_km: distance between nearest_harbor and the nearest named harbor
                - name: name of the nearest harbor with a name
            Returns None if there is no harbor with a name.
        """
        if len(harbors) > 0:
            
            named_harbors = [harbor for harbor in harbors if harbor.name is not None]
            
            if len(named_harbors) > 0:
                
                nearest_named = min(
                    (h for h in named_harbors if (h.lat, h.lon) != (nearest_harbor.lat, nearest_harbor.lon)),
                    key = lambda h: self.utility_calculator.haversine_formula(
                        lat1 = nearest_harbor.lat,
                        lon1 = nearest_harbor.lon,
                        lat2 = h.lat,
                        lon2 = h.lon
                    ),
                    default = None
                )
                
                if nearest_named is not None:
                    
                    distance_km = self.utility_calculator.haversine_formula(
                        lat1 = nearest_harbor.lat, 
                        lon1 = nearest_harbor.lon, 
                        lat2 = nearest_named.lat, 
                        lon2 = nearest_named.lon
                    )
                    
                    return distance_km, nearest_named.name
                
        return None, None
