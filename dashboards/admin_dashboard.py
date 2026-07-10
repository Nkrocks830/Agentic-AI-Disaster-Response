"""
ResQNet AI - Admin Dashboard
System management, agent logs, hospital/ambulance/resource management, analytics.
"""

import streamlit as st
import json
import pandas as pd
from database import db_manager as db
from services import analytics_service as analytics
from services.gemini_service import get_mode_info


def render():
    st.markdown("""
    <style>
    .admin-card { background:#1E293B; border:1px solid #475569; border-radius:12px;
                  padding:18px; margin-bottom:12px; }
    .log-entry { background:#0F172A; border-left:3px solid #334155; border-radius:6px;
                 padding:10px 14px; margin:6px 0; font-size:0.85rem; }
    .log-success { border-left-color:#10B981; }
    .log-failed  { border-left-color:#EF4444; }
    .log-sim     { border-left-color:#7C3AED; }
    .badge { display:inline-block; padding:2px 10px; border-radius:10px;
             font-size:0.75rem; font-weight:600; }
    </style>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div style='text-align:center; padding:16px 0 8px 0;'>
        <h1 style='color:#7C3AED; font-size:2rem; margin:0;'>⚙️ ResQNet AI - Admin Console</h1>
        <p style='color:#94A3B8;'>System management · Agent logs · Resource administration</p>
    </div>
    """, unsafe_allow_html=True)

    # ── Mode Banner ────────────────────────────────────────────────────────────
    mode_info = get_mode_info()
    mode = mode_info["mode"]
    reason = mode_info["reason"]
    mode_color = "#10B981" if mode == "live" else "#7C3AED"
    mode_icon = "🟢" if mode == "live" else "🟣"
    st.markdown(f"""
    <div style='background:linear-gradient(90deg,{mode_color}22,transparent);
                border:1px solid {mode_color}; border-radius:10px; padding:12px 20px;
                margin-bottom:16px;'>
        {mode_icon} <b>AI Mode: {mode.upper()}</b> &nbsp;|&nbsp; {reason}
    </div>
    """, unsafe_allow_html=True)

    tabs = st.tabs([
        "📊 System Overview",
        "🤖 Agent Logs",
        "🏥 Hospital Mgmt",
        "🚑 Ambulance Mgmt",
        "⛵ Resource Mgmt",
        "📨 Notifications",
    ])

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 1: SYSTEM OVERVIEW
    # ══════════════════════════════════════════════════════════════════════════
    with tabs[0]:
        summary = db.get_dashboard_summary()
        c1,c2,c3 = st.columns(3)
        c1.metric("🏥 Hospitals",        len(db.get_all_hospitals()))
        c2.metric("🚑 Ambulances",        len(db.get_all_ambulances()))
        c3.metric("⛵ Resources",          len(db.get_all_resources()))
        c4,c5,c6 = st.columns(3)
        c4.metric("📝 Total Requests",    summary["total_requests"])
        c5.metric("🚧 Blocked Roads",     summary["blocked_roads"])
        c6.metric("🔥 Active Disasters",  summary["active_disasters"])

        st.divider()

        # Agent log analytics
        logs = db.get_agent_logs(limit=200)
        st.markdown("#### ⚡ Agent Execution Performance")
        st.plotly_chart(analytics.agent_timeline_chart(logs),
                        use_container_width=True, key="adm_timeline")

        # Mode breakdown
        if logs:
            live_count = sum(1 for l in logs if l.get("mode") == "live")
            sim_count = len(logs) - live_count
            success_count = sum(1 for l in logs if l.get("status") == "success")
            fail_count = len(logs) - success_count
            cc1,cc2,cc3,cc4 = st.columns(4)
            cc1.metric("🟢 Live Executions",       live_count)
            cc2.metric("🟣 Simulation Executions", sim_count)
            cc3.metric("[DONE] Successful",            success_count)
            cc4.metric("[X] Failed",                fail_count)

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 2: AGENT LOGS
    # ══════════════════════════════════════════════════════════════════════════
    with tabs[1]:
        st.markdown("#### 🤖 Agent Execution Log")

        col_f1, col_f2, col_f3 = st.columns([2,2,1])
        with col_f1:
            agent_filter = st.selectbox("Filter by Agent",
                                        ["All"] + list({l["agent_name"] for l in db.get_agent_logs(limit=500)}))
        with col_f2:
            status_filter = st.selectbox("Filter by Status", ["All", "success", "failed"])
        with col_f3:
            log_limit = st.number_input("Limit", min_value=10, max_value=500, value=50)

        logs = db.get_agent_logs(
            limit=log_limit,
            agent_name=agent_filter if agent_filter != "All" else None,
        )
        if status_filter != "All":
            logs = [l for l in logs if l.get("status") == status_filter]

        st.caption(f"Showing {len(logs)} log entries")

        for log in logs:
            status = log.get("status", "success")
            mode = log.get("mode", "live")
            css_class = f"log-entry log-{'success' if status=='success' else 'failed'}"
            if mode == "simulation":
                css_class += " log-sim"

            mode_badge_color = "#10B981" if mode == "live" else "#7C3AED"
            status_badge_color = "#10B981" if status == "success" else "#EF4444"

            st.markdown(f"""
            <div class='{css_class}'>
                <div style='display:flex; justify-content:space-between; align-items:center;'>
                    <b style='color:#E2E8F0;'>{log.get('agent_name','?')}</b>
                    <div>
                        <span class='badge' style='background:{mode_badge_color}22;color:{mode_badge_color};border:1px solid {mode_badge_color};'>{mode.upper()}</span>
                        &nbsp;
                        <span class='badge' style='background:{status_badge_color}22;color:{status_badge_color};border:1px solid {status_badge_color};'>{status.upper()}</span>
                        &nbsp;
                        <small style='color:#64748B;'>{str(log.get('created_at',''))[:19]}</small>
                    </div>
                </div>
                <div style='color:#94A3B8; margin-top:4px;'>{log.get('decision','')[:200]}</div>
                {"<div style='color:#64748B; font-size:0.8rem;'>Req #" + str(log.get('request_id','--')) + " | " + str(log.get('execution_time_ms',0)) + "ms</div>" if log.get('request_id') else ""}
            </div>
            """, unsafe_allow_html=True)

        if st.button("📥 Export Logs as CSV"):
            if logs:
                df = pd.DataFrame(logs)
                csv = df.to_csv(index=False)
                st.download_button("Download", csv, "agent_logs.csv", "text/csv")

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 3: HOSPITAL MANAGEMENT
    # ══════════════════════════════════════════════════════════════════════════
    with tabs[2]:
        st.markdown("#### 🏥 Hospital Management")
        hospitals = db.get_all_hospitals()

        for h in hospitals:
            with st.expander(f"🏥 {h['name']} - {h['status']}", expanded=False):
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**Address:** {h['address']}")
                    st.write(f"**Beds:** {h['available_beds']}/{h['total_beds']}")
                    st.write(f"**ICU:** {h['available_icu']}/{h['total_icu']}")
                    st.write(f"**Doctors:** {h['available_doctors']}/{h['total_doctors']}")
                with col2:
                    new_status = st.selectbox("Status", ["Operational","At Capacity","Overloaded","Offline"],
                                             index=["Operational","At Capacity","Overloaded","Offline"].index(
                                                 h["status"] if h["status"] in ["Operational","At Capacity","Overloaded","Offline"] else "Operational"),
                                             key=f"hosp_status_{h['id']}")
                    bed_adj = st.number_input("Adjust Available Beds (+/-)", min_value=-100, max_value=100, value=0,
                                              key=f"bed_adj_{h['id']}")
                    if st.button("💾 Update", key=f"hosp_update_{h['id']}"):
                        db.update_hospital_status(h["id"], new_status)
                        if bed_adj != 0:
                            db.update_hospital_beds(h["id"], bed_adj, 0)
                        st.success(f"Hospital {h['name']} updated!")
                        st.rerun()

        st.plotly_chart(analytics.hospital_capacity_chart(hospitals),
                        use_container_width=True, key="adm_hosp_chart")

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 4: AMBULANCE MANAGEMENT
    # ══════════════════════════════════════════════════════════════════════════
    with tabs[3]:
        st.markdown("#### 🚑 Ambulance Fleet Management")
        ambulances = db.get_all_ambulances()

        status_colors = {"Available":"#10B981","Dispatched":"#EF4444",
                         "En Route":"#F59E0B","At Hospital":"#00D4FF"}

        df_data = []
        for a in ambulances:
            df_data.append({
                "ID": a["id"],
                "Vehicle": a["vehicle_number"],
                "Driver": a["driver_name"],
                "Phone": a["driver_phone"],
                "Status": a["status"],
                "Fuel %": a.get("fuel_level", 100),
                "Lat": a["latitude"],
                "Lon": a["longitude"],
            })
        if df_data:
            df = pd.DataFrame(df_data)
            st.dataframe(df, use_container_width=True, hide_index=True)

        st.markdown("**Release All Dispatched Ambulances (After Shift Reset)**")
        if st.button("🔄 Release All Ambulances to Available"):
            for a in ambulances:
                if a["status"] != "Available":
                    db.release_ambulance(a["id"])
            st.success("All ambulances released to Available!")
            st.rerun()

        st.plotly_chart(analytics.resource_utilization_chart([], ambulances),
                        use_container_width=True, key="adm_amb_chart")

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 5: RESOURCE MANAGEMENT
    # ══════════════════════════════════════════════════════════════════════════
    with tabs[4]:
        st.markdown("#### ⛵ Emergency Resource Management")
        resources = db.get_all_resources()

        for r in resources:
            s_color = "#10B981" if r["status"] == "Available" else "#EF4444"
            col1, col2 = st.columns([3, 1])
            with col1:
                st.markdown(f"""
                <div class='admin-card'>
                    <b>{r['name']}</b> &nbsp;
                    <span class='badge' style='background:{s_color}22;color:{s_color};border:1px solid {s_color};'>
                        {r['status']}
                    </span><br>
                    Type: {r['resource_type']} | Capacity: {r['capacity']}<br>
                    📍 {r['location_name']}<br>
                    👤 {r.get('operator_name','')} - {r.get('operator_phone','')}
                </div>
                """, unsafe_allow_html=True)
            with col2:
                st.markdown("<br><br>", unsafe_allow_html=True)
                if r["status"] == "Deployed":
                    if st.button("↩️ Release", key=f"rel_{r['id']}", use_container_width=True):
                        db.release_resource(r["id"])
                        st.success("Resource released!")
                        st.rerun()
                else:
                    disasters = db.get_active_disasters()
                    if disasters and st.button("🚀 Deploy", key=f"dep_{r['id']}", use_container_width=True):
                        db.deploy_resource(r["id"], disasters[0]["id"])
                        st.success("Resource deployed!")
                        st.rerun()

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 6: NOTIFICATIONS
    # ══════════════════════════════════════════════════════════════════════════
    with tabs[5]:
        st.markdown("#### 📨 Notification Log")
        notifications = db.get_notifications(limit=100)

        type_icons = {"citizen":"👤","hospital":"🏥","ambulance":"🚑",
                      "authority":"🏛️","public":"📢"}
        channel_icons = {"sms":"📱","email":"📧","app":"📲","broadcast":"📡"}

        if notifications:
            for n in notifications:
                t_icon = type_icons.get(n.get("recipient_type",""), "📬")
                c_icon = channel_icons.get(n.get("channel",""), "📨")
                st.markdown(f"""
                <div class='log-entry log-success'>
                    <div style='display:flex; justify-content:space-between;'>
                        <span>{t_icon} <b>{n.get('recipient_type','').title()}</b>
                        - {n.get('recipient_name','')} {c_icon}</span>
                        <small style='color:#64748B;'>{str(n.get('created_at',''))[:19]}</small>
                    </div>
                    <div style='color:#CBD5E1; margin-top:4px; font-size:0.82rem;'>
                        {str(n.get('message',''))[:200]}
                    </div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("No notifications logged yet.")
