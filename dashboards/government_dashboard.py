"""
ResQNet AI - Government Dashboard
Live disaster map, active incidents, resource utilization, road closures, analytics.
"""

import streamlit as st
from streamlit_folium import st_folium

from database import db_manager as db
from services.map_service import create_disaster_overview_map
from services import analytics_service as analytics
from config.settings import SEVERITY_LEVELS, COLORS


def render():
    st.markdown("""
    <style>
    .gov-metric { background: linear-gradient(135deg, #1E293B, #0F172A);
                  border:1px solid #334155; border-radius:14px; padding:18px;
                  text-align:center; }
    .gov-metric .value { font-size:2.4rem; font-weight:900; color:#00D4FF; }
    .gov-metric .label { font-size:0.85rem; color:#94A3B8; margin-top:4px; }
    .gov-metric.danger .value { color:#EF4444; }
    .gov-metric.warning .value { color:#F59E0B; }
    .gov-metric.success .value { color:#10B981; }
    .section-header { color:#E2E8F0; font-size:1.2rem; font-weight:700;
                      margin:20px 0 12px 0; padding-bottom:6px;
                      border-bottom:2px solid #334155; }
    </style>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div style='text-align:center; padding:16px 0 8px 0;'>
        <h1 style='color:#00D4FF; font-size:2rem; margin:0;'>🏛️ Government Disaster Command Center</h1>
        <p style='color:#94A3B8;'>Chennai Flood Response Operations - Live Dashboard</p>
    </div>
    """, unsafe_allow_html=True)

    # ── KPI Row ────────────────────────────────────────────────────────────────
    summary = db.get_dashboard_summary()
    disasters = db.get_active_disasters()

    c1, c2, c3, c4, c5, c6, c7 = st.columns(7)
    kpis = [
        (c1, summary["active_disasters"],       "Active Disasters",   "danger"),
        (c2, summary["total_requests"],          "Total Requests",     ""),
        (c3, summary["pending_requests"],        "Pending",            "danger" if summary["pending_requests"]>10 else "warning"),
        (c4, summary["dispatched_ambulances"],   "Ambs Dispatched",    "warning"),
        (c5, summary["available_ambulances"],    "Ambs Available",     "success"),
        (c6, summary["blocked_roads"],           "Roads Blocked",      "danger"),
        (c7, summary["deployed_resources"],      "Resources Deployed", "warning"),
    ]
    for col, val, label, cls in kpis:
        with col:
            st.markdown(f"""
            <div class='gov-metric {cls}'>
                <div class='value'>{val}</div>
                <div class='label'>{label}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Active Disaster Alerts ─────────────────────────────────────────────────
    if disasters:
        for d in disasters:
            sev = d["severity"]
            sev_info = SEVERITY_LEVELS.get(sev, {"emoji":"[!]️","label":"Unknown","color":"#888"})
            st.markdown(f"""
            <div style='background:linear-gradient(90deg,{sev_info["color"]}22,transparent);
                        border-left:5px solid {sev_info["color"]}; border-radius:10px;
                        padding:16px 20px; margin-bottom:10px;'>
                <b style='color:{sev_info["color"]};'>{sev_info["emoji"]} {d["name"]}</b>
                &nbsp;&nbsp;|&nbsp;&nbsp; Type: {d["disaster_type"]}
                &nbsp;&nbsp;|&nbsp;&nbsp; Severity: {sev}/5 ({sev_info["label"]})
                &nbsp;&nbsp;|&nbsp;&nbsp; Affected: <b>{d["affected_people"]:,}</b> people
                &nbsp;&nbsp;|&nbsp;&nbsp; Radius: {d["affected_radius_km"]} km
                &nbsp;&nbsp;|&nbsp;&nbsp; Status: <b>{d["status"]}</b>
            </div>
            """, unsafe_allow_html=True)

    # ── Live Map ───────────────────────────────────────────────────────────────
    st.markdown('<div class="section-header">🗺️ Live Disaster Overview Map</div>',
                unsafe_allow_html=True)

    hospitals     = db.get_all_hospitals()
    ambulances    = db.get_all_ambulances()
    blocked_roads = db.get_blocked_roads()
    requests      = db.get_all_requests()
    shelters      = db.get_shelters()

    overview_map = create_disaster_overview_map(
        disasters=disasters,
        hospitals=hospitals,
        ambulances=ambulances,
        blocked_roads=blocked_roads,
        emergency_requests=requests,
        shelters=shelters,
    )
    st_folium(overview_map, width=None, height=550, key="gov_map")

    # ── Analytics Row ──────────────────────────────────────────────────────────
    st.markdown('<div class="section-header">📊 Analytics</div>', unsafe_allow_html=True)

    col_a, col_b = st.columns(2)
    with col_a:
        st.plotly_chart(analytics.request_status_pie(requests),
                        use_container_width=True, key="status_pie")
    with col_b:
        st.plotly_chart(analytics.severity_distribution_chart(requests),
                        use_container_width=True, key="sev_dist")

    col_c, col_d = st.columns(2)
    with col_c:
        resources = db.get_all_resources()
        st.plotly_chart(analytics.resource_utilization_chart(resources, ambulances),
                        use_container_width=True, key="resource_util")
    with col_d:
        st.plotly_chart(analytics.road_condition_chart(db.get_all_roads()),
                        use_container_width=True, key="road_cond")

    st.plotly_chart(analytics.requests_over_time_chart(requests),
                    use_container_width=True, key="req_time")

    # ── Road Closures Table ────────────────────────────────────────────────────
    st.markdown('<div class="section-header">🚧 Active Road Closures</div>',
                unsafe_allow_html=True)

    condition_emoji = {"Flooded":"🌊", "Blocked":"🚧", "Damaged":"[!]️",
                       "Collapsed":"💥", "Clear":"[DONE]"}
    if blocked_roads:
        cols = st.columns([3,2,2,2,2])
        for c, h in zip(cols, ["Road Name","From","To","Condition","Severity"]):
            c.markdown(f"**{h}**")
        for road in blocked_roads:
            c1,c2,c3,c4,c5 = st.columns([3,2,2,2,2])
            cond = road.get("condition","Blocked")
            c1.write(road["road_name"])
            c2.write(road["from_location"])
            c3.write(road["to_location"])
            c4.write(f"{condition_emoji.get(cond,'🚧')} {cond}")
            c5.write(f"{'🔴' if road.get('severity',0)>=4 else '🟡' if road.get('severity',0)>=2 else '🟢'} {road.get('severity',0)}/5")
    else:
        st.success("All roads are clear!")

    # ── Shelter Occupancy ──────────────────────────────────────────────────────
    st.markdown('<div class="section-header">🏠 Emergency Shelter Status</div>',
                unsafe_allow_html=True)
    if shelters:
        for s in shelters:
            occ_pct = (s.get("current_occupancy", 0) / max(s.get("capacity", 1), 1)) * 100
            bar_color = "#10B981" if occ_pct < 70 else "#F59E0B" if occ_pct < 95 else "#EF4444"
            col_s1, col_s2, col_s3 = st.columns([3,2,1])
            with col_s1:
                st.write(f"🏠 **{s['name']}**")
            with col_s2:
                st.progress(int(occ_pct), text=f"{s['current_occupancy']:,}/{s['capacity']:,} ({occ_pct:.0f}%)")
            with col_s3:
                status_color = "#10B981" if occ_pct < 70 else "#EF4444"
                st.markdown(f"<span style='color:{status_color};'>{s.get('status','Active')}</span>",
                            unsafe_allow_html=True)

    # ── Recent Agent Activity ──────────────────────────────────────────────────
    st.markdown('<div class="section-header">🤖 Recent Agent Activity</div>',
                unsafe_allow_html=True)
    logs = db.get_agent_logs(limit=10)
    if logs:
        st.plotly_chart(analytics.agent_timeline_chart(logs),
                        use_container_width=True, key="agent_timeline")
        for log in logs[:5]:
            mode_badge = f"<span style='background:#1E3A5F;color:#00D4FF;padding:2px 8px;border-radius:10px;font-size:0.75rem;'>{log.get('mode','?').upper()}</span>"
            st.markdown(f"**{log['agent_name']}** - {log['decision'][:100]} {mode_badge}",
                        unsafe_allow_html=True)

    # ── Refresh control ────────────────────────────────────────────────────────
    st.divider()
    col_ref, col_info = st.columns([1, 3])
    with col_ref:
        if st.button("🔄 Refresh Dashboard", use_container_width=True):
            st.rerun()
    with col_info:
        from datetime import datetime
        st.caption(f"Last updated: {datetime.now().strftime('%H:%M:%S')} | Auto-refresh: manual")
