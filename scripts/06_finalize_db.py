import geopandas as gpd
from sqlalchemy import create_engine, text

# 1. Database Connection
engine = create_engine('postgresql://postgres:sql123@localhost:5432/vneuron_db')

print("Updating V-NEURON Database with Metric Data...")

# 2. Re-importing PROJECTED layers (using the files from Step 5)
# These files are already in EPSG:32644 (Meters)
metro_proj = gpd.read_file("data/nagpur_metro_projected.geojson")
bus_proj = gpd.read_file("data/nagpur_bus_projected.geojson")

# Use if_exists='replace' to overwrite the old 'Degree' based tables
metro_proj.to_postgis("nagpur_metro_projected", engine, if_exists='replace')
bus_proj.to_postgis("nagpur_bus_projected", engine, if_exists='replace')

print("✅ Projected Transit layers updated.")

# 3. Create Spatial Indexes for fast routing
with engine.connect() as conn:
    # Adding indexes to the geometry columns
    conn.execute(text("CREATE INDEX idx_metro_geom ON nagpur_metro_projected USING GIST (geometry);"))
    conn.execute(text("CREATE INDEX idx_bus_geom ON nagpur_bus_projected USING GIST (geometry);"))
    conn.execute(text("COMMIT;"))

print("✅ Spatial Indexes created for performance.")