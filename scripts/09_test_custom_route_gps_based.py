import osmnx as ox
import networkx as nx
import geopandas as gpd

# 1. Load and Weight Graph
G = ox.load_graphml("data/nagpur_roads_projected.graphml")
G = ox.routing.add_edge_speeds(G, hwy_speeds={'primary': 50, 'secondary': 40, 'tertiary': 30})
G = ox.routing.add_edge_travel_times(G)

# 2. Define coordinates (X, Y in Meters from QGIS)
sadar_xy = (300123.45, 2341234.56) 
mankapur_xy = (299567.89, 2345678.90)

# 3. Find closest nodes
node_a = ox.distance.nearest_nodes(G, X=sadar_xy[0], Y=sadar_xy[1])
node_b = ox.distance.nearest_nodes(G, X=mankapur_xy[0], Y=mankapur_xy[1])

# 4. Calculate Route
route = nx.shortest_path(G, node_a, node_b, weight='travel_time')
print(f"Distance: {nx.path_weight(G, route, weight='length')/1000:.2f} km")

# 5. EXPORT FOR QGIS
route_gdf = ox.routing.route_to_gdf(G, route)
route_gdf.to_file("data/route_test.geojson", driver='GeoJSON')
print("✅ GPS-based route saved to data/route_sadar_mankapur_gps.geojson")