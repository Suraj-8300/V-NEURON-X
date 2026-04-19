import osmnx as ox
import networkx as nx
import geopandas as gpd
import pandas as pd

# 1. Load the Weighted Road Graph
print("Loading weighted road network...")
G = ox.load_graphml("data/nagpur_roads_projected.graphml")
# Ensure travel times are present for the road edges
G = ox.routing.add_edge_speeds(G, hwy_speeds={'primary': 50, 'secondary': 40, 'tertiary': 30, 'residential': 20})
G = ox.routing.add_edge_travel_times(G)

# 2. Load Projected Metro Stations
print("Loading Metro stations...")
metro_gdf = gpd.read_file("data/nagpur_metro_projected.geojson")
# Filter for points only (Stations)
metro_stations = metro_gdf[metro_gdf.geom_type == 'Point'].copy()

# 3. The "Snap" Logic: Connecting Metro to Roads
print(f"Connecting {len(metro_stations)} stations to the road network...")

walking_speed_kmh = 4.5  # Average human walking speed
walking_speed_mps = (walking_speed_kmh * 1000) / 3600 # Convert to meters/second

for idx, station in metro_stations.iterrows():
    # Find the nearest road node to the station coordinate
    # (Station is already in meters/EPSG:32644)
    nearest_node = ox.distance.nearest_nodes(G, X=station.geometry.x, Y=station.geometry.y)
    
    # Calculate walking distance between station and road node
    # Note: For a semester project, a straight-line Euclidean distance is acceptable here
    dist_m = ox.distance.euclidean(station.geometry.y, station.geometry.x, 
                                   G.nodes[nearest_node]['y'], G.nodes[nearest_node]['x'])
    
    walk_time_sec = dist_m / walking_speed_mps
    
    # Add a virtual node for the Metro Station
    station_node_id = f"metro_{idx}"
    G.add_node(station_node_id, x=station.geometry.x, y=station.geometry.y, highway='metro_station')
    
    # Add a bidirectional walking edge between the Road and the Metro Station
    G.add_edge(station_node_id, nearest_node, length=dist_m, travel_time=walk_time_sec, highway='footway')
    G.add_edge(nearest_node, station_node_id, length=dist_m, travel_time=walk_time_sec, highway='footway')

# 4. Save the Multimodal Graph
ox.save_graphml(G, filepath="data/vneuron_multimodal_base.graphml")
print("✅ Success: Metro stations are now logically connected to the road network.")