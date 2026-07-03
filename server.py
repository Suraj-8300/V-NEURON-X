import os
import re
import json
import pickle
import difflib
import functools
import time
from flask import Flask, request, jsonify, render_template
from pyproj import Transformer
from geopy.geocoders import Nominatim
import osmnx as ox
import networkx as nx

app = Flask(__name__, static_folder='static', template_folder='templates')

# ---------------------------------------------------------------------------
# CORS support for cross-origin frontend requests
# ---------------------------------------------------------------------------
@app.before_request
def before_request():
    if request.method == 'OPTIONS':
        response = app.make_response('')
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
        return response

@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response

# Create necessary static directories
os.makedirs('static/css', exist_ok=True)
os.makedirs('static/js', exist_ok=True)
os.makedirs('templates', exist_ok=True)

# ---------------------------------------------------------------------------
# Coordinate Transformers  (module-level singletons)
# ---------------------------------------------------------------------------
gps_to_utm = Transformer.from_crs("EPSG:4326", "EPSG:32644", always_xy=True)
utm_to_gps = Transformer.from_crs("EPSG:32644", "EPSG:4326", always_xy=True)

# Pre-compiled coordinate string pattern  →  avoids recompiling on every call
_COORD_RE = re.compile(r"^\s*(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)\s*$")

# ---------------------------------------------------------------------------
# Data directory resolution
# ---------------------------------------------------------------------------
def get_data_dir():
    if os.path.exists(os.path.join("backend", "data", "vneuron_omnimodal_final.graphml")):
        return os.path.join("backend", "data")
    if os.path.isfile("data"):
        try:
            with open("data", "r", encoding="utf-8") as f:
                target = f.read().strip()
                if os.path.exists(target):
                    return target
        except Exception:
            pass
    return "data"

DATA_DIR = get_data_dir()
print(f"[startup] Resolved data directory: {DATA_DIR}")

# ---------------------------------------------------------------------------
# Graph loading
# ---------------------------------------------------------------------------
def load_graph(base_name):
    pkl_path = os.path.join(DATA_DIR, f"{base_name}.pickle")
    xml_path = os.path.join(DATA_DIR, f"{base_name}.graphml")
    if os.path.exists(pkl_path):
        print(f"[startup] Loading {base_name} from pickle…")
        try:
            with open(pkl_path, "rb") as f:
                return pickle.load(f)
        except Exception as e:
            print(f"[startup] Pickle failed ({e}), falling back to GraphML…")
    if os.path.exists(xml_path):
        print(f"[startup] Loading {base_name} from GraphML…")
        return ox.load_graphml(xml_path)
    raise FileNotFoundError(f"No graph file found for {base_name} in {DATA_DIR}")

t0 = time.time()
print("[startup] Loading V-NEURON graphs…")
G_omni  = load_graph("vneuron_omnimodal_final")
G_calib = load_graph("vneuron_calibrated_network")
print(f"[startup] Graphs loaded in {time.time() - t0:.1f}s")

# ---------------------------------------------------------------------------
# OPT-1: Pre-compute road-only subgraphs at startup
#         Previously these were rebuilt on EVERY /api/route request by
#         iterating all ~250 k edges — now done once and reused.
# ---------------------------------------------------------------------------
def _build_road_subgraph(G):
    road_edges = [
        (u, v, k)
        for u, v, k, d in G.edges(data=True, keys=True)
        if d.get('highway') not in ('subway', 'footway')
    ]
    return G.edge_subgraph(road_edges)

print("[startup] Pre-computing road-only subgraphs…")
G_omni_road  = _build_road_subgraph(G_omni)
G_calib_road = _build_road_subgraph(G_calib)

# Convenience selector: (scenario, mode) → graph
_GRAPH_MAP = {
    ("off_peak", "all_modes"):  G_omni,
    ("off_peak", "road_only"):  G_omni_road,
    ("peak",     "all_modes"):  G_calib,
    ("peak",     "road_only"):  G_calib_road,
}

