import osmnx as ox
import networkx as nx
import matplotlib.pyplot as plt
import geopandas as gpd
from shapely.geometry import Point

# 1. Load the Final Omnimodal Graph
print("Loading V-NEURON Omnimodal Graph...")
G = ox.load_graphml("data/vneuron_omnimodal_final.graphml")

# 2. Define Multimodal Test Points (Coordinates)
# SVPCET (South Nagpur) to Automotive Square (North Nagpur)
orig_lat_lon = (21.056, 79.027) 
dest_lat_lon = (21.203, 79.083) 

# 3. Project Points to EPSG:32644 (Meters)
orig_gs = gpd.GeoSeries([Point(orig_lat_lon[1], orig_lat_lon[0])], crs="EPSG:4326").to_crs("EPSG:32644")
dest_gs = gpd.GeoSeries([Point(dest_lat_lon[1], dest_lat_lon[0])], crs="EPSG:4326").to_crs("EPSG:32644")
orig_proj, dest_proj = orig_gs[0], dest_gs[0]

# 4. Find Nearest Nodes
orig_node = ox.distance.nearest_nodes(G, X=orig_proj.x, Y=orig_proj.y)
dest_node = ox.distance.nearest_nodes(G, X=dest_proj.x, Y=dest_proj.y)

# 5. Execute Routing Algorithm (using travel_time)
print("Calculating fastest omnimodal route...")
route = nx.shortest_path(G, orig_node, dest_node, weight='travel_time')

# 6. Analyze the Mode Segments
# We look at the 'highway' attribute of the edges in the route
edge_types = ox.routing.route_to_gdf(G, route)['highway'].unique()
print(f"Modes used in this route: {edge_types}")

# 7. Calculate Statistics
total_time_min = nx.path_weight(G, route, weight='travel_time') / 60
total_dist_km = nx.path_weight(G, route, weight='length') / 1000

print(f"\n--- V-NEURON Omnimodal Summary ---")
print(f"From: SVPCET Area | To: Automotive Square")
print(f"Total Distance: {total_dist_km:.2f} km")
print(f"Estimated Travel Time: {total_time_min:.2f} minutes")

# 8. Visualize and Save for QGIS
route_gdf = ox.routing.route_to_gdf(G, route)
route_gdf.to_file("data/vneuron_multimodal_test_route.geojson", driver='GeoJSON')
print("✅ Success: Test route saved to data/vneuron_multimodal_test_route.geojson")

# Plotting
fig, ax = ox.plot.plot_graph_route(G, route, route_color='orange', route_linewidth=4, node_size=0)
plt.show()