import osmnx as ox
import networkx as nx
import geopandas as gpd

print("Loading and weighting graph...")
G = ox.load_graphml("data/nagpur_roads_projected.graphml")
hwy_speeds = {'motorway': 80, 'trunk': 60, 'primary': 50, 'secondary': 40, 'tertiary': 30, 'residential': 20}
G = ox.routing.add_edge_speeds(G, hwy_speeds=hwy_speeds)
G = ox.routing.add_edge_travel_times(G)

sadar_node_id = 4602227395
mankapur_node_id = 6045642714

try:
    print(f"Finding route between {sadar_node_id} and {mankapur_node_id}...")
    route = nx.shortest_path(G, sadar_node_id, mankapur_node_id, weight='travel_time')

    # Calculate Stats
    dist_km = nx.path_weight(G, route, weight='length') / 1000
    print(f"Distance: {dist_km:.2f} km")

    # EXPORT FOR QGIS
    route_gdf = ox.routing.route_to_gdf(G, route)
    route_gdf.to_file("data/route_test.geojson", driver='GeoJSON')
    print("✅ ID-based route saved to data/route_sadar_mankapur_id.geojson")
    
except nx.NetworkXNoPath:
    print("❌ Error: No path found.")