# ---------------------------------------------------------------------------
# OPT-2: Pre-warm OSMnx KD-tree spatial index
#         nearest_nodes builds a KD-tree internally on first call per graph.
#         Calling it once at startup means user requests skip this penalty.
# ---------------------------------------------------------------------------
print("[startup] Pre-warming spatial indexes…")
_NAGPUR_CENTER_UTM = gps_to_utm.transform(79.0882, 21.1458)  # lon, lat → x, y
for _G in (G_omni, G_calib, G_omni_road, G_calib_road):
    try:
        ox.distance.nearest_nodes(_G, X=_NAGPUR_CENTER_UTM[0], Y=_NAGPUR_CENTER_UTM[1])
    except Exception:
        pass
print(f"[startup] Ready in {time.time() - t0:.1f}s total")

# ---------------------------------------------------------------------------
# Geocoder
# ---------------------------------------------------------------------------
geolocator = Nominatim(user_agent="vneuron_routing_app_v2")

# Predefined landmarks
landmark_lookup = {
    "hingna":                    (21.1000, 78.9700),
    "ycce":                      (21.1004, 78.9782),
    "ycce college":              (21.1004, 78.9782),
    "medical square":            (21.1345, 79.0984),
    "medical chowk":             (21.1345, 79.0984),
    "svpcet":                    (21.056,  79.027),
    "st. vincent pallotti college": (21.056, 79.027),
    "sitabuldi":                 (21.146,  79.083),
    "airport":                   (21.088,  79.058),
    "sadar":                     (21.161,  79.080),
    "mankapur":                  (21.189,  79.073),
    "automotive square":         (21.203,  79.083),
    "cotton market":             (21.150,  79.090),
    "khapri":                    (21.066,  79.055),
    "vnit":                      (21.125,  79.049),
    "ramdeobaba":                (21.176,  79.061),
}

