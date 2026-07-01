// V-NEURON - Frontend Script

// Global State
let map;
let baseLayers = {};
let originMarker = null;
let destinationMarker = null;
let routeLayersGroup = null;
let trackerMarker = null;

let currentScenario = 'off_peak';
let currentMode = 'all_modes';
let knownLandmarks = [];

// Simulation State
let routeCoords = [];
let trackerIndex = 0;
let trackerTimer = null;
let simSpeed = 1;
let isTracking = false;

// Initialize Web App
document.addEventListener("DOMContentLoaded", () => {
    initMap();
    loadStations();
    initEventListeners();
});

// 1. Initialize Leaflet Map
function initMap() {
    // Center Nagpur
    map = L.map('map', {
        zoomControl: true,
        attributionControl: true
    }).setView([21.1458, 79.0882], 13);

    // CartoDB Positron - Light and clean basemap
    const lightTiles = L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
        subdomains: 'abcd',
        maxZoom: 20
    }).addTo(map);

    const osmTiles = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    });

    baseLayers = {
        "Light Vector Map": lightTiles,
        "Street Map (OSM)": osmTiles
    };

    L.control.layers(baseLayers, null, { position: 'topright' }).addTo(map);
    
    // Group for holding route polylines
    routeLayersGroup = L.featureGroup().addTo(map);

    // Map Click Listener to select pins
    map.on('click', onMapClick);
}

// 2. Fetch autocomplete landmarks
async function loadStations() {
    try {
        const response = await fetch('/api/stations');
        knownLandmarks = await response.json();
        const datalist = document.getElementById("stations-list");
        datalist.innerHTML = "";
        knownLandmarks.forEach(station => {
            const option = document.createElement("option");
            option.value = station;
            datalist.appendChild(option);
        });
    } catch (e) {
        console.error("Failed to load known landmarks: ", e);
    }
}

// Event Listeners setup
function initEventListeners() {
    // Setup inputs click highlight
    const inputs = ['origin', 'destination'];
    inputs.forEach(id => {
        const el = document.getElementById(id);
        el.addEventListener('focus', () => {
            el.select();
        });
    });
}

// Map Click coordinate Snapping
function onMapClick(e) {
    const lat = parseFloat(e.latlng.lat.toFixed(6));
    const lon = parseFloat(e.latlng.lng.toFixed(6));
    const coordStr = `${lat}, ${lon}`;

    const originInput = document.getElementById("origin");
    const destInput = document.getElementById("destination");

    // Click fills empty fields first, or active fields, or overrides destination
    if (!originInput.value) {
        originInput.value = coordStr;
        setOriginMarker([lat, lon]);
    } else if (!destInput.value) {
        destInput.value = coordStr;
        setDestinationMarker([lat, lon]);
        // Auto-calculate when destination is clicked/set
        calculateRoute();
    } else {
        // Override destination
        destInput.value = coordStr;
        setDestinationMarker([lat, lon]);
        calculateRoute();
    }
}

function setOriginMarker(coords) {
    if (originMarker) {
        originMarker.setLatLng(coords);
    } else {
        originMarker = L.marker(coords, {
            draggable: true,
            icon: L.divIcon({
                className: 'custom-pin-origin',
                html: '<div style="background:#2563eb; width:22px; height:22px; border-radius:50%; border:3px solid white; box-shadow:0 2px 8px rgba(0,0,0,0.3); display:flex; align-items:center; justify-content:center; color:white; font-size:10px;"><i class="fa-solid fa-play"></i></div>',
                iconSize: [22, 22],
                iconAnchor: [11, 11]
            })
        }).addTo(map);

        originMarker.on('dragend', function (event) {
            const marker = event.target;
            const position = marker.getLatLng();
            document.getElementById("origin").value = `${position.lat.toFixed(6)}, ${position.lng.toFixed(6)}`;
            calculateRoute();
        });
    }
}

function setDestinationMarker(coords) {
    if (destinationMarker) {
        destinationMarker.setLatLng(coords);
    } else {
        destinationMarker = L.marker(coords, {
            draggable: true,
            icon: L.divIcon({
                className: 'custom-pin-dest',
                html: '<div style="background:#ef4444; width:22px; height:22px; border-radius:50%; border:3px solid white; box-shadow:0 2px 8px rgba(0,0,0,0.3); display:flex; align-items:center; justify-content:center; color:white; font-size:10px;"><i class="fa-solid fa-flag"></i></div>',
                iconSize: [22, 22],
                iconAnchor: [11, 11]
            })
        }).addTo(map);

        destinationMarker.on('dragend', function (event) {
            const marker = event.target;
            const position = marker.getLatLng();
            document.getElementById("destination").value = `${position.lat.toFixed(6)}, ${position.lng.toFixed(6)}`;
            calculateRoute();
        });
    }
}

