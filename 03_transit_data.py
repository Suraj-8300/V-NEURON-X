import osmnx as ox
import pandas as pd
import os
import certifi

# 1. Environment Setup
# Force correct certificate path to avoid SSL errors
os.environ['SSL_CERT_FILE'] = certifi.where()
os.environ['REQUESTS_CA_BUNDLE'] = certifi.where()
os.environ['CURL_CA_BUNDLE'] = certifi.where()

# Ensure data directory exists
if not os.path.exists('data'):
    os.makedirs('data')

print("--- Starting V-NEURON Transit Data Extraction ---")

# 2. Fetch Nagpur Metro (Railway + Stations)
print("Fetching Nagpur Metro data...")
metro_infrastructure = ox.features_from_place(
    "Nagpur, Maharashtra, India", 
    tags={"railway": ["subway", "light_rail", "station"]}
)

# 3. Fetch Nagpur Bus (Broad Search)
print("Performing broad search for Aapli Bus features...")
bus_features = ox.features_from_place(
    "Nagpur, Maharashtra, India", 
    tags={
        "highway": ["bus_stop", "platform"],
        "public_transport": ["stop_position", "platform", "station"],
        "amenity": "bus_station"
    }
)

# 4. Analysis and Filtering
# Filter only for points (Stations) to identify specific boarding locations
metro_stations = metro_infrastructure[metro_infrastructure.geom_type == 'Point']

print(f"\n--- Results Summary ---")
print(f"Total Metro Features: {len(metro_infrastructure)}")
print(f"Confirmed Metro Stations (Points): {len(metro_stations)}")

# List the names of Metro Stations found
if 'name' in metro_stations.columns:
    station_list = metro_stations['name'].dropna().unique()
    print(f"Metro Stations Detected: {len(station_list)}")
    for name in sorted(station_list):
        print(f" - {name}")

print(f"\nBroader Bus search found {len(bus_features)} features.")

# 5. Clean and Save
# Saving as GeoJSON for future PostGIS import
metro_infrastructure.to_file("data/nagpur_metro.geojson", driver='GeoJSON')
bus_features.to_file("data/nagpur_bus_stops.geojson", driver='GeoJSON')

print("\nSuccess! Files saved to data/ folder.")