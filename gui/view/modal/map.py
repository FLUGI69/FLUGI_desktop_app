from PyQt6.QtWidgets import QDialog, QVBoxLayout
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtCore import QUrl

from utils.dc.marine_traffic.vessel_position import VesselPosition
from utils.dc.marine_traffic.harbor import Harbor

class MapModal(QDialog):
    
    def __init__(self,
        vessel: VesselPosition,
        nearest_harbor: Harbor,
        parent = None,
        distance_km: float | None = None,
        nearest_name: str | None = None
        ):
    
        super().__init__(parent)
        
        self.vessel = vessel
        
        self.nearest_harbor = nearest_harbor
        
        self.distance_km = distance_km
        
        self.nearest_name = nearest_name
        
        self.__init_view()
        
    def __init_view(self):
        
        self.setWindowTitle("Map")
        
        self.resize(800, 600)  

        layout = QVBoxLayout(self)
        
        self.view = QWebEngineView()
        
        layout.addWidget(self.view)
        
        self.view.loadFinished.connect(self._on_load_finished)
        
        self._loaded = False

    def load_map(self):
        
        if self.vessel is not None and self.nearest_harbor is not None:
            
            if self.nearest_harbor.name is not None:
                
                tooltip_text = f"{self.vessel.ship_name} current location: {self.nearest_harbor.name}"
                
            elif self.distance_km is not None and self.nearest_name is not None:
                
                tooltip_text = f"{self.vessel.ship_name} currently at {self.nearest_name} km from the port of {self.distance_km:.2f} km away"
            
            else:
                
                tooltip_text = f"{self.vessel.ship_name} location unknown"
                
                
            html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Map</title>
                <meta charset="utf-8" />
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
                <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
                <style>
                    #map {{ height: 100vh; margin: 0; padding: 0; }}
                    html, body {{ height: 100%; margin: 0; padding: 0; }}
                </style>
            </head>
            <body>
                <div id="map"></div>
                <script>
                    // Initialize the map centered at the ship's position
                    var map = L.map('map').setView([{self.vessel.lat}, {self.vessel.lon}], 15);

                    // OpenStreetMap layer
                    L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
                        maxZoom: 19,
                        attribution: '© OpenStreetMap contributors'
                    }}).addTo(map);

                    // OpenSeaMap layer
                    L.tileLayer('https://tiles.openseamap.org/seamark/{{z}}/{{x}}/{{y}}.png', {{
                        maxZoom: 18,
                        attribution: '© OpenSeaMap contributors'
                    }}).addTo(map);

                    // Ship icon
                    var shipIcon = L.icon({{
                        iconUrl: 'https://toppng.com/free-image/red-dot-circle-icon-PNG-free-PNG-Images_475098.png',
                        iconSize: [30, 30],
                        iconAnchor: [15, 15],
                        popupAnchor: [0, -15]
                    }});

                    // Ship marker
                    var shipMarker = L.circleMarker(
                        [{self.vessel.lat}, {self.vessel.lon}],
                        {{
                            radius: 8,
                            color: '#FF3333',
                            fillColor: '#FF3333',
                            fillOpacity: 1,
                            weight: 0
                        }}
                    ).addTo(map).bindTooltip('{tooltip_text}', {{ permanent: false, direction: 'top' }}).openTooltip();

                    // Blinking effect
                    var visible = true;
                    setInterval(() => {{
                        shipMarker.setStyle({{
                            fillOpacity: visible ? 0.3 : 1
                        }});
                        visible = !visible;
                    }}, 500);

                </script>
            </body>
            </html>
            """
            
            self.view.setHtml(html, QUrl("https://localhost/"))
        
    def _on_load_finished(self, ok):
        
        if ok and not self._loaded:
            
            self._loaded = True
            self.show()