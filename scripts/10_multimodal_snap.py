import osmnx as ox
#import nx_parallel as nxp # Optional: if you have it, otherwise use nx
import networkx as nx
import geopandas as gpd

print("Loading weighted road network...")
G = ox.load_graphml("data/nagpur_roads_projected.graphml")
G = ox.routing.add_edge_speeds(G, hwy_speeds={'primary': 50, 'secondary': 40, 'tertiary': 30, 'residential': 20})
G = ox.routing.add_edge_travel_times(G)

print("Loading Metro stations...")
metro_gdf = gpd.read_file("data/nagpur_metro_projected.geojson")
metro_stations = metro_gdf[metro_gdf.geom_type == 'Point'].copy()

# Base ID for metro nodes to avoid conflict with OSM IDs
METRO_ID_BASE = 1000000000000 

print(f"Connecting {len(metro_stations)} stations to the road network...")
walking_speed_mps = 1.25 # approx 4.5 km/h

for idx, station in metro_stations.iterrows():
    nearest_node = ox.distance.nearest_nodes(G, X=station.geometry.x, Y=station.geometry.y)
    dist_m = ox.distance.euclidean(station.geometry.y, station.geometry.x, 
                                   G.nodes[nearest_node]['y'], G.nodes[nearest_node]['x'])
    
    walk_time_sec = dist_m / walking_speed_mps
    
    # FIX: Use a large INTEGER instead of a string
    station_node_id = METRO_ID_BASE + idx
    
    # Store the name attribute so we can find it in Step 11
    s_name = station['name'] if 'name' in station else f"Station_{idx}"
    
    G.add_node(station_node_id, x=station.geometry.x, y=station.geometry.y, 
               highway='metro_station', name=s_name)
    
    G.add_edge(station_node_id, nearest_node, length=dist_m, travel_time=walk_time_sec, highway='footway')
    G.add_edge(nearest_node, station_node_id, length=dist_m, travel_time=walk_time_sec, highway='footway')

ox.save_graphml(G, filepath="data/vneuron_multimodal_base.graphml")
print("✅ Success: Metro stations connected with Integer IDs.")