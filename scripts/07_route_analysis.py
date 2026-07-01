import osmnx as ox
import networkx as nx
import matplotlib.pyplot as plt
import geopandas as gpd
from shapely.geometry import Point

# 1. Load the Projected Graph (Meters - EPSG:32644)
print("Loading projected road network...")
G = ox.load_graphml("data/nagpur_roads_projected.graphml")

# 2. Impute Speed and Travel Time
print("Calculating speeds and travel times...")
hwy_speeds = {
    'motorway': 80,
    'trunk': 60,
    'primary': 50,
    'secondary': 40,
    'tertiary': 30,
    'residential': 20
}
G = ox.routing.add_edge_speeds(G, hwy_speeds=hwy_speeds)
G = ox.routing.add_edge_travel_times(G)

# 3. Define Test Points (Latitude, Longitude)
orig_lat_lon = (21.056, 79.027) # SVPCET (Nagpur)
dest_lat_lon = (21.146, 79.083) # Sitabuldi (Nagpur)

# 4. Project Points to EPSG:32644 (Meters)
# We convert (Long, Lat) because Shapeley/GIS uses X,Y order
# FIX: Both points now correctly project FROM 4326 TO 32644
orig_gs = gpd.GeoSeries([Point(orig_lat_lon[1], orig_lat_lon[0])], crs="EPSG:4326").to_crs("EPSG:32644")
dest_gs = gpd.GeoSeries([Point(dest_lat_lon[1], dest_lat_lon[0])], crs="EPSG:4326").to_crs("EPSG:32644")

orig_proj = orig_gs[0]
dest_proj = dest_gs[0]

print(f"DEBUG: Start Point (Meters): X={orig_proj.x:.2f}, Y={orig_proj.y:.2f}")
print(f"DEBUG: End Point (Meters): X={dest_proj.x:.2f}, Y={dest_proj.y:.2f}")

# 5. Find Nearest Nodes
orig_node = ox.distance.nearest_nodes(G, X=orig_proj.x, Y=orig_proj.y)
dest_node = ox.distance.nearest_nodes(G, X=dest_proj.x, Y=dest_proj.y)

# 6. Execute Shortest Path Algorithm (A*)
print(f"Running A* between Node {orig_node} and Node {dest_node}...")
route = nx.shortest_path(G, orig_node, dest_node, weight='travel_time', method='dijkstra')

# 7. Calculate Route Statistics
total_travel_time = nx.path_weight(G, route, weight='travel_time')
total_distance = nx.path_weight(G, route, weight='length')

print(f"\n--- V-NEURON Route Summary ---")
print(f"Total Distance: {total_distance/1000:.2f} km")
print(f"Estimated Travel Time: {total_travel_time/60:.2f} minutes")

# 8. Visualize the Route
fig, ax = ox.plot.plot_graph_route(G, route, route_color='r', route_linewidth=3, node_size=0)
plt.show()