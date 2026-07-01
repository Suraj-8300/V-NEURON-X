import geopandas as gpd
import osmnx as ox

# 1. Load the Road Network Graph
G = ox.load_graphml("data/nagpur_roads.graphml")

# 2. Project the Road Network to UTM (Meters)
# osmnx automatically finds the correct UTM zone for the location
print("Projecting Road Network to UTM...")
G_projected = ox.project_graph(G)
ox.save_graphml(G_projected, filepath="data/nagpur_roads_projected.graphml")

# 3. Load and Project the Transit GeoJSONs
print("Projecting Metro and Bus layers to EPSG:32644...")
metro = gpd.read_file("data/nagpur_metro.geojson")
bus = gpd.read_file("data/nagpur_bus_stops.geojson")

# Transform to the Nagpur UTM Zone
metro_projected = metro.to_crs(epsg=32644)
bus_projected = bus_projected = bus.to_crs(epsg=32644)

# 4. Save the "Clean" Projected versions
metro_projected.to_file("data/nagpur_metro_projected.geojson", driver='GeoJSON')
bus_projected.to_file("data/nagpur_bus_projected.geojson", driver='GeoJSON')

print("✅ All layers standardized to Meters (EPSG:32644).")
print(f"Road units: {G_projected.graph['crs']}")


import osmnx as ox
import os

# 1. Load GraphML
G = ox.load_graphml("data/nagpur_roads.graphml")

print("Loaded GraphML...")

# 2. Project to UTM (important for correct geometry in meters)
G_proj = ox.project_graph(G)

print("Graph projected to UTM...")

# 3. Convert graph to GeoDataFrames
nodes, edges = ox.graph_to_gdfs(G_proj)

# 4. Create output folder
output_dir = "data/shapefiles"
os.makedirs(output_dir, exist_ok=True)

# 5. Save Edges (Roads)
edges.to_file(f"{output_dir}/nagpur_roads_edges.shp")

# 6. Save Nodes (Intersections)
nodes.to_file(f"{output_dir}/nagpur_roads_nodes.shp")

print("✅ Shapefiles exported successfully!")
print(f"Saved to: {output_dir}")