// Time Scenario toggles
function setScenario(scen) {
    currentScenario = scen;
    document.getElementById("btn-off-peak").classList.toggle("active", scen === 'off_peak');
    document.getElementById("btn-peak").classList.toggle("active", scen === 'peak');
    
    // Recalculate if route is already drawn
    if (document.getElementById("origin").value && document.getElementById("destination").value) {
        calculateRoute();
    }
}

// Mode Selection toggles
function setMode(mode) {
    currentMode = mode;
    document.getElementById("btn-all-modes").classList.toggle("active", mode === 'all_modes');
    document.getElementById("btn-road-only").classList.toggle("active", mode === 'road_only');
    
    if (document.getElementById("origin").value && document.getElementById("destination").value) {
        calculateRoute();
    }
}

// 3. Trigger Routing calculation API
async function calculateRoute() {
    const originVal = document.getElementById("origin").value.trim();
    const destVal = document.getElementById("destination").value.trim();

    if (!originVal || !destVal) {
        alert("Please enter both Start and Destination points.");
        return;
    }

    // Set UI loading state
    const calcBtn = document.getElementById("btn-calculate");
    calcBtn.disabled = true;
    calcBtn.innerHTML = '<i class="fa-solid fa-circle-notch fa-spin"></i> Calculating...';

    try {
        const response = await fetch('/api/route', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                origin: originVal,
                destination: destVal,
                scenario: currentScenario,
                mode: currentMode
            })
        });

        const result = await response.json();
        
        if (result.error) {
            alert(result.error);
            resetRouteState();
        } else {
            drawRoute(result);
        }
    } catch (e) {
        console.error(e);
        alert("Error connecting to V-NEURON routing service.");
    } finally {
        calcBtn.disabled = false;
        calcBtn.innerHTML = 'Calculate Route';
    }
}

function resetRouteState() {
    routeLayersGroup.clearLayers();
    routeCoords = [];
    resetTracking();
    document.getElementById("route-details").classList.add("hidden");
    document.getElementById("simulator-panel").classList.add("hidden");
}

