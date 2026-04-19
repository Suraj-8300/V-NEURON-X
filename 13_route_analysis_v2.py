import osmnx as ox
import networkx as nx
import pandas as pd

# 1. Load the Omnimodal Graph
G = ox.load_graphml("data/vneuron_omnimodal_final.graphml")

# 2. Re-simulate the same test (with traffic simulation)
traffic_speeds = {'motorway': 20, 'trunk': 15, 'primary': 12, 'secondary': 10, 'tertiary': 8, 'residential': 5}
G = ox.routing.add_edge_speeds(G, hwy_speeds=traffic_speeds)
G = ox.routing.add_edge_travel_times(G)

# 3. Nodes for SVPCET and Automotive Square
orig_node = 11700645320 
dest_node = 1000000000000 

# 4. Calculate Route
route = nx.shortest_path(G, orig_node, dest_node, weight='travel_time')
route_gdf = ox.routing.route_to_gdf(G, route)

# 5. DETAILED ANALYSIS: Group by Highway Type
# This shows exactly how many km and minutes are spent on each mode
analysis = route_gdf.groupby('highway').agg({
    'length': 'sum',
    'travel_time': 'sum'
}).reset_index()

# Convert to KM and Minutes
analysis['length_km'] = analysis['length'] / 1000
analysis['time_min'] = analysis['travel_time'] / 60

print("\n--- V-NEURON: Modal Split Analysis ---")
print(analysis[['highway', 'length_km', 'time_min']])

total_dist = analysis['length_km'].sum()
total_time = analysis['time_min'].sum()

print(f"\nTotal Trip: {total_dist:.2f} km | {total_time:.2f} minutes")

# 6. Check for "The Transfer"
# Find the specific road nodes where the user switches to Metro
transfer_points = route_gdf[route_gdf['highway'] == 'footway']
print(f"\nNumber of modal transfers: {len(transfer_points)}")