"""
ResQNet AI - Ambulance Dashboard
Mission status, patient info, navigation route, destination hospital.
"""

import streamlit as st
import json
from streamlit_folium import st_folium
from database import db_manager as db
from services.map_service import create_ambulance_route_map
from config.settings import SEVERITY_LEVELS


def render():
    st.markdown("""
    <style>
    .amb-card { background: linear-gradient(135deg, #1E293B, #0F172A);
                border:1px solid #F59E0B; border-radius:14px; padding:20px; margin-bottom:14px; }
    .mission-active { border-color:#EF4444 !important;
                      box-shadow: 0 0 20px rgba(239,68,68,0.3); }
    .status-pill { display:inline-block; padding:4px 14px; border-radius:20px;
                   font-weight:bold; font-size:0.9rem; }
    </style>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div style='text-align:center; padding:16px 0 8px 0;'>
        <h1 style='color:#F59E0B; font-size:2rem; margin:0;'>🚑 Ambulance Operations Hub</h1>
        <p style='color:#94A3B8;'>Mission control · Navigation · Patient coordination</p>
    </div>
    """, unsafe_allow_html=True)

    ambulances = db.get_all_ambulances()
    if not ambulances:
        st.warning("No ambulances in the database.")
        return

    # ── Ambulance selector ─────────────────────────────────────────────────────
    amb_options = {f"{a['vehicle_number']} - {a['driver_name']} ({a['status']})": a["id"]
                   for a in ambulances}
    selected_label = st.selectbox("Select Ambulance / Driver", list(amb_options.keys()))
    amb_id = amb_options[selected_label]
    amb = db.get_ambulance_by_id(amb_id)
    if not amb:
        return

    # ── Vehicle Status ─────────────────────────────────────────────────────────
    status_colors = {"Available": "#10B981", "Dispatched": "#EF4444",
                     "En Route": "#F59E0B", "At Hospital": "#00D4FF"}
    s_color = status_colors.get(amb["status"], "#888")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("🚑 Vehicle", amb["vehicle_number"])
    col2.metric("👤 Driver", amb["driver_name"])
    col3.metric("⛽ Fuel", f"{amb.get('fuel_level', 100)}%")
    col4.metric("📍 Status", amb["status"])

    # ── Mission Info ───────────────────────────────────────────────────────────
    active_requests = db.get_requests_for_ambulance(amb_id)

    if not active_requests:
        st.markdown(f"""
        <div class='amb-card'>
            <h3 style='color:#10B981;'>[DONE] No Active Mission</h3>
            <p style='color:#94A3B8;'>Vehicle {amb['vehicle_number']} is available and ready for dispatch.</p>
            <p>Driver: <b>{amb['driver_name']}</b> | Phone: {amb['driver_phone']}</p>
        </div>
        """, unsafe_allow_html=True)
    else:
        req = active_requests[0]
        sev = req.get("severity", 1)
        sev_info = SEVERITY_LEVELS.get(sev, {"emoji": "⚪", "label": "Unknown", "color": "#888"})

        st.markdown(f"""
        <div class='amb-card mission-active'>
            <div style='display:flex; justify-content:space-between; align-items:center;'>
                <h3 style='color:#EF4444; margin:0;'>🚨 ACTIVE MISSION - Request #{req['id']}</h3>
                <span class='status-pill' style='background:{sev_info["color"]}22; color:{sev_info["color"]};
                      border:1px solid {sev_info["color"]};'>
                    {sev_info["emoji"]} Severity {sev}/5 - {sev_info["label"]}
                </span>
            </div>
            <hr style='border-color:#334155;'>
            <div style='display:grid; grid-template-columns:1fr 1fr; gap:12px;'>
                <div>
                    <b>👤 Patient:</b> {req.get("citizen_name","N/A")}<br>
                    <b>📞 Phone:</b> {req.get("citizen_phone","N/A")}<br>
                    <b>👥 People:</b> {req.get("num_people",1)}
                </div>
                <div>
                    <b>📍 Pickup:</b> {req.get("address","N/A")}<br>
                    <b>⏱️ ETA:</b> {req.get("eta_minutes","--")} minutes<br>
                    <b>🔄 Status:</b> {req.get("status","Pending")}
                </div>
            </div>
            <hr style='border-color:#334155;'>
            <b>📋 Emergency Description:</b><br>
            <em style='color:#CBD5E1;'>{req.get("description","")[:200]}</em>
        </div>
        """, unsafe_allow_html=True)

        # Hospital destination
        if req.get("assigned_hospital_id"):
            hosp = db.get_hospital_by_id(req["assigned_hospital_id"])
            if hosp:
                st.markdown(f"""
                <div class='amb-card'>
                    <h4 style='color:#10B981;'>🏥 Destination Hospital</h4>
                    <b>{hosp['name']}</b><br>
                    📍 {hosp['address']}<br>
                    📞 {hosp.get('contact_phone','N/A')}<br>
                    🛏️ Beds Reserved for this patient
                </div>
                """, unsafe_allow_html=True)

                # Navigation Route Map
                st.markdown("#### 🗺️ Navigation Route")
                route_map = create_ambulance_route_map(
                    origin_lat=req["latitude"],
                    origin_lon=req["longitude"],
                    origin_name=req.get("address", "Pickup"),
                    dest_lat=hosp["latitude"],
                    dest_lon=hosp["longitude"],
                    dest_name=hosp["name"],
                    blocked_roads=db.get_blocked_roads()[:6],
                )
                st_folium(route_map, width=700, height=400, key=f"amb_map_{amb_id}")

        # Mission actions
        st.markdown("#### 🎯 Mission Actions")
        mcol1, mcol2, mcol3 = st.columns(3)
        with mcol1:
            if st.button("🚑 En Route to Patient", use_container_width=True):
                db.execute_write(
                    "UPDATE ambulances SET status='En Route', updated_at=datetime('now') WHERE id=?",
                    (amb_id,)
                )
                db.update_request_status(req["id"], "Dispatched")
                st.success("Status: En Route to Patient!")
                st.rerun()
        with mcol2:
            if st.button("🏥 Arrived at Hospital", use_container_width=True):
                db.execute_write(
                    "UPDATE ambulances SET status='At Hospital', updated_at=datetime('now') WHERE id=?",
                    (amb_id,)
                )
                st.success("Status: At Hospital!")
                st.rerun()
        with mcol3:
            if st.button("[DONE] Mission Complete", use_container_width=True):
                db.release_ambulance(amb_id)
                db.update_request_status(req["id"], "Resolved")
                st.success("Mission Complete! Ambulance Available.")
                st.rerun()

    # ── Fleet Overview ─────────────────────────────────────────────────────────
    st.divider()
    st.markdown("### 🚑 Fleet Status Overview")
    cols = st.columns(min(len(ambulances), 5))
    for i, a in enumerate(ambulances):
        with cols[i % 5]:
            s = a["status"]
            color = status_colors.get(s, "#888")
            st.markdown(f"""
            <div style='background:#1E293B; border:1px solid {color}; border-radius:10px;
                        padding:10px; text-align:center; margin:4px 0; font-size:0.8rem;'>
                🚑 <b>{a['vehicle_number']}</b><br>
                <span style='color:{color};'>{s}</span><br>
                ⛽ {a.get('fuel_level',100)}%
            </div>
            """, unsafe_allow_html=True)
