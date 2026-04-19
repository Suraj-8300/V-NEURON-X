import osmnx as ox
import networkx as nx

# 1. Load the Omnimodal Graph
print("Loading V-NEURON Omnimodal Graph...")
G = ox.load_graphml("data/vneuron_omnimodal_final.graphml")

# 2. Define Penalties
# Average wait time for a train + station navigation in seconds
boarding_penalty_sec = 300  # 5 minutes

# 3. Apply Penalties to 'footway' edges (The Transfer Links)
print(f"Applying a {boarding_penalty_sec/60} min boarding penalty to all transfers...")
for u, v, k, data in G.edges(data=True, keys=True):
    if data.get('highway') == 'footway':
        # Add the penalty to the existing walking time
        data['travel_time'] += boarding_penalty_sec

# 4. Refine Congestion Simulation
# Capping road speeds even further to simulate a heavy 'bottleneck'
print("Simulating extreme congestion on trunk roads...")
traffic_speeds = {
    'motorway': 15, 'trunk': 10, 'primary': 8, 
    'secondary': 7, 'tertiary': 5, 'residential': 4
}
G = ox.routing.add_edge_speeds(G, hwy_speeds=traffic_speeds)
G = ox.routing.add_edge_travel_times(G)

# 5. Save the Calibrated Graph
ox.save_graphml(G, filepath="data/vneuron_calibrated_network.graphml")
print("✅ Success: Transfer penalties and congestion logic applied.")