def load_metro_stations():
    stations = {}
    try:
        metro_path = os.path.join(DATA_DIR, "nagpur_metro.geojson")
        with open(metro_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            for feature in data.get("features", []):
                geom  = feature.get("geometry", {})
                props = feature.get("properties", {})
                if geom.get("type") == "Point":
                    coords = geom.get("coordinates")
                    name   = props.get("name")
                    if name and coords:
                        stations[name.lower().strip()] = (coords[1], coords[0])
    except Exception as e:
        print(f"[warn] Could not load metro stations: {e}")
    return stations

metro_stations = load_metro_stations()
landmark_lookup.update(metro_stations)

# Pre-build sorted keys list for fuzzy matching (avoids rebuilding on every miss)
_LANDMARK_KEYS = list(landmark_lookup.keys())

# ---------------------------------------------------------------------------
# Geocoding — 4-tier: direct → substring → fuzzy → Nominatim
# OPT-3: Results cached in a dict so identical queries never recompute.
# ---------------------------------------------------------------------------
_location_cache: dict = {}

def geocode_place(query: str):
    """Returns (coords_tuple, canonical_name) or (None, None)."""
    query_clean = query.lower().strip()

    # 1. Direct lookup
    if query_clean in landmark_lookup:
        return landmark_lookup[query_clean], query_clean

    # 2. Substring match
    for key, coords in landmark_lookup.items():
        if query_clean in key or key in query_clean:
            return coords, key

    # 3. Fuzzy / spelling correction
    matches = difflib.get_close_matches(query_clean, _LANDMARK_KEYS, n=1, cutoff=0.70)
    if matches:
        matched_key = matches[0]
        print(f"[geocode] Spelling corrected: '{query_clean}' → '{matched_key}'")
        return landmark_lookup[matched_key], matched_key

    # 4. Online Nominatim fallback
    try:
        location = geolocator.geocode(query + ", Nagpur, Maharashtra, India", timeout=5)
        if location:
            return (location.latitude, location.longitude), query
    except Exception as e:
        print(f"[geocode] Nominatim failed for '{query}': {e}")

    return None, None


def parse_coordinate_str(s: str):
    m = _COORD_RE.match(s)
    if m:
        return float(m.group(1)), float(m.group(2))
    return None


def resolve_location(query: str):
    """Returns (coords, canonical_name).  Results are cached."""
    if query in _location_cache:
        return _location_cache[query]
    coords = parse_coordinate_str(query)
    if coords:
        result = coords, query
    else:
        result = geocode_place(query)
    _location_cache[query] = result
    return result

# ---------------------------------------------------------------------------
# Flask routes
# ---------------------------------------------------------------------------
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/stations', methods=['GET'])
def get_stations():
    return __import__('flask').jsonify(sorted(_LANDMARK_KEYS))

@app.route('/api/landmarks/detailed', methods=['GET'])
def get_detailed_landmarks():
    metro_names = set(metro_stations.keys())
    detailed = [
        {
            "name":   name.title(),
            "coords": coords,
            "type":   "metro" if name in metro_names else "landmark",
        }
        for name, coords in landmark_lookup.items()
    ]
    return __import__('flask').jsonify(detailed)

@app.route('/api/route', methods=['POST'])
def get_route():
    data     = request.json or {}
    origin   = data.get('origin',   '')
    dest     = data.get('destination', '')
    scenario = data.get('scenario', 'off_peak')
    mode     = data.get('mode',     'all_modes')
    result   = compute_route_internal(origin, dest, scenario, mode)
    return __import__('flask').jsonify(result)

@app.route('/api/chat', methods=['POST'])
def chat():
    data    = request.json or {}
    message = data.get('message', '')

    scenario = "off_peak"
    mode     = "all_modes"

    # Traffic scenario detection
    traffic_keywords = ["traffic", "peak hour", "congested", "rush hour",
                        "busy", "8pm", "9am", "5pm", "6pm", "peak"]
    if any(kw in message.lower() for kw in traffic_keywords):
        scenario = "peak"

    # Road-only mode detection
    road_keywords = ["road only", "drive only", "car only", "by car", "by road",
                     "drive", "driving"]
    if any(kw in message.lower() for kw in road_keywords):
        mode = "road_only"

    # Parse origin / destination from natural language
    origin = destination = ""

    m = re.search(r"from\s+(.+?)\s+to\s+(.+)", message, re.IGNORECASE)
    if m:
        origin, destination = m.group(1).strip(), m.group(2).strip()
    else:
        m = re.search(r"between\s+(.+?)\s+and\s+(.+)", message, re.IGNORECASE)
        if m:
            origin, destination = m.group(1).strip(), m.group(2).strip()
        else:
            m = re.search(r"(.+?)\s+to\s+(.+)", message, re.IGNORECASE)
            if m:
                origin, destination = m.group(1).strip(), m.group(2).strip()

    # Trim trailing context words and punctuation
    if destination:
        destination = re.split(
            r"\s+(?:it's|so|at|under|with|using|in|for|traffic|peak|road)\b|[,.!?]",
            destination, flags=re.IGNORECASE
        )[0].strip()
    if origin:
        origin = re.split(r"[,.!?]", origin)[0].strip()

    if not origin or not destination:
        return __import__('flask').jsonify({
            "response": (
                "I couldn't extract your start and end locations. "
                "Try: *'I want to go from Hingna to Medical Square'*."
            ),
            "route_data": None
        })

    route_result = compute_route_internal(origin, destination, scenario, mode)

    if "error" in route_result:
        return __import__('flask').jsonify({
            "response": (
                f"I understood the route as **{origin}** → **{destination}**, "
                f"but hit an error: {route_result['error']}"
            ),
            "route_data": None
        })

    route_result['scenario'] = scenario
    route_result['mode']     = mode

    dist_km        = route_result['total_distance_km']
    time_min       = route_result['total_time_min']
    scenario_label = "Peak Hour traffic" if scenario == "peak" else "Off-Peak free flow"
    mode_label     = "Road Driving Only" if mode == "road_only" else "Multimodal (Walk + Metro + Drive)"

    response_msg = (
        f"Calculated multimodal path. "
        f"Distance: **{dist_km:.2f} km**. Travel time: **{time_min:.1f} mins**.\n\n"
        f"Configured Route: **{route_result['origin_name']}** → **{route_result['destination_name']}**\n"
        f"Scenario: *{scenario_label}* | Mode: *{mode_label}*"
    )

    return __import__('flask').jsonify({"response": response_msg, "route_data": route_result})

# ---------------------------------------------------------------------------
# Core routing  — heavily optimised
# ---------------------------------------------------------------------------

# OPT-4: Route-level LRU cache
#         Identical (origin, dest, scenario, mode) tuples skip all graph work.
#         maxsize=128 covers ~128 unique recent queries in memory.
@functools.lru_cache(maxsize=128)
def _route_cached(origin_str: str, dest_str: str, scenario: str, mode: str):
    """Inner cached function.  Returns a frozen result dict (as a tuple of items)."""
    return _route_compute(origin_str, dest_str, scenario, mode)


def compute_route_internal(origin_str: str, dest_str: str, scenario: str, mode: str):
    """Public entry — resolves locations then delegates to the LRU-cached core."""
    orig_coords, resolved_orig = resolve_location(origin_str)
    dest_coords, resolved_dest = resolve_location(dest_str)

    if not orig_coords:
        return {"error": f"Could not resolve origin: '{origin_str}'"}
    if not dest_coords:
        return {"error": f"Could not resolve destination: '{dest_str}'"}

    # Build a normalised cache key using resolved canonical names
    cache_key = (
        resolved_orig or origin_str,
        resolved_dest or dest_str,
        scenario,
        mode,
    )
    result = _route_cached(*cache_key)

    # _route_cached may itself return an error dict
    return result


def _route_compute(origin_str: str, dest_str: str, scenario: str, mode: str):
    """
    Actual routing logic.  Called only on cache misses.
    Uses bidirectional Dijkstra (2–5× faster than unidirectional on large graphs).
    """
    orig_coords, _ = resolve_location(origin_str)
    dest_coords, _ = resolve_location(dest_str)

    if not orig_coords:
        return {"error": f"Could not resolve origin: '{origin_str}'"}
    if not dest_coords:
        return {"error": f"Could not resolve destination: '{dest_str}'"}

    orig_lat, orig_lon = orig_coords
    dest_lat, dest_lon = dest_coords

    # OPT-1 payoff: pick pre-built graph directly — no per-request edge iteration
    G_active = _GRAPH_MAP.get((scenario, mode), G_omni)

    # GPS → UTM
    utm_x_orig, utm_y_orig = gps_to_utm.transform(orig_lon, orig_lat)
    utm_x_dest, utm_y_dest = gps_to_utm.transform(dest_lon, dest_lat)

    try:
        orig_node = ox.distance.nearest_nodes(G_active, X=utm_x_orig, Y=utm_y_orig)
        dest_node = ox.distance.nearest_nodes(G_active, X=utm_x_dest, Y=utm_y_dest)
    except Exception as e:
        return {"error": f"Could not snap to road network: {e}"}

    # OPT-5: Bidirectional Dijkstra — significantly faster than nx.shortest_path
    #         on large sparse graphs because it expands from both ends simultaneously.
    try:
        _, route = nx.bidirectional_dijkstra(
            G_active, orig_node, dest_node, weight='travel_time'
        )
    except nx.NetworkXNoPath:
        return {"error": "No viable path found between these points under the selected mode."}
    except nx.NodeNotFound as e:
        return {"error": f"Node not found in graph: {e}"}

    # ---- Build path coordinates & segments ----
    path_coords = [[orig_lat, orig_lon]]
    segments    = []
    utm_points  = []

    node_start = G_active.nodes[orig_node]
    utm_points.append((node_start['x'], node_start['y']))

    # Walk segment from user location to nearest network node
    walk_dist = ox.distance.euclidean(utm_y_orig, utm_x_orig, node_start['y'], node_start['x'])
    if walk_dist > 15:
        segments.append({
            "mode": "Walk", "length_m": walk_dist,
            "time_sec": walk_dist / 1.25, "name": "Walk to main network"
        })

    current_mode = current_len = current_time = None
    current_name = ""

    for i in range(len(route) - 1):
        u, v = route[i], route[i + 1]
        edge_data = G_active.get_edge_data(u, v)
        if not edge_data:
            continue
        d = list(edge_data.values())[0]

        length      = d.get('length', 0)
        travel_time = d.get('travel_time', 0)
        hwy         = d.get('highway', 'road')
        name        = d.get('name', '')
        if isinstance(name, list):
            name = ", ".join(str(n) for n in name)

        seg_mode = 'Metro' if hwy == 'subway' else ('Walk' if hwy == 'footway' else 'Road')

        # Collect UTM coordinates for batch transform
        if 'geometry' in d:
            utm_points.extend(d['geometry'].coords)
        else:
            n1, n2 = G_active.nodes[u], G_active.nodes[v]
            utm_points.append((n1['x'], n1['y']))
            utm_points.append((n2['x'], n2['y']))

        # Merge consecutive segments of the same mode
        if seg_mode != current_mode:
            if current_mode is not None:
                segments.append({
                    "mode": current_mode, "length_m": current_len,
                    "time_sec": current_time, "name": current_name
                })
            current_mode = seg_mode
            current_len  = length
            current_time = travel_time
            current_name = name or f"{seg_mode} Link"
        else:
            current_len  += length
            current_time += travel_time
            if name and name not in current_name:
                current_name = name if not current_name else f"{current_name}, {name}"

    if current_mode is not None:
        segments.append({
            "mode": current_mode, "length_m": current_len,
            "time_sec": current_time, "name": current_name
        })

    # Walk segment from last network node to destination
    node_end = G_active.nodes[dest_node]
    walk_dist_end = ox.distance.euclidean(utm_y_dest, utm_x_dest, node_end['y'], node_end['x'])
    if walk_dist_end > 15:
        segments.append({
            "mode": "Walk", "length_m": walk_dist_end,
            "time_sec": walk_dist_end / 1.25, "name": "Walk to destination"
        })
    utm_points.append((node_end['x'], node_end['y']))

    # Batch UTM → GPS transform (single vectorised call)
    if utm_points:
        xs   = [pt[0] for pt in utm_points]
        ys   = [pt[1] for pt in utm_points]
        lons, lats = utm_to_gps.transform(xs, ys)
        for lat, lon in zip(lats, lons):
            pt = [lat, lon]
            if not path_coords or path_coords[-1] != pt:
                path_coords.append(pt)

    path_coords.append([dest_lat, dest_lon])

    total_dist_km = sum(s["length_m"] for s in segments) / 1000.0
    total_time_min = sum(s["time_sec"] for s in segments) / 60.0

    orig_name = (origin_str if isinstance(origin_str, str)
                 else f"{orig_lat:.4f}, {orig_lon:.4f}").title()
    dest_name = (dest_str if isinstance(dest_str, str)
                 else f"{dest_lat:.4f}, {dest_lon:.4f}").title()

    return {
        "origin_name":        orig_name,
        "destination_name":   dest_name,
        "origin_coords":      [orig_lat, orig_lon],
        "destination_coords": [dest_lat, dest_lon],
        "total_distance_km":  round(total_dist_km, 2),
        "total_time_min":     round(total_time_min, 1),
        "path_coords":        path_coords,
        "segments": [
            {
                "mode":       s["mode"],
                "length_km":  round(s["length_m"] / 1000.0, 2),
                "time_min":   round(s["time_sec"] / 60.0, 1),
                "name":       s["name"],
            }
            for s in segments
        ],
    }


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 7860))
    app.run(debug=True, host='0.0.0.0', port=port)
