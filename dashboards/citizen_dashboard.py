"""
ResQNet AI - Citizen Dashboard
Emergency reporting, request tracking, hospital assignment, ambulance ETA, route and alerts.
"""

import streamlit as st
import json
from datetime import datetime
from streamlit_folium import st_folium

from database import db_manager as db
from orchestrator.orchestrator import Orchestrator
from models.disaster_models import DisasterInput
from services.map_service import create_citizen_map
from services import analytics_service as analytics
from config.settings import SEVERITY_LEVELS, COLORS


def _severity_badge(sev: int) -> str:
    info = SEVERITY_LEVELS.get(sev, {"emoji": "⚪", "label": "Unknown", "color": "#666"})
    return f"{info['emoji']} {info['label']}"


def _status_badge(status: str) -> str:
    icons = {"Pending": "🔴", "Processing": "🟡", "Dispatched": "🔵", "Resolved": "🟢"}
    return f"{icons.get(status, '⚪')} {status}"


def render():
    st.markdown("""
    <style>
    .citizen-card {
        background: linear-gradient(135deg, #1E293B 0%, #0F172A 100%);
        border: 1px solid #334155;
        border-radius: 16px;
        padding: 24px;
        margin-bottom: 16px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.4);
    }
    .alert-banner {
        background: linear-gradient(90deg, #7c3aed, #ef4444);
        border-radius: 12px;
        padding: 14px 20px;
        margin-bottom: 20px;
        animation: pulse 2s infinite;
        color: white;
        font-weight: bold;
    }
    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.85; }
    }
    .metric-mini {
        background: #1E293B;
        border-radius: 10px;
        padding: 12px;
        text-align: center;
        border: 1px solid #334155;
    }
    </style>
    """, unsafe_allow_html=True)

    # ── Header ─────────────────────────────────────────────────────────────────
    st.markdown("""
    <div style='text-align:center; padding: 20px 0 10px 0;'>
        <h1 style='font-size:2.2rem; color:#00D4FF; margin:0;'>🆘 Citizen Emergency Portal</h1>
        <p style='color:#94A3B8; font-size:1rem; margin:4px 0 0 0;'>
            Report emergencies · Track your request · Get real-time updates
        </p>
    </div>
    """, unsafe_allow_html=True)

    # ── Live Alert Banner ──────────────────────────────────────────────────────
    disasters = db.get_active_disasters()
    if disasters:
        d = disasters[0]
        st.markdown(f"""
        <div class='alert-banner'>
            🚨 ACTIVE DISASTER ALERT &nbsp;|&nbsp; {d['name']}
            &nbsp;|&nbsp; Severity: {d['severity']}/5
            &nbsp;|&nbsp; Affected: {d['affected_people']:,} people
            &nbsp;|&nbsp; Emergency: 108
        </div>
        """, unsafe_allow_html=True)

    tab1, tab2, tab3 = st.tabs(["📝 Report Emergency", "📊 Track My Request", "🗺️ Map & Alerts"])

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 1: REPORT EMERGENCY
    # ══════════════════════════════════════════════════════════════════════════
    with tab1:
        st.markdown("### 🚨 Submit Emergency Report")
        st.info("Fill in all details accurately. AI agents will process your request immediately.")

        with st.form("emergency_form", clear_on_submit=False):
            col1, col2 = st.columns(2)
            with col1:
                name = st.text_input("Your Name *", placeholder="e.g. Arjun Sharma")
                phone = st.text_input("Mobile Number *", placeholder="+91-98765-43210")
                address = st.text_input("Location / Address *",
                                        placeholder="e.g. 5th Street, Velachery, Chennai")
            with col2:
                num_people = st.number_input("Number of People Affected *", min_value=1, max_value=500, value=1)
                col2a, col2b = st.columns(2)
                with col2a:
                    lat = st.number_input("Latitude", value=13.0827, format="%.6f",
                                          help="Chennai default: 13.0827")
                with col2b:
                    lon = st.number_input("Longitude", value=80.2707, format="%.6f",
                                          help="Chennai default: 80.2707")

            description = st.text_area(
                "Describe the Emergency *",
                placeholder="e.g. Water level has reached 3 feet in our house. "
                            "Elderly mother and 2 children trapped. Need immediate rescue.",
                height=120,
            )

            st.markdown("**Quick Location Presets (Chennai Flood Zones)**")
            preset_cols = st.columns(5)
            presets = [
                ("Velachery", 12.9786, 80.2209),
                ("Tambaram", 12.9229, 80.1275),
                ("Adyar", 13.0067, 80.2508),
                ("Anna Nagar", 13.0870, 80.2101),
                ("Perambur", 13.1098, 80.2599),
            ]
            # Note: presets only update display - user sets coords manually

            submitted = st.form_submit_button(
                "🚨 SUBMIT EMERGENCY", use_container_width=True,
                type="primary"
            )

        if submitted:
            # Validation
            errors = []
            if not name or len(name.strip()) < 2:
                errors.append("Name must be at least 2 characters")
            if not phone or len(phone.strip()) < 10:
                errors.append("Valid phone number required")
            if not address or len(address.strip()) < 5:
                errors.append("Address is required")
            if not description or len(description.strip()) < 10:
                errors.append("Please describe the emergency in detail")

            if errors:
                for e in errors:
                    st.error(f"[X] {e}")
            else:
                with st.spinner("🤖 AI Agents are processing your emergency..."):
                    try:
                        # Initialize orchestrator (cached)
                        if "orchestrator" not in st.session_state:
                            st.session_state["orchestrator"] = Orchestrator()
                        orch: Orchestrator = st.session_state["orchestrator"]

                        citizen_input = DisasterInput(
                            citizen_name=name.strip(),
                            citizen_phone=phone.strip(),
                            latitude=lat,
                            longitude=lon,
                            address=address.strip(),
                            description=description.strip(),
                            num_people=int(num_people),
                        )

                        result = orch.process_emergency(citizen_input)

                        # Store in session for tracking tab
                        st.session_state["last_request_id"] = result.request_id
                        st.session_state["last_pipeline_result"] = result

                        st.success(f"[DONE] Emergency #{result.request_id} submitted successfully!")
                        st.info(f"🤖 **Mode:** {result.mode.upper()} | **Total Time:** {result.total_time_ms}ms")

                        # Show agent pipeline results
                        st.markdown("#### 🤖 Agent Pipeline Execution")
                        for log in result.agent_logs:
                            status_icon = "[DONE]" if log.status == "success" else "[X]"
                            with st.expander(f"{status_icon} {log.agent_name} - {log.execution_time_ms}ms"):
                                st.markdown(f"**Decision:** {log.decision}")
                                if log.reasoning:
                                    st.markdown(f"**Reasoning:** {log.reasoning[:400]}")

                        st.markdown(f"""
                        <div class='citizen-card'>
                            <h3 style='color:#00D4FF;'>📋 Response Summary</h3>
                            <pre style='color:#E2E8F0; font-size:0.9rem;'>{result.summary}</pre>
                        </div>
                        """, unsafe_allow_html=True)

                    except Exception as e:
                        st.error(f"[X] Error processing request: {str(e)}")
                        st.exception(e)

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 2: TRACK REQUEST
    # ══════════════════════════════════════════════════════════════════════════
    with tab2:
        st.markdown("### 📊 Track Your Emergency Request")

        col1, col2 = st.columns([2, 1])
        with col1:
            req_id_input = st.number_input(
                "Enter Request ID",
                min_value=1, value=st.session_state.get("last_request_id", 1),
                help="Get this from your submission confirmation",
            )
        with col2:
            st.markdown("<br>", unsafe_allow_html=True)
            track_btn = st.button("🔍 Track", use_container_width=True)

        req = db.get_request_by_id(int(req_id_input))

        if req:
            # Status header
            status = req.get("status", "Pending")
            sev = req.get("severity", 1)
            st.markdown(f"""
            <div class='citizen-card'>
                <div style='display:flex; justify-content:space-between; align-items:center;'>
                    <div>
                        <h2 style='color:#00D4FF; margin:0;'>Request #{req['id']}</h2>
                        <p style='color:#94A3B8; margin:4px 0;'>{req.get('address','')}</p>
                    </div>
                    <div style='text-align:right;'>
                        <span style='font-size:1.4rem;'>{_status_badge(status)}</span><br>
                        <span style='font-size:1rem;'>{_severity_badge(sev)}</span>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            # Metrics
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("👤 Citizen", req.get("citizen_name", "N/A"))
            with col2:
                st.metric("👥 People", req.get("num_people", 1))
            with col3:
                eta = req.get("eta_minutes", "--")
                st.metric("⏱️ Ambulance ETA", f"{eta} min" if eta else "--")
            with col4:
                st.metric("🏥 Hospital", f"#{req.get('assigned_hospital_id','--')}")

            # Hospital info
            if req.get("assigned_hospital_id"):
                hosp = db.get_hospital_by_id(req["assigned_hospital_id"])
                if hosp:
                    st.markdown(f"""
                    <div class='citizen-card'>
                        <h4 style='color:#10B981;'>🏥 Assigned Hospital</h4>
                        <b>{hosp['name']}</b><br>
                        {hosp['address']}<br>
                        📞 {hosp.get('contact_phone','N/A')}<br>
                        🛏️ Beds Available: {hosp['available_beds']} | 🩺 ICU: {hosp['available_icu']}
                    </div>
                    """, unsafe_allow_html=True)

            # Ambulance info
            if req.get("assigned_ambulance_id"):
                amb = db.get_ambulance_by_id(req["assigned_ambulance_id"])
                if amb:
                    st.markdown(f"""
                    <div class='citizen-card'>
                        <h4 style='color:#F59E0B;'>🚑 Assigned Ambulance</h4>
                        <b>{amb['vehicle_number']}</b><br>
                        Driver: {amb['driver_name']} - 📞 {amb['driver_phone']}<br>
                        Status: {amb['status']} | Fuel: {amb.get('fuel_level',100)}%
                    </div>
                    """, unsafe_allow_html=True)

            # Notifications
            st.markdown("#### 📨 Notifications Received")
            notifications = db.fetch_all(
                "SELECT * FROM notifications WHERE request_id=? ORDER BY created_at DESC",
                (req["id"],)
            )
            if notifications:
                for n in notifications[:5]:
                    icon = {"citizen":"👤","hospital":"🏥","ambulance":"🚑","authority":"🏛️","public":"📢"}.get(n["recipient_type"],"📬")
                    st.info(f"**{icon} {n['recipient_type'].title()}** - {n.get('channel','sms').upper()}\n\n{n['message']}")
            else:
                st.info("No notifications yet.")

            # Agent logs for this request
            st.markdown("#### 🤖 Agent Decision Trail")
            logs = db.get_logs_for_request(req["id"])
            if logs:
                for log in logs:
                    with st.expander(f"{'[DONE]' if log['status']=='success' else '[X]'} {log['agent_name']} @ {log['created_at'][:19]}"):
                        st.write(f"**Decision:** {log['decision']}")
                        if log.get("reasoning"):
                            st.write(f"**Reasoning:** {log['reasoning'][:300]}")
                        st.caption(f"Mode: {log.get('mode','?').upper()} | Time: {log.get('execution_time_ms',0)}ms")
        else:
            st.warning("Request not found. Please check the ID and try again.")

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 3: MAP & ALERTS
    # ══════════════════════════════════════════════════════════════════════════
    with tab3:
        st.markdown("### 🗺️ Emergency Map & Evacuation Alerts")

        # Quick map for citizen
        req_id = st.session_state.get("last_request_id")
        if req_id:
            req = db.get_request_by_id(req_id)
            if req:
                hosp = db.get_hospital_by_id(req["assigned_hospital_id"]) if req.get("assigned_hospital_id") else None
                amb = db.get_ambulance_by_id(req["assigned_ambulance_id"]) if req.get("assigned_ambulance_id") else None

                citizen_map = create_citizen_map(
                    request_lat=req["latitude"],
                    request_lon=req["longitude"],
                    hospital_lat=hosp["latitude"] if hosp else None,
                    hospital_lon=hosp["longitude"] if hosp else None,
                    hospital_name=hosp["name"] if hosp else "",
                    ambulance_lat=amb["latitude"] if amb else None,
                    ambulance_lon=amb["longitude"] if amb else None,
                )
                st_folium(citizen_map, width=700, height=420)

        # Public Safety Alerts
        st.markdown("#### 📢 Public Safety Alerts")
        shelters = db.get_shelters()
        if shelters:
            st.markdown("**🏠 Emergency Shelters Near You:**")
            for s in shelters[:5]:
                occ_pct = (s.get("current_occupancy", 0) / max(s.get("capacity", 1), 1)) * 100
                color = "#10B981" if occ_pct < 70 else "#F59E0B" if occ_pct < 95 else "#EF4444"
                st.markdown(f"""
                <div style='background:#1E293B; border-left: 4px solid {color};
                            padding:12px; border-radius:8px; margin:6px 0;'>
                    🏠 <b>{s['name']}</b><br>
                    📍 {s['address']}<br>
                    👥 Occupancy: {s['current_occupancy']:,}/{s['capacity']:,} ({occ_pct:.0f}%)<br>
                    📞 {s.get('contact_person','')}
                </div>
                """, unsafe_allow_html=True)

        st.warning("🆘 Emergency Numbers: **108** (Ambulance) | **101** (Fire) | **100** (Police) | **1800-123-0011** (Disaster Hotline)")
