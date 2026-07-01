import os
import json
import re
from flask import Flask, request, jsonify, render_template, send_from_directory
import osmnx as ox
import networkx as nx
import geopandas as gpd
from pyproj import Transformer
from geopy.geocoders import Nominatim

app = Flask(__name__, static_folder='static', template_folder='templates')

# Create necessary static directories
os.makedirs('static/css', exist_ok=True)
os.makedirs('static/js', exist_ok=True)
os.makedirs('templates', exist_ok=True)

# Coordinate Transformers: WGS84 (lat, lon) <-> UTM Zone 44N (m)
gps_to_utm = Transformer.from_crs("EPSG:4326", "EPSG:32644", always_xy=True)
utm_to_gps = Transformer.from_crs("EPSG:32644", "EPSG:4326", always_xy=True)

print("Loading V-NEURON graphs...")
G_omni = ox.load_graphml("data/vneuron_omnimodal_final.graphml")
G_calib = ox.load_graphml("data/vneuron_calibrated_network.graphml")
print("Graphs loaded successfully!")

# Initialize Nominatim Geocoder
geolocator = Nominatim(user_agent="vneuron_routing_app_v2")

# Predefined Landmarks & Metro Station Coordinates for Offline/Fast Resolving
landmark_lookup = {
    "hingna": (21.1000, 78.9700),
    "ycce": (21.1004, 78.9782),
    "ycce college": (21.1004, 78.9782),
    "medical square": (21.1345, 79.0984),
    "medical chowk": (21.1345, 79.0984),
    "svpcet": (21.056, 79.027),
    "st. vincent pallotti college": (21.056, 79.027),
    "sitabuldi": (21.146, 79.083),
    "airport": (21.088, 79.058),
    "sadar": (21.161, 79.080),
    "mankapur": (21.189, 79.073),
    "automotive square": (21.203, 79.083),
    "cotton market": (21.150, 79.090),
    "khapri": (21.066, 79.055),
    "vnit": (21.125, 79.049),
    "ramdeobaba": (21.176, 79.061)
}

def load_metro_stations():
    stations = {}
    try:
        with open("data/nagpur_metro.geojson", "r", encoding="utf-8") as f:
            data = json.load(f)
            for feature in data.get("features", []):
                geom = feature.get("geometry", {})
                if geom.get("type") == "Point":
                    coords = geom.get("coordinates")  # [lon, lat]
                    props = feature.get("properties", {})
                    name = props.get("name")
                    if name and coords:
                        stations[name.lower().strip()] = (coords[1], coords[0])  # (lat, lon)
    except Exception as e:
        print(f"Error loading metro stations: {e}")
    return stations

# Load dynamically from geojson and merge
metro_stations = load_metro_stations()
for name, coords in metro_stations.items():
    landmark_lookup[name] = coords

def geocode_place(query):
    if not query:
        return None
    query_clean = query.lower().strip()
    
    # 1. Direct Lookup
    if query_clean in landmark_lookup:
        return landmark_lookup[query_clean]
    
    # 2. Substring Matching
    for key, coords in landmark_lookup.items():
        if query_clean in key or key in query_clean:
            return coords
            
    # 3. Online Geocoding via Nominatim
    try:
        location = geolocator.geocode(query + ", Nagpur, Maharashtra, India", timeout=5)
        if location:
            return (location.latitude, location.longitude)
    except Exception as e:
        print(f"Online Geocoding failed for {query}: {e}")
        
    return None

def parse_coordinate_str(s):
    # Detect if string matches coordinate format: "lat, lon"
    match = re.match(r"^\s*(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)\s*$", s)
    if match:
        return float(match.group(1)), float(match.group(2))
    return None

def resolve_location(query):
    coords = parse_coordinate_str(query)
    if coords:
        return coords
    return geocode_place(query)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/stations', methods=['GET'])
def get_stations():
    # Return sorted list of known landmarks and metro stations
    station_names = sorted(list(landmark_lookup.keys()))
    return jsonify(station_names)

@app.route('/api/route', methods=['POST'])
def get_route():
    data = request.json or {}
    origin_str = data.get('origin', '')
    dest_str = data.get('destination', '')
    scenario = data.get('scenario', 'off_peak')  # off_peak or peak
    mode = data.get('mode', 'all_modes')          # all_modes or road_only
    
    result = compute_route_internal(origin_str, dest_str, scenario, mode)
    return jsonify(result)

