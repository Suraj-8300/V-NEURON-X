import geopandas as gpd
from sqlalchemy import create_engine
import osmnx as ox

# 1. Database Connection String
# Replace with your actual password
engine = create_engine('postgresql://postgres:sql123@localhost:5432/vneuron_db')

print("Starting Database Import...")

# 2. Import Road Network
# We reload the graph we saved earlier and convert to GeoDataFrames
G = ox.load_graphml("data/nagpur_roads.graphml")
nodes, edges = ox.graph_to_gdfs(G)

# Push Roads to PostGIS
edges.to_postgis("nagpur_roads", engine, if_exists='replace')
nodes.to_postgis("nagpur_road_nodes", engine, if_exists='replace')
print("✅ Road Network imported (Nodes and Edges).")

# 3. Import Transit Layers
metro = gpd.read_file("data/nagpur_metro.geojson")
bus = gpd.read_file("data/nagpur_bus_stops.geojson")

# Push Transit to PostGIS
metro.to_postgis("nagpur_metro", engine, if_exists='replace')
bus.to_postgis("nagpur_bus", engine, if_exists='replace')
print("✅ Metro and Bus layers imported.")

print("\n--- V-NEURON Database is now Live ---")