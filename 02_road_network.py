import osmnx as ox
import matplotlib.pyplot as plt

# 1. Define the area (Nagpur)
place_name = "Nagpur, Maharashtra, India"

# 2. Download the road network data
# 'drive' ensures we only get roads accessible by cars/bikes
print(f"Fetching road network for {place_name}... this may take a minute.")
G = ox.graph_from_place(place_name, network_type='drive')

# 3. Basic analysis
print(f"Number of intersections (nodes): {len(G.nodes)}")
print(f"Number of road segments (edges): {len(G.edges)}")

# 4. Save a local copy (so we don't have to download it every time)
ox.save_graphml(G, filepath="data/nagpur_roads.graphml")

# 5. Visualize and save the network
fig, ax = ox.plot_graph(
    G, 
    node_size=0, 
    edge_color='#1f77b4', 
    edge_linewidth=0.3, 
    bgcolor='k',
    
    # Add these parameters to save the image:
    save=True,           # Enable saving
    filepath="data/nagpur_roads.png",  # Change path/name/extension as needed
    show=True,           # Set to False if you don't want to display it
    close=True,          # Close the figure after saving (recommended to free memory)
    dpi=300              # Higher DPI = better quality (default is usually 300)
)

# 5. Visualize the network
fig, ax = ox.plot_graph(G, node_size=0, edge_color='#1f77b4', edge_linewidth=0.3, bgcolor='k')
plt.show()
