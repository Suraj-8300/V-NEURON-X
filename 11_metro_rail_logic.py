import osmnx as ox
import networkx as nx

# 1. Load the Multimodal Base Graph
print("Loading multimodal base graph...")
G = ox.load_graphml("data/vneuron_multimodal_base.graphml")

# 2. Define Metro Operational Parameters
metro_speed_kmh = 33 
metro_speed_mps = (metro_speed_kmh * 1000) / 3600 # ~9.16 meters/second

# 3. Create a Name-to-Node Mapping
# This allows us to find the Integer ID of a station by its name
name_to_node = {data['name']: node for node, data in G.nodes(data=True) if data.get('highway') == 'metro_station'}

# 4. Define Nagpur Metro Sequences
orange_line = [
    "Automotive Square", "Nari Road", "Indora Square", "Kadvi Square", 
    "Gaddi Godam Square", "Kasturchand Park", "Zero Mile", "Sitabuldi", 
    "Congress Nagar", "Rahate Colony", "Ajni Square", "Chhatrapati Square", 
    "Jaiprakash Nagar", "Ujjwal Nagar", "Airport", "Airport South", "New Airport", "Khapri"
]

aqua_line = [
    "Prajapati Nagar", "Vaishnodevi Square", "Ambedkar Square", "Telephone Exchange", 
    "Chitaroli Square", "Agrasen Square", "Dosar Vaisya Square", "Nagpur Junction railway station", 
    "Cotton Market", "Sitabuldi", "Jhasi Rani Square", "Institute of Engineers", 
    "Shankar Nagar Square", "LAD College", "Ambazari Lake", "Subhash Nagar", 
    "Vasudev Nagar", "Rachna Ring Road", "Lokmanya Nagar"
]

def add_rail_edges(line_stations, line_name):
    print(f"Connecting {line_name}...")
    edges_added = 0
    for i in range(len(line_stations) - 1):
        u_name = line_stations[i]
        v_name = line_stations[i+1]
        
        if u_name in name_to_node and v_name in name_to_node:
            u, v = name_to_node[u_name], name_to_node[v_name]
            
            # Calculate distance between station nodes
            dist_m = ox.distance.euclidean(G.nodes[u]['y'], G.nodes[u]['x'], 
                                           G.nodes[v]['y'], G.nodes[v]['x'])
            
            # Travel time at metro speeds
            travel_time = dist_m / metro_speed_mps
            
            # Add bidirectional rail edges
            G.add_edge(u, v, length=dist_m, travel_time=travel_time, highway='subway', name=line_name)
            G.add_edge(v, u, length=dist_m, travel_time=travel_time, highway='subway', name=line_name)
            edges_added += 1
    print(f"✅ Added {edges_added} rail segments for {line_name}.")

# 5. Run the connection logic
add_rail_edges(orange_line, "Orange Line")
add_rail_edges(aqua_line, "Aqua Line")

# 6. Save the final Omnimodal Graph
ox.save_graphml(G, filepath="data/vneuron_omnimodal_final.graphml")
print("\n--- V-NEURON Omnimodal Graph is now logically complete ---")