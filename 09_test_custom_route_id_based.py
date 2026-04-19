import osmnx as ox
import networkx as nx

# 1. Load the Projected Graph (Meters)
print("Loading projected road network...")
G = ox.load_graphml("data/nagpur_roads_projected.graphml")

# 2. Impute Speed and Travel Time (MANDATORY step for travel_time calculation)
print("Calculating weights...")
hwy_speeds = {
    'motorway': 80, 'trunk': 60, 'primary': 50, 
    'secondary': 40, 'tertiary': 30, 'residential': 20
}
G = ox.routing.add_edge_speeds(G, hwy_speeds=hwy_speeds)
G = ox.routing.add_edge_travel_times(G)

# 3. Save as Master Weighted Graph (Optional - prevents needing step 2 next time)
# ox.save_graphml(G, filepath="data/nagpur_roads_weighted.graphml")

# 4. Input the IDs you found in QGIS
# Ensure these IDs are correct for your specific graph
sadar_node_id = 10997222050 # Replace with your actual QGIS ID
mankapur_node_id = 10997213636 # Replace with your actual QGIS ID

try:
    # 5. Execute Shortest Path Algorithm
    print(f"Finding route between {sadar_node_id} and {mankapur_node_id}...")
    route = nx.shortest_path(G, sadar_node_id, mankapur_node_id, weight='travel_time')

    # 6. Calculate Statistics
    dist_meters = nx.path_weight(G, route, weight='length')
    time_seconds = nx.path_weight(G, route, weight='travel_time')

    print(f"\n--- V-NEURON: Sadar to Mankapur ---")
    print(f"Distance: {dist_meters/1000:.2f} km")
    print(f"Estimated Travel Time: {time_seconds/60:.2f} minutes")
    
except nx.NetworkXNoPath:
    print("❌ Error: No path found between these two nodes.")
except KeyError as e:
    print(f"❌ Error: Missing attribute in graph: {e}")