// 4. Render Route on Leaflet Map
function drawRoute(data) {
    // Clean old path drawings
    routeLayersGroup.clearLayers();
    resetTracking();

    routeCoords = data.path_coords;

    // Ensure markers are placed at exact resolved locations
    setOriginMarker(data.origin_coords);
    setDestinationMarker(data.destination_coords);

    // Set field values to titles
    document.getElementById("origin").value = data.origin_name;
    document.getElementById("destination").value = data.destination_name;

    // Split coordinates by modes to draw color-coded paths
    // Iterate through segments and slice coordinate array
    let coordPointer = 0;
    
    data.segments.forEach(seg => {
        // Approximate coordinates belonging to this segment based on its percentage length
        // To be precise, since coordinates map to intersections, we track the coordinate indexing
        // We will match coordinates along the segment line.
        // We draw individual sub-polylines representing segments.
        const segMode = seg.mode;
        const segName = seg.name;
        
        let pathColor = '#2563eb'; // Default Road (Blue)
        let isDashed = false;
        
        if (segMode === 'Walk') {
            pathColor = '#d97706'; // Walking (Orange/Brown)
            isDashed = true;
        } else if (segMode === 'Metro') {
            // Distinguish Orange vs Aqua line
            if (segName.includes("Orange Line")) {
                pathColor = '#ea580c'; // Orange Line
            } else if (segName.includes("Aqua Line")) {
                pathColor = '#0891b2'; // Aqua Line
            } else {
                pathColor = '#10b981'; // General Subway (Green)
            }
        }
        
        // Find segment coordinate coordinates (segment boundaries are approximate based on distance)
    });

    // Let's draw a full path but styled by mode
    // To draw it cleanly, we can draw the route polylines. Let's do it using segments
    // Or simpler, let's draw the continuous coordinate polyline.
    // For stunning look: We trace each segment. Let's trace it and draw:
    // To do this, let's look at coordinate bounds. Since backend segments are computed in order, 
    // we can draw the path segments by mapping node coords or mapping continuous indices:
    let remainingCoords = [...routeCoords];
    
    // Draw base line for the entire route
    const basePolyline = L.polyline(routeCoords, {
        color: '#94a3b8',
        weight: 8,
        opacity: 0.4
    }).addTo(routeLayersGroup);

    // Draw the active color-coded overlay path
    // We will segment the polyline. To do this, let's compute coordinates for each segment.
    // We can estimate coordinate count proportional to distance, or backend can provide segments coordinates.
    // Let's do a sliding window of coordinates matching segment distances.
    // Since coordinates are ordered, we can map segments directly to segments coordinates.
    // To be perfectly accurate and simple: we draw the overall polyline color-coded based on transit modes.
    // Since we want high-end styling, let's slice routeCoords into matching sub-lines.
    // Let's map each edge coordinate. In server.py, we have segment-specific properties.
    // Let's draw segment lines:
    let startIdx = 0;
    
    data.segments.forEach(seg => {
        // Estimate number of points in segment. We divide total routeCoords length proportionally
        // to segment distance. This is an approximation but works beautifully for rendering!
        const totalDist = data.total_distance_km * 1000; // m
        const segDist = seg.length_km * 1000; // m
        
        let pointCount = Math.round((segDist / totalDist) * routeCoords.length);
        if (pointCount < 2) pointCount = 2;
        
        let endIdx = startIdx + pointCount;
        if (endIdx > routeCoords.length) endIdx = routeCoords.length;
        if (startIdx >= routeCoords.length - 1) return;

        const segCoords = routeCoords.slice(startIdx, endIdx);
        startIdx = endIdx - 1; // overlap by 1 point to avoid visual gaps

        if (segCoords.length < 2) return;

        let pathColor = '#3b82f6'; // Road
        let isDashed = false;
        let lineWeight = 6;

        if (seg.mode === 'Walk') {
            pathColor = '#f59e0b'; // Walk
            isDashed = true;
            lineWeight = 4;
        } else if (seg.mode === 'Metro') {
            lineWeight = 8;
            if (seg.name.includes("Orange Line")) {
                pathColor = '#f97316';
            } else if (seg.name.includes("Aqua Line")) {
                pathColor = '#06b6d4';
            } else {
                pathColor = '#10b981';
            }
        }

        const poly = L.polyline(segCoords, {
            color: pathColor,
            weight: lineWeight,
            opacity: 0.9,
            dashArray: isDashed ? '5, 8' : null,
            lineJoin: 'round',
            lineCap: 'round'
        }).addTo(routeLayersGroup);
        
        poly.bindPopup(`<b>${seg.mode} Segment</b><br>${seg.name}<br>${seg.length_km} km | ${seg.time_min} mins`);
    });

    // Fit map bounds
    map.fitBounds(basePolyline.getBounds(), { padding: [40, 40] });

    // 5. Update UI Panels
    document.getElementById("detail-distance").innerText = `${data.total_distance_km} km`;
    document.getElementById("detail-time").innerText = `${data.total_time_min} mins`;

    // Populate modes row
    const modesList = document.getElementById("detail-modes-list");
    modesList.innerHTML = "";
    
    data.segments.forEach((seg, idx) => {
        if (idx > 0) {
            const separator = document.createElement("span");
            separator.className = "mode-separator";
            separator.innerHTML = '<i class="fa-solid fa-chevron-right"></i>';
            modesList.appendChild(separator);
        }

        const badge = document.createElement("div");
        let badgeClass = "road";
        let iconClass = "fa-car";
        
        if (seg.mode === 'Walk') {
            badgeClass = "walk";
            iconClass = "fa-walking";
        } else if (seg.mode === 'Metro') {
            badgeClass = "metro";
            iconClass = "fa-subway";
        }

        badge.className = `mode-badge ${badgeClass}`;
        badge.innerHTML = `<i class="fa-solid ${iconClass}"></i> ${seg.mode}`;
        modesList.appendChild(badge);
    });

    // Populate step directions list
    const dirContainer = document.getElementById("step-directions");
    dirContainer.innerHTML = "";
    
    data.segments.forEach((seg, idx) => {
        const step = document.createElement("div");
        step.className = "direction-step";

        let icon = "fa-car";
        let iconClass = "road";
        if (seg.mode === 'Walk') { icon = "fa-walking"; iconClass = "walk"; }
        if (seg.mode === 'Metro') { icon = "fa-subway"; iconClass = "metro"; }

        step.innerHTML = `
            <div class="step-icon ${iconClass}">
                <i class="fa-solid ${icon}"></i>
            </div>
            <div class="step-text">
                <strong>${seg.mode}</strong>: ${seg.name}
            </div>
            <div class="step-meta">
                ${seg.length_km} km<br>
                ${seg.time_min} mins
            </div>
        `;
        dirContainer.appendChild(step);
    });

    document.getElementById("route-details").classList.remove("hidden");
    document.getElementById("simulator-panel").classList.remove("hidden");
}

