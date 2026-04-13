import osmnx as ox
import pandas as pd
import os
import certifi

# Force correct certificate path
os.environ['SSL_CERT_FILE'] = certifi.where()
os.environ['REQUESTS_CA_BUNDLE'] = certifi.where()
os.environ['CURL_CA_BUNDLE'] = certifi.where()

# 1. Fetch Nagpur Metro (Railway + Stations)
# We search for 'light_rail' and 'subway' tags used by Maha Metro
print("Fetching Nagpur Metro data...")
metro_infrastructure = ox.features_from_place(
    "Nagpur, Maharashtra, India", 
    tags={"railway": ["subway", "light_rail", "station"]}
)

# 2. Fetch Nagpur Bus Stops
# We search for 'bus_stop' or 'highway=bus_stop'
print("Fetching Aapli Bus stop locations...")
bus_stops = ox.features_from_place(
    "Nagpur, Maharashtra, India", 
    tags={"highway": "bus_stop"}
)

# 3. Clean and Save to CSV/GeoJSON
# Saving as GeoJSON makes it easy to open in QGIS or ArcGIS later
metro_infrastructure.to_file("data/nagpur_metro.geojson", driver='GeoJSON')
bus_stops.to_file("data/nagpur_bus_stops.geojson", driver='GeoJSON')

print(f"Success! Found {len(metro_infrastructure)} Metro features and {len(bus_stops)} Bus stops.")