@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.json or {}
    message = data.get('message', '')
    
    # Parse natural language query (Rule-Based NLP)
    # Matches patterns like:
    # "from X to Y" or "route from X to Y" or "between X and Y"
    scenario = "off_peak"
    mode = "all_modes"
    
    # Check for traffic / peak hour triggers
    traffic_keywords = ["traffic", "peak hour", "congested", "rush hour", "busy", "8pm", "9am", "5pm", "6pm", "peak"]
    for keyword in traffic_keywords:
        if keyword in message.lower():
            scenario = "peak"
            break
            
    # Check for road only triggers
    road_keywords = ["road only", "drive only", "car only", "by car", "by road", "drive", "driving"]
    for keyword in road_keywords:
        if keyword in message.lower():
            mode = "road_only"
            break
            
    # Parse source and destination
    origin = ""
    destination = ""
    
    # Match "from [X] to [Y]"
    match_from_to = re.search(r"from\s+(.+?)\s+to\s+(.+)", message, re.IGNORECASE)
    if match_from_to:
        origin = match_from_to.group(1).strip()
        destination = match_from_to.group(2).strip()
    else:
        # Match "between [X] and [Y]"
        match_between = re.search(r"between\s+(.+?)\s+and\s+(.+)", message, re.IGNORECASE)
        if match_between:
            origin = match_between.group(1).strip()
            destination = match_between.group(2).strip()
        else:
            # Match "[X] to [Y]"
            match_to = re.search(r"(.+?)\s+to\s+(.+)", message, re.IGNORECASE)
            if match_to:
                origin = match_to.group(1).strip()
                destination = match_to.group(2).strip()
                
    # Clean up punctuation and text after destination (like "it's 8pm")
    if destination:
        # Trim at keywords like "so", "at", "under", "it's", "with" or punctuation
        clean_dest = re.split(r"\s+(?:it's|so|at|under|with|using|in|for|traffic|peak|road)\b|[,.!?]", destination, flags=re.IGNORECASE)[0]
        destination = clean_dest.strip()
    if origin:
        clean_orig = re.split(r"[,.!?]", origin)[0]
        origin = clean_orig.strip()

    if not origin or not destination:
        return jsonify({
            "response": "I couldn't quite extract your start and end locations. Try asking like: *'I want to go from Hingna to Medical Square'*.",
            "route_data": None
        })
        
    # Compute route
    route_result = compute_route_internal(origin, destination, scenario, mode)
    
    if "error" in route_result:
        return jsonify({
            "response": f"I parsed your request as going from **{origin}** to **{destination}**, but encountered an error: {route_result['error']}",
            "route_data": None
        })
        
    route_result['scenario'] = scenario
    route_result['mode'] = mode
        
    # Generate bot message
    dist_km = route_result['total_distance_km']
    time_min = route_result['total_time_min']
    scenario_label = "Peak Hour traffic" if scenario == "peak" else "Off-Peak free flow"
    mode_label = "Road Driving Only" if mode == "road_only" else "Multimodal (Walk + Metro + Drive)"
    
    response_msg = (
        f"Calculated multimodal path. Distance: **{dist_km:.2f} km**. Travel time: **{time_min:.1f} mins**.\n\n"
        f"Configured Route: **{route_result['origin_name']}** → **{route_result['destination_name']}**\n"
        f"Scenario: *{scenario_label}* | Mode: *{mode_label}*"
    )
    
    return jsonify({
        "response": response_msg,
        "route_data": route_result
    })

