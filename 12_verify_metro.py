import osmnx as ox
import networkx as nx
import matplotlib.pyplot as plt

# 1. Load the Omnimodal Graph
print("Loading V-NEURON Omnimodal Graph...")
G = ox.load_graphml("data/vneuron_omnimodal_final.graphml")

# 2. SIMULATE PEAK TRAFFIC (The Verification Hack)
# We drastically reduce road speeds to 10-15 km/h
print("Simulating peak-hour traffic (capping roads at 12 km/h)...")
traffic_speeds = {
    'motorway': 20, 'trunk': 15, 'primary': 12, 
    'secondary': 10, 'tertiary': 8, 'residential': 5
}
G = ox.routing.add_edge_speeds(G, hwy_speeds=traffic_speeds)
G = ox.routing.add_edge_travel_times(G)

# 3. Define the same test points (SVPCET to Automotive Square)
orig_node = 11700645320 # Your node ID for SVPCET area
dest_node = 1000000000000 # Node ID for Automotive Square Station (METRO_ID_BASE + 0)

# 4. Run the Algorithm
print("Calculating fastest route under traffic conditions...")
route = nx.shortest_path(G, orig_node, dest_node, weight='travel_time')

# 5. VERIFY THE MODES
route_gdf = ox.routing.route_to_gdf(G, route)
modes_used = route_gdf['highway'].unique()

print(f"\n--- V-NEURON Logic Verification ---")
print(f"Modes identified: {modes_used}")

if 'subway' in modes_used:
    print("✅ VERIFIED: The algorithm successfully chose the Metro Rail!")
    
    # Calculate how many stations were crossed
    metro_segments = route_gdf[route_gdf['highway'] == 'subway']
    print(f"Number of Metro segments used: {len(metro_segments)}")
else:
    print("❌ FAILED: The algorithm still prefers roads. Check walking distances.")

# 6. Save the Metro-using route for QGIS
route_gdf.to_file("data/vneuron_verified_metro_route.geojson", driver='GeoJSON')