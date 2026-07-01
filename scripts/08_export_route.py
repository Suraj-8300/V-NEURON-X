import osmnx as ox
import networkx as nx
import geopandas as gpd

# Load the same graph and points used in Step 7
G = ox.load_graphml("data/nagpur_roads_projected.graphml")
# (Use the same nodes from your previous run)
orig_node = 11700645320 
dest_node = 9169431177

# 1. Generate the route
route = nx.shortest_path(G, orig_node, dest_node, weight='travel_time')

# 2. Convert route to a GeoDataFrame (Edges only)
route_edges = ox.routing.route_to_gdf(G, route)

# 3. Save to data folder
route_edges.to_file("data/test_route_svpcet_to_sitabuldi.geojson", driver='GeoJSON')
print("✅ Route exported to data/test_route_svpcet_to_sitabuldi.geojson")