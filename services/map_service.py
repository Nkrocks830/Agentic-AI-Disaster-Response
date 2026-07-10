"""
ResQNet AI - Map Service
Generates interactive Folium maps for dashboards.
"""

import json
import folium
from folium.plugins import MarkerCluster, HeatMap
from typing import List, Optional, Dict, Any


def _safe_color(condition: str) -> str:
    colors = {"Clear": "green", "Blocked": "red", "Flooded": "blue",
              "Damaged": "orange", "Collapsed": "darkred"}
    return colors.get(condition, "gray")


def create_disaster_overview_map(
    disasters: List[Dict],
    hospitals: List[Dict],
    ambulances: List[Dict],
    blocked_roads: List[Dict],
    emergency_requests: List[Dict],
    shelters: List[Dict] = None,
    center: tuple = (13.0827, 80.2707),
    zoom: int = 12,
) -> folium.Map:
    """Full disaster overview map for Government Dashboard."""
    m = folium.Map(
        location=center,
        zoom_start=zoom,
        tiles="CartoDB dark_matter",
    )

    # ── Disaster zones ─────────────────────────────────────────────────────────
    severity_colors = {1:"#22c55e", 2:"#eab308", 3:"#f97316", 4:"#ef4444", 5:"#7c3aed"}
    for d in disasters:
        color = severity_colors.get(d.get("severity", 1), "#ef4444")
        folium.Circle(
            location=(d["latitude"], d["longitude"]),
            radius=d.get("affected_radius_km", 5) * 1000,
            color=color, fill=True, fill_opacity=0.2,
            popup=folium.Popup(
                f"<b>🌊 {d['name']}</b><br>"
                f"Type: {d['disaster_type']}<br>"
                f"Severity: {d['severity']}/5<br>"
                f"Affected: {d['affected_people']:,} people<br>"
                f"Status: {d['status']}",
                max_width=250
            ),
            tooltip=f"[!]️ {d['name']} (Sev {d['severity']})",
        ).add_to(m)
        folium.Marker(
            location=(d["latitude"], d["longitude"]),
            icon=folium.Icon(color="red", icon="exclamation-triangle", prefix="fa"),
            popup=d["name"],
        ).add_to(m)

    # ── Hospitals ──────────────────────────────────────────────────────────────
    hosp_cluster = MarkerCluster(name="🏥 Hospitals").add_to(m)
    for h in hospitals:
        avail_pct = (h.get("available_beds", 0) / max(h.get("total_beds", 1), 1)) * 100
        h_color = "green" if avail_pct > 30 else "orange" if avail_pct > 10 else "red"
        folium.Marker(
            location=(h["latitude"], h["longitude"]),
            icon=folium.Icon(color=h_color, icon="plus-square", prefix="fa"),
            popup=folium.Popup(
                f"<b>🏥 {h['name']}</b><br>"
                f"Beds: {h['available_beds']}/{h['total_beds']}<br>"
                f"ICU: {h['available_icu']}/{h['total_icu']}<br>"
                f"Status: {h['status']}<br>"
                f"📞 {h.get('contact_phone', 'N/A')}",
                max_width=250
            ),
            tooltip=f"🏥 {h['name']} ({h['available_beds']} beds)",
        ).add_to(hosp_cluster)

    # ── Emergency Requests (Heat Map) ──────────────────────────────────────────
    if emergency_requests:
        heat_data = [
            [r["latitude"], r["longitude"], r.get("severity", 1) * 0.2]
            for r in emergency_requests if r.get("latitude") and r.get("longitude")
        ]
        if heat_data:
            HeatMap(
                heat_data,
                name="🔥 Emergency Density",
                min_opacity=0.3,
                radius=25,
                blur=15,
            ).add_to(m)

    # ── Emergency request markers (sample) ────────────────────────────────────
    req_cluster = MarkerCluster(name="🆘 Emergency Requests").add_to(m)
    status_colors = {"Pending": "red", "Processing": "orange", "Dispatched": "blue", "Resolved": "green"}
    for r in emergency_requests[:30]:
        color = status_colors.get(r.get("status", "Pending"), "gray")
        folium.CircleMarker(
            location=(r["latitude"], r["longitude"]),
            radius=6,
            color=color, fill=True, fill_opacity=0.8,
            popup=folium.Popup(
                f"<b>🆘 Request #{r['id']}</b><br>"
                f"Name: {r['citizen_name']}<br>"
                f"People: {r.get('num_people', 1)}<br>"
                f"Status: {r.get('status', 'Pending')}<br>"
                f"Desc: {str(r.get('description',''))[:80]}...",
                max_width=250
            ),
            tooltip=f"#{r['id']} - {r.get('status','Pending')}",
        ).add_to(req_cluster)

    # ── Blocked Roads ──────────────────────────────────────────────────────────
    for road in blocked_roads:
        folium.PolyLine(
            locations=[
                (road["from_lat"], road["from_lon"]),
                (road["to_lat"], road["to_lon"])
            ],
            color=_safe_color(road.get("condition", "Blocked")),
            weight=5, opacity=0.9, dash_array="10",
            popup=folium.Popup(
                f"<b>🚧 {road['road_name']}</b><br>"
                f"Condition: {road.get('condition','Blocked')}<br>"
                f"Reason: {road.get('blockage_reason','Unknown')}<br>"
                f"Severity: {road.get('severity',0)}/5",
                max_width=250
            ),
            tooltip=f"🚧 {road['road_name']} - {road.get('condition','Blocked')}",
        ).add_to(m)

    # ── Ambulances ─────────────────────────────────────────────────────────────
    amb_cluster = MarkerCluster(name="🚑 Ambulances").add_to(m)
    for a in ambulances:
        amb_color = "green" if a["status"] == "Available" else "orange"
        folium.Marker(
            location=(a["latitude"], a["longitude"]),
            icon=folium.Icon(color=amb_color, icon="ambulance", prefix="fa"),
            popup=folium.Popup(
                f"<b>🚑 {a['vehicle_number']}</b><br>"
                f"Driver: {a['driver_name']}<br>"
                f"Status: {a['status']}<br>"
                f"Fuel: {a.get('fuel_level',100)}%",
                max_width=200
            ),
            tooltip=f"🚑 {a['vehicle_number']} ({a['status']})",
        ).add_to(amb_cluster)

    # ── Shelters ───────────────────────────────────────────────────────────────
    if shelters:
        for s in shelters:
            occ_pct = (s.get("current_occupancy", 0) / max(s.get("capacity", 1), 1)) * 100
            s_color = "green" if occ_pct < 70 else "orange" if occ_pct < 95 else "red"
            folium.Marker(
                location=(s["latitude"], s["longitude"]),
                icon=folium.Icon(color=s_color, icon="home", prefix="fa"),
                popup=folium.Popup(
                    f"<b>🏠 {s['name']}</b><br>"
                    f"Capacity: {s.get('current_occupancy',0):,}/{s.get('capacity',0):,}<br>"
                    f"Status: {s.get('status','Active')}<br>"
                    f"Contact: {s.get('contact_person','')}",
                    max_width=250
                ),
                tooltip=f"🏠 {s['name']} ({s.get('current_occupancy',0)}/{s.get('capacity',0)})",
            ).add_to(m)

    # ── Layer control ──────────────────────────────────────────────────────────
    folium.LayerControl(collapsed=False).add_to(m)

    return m


