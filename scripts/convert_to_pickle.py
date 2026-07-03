import os
import time
import pickle
import osmnx as ox

data_dir = "backend/data"
if not os.path.exists(data_dir):
    data_dir = "data"

print(f"Using data directory: {data_dir}")

graphs = [
    ("vneuron_omnimodal_final.graphml", "vneuron_omnimodal_final.pickle"),
    ("vneuron_calibrated_network.graphml", "vneuron_calibrated_network.pickle")
]

for g_xml, g_pkl in graphs:
    xml_path = os.path.join(data_dir, g_xml)
    pkl_path = os.path.join(data_dir, g_pkl)
    
    print(f"\n--- Processing {g_xml} ---")
    
    # Measure XML load time
    start = time.time()
    print("Loading GraphML (XML)...")
    G = ox.load_graphml(xml_path)
    xml_time = time.time() - start
    print(f"Loaded in {xml_time:.2f} seconds.")
    
    # Save as pickle
    print("Saving as pickle...")
    with open(pkl_path, "wb") as f:
        pickle.dump(G, f, pickle.HIGHEST_PROTOCOL)
    print(f"Saved to {pkl_path}")
    
    # Measure pickle load time
    start = time.time()
    print("Loading from pickle...")
    with open(pkl_path, "rb") as f:
        G_loaded = pickle.load(f)
    pkl_time = time.time() - start
    print(f"Loaded from pickle in {pkl_time:.2f} seconds.")
    
    # Compare
    print(f"Speedup: {xml_time / pkl_time:.1f}x faster!")
