import osmnx as ox
import networkx as nx
import pandas as pd
import time

# 1. Load the graphs
print("Loading graphs for audit...")
G_omni = ox.load_graphml("data/vneuron_omnimodal_final.graphml") # Original
G_calib = ox.load_graphml("data/vneuron_calibrated_network.graphml") # Congested + Penalties

# 2. Define Test Route (SVPCET to Automotive Square)
orig_node = 11700645320 
dest_node = 1000000000000 

def get_stats(G, label):
    start_time = time.time()
    route = nx.shortest_path(G, orig_node, dest_node, weight='travel_time')
    exec_time = (time.time() - start_time) * 1000 # ms
    
    dist_km = nx.path_weight(G, route, weight='length') / 1000
    time_min = nx.path_weight(G, route, weight='travel_time') / 60
    
    # Identify modes
    route_gdf = ox.routing.route_to_gdf(G, route)
    modes = route_gdf['highway'].unique().tolist()
    
    return {
        "Scenario": label,
        "Distance_KM": round(dist_km, 2),
        "Time_Min": round(time_min, 2),
        "Modes": modes,
        "Compute_MS": round(exec_time, 2)
    }

# 3. Run Audit
print("Auditing scenarios...")
results = []
results.append(get_stats(G_omni, "Off-Peak (Free Flow)"))
results.append(get_stats(G_calib, "Peak Hour (Congested)"))

# 4. Generate Report
df = pd.DataFrame(results)
print("\n--- V-NEURON Comparative Performance Report ---")
print(df[["Scenario", "Distance_KM", "Time_Min", "Modes"]])

# 5. Save Tracking Logs
df.to_csv("data/vneuron_route_logs.csv", index=False)
print("\n✅ Success: Route statistics and tracking logs saved to data/vneuron_route_logs.csv")