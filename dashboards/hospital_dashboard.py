"""
ResQNet AI - Hospital Dashboard
Bed/ICU availability, incoming patient queue, accept/reject allocation.
"""

import streamlit as st
import json
from database import db_manager as db
from services import analytics_service as analytics
from config.settings import SEVERITY_LEVELS


def _sev_color(sev: int) -> str:
    return {1:"#22c55e", 2:"#eab308", 3:"#f97316", 4:"#ef4444", 5:"#7c3aed"}.get(sev, "#888")


def render():
    st.markdown("""
    <style>
    .hosp-card { background:#1E293B; border-radius:12px; padding:20px; margin-bottom:12px;
                 border:1px solid #334155; }
    .patient-card { background:#0F172A; border-radius:10px; padding:16px; margin:8px 0;
                    border-left:4px solid #00D4FF; }
    .urgent { border-left-color: #EF4444 !important; }
    </style>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div style='text-align:center; padding:16px 0 8px 0;'>
        <h1 style='color:#10B981; font-size:2rem; margin:0;'>🏥 Hospital Command Center</h1>
        <p style='color:#94A3B8;'>Patient allocation · Bed management · Queue management</p>
    </div>
    """, unsafe_allow_html=True)

    hospitals = db.get_all_hospitals()
    if not hospitals:
        st.warning("No hospitals in the database.")
        return

    # ── Hospital selector ──────────────────────────────────────────────────────
    hosp_options = {f"{h['name']} (ID: {h['id']})": h["id"] for h in hospitals}
    selected_label = st.selectbox("Select Hospital", list(hosp_options.keys()))
    hosp_id = hosp_options[selected_label]
    hosp = db.get_hospital_by_id(hosp_id)
    if not hosp:
        return

    # ── Capacity Metrics ───────────────────────────────────────────────────────
    col1, col2, col3, col4, col5 = st.columns(5)
    metrics = [
        ("🛏️ Total Beds", hosp["total_beds"]),
        ("[DONE] Available", hosp["available_beds"]),
        ("🏥 ICU Total", hosp["total_icu"]),
        ("💉 ICU Avail", hosp["available_icu"]),
        ("👩‍⚕️ Doctors", hosp["available_doctors"]),
    ]
    for col, (label, val) in zip([col1,col2,col3,col4,col5], metrics):
        with col:
            col.metric(label, val)

    # ── Gauge Chart ────────────────────────────────────────────────────────────
    col_g1, col_g2 = st.columns([1, 2])
    with col_g1:
        st.plotly_chart(analytics.hospital_occupancy_gauge(hosp),
                        use_container_width=True, key="hosp_gauge")
    with col_g2:
        # Hospital details
        specs = hosp.get("specializations", "[]")
        if isinstance(specs, str):
            try:
                specs = json.loads(specs)
            except Exception:
                specs = []
        st.markdown(f"""
        <div class='hosp-card'>
            <h3 style='color:#10B981;'>{hosp['name']}</h3>
            <p>📍 {hosp['address']}</p>
            <p>📞 {hosp.get('contact_phone','N/A')}</p>
            <p>🩺 Specializations: {', '.join(specs) if specs else 'General'}</p>
            <p>🔄 Status: <b style='color:{"#10B981" if hosp["status"]=="Operational" else "#EF4444"};'>
                {hosp['status']}</b></p>
        </div>
        """, unsafe_allow_html=True)

    st.divider()

    # ── Patient Queue ──────────────────────────────────────────────────────────
    st.markdown("### 📋 Incoming Patient Queue")
    allocations = db.get_allocations_for_hospital(hosp_id)

    if not allocations:
        st.info("No pending patient allocations for this hospital.")
    else:
        for alloc in allocations:
            sev = alloc.get("severity", 1)
            is_urgent = sev >= 4
            card_class = "patient-card urgent" if is_urgent else "patient-card"
            sev_color = _sev_color(sev)
            sev_label = SEVERITY_LEVELS.get(sev, {}).get("label", "Unknown")

            col_info, col_actions = st.columns([5, 3])
            with col_info:
                st.markdown(f"""
                <div class='{card_class}'>
                    <div style='display:flex; justify-content:space-between;'>
                        <span><b>Request #{alloc['request_id']}</b> - {alloc.get('citizen_name','N/A')}</span>
                        <span style='color:{sev_color};'><b>Severity {sev}/5 - {sev_label}</b></span>
                    </div>
                    <small>📞 {alloc.get('citizen_phone','N/A')}</small><br>
                    <small>👥 {alloc.get('num_people',1)} people | 🛏️ {alloc['beds_reserved']} beds | 💉 {alloc['icu_reserved']} ICU reserved</small><br>
                    <small>🕐 Allocated: {str(alloc.get('allocated_at',''))[:19]}</small>
                </div>
                """, unsafe_allow_html=True)
            with col_actions:
                # Retrieve available ambulances
                avail_ambs = db.get_available_ambulances()
                
                # We also want to include the AI-recommended one in case it is still Available
                rec_amb_id = alloc.get("assigned_ambulance_id")
                rec_amb = None
                if rec_amb_id:
                    rec_amb = db.get_ambulance_by_id(rec_amb_id)
                
                # Format options
                amb_options = {}
                default_index = 0
                
                # Build list of options for the selectbox
                list_options = []
                for a in avail_ambs:
                    label = f"🚑 {a['vehicle_number']} - {a['driver_name']} (Available)"
                    amb_options[label] = a["id"]
                    list_options.append(label)
                
                # If the tentatively recommended ambulance is available, make it default.
                # If it's not in the available list (maybe already dispatched), add it if it's somehow available,
                # or highlight that it is no longer available.
                if rec_amb:
                    rec_label = f"⭐ [Recommended] {rec_amb['vehicle_number']} - {rec_amb['driver_name']} ({rec_amb['status']})"
                    if rec_amb["status"] == "Available":
                        # If already in list, we find it and use it as default, or replace it with recommendation label
                        if rec_label not in amb_options:
                            amb_options[rec_label] = rec_amb["id"]
                            list_options.insert(0, rec_label)
                        default_index = 0
                    else:
                        # Preassigned one is no longer available
                        st.caption(f"⚠️ AI-recommended ambulance {rec_amb['vehicle_number']} is currently {rec_amb['status']}.")
                
                selected_amb_label = None
                chosen_amb_id = None
                if list_options:
                    selected_amb_label = st.selectbox(
                        "Assign Ambulance / Driver",
                        list_options,
                        index=default_index,
                        key=f"amb_select_{alloc['id']}"
                    )
                    chosen_amb_id = amb_options[selected_amb_label]
                else:
                    st.error("🚨 No available ambulances in fleet!")
                
                col_btn1, col_btn2 = st.columns(2)
                with col_btn1:
                    accept_enabled = chosen_amb_id is not None
                    accept = st.button(
                        "[DONE] Accept",
                        key=f"accept_{alloc['id']}",
                        use_container_width=True,
                        disabled=not accept_enabled,
                        type="primary"
                    )
                with col_btn2:
                    reject = st.button(
                        "[X] Reject",
                        key=f"reject_{alloc['id']}",
                        use_container_width=True
                    )

                # ── ACCEPT ──────────────────────────────────────────────────
                if accept and chosen_amb_id:
                    success = db.accept_patient_allocation(
                        allocation_id=alloc["id"],
                        request_id=alloc["request_id"],
                        hospital_id=hosp_id,
                        hospital_name=hosp["name"],
                        chosen_ambulance_id=chosen_amb_id
                    )
                    if success:
                        st.success(
                            f"Request #{alloc['request_id']} **ACCEPTED** and dispatched. "
                            f"Ambulance has been sent. Citizen notified."
                        )
                        st.rerun()
                    else:
                        st.error(
                            "🚨 Concurrency Conflict: The selected ambulance was just dispatched to another mission. "
                            "Please choose a different ambulance and try again."
                        )

                # ── REJECT ──────────────────────────────────────────────────
                if reject:
                    # Release reserved beds back to this hospital, then
                    # automatically find and allocate the next nearest
                    # hospital with available capacity.
                    result = db.reject_patient_allocation(
                        allocation_id=alloc["id"],
                        request_id=alloc["request_id"],
                        rejected_hospital_id=hosp_id,
                        rejected_hospital_name=hosp["name"],
                        beds_to_release=alloc["beds_reserved"],
                        icu_to_release=alloc["icu_reserved"],
                    )
                    if result:
                        next_hosp, new_alloc_id = result
                        st.warning(
                            f"Request #{alloc['request_id']} **REJECTED**. "
                            f"{alloc['beds_reserved']} bed(s) released. "
                            f"Auto-re-assigned to **{next_hosp['name']}** "
                            f"(Allocation #{new_alloc_id}). Citizen notified."
                        )
                    else:
                        st.error(
                            f"Request #{alloc['request_id']} rejected. "
                            f"No alternative hospital with capacity found — "
                            f"request returned to Pending queue."
                        )
                    st.rerun()

    st.divider()

    # ── All Hospitals Overview ─────────────────────────────────────────────────
    st.markdown("### 🏥 All Hospitals - Capacity Overview")
    st.plotly_chart(analytics.hospital_capacity_chart(hospitals),
                    use_container_width=True, key="all_hosp_chart")

    # ── Hospital Admin Actions ─────────────────────────────────────────────────
    with st.expander("⚙️ Hospital Admin Actions"):
        col1, col2 = st.columns(2)
        with col1:
            release_beds = st.number_input("Release Beds", min_value=1, max_value=100, value=5)
            if st.button("🛏️ Release Beds"):
                db.update_hospital_beds(hosp_id, release_beds, 0)
                st.success(f"Released {release_beds} beds!")
                st.rerun()
        with col2:
            new_status = st.selectbox("Set Status", ["Operational", "At Capacity", "Overloaded", "Offline"])
            if st.button("🔄 Update Status"):
                db.update_hospital_status(hosp_id, new_status)
                st.success(f"Status updated to {new_status}!")
                st.rerun()