def compute_route_internal(origin_str, dest_str, scenario, mode):
    orig_coords = resolve_location(origin_str)
    dest_coords = resolve_location(dest_str)
    
    if not orig_coords:
        return {"error": f"Could not resolve origin place: '{origin_str}'"}
    if not dest_coords:
        return {"error": f"Could not resolve destination place: '{dest_str}'"}
        
    orig_lat, orig_lon = orig_coords
    dest_lat, dest_lon = dest_coords
    
    # Choose network graph
    G = G_calib if scenario == "peak" else G_omni
    
    # Filter for road only if required
    if mode == "road_only":
        road_edges = []
        for u, v, k, data in G.edges(data=True, keys=True):
            if data.get('highway') not in ['subway', 'footway']:
                road_edges.append((u, v, k))
        G_active = G.edge_subgraph(road_edges)
    else:
        G_active = G
        
    # Convert GPS to UTM Zone 44N (Meters)
    utm_x_orig, utm_y_orig = gps_to_utm.transform(orig_lon, orig_lat)
    utm_x_dest, utm_y_dest = gps_to_utm.transform(dest_lon, dest_lat)
    
    try:
        orig_node = ox.distance.nearest_nodes(G_active, X=utm_x_orig, Y=utm_y_orig)
        dest_node = ox.distance.nearest_nodes(G_active, X=utm_x_dest, Y=utm_y_dest)
    except Exception as e:
        return {"error": f"Could not find nearest network intersections: {e}"}
        
    try:
        route = nx.shortest_path(G_active, orig_node, dest_node, weight='travel_time')
    except nx.NetworkXNoPath:
        return {"error": "No viable path found between these points under the selected transportation mode."}
        
    path_coords = []
    segments = []
    
    # Start Coord
    path_coords.append([orig_lat, orig_lon])
    
    node_start = G_active.nodes[orig_node]
    first_lon, first_lat = utm_to_gps.transform(node_start['x'], node_start['y'])
    path_coords.append([first_lat, first_lon])
    
    # Starting Walk Segment to snapping node
    walk_dist = ox.distance.euclidean(utm_y_orig, utm_x_orig, node_start['y'], node_start['x'])
    walk_time = walk_dist / 1.25  # 1.25 m/s
    if walk_dist > 15:
        segments.append({
            "mode": "Walk",
            "length_m": walk_dist,
            "time_sec": walk_time,
            "name": "Walk to main network"
        })
        
    current_mode = None
    current_segment_len = 0
    current_segment_time = 0
    current_segment_name = ""
    
    for i in range(len(route) - 1):
        u, v = route[i], route[i+1]
        edge_data = G_active.get_edge_data(u, v)
        if not edge_data:
            continue
        data = list(edge_data.values())[0]
        
        length = data.get('length', 0)
        travel_time = data.get('travel_time', 0)
        hwy = data.get('highway', 'road')
        name = data.get('name', '')
        if isinstance(name, list):
            name = ", ".join(str(n) for n in name)
        
        # Mode Identification
        if hwy == 'subway':
            seg_mode = 'Metro'
        elif hwy == 'footway':
            seg_mode = 'Walk'
        else:
            seg_mode = 'Road'
            
        # Coordinates tracing
        edge_coords = []
        if 'geometry' in data:
            geom = data['geometry']
            for x, y in geom.coords:
                lon, lat = utm_to_gps.transform(x, y)
                edge_coords.append([lat, lon])
        else:
            n1 = G_active.nodes[u]
            n2 = G_active.nodes[v]
            lon1, lat1 = utm_to_gps.transform(n1['x'], n1['y'])
            lon2, lat2 = utm_to_gps.transform(n2['x'], n2['y'])
            edge_coords = [[lat1, lon1], [lat2, lon2]]
            
        for pt in edge_coords:
            if not path_coords or path_coords[-1] != pt:
                path_coords.append(pt)
                
        # Group similar modes
        if seg_mode != current_mode:
            if current_mode is not None:
                segments.append({
                    "mode": current_mode,
                    "length_m": current_segment_len,
                    "time_sec": current_segment_time,
                    "name": current_segment_name
                })
            current_mode = seg_mode
            current_segment_len = length
            current_segment_time = travel_time
            current_segment_name = name if name else f"{seg_mode} Link"
        else:
            current_segment_len += length
            current_segment_time += travel_time
            if name and name not in current_segment_name:
                current_segment_name = name if not current_segment_name else f"{current_segment_name}, {name}"
                
    # Add final network segment
    if current_mode is not None:
        segments.append({
            "mode": current_mode,
            "length_m": current_segment_len,
            "time_sec": current_segment_time,
            "name": current_segment_name
        })
        
    # Last Walk Segment to actual destination coords
    node_end = G_active.nodes[dest_node]
    dest_lon_snap, dest_lat_snap = utm_to_gps.transform(node_end['x'], node_end['y'])
    walk_dist_end = ox.distance.euclidean(utm_y_dest, utm_x_dest, node_end['y'], node_end['x'])
    walk_time_end = walk_dist_end / 1.25
    if walk_dist_end > 15:
        segments.append({
            "mode": "Walk",
            "length_m": walk_dist_end,
            "time_sec": walk_time_end,
            "name": "Walk to destination"
        })
        
    path_coords.append([dest_lat, dest_lon])
    
    total_distance_km = sum(seg["length_m"] for seg in segments) / 1000.0
    total_time_min = sum(seg["time_sec"] for seg in segments) / 60.0
    
    # Pretty names
    orig_name = origin_str if isinstance(origin_str, str) else f"{orig_lat:.4f}, {orig_lon:.4f}"
    dest_name = dest_str if isinstance(dest_str, str) else f"{dest_lat:.4f}, {dest_lon:.4f}"
    
    # Capitalize names for formatting
    orig_name = orig_name.title()
    dest_name = dest_name.title()
    
    # Format segment list for UI rendering
    formatted_segments = []
    for s in segments:
        formatted_segments.append({
            "mode": s["mode"],
            "length_km": round(s["length_m"] / 1000.0, 2),
            "time_min": round(s["time_sec"] / 60.0, 1),
            "name": s["name"]
        })
        
    return {
        "origin_name": orig_name,
        "destination_name": dest_name,
        "origin_coords": [orig_lat, orig_lon],
        "destination_coords": [dest_lat, dest_lon],
        "total_distance_km": round(total_distance_km, 2),
        "total_time_min": round(total_time_min, 1),
        "path_coords": path_coords,
        "segments": formatted_segments
    }

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
