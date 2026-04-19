import osmnx as ox
import networkx as nx

G = ox.load_graphml("data/nagpur_roads_projected.graphml")
G = ox.routing.add_edge_speeds(G, hwy_speeds={'primary': 50, 'secondary': 40, 'tertiary': 30})
G = ox.routing.add_edge_travel_times(G)

# Use the X, Y coordinates from your QGIS status bar
# X = 300xxx.xx, Y = 234xxx.xx
sadar_xy = (300123.45, 2341234.56) 
mankapur_xy = (299567.89, 2345678.90)

# Find the closest nodes automatically
node_a = ox.distance.nearest_nodes(G, X=sadar_xy[0], Y=sadar_xy[1])
node_b = ox.distance.nearest_nodes(G, X=mankapur_xy[0], Y=mankapur_xy[1])

route = nx.shortest_path(G, node_a, node_b, weight='travel_time')
print(f"Distance: {nx.path_weight(G, route, weight='length')/1000:.2f} km")