def create_ambulance_route_map(
    origin_lat: float, origin_lon: float, origin_name: str,
    dest_lat: float, dest_lon: float, dest_name: str,
    waypoints: List[Dict] = None,
    blocked_roads: List[Dict] = None,
    center: tuple = (13.0827, 80.2707),
) -> folium.Map:
    """Route map for Ambulance Dashboard."""
    mid_lat = (origin_lat + dest_lat) / 2
    mid_lon = (origin_lon + dest_lon) / 2

    m = folium.Map(
        location=(mid_lat, mid_lon),
        zoom_start=13,
        tiles="CartoDB positron",
    )

    # Origin marker
    folium.Marker(
        location=(origin_lat, origin_lon),
        icon=folium.Icon(color="red", icon="map-marker", prefix="fa"),
        popup=f"🆘 Patient Location: {origin_name}",
        tooltip=f"📍 Pickup: {origin_name}",
    ).add_to(m)

    # Destination marker
    folium.Marker(
        location=(dest_lat, dest_lon),
        icon=folium.Icon(color="green", icon="plus-square", prefix="fa"),
        popup=f"🏥 Hospital: {dest_name}",
        tooltip=f"🏥 {dest_name}",
    ).add_to(m)

    # Route line
    route_coords = [(origin_lat, origin_lon)]
    if waypoints:
        for wp in waypoints:
            route_coords.append((wp.get("latitude", origin_lat), wp.get("longitude", origin_lon)))
    route_coords.append((dest_lat, dest_lon))

    folium.PolyLine(
        locations=route_coords,
        color="#00D4FF", weight=6, opacity=0.9,
        tooltip="🚑 Safe Route",
    ).add_to(m)

    # Waypoint markers
    if waypoints:
        for wp in waypoints[1:-1]:
            folium.CircleMarker(
                location=(wp.get("latitude", 0), wp.get("longitude", 0)),
                radius=6, color="#FFD700", fill=True,
                popup=wp.get("location_name", "Waypoint"),
            ).add_to(m)

    # Blocked roads
    if blocked_roads:
        for road in blocked_roads[:5]:
            folium.PolyLine(
                locations=[(road["from_lat"], road["from_lon"]), (road["to_lat"], road["to_lon"])],
                color="red", weight=4, dash_array="10",
                tooltip=f"🚧 Blocked: {road['road_name']}",
            ).add_to(m)

    return m


def create_citizen_map(
    request_lat: float, request_lon: float,
    hospital_lat: Optional[float] = None, hospital_lon: Optional[float] = None,
    hospital_name: str = "",
    ambulance_lat: Optional[float] = None, ambulance_lon: Optional[float] = None,
) -> folium.Map:
    """Simple map for citizen status tracking."""
    m = folium.Map(
        location=(request_lat, request_lon),
        zoom_start=14,
        tiles="OpenStreetMap",
    )

    # Citizen location
    folium.Marker(
        location=(request_lat, request_lon),
        icon=folium.Icon(color="red", icon="user", prefix="fa"),
        popup="📍 Your Location",
        tooltip="📍 Your Location",
    ).add_to(m)

    # Hospital
    if hospital_lat and hospital_lon:
        folium.Marker(
            location=(hospital_lat, hospital_lon),
            icon=folium.Icon(color="green", icon="plus-square", prefix="fa"),
            popup=f"🏥 {hospital_name}",
            tooltip=f"🏥 {hospital_name}",
        ).add_to(m)
        folium.PolyLine(
            [(request_lat, request_lon), (hospital_lat, hospital_lon)],
            color="blue", weight=3, dash_array="5",
        ).add_to(m)

    # Ambulance
    if ambulance_lat and ambulance_lon:
        folium.Marker(
            location=(ambulance_lat, ambulance_lon),
            icon=folium.Icon(color="orange", icon="ambulance", prefix="fa"),
            popup="🚑 Ambulance En Route",
            tooltip="🚑 Ambulance",
        ).add_to(m)

    return m