// 6. Route Tracking Simulator Logic
function toggleTracking() {
    if (routeCoords.length === 0) return;

    const playBtn = document.getElementById("btn-track-play");
    
    if (isTracking) {
        // Pause tracking
        isTracking = false;
        clearInterval(trackerTimer);
        playBtn.innerHTML = '<i class="fa-solid fa-play"></i> Resume tracking';
        playBtn.classList.add("paused");
    } else {
        // Start tracking
        isTracking = true;
        playBtn.innerHTML = '<i class="fa-solid fa-pause"></i> Pause tracking';
        playBtn.classList.remove("paused");
        
        trackerTimer = setInterval(trackingStep, 200 / simSpeed);
    }
}

function trackingStep() {
    if (trackerIndex >= routeCoords.length) {
        // Reached end of path
        resetTracking();
        alert("Trip completed!");
        return;
    }

    const currentCoords = routeCoords[trackerIndex];
    
    if (!trackerMarker) {
        trackerMarker = L.marker(currentCoords, {
            icon: L.divIcon({
                className: 'custom-pin-tracker',
                html: '<div style="background:#3b82f6; width:18px; height:18px; border-radius:50%; border:3px solid white; box-shadow:0 0 10px rgba(59,130,246,0.8); animation: pulse 1.5s infinite;"></div>',
                iconSize: [18, 18],
                iconAnchor: [9, 9]
            })
        }).addTo(map);
    } else {
        trackerMarker.setLatLng(currentCoords);
    }

    // Pan map to follow tracker
    map.panTo(currentCoords);
    
    trackerIndex++;
}

function resetTracking() {
    isTracking = false;
    clearInterval(trackerTimer);
    trackerIndex = 0;
    
    if (trackerMarker) {
        map.removeLayer(trackerMarker);
        trackerMarker = null;
    }
    
    const playBtn = document.getElementById("btn-track-play");
    playBtn.innerHTML = '<i class="fa-solid fa-play"></i> Start tracking';
    playBtn.classList.remove("paused");
}

function setSimSpeed(speed) {
    simSpeed = speed;
    
    // Update active speed button styling
    const speedButtons = document.querySelectorAll(".speed-btn");
    speedButtons.forEach(btn => {
        btn.classList.toggle("active", parseInt(btn.innerText) === speed);
    });

    // If already tracking, reset interval timer with new speed
    if (isTracking) {
        clearInterval(trackerTimer);
        trackerTimer = setInterval(trackingStep, 200 / simSpeed);
    }
}

// 7. Chatbot UI Logic
function toggleChatCollapse() {
    const chatPanel = document.getElementById("chat-panel");
    chatPanel.classList.toggle("collapsed");
}

function handleChatKey(e) {
    if (e.key === "Enter") {
        sendChatMessage();
    }
}

async function sendChatMessage() {
    const inputEl = document.getElementById("chat-input");
    const messageText = inputEl.value.trim();
    if (!messageText) return;

    // Append User message
    appendMessage(messageText, "user");
    inputEl.value = "";

    // Show bot typing indicator
    const typingBubble = appendMessage('<i class="fa-solid fa-ellipsis fa-fade"></i>', "bot typing");

    try {
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: messageText })
        });
        
        const result = await response.json();
        
        // Remove typing bubble
        typingBubble.remove();

        // Convert newlines in response to HTML breaks
        const formattedResponse = result.response.replace(/\n/g, "<br>");
        appendMessage(formattedResponse, "bot");

        // If route was parsed and calculated successfully, update map & controls
        if (result.route_data) {
            // Sync scenario selection UI
            const scenario = result.route_data.scenario || "off_peak";
            const mode = result.route_data.mode || "all_modes";
            
            // Force local variables sync and button selection sync
            currentScenario = scenario;
            document.getElementById("btn-off-peak").classList.toggle("active", scenario === 'off_peak');
            document.getElementById("btn-peak").classList.toggle("active", scenario === 'peak');

            currentMode = mode;
            document.getElementById("btn-all-modes").classList.toggle("active", mode === 'all_modes');
            document.getElementById("btn-road-only").classList.toggle("active", mode === 'road_only');

            drawRoute(result.route_data);
        }
    } catch (e) {
        console.error(e);
        typingBubble.remove();
        appendMessage("Sorry, I encountered an issue processing your chat message.", "bot");
    }
}

function appendMessage(text, sender) {
    const messagesContainer = document.getElementById("chat-messages");
    const msgElement = document.createElement("div");
    msgElement.className = `message ${sender}`;
    msgElement.innerHTML = text;
    messagesContainer.appendChild(msgElement);
    
    // Auto-scroll chat to bottom
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
    
    return msgElement;
}
