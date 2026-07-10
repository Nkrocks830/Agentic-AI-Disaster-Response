# -*- coding: utf-8 -*-
# ResQNet AI - Main Application
# Run with: streamlit run app.py

"""
ResQNet AI - Agentic Disaster Response Coordination Platform
============================================================
"""

import sys
import os

# Set UTF-8 encoding env vars BEFORE any imports (Windows fix)
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
os.environ.setdefault("PYTHONUTF8", "1")

# ── Ensure project root is in Python path ────────────────────────────────────
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import streamlit as st
from database.db_manager import initialize_database
from database.seed_data import run_seed
from services.gemini_service import initialize_gemini, get_mode_info

# ══════════════════════════════════════════════════════════════════════════════
# PAGE CONFIG  (must be first Streamlit call)
# ══════════════════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="ResQNet AI - Disaster Response",
    page_icon="🆘",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        "Get Help": "https://github.com/resqnet-ai",
        "About": "ResQNet AI - Agentic Disaster Response Coordination Platform v1.0",
    },
)

# ══════════════════════════════════════════════════════════════════════════════
# GLOBAL CSS
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<style>
/* ── Google Font ── */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;900&display=swap');

/* ── Base ── */
html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0F172A 0%, #1E293B 100%);
    border-right: 1px solid #334155;
}
[data-testid="stSidebar"] .stMarkdown p {
    color: #CBD5E1;
}

/* ── Main background ── */
.stApp {
    background: #0F172A;
    color: #E2E8F0;
}

/* ── Metric styling ── */
[data-testid="stMetricValue"] {
    color: #00D4FF;
    font-weight: 700;
}
[data-testid="stMetricDelta"] {
    font-size: 0.8rem;
}

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"] {
    background: #1E293B;
    border-radius: 10px;
    padding: 4px;
    gap: 4px;
}
.stTabs [data-baseweb="tab"] {
    background: transparent;
    color: #94A3B8;
    border-radius: 8px;
    font-weight: 500;
}
.stTabs [aria-selected="true"] {
    background: #334155 !important;
    color: #00D4FF !important;
}

/* ── Buttons ── */
.stButton > button {
    background: linear-gradient(135deg, #1E3A5F, #1E293B);
    border: 1px solid #334155;
    color: #E2E8F0;
    border-radius: 10px;
    font-weight: 500;
    transition: all 0.2s ease;
}
.stButton > button:hover {
    border-color: #00D4FF;
    color: #00D4FF;
    box-shadow: 0 0 15px rgba(0,212,255,0.2);
    transform: translateY(-1px);
}
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #EF4444, #7C3AED);
    border-color: #EF4444;
    color: white;
    font-weight: 700;
    font-size: 1rem;
    padding: 12px;
}
.stButton > button[kind="primary"]:hover {
    box-shadow: 0 0 25px rgba(239,68,68,0.4);
    transform: translateY(-2px);
}

/* ── Selectbox / inputs ── */
.stSelectbox > div > div,
.stTextInput > div > div > input,
.stNumberInput > div > div > input,
.stTextArea > div > div > textarea {
    background: #1E293B;
    border: 1px solid #334155;
    color: #E2E8F0;
    border-radius: 8px;
}

/* ── Expander ── */
.streamlit-expanderHeader {
    background: #1E293B;
    border-radius: 8px;
    color: #E2E8F0;
}

/* ── Progress bar ── */
.stProgress > div > div {
    background: linear-gradient(90deg, #00D4FF, #7C3AED);
    border-radius: 4px;
}

/* ── Divider ── */
hr {
    border-color: #334155;
}

/* ── Sidebar logo area ── */
.sidebar-logo {
    text-align: center;
    padding: 20px 0 10px 0;
    border-bottom: 1px solid #334155;
    margin-bottom: 20px;
}
.sidebar-logo h1 {
    font-size: 1.8rem;
    color: #00D4FF;
    margin: 0;
    font-weight: 900;
}
.sidebar-logo p {
    color: #94A3B8;
    font-size: 0.8rem;
    margin: 4px 0 0 0;
}

/* ── Nav link ── */
.nav-item {
    display: block;
    padding: 10px 16px;
    margin: 4px 0;
    border-radius: 10px;
    cursor: pointer;
    transition: all 0.2s;
    text-decoration: none;
    color: #CBD5E1;
    border: 1px solid transparent;
    font-weight: 500;
}
.nav-item:hover, .nav-item.active {
    background: #1E293B;
    border-color: #334155;
    color: #00D4FF;
}

/* ── Info/success/warning/error ── */
.stAlert {
    border-radius: 10px;
}
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# ONE-TIME INITIALIZATION (cached across sessions)
# ══════════════════════════════════════════════════════════════════════════════
@st.cache_resource
def _bootstrap():
    """Initialize DB, seed data, and Gemini - runs exactly once per server start."""
    print("[APP] Bootstrapping ResQNet AI...")
    initialize_database()
    run_seed()
    mode, reason = initialize_gemini()
    print(f"[APP] AI Mode: {mode.upper()} - {reason}")
    return {"mode": mode, "reason": reason}


boot = _bootstrap()


# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR NAVIGATION
# ══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("""
    <div class='sidebar-logo'>
        <h1>🆘 ResQNet AI</h1>
        <p>Agentic Disaster Response Platform</p>
    </div>
    """, unsafe_allow_html=True)

    # ── AI Mode badge ──────────────────────────────────────────────────────────
    mode = boot["mode"]
    mode_color  = "#10B981" if mode == "live" else "#7C3AED"
    mode_icon   = "🟢 LIVE AI" if mode == "live" else "🟣 SIMULATION"
    st.markdown(f"""
    <div style='background:{mode_color}22; border:1px solid {mode_color};
                border-radius:8px; padding:8px 12px; margin-bottom:16px;
                text-align:center; font-weight:600; color:{mode_color};'>
        {mode_icon}
    </div>
    """, unsafe_allow_html=True)

    st.markdown("### 📱 Select Dashboard")

    # Navigation state
    if "active_page" not in st.session_state:
        st.session_state["active_page"] = "🏛️ Government"

    pages = [
        ("🏛️ Government",    "Real-time disaster command"),
        ("🆘 Citizen",       "Report & track emergencies"),
        ("🏥 Hospital",      "Bed & patient management"),
        ("🚑 Ambulance",     "Mission & navigation"),
        ("⚙️ Admin",         "System & agent logs"),
    ]

    for page_name, desc in pages:
        is_active = st.session_state["active_page"] == page_name
        btn_type = "primary" if is_active else "secondary"
        if st.button(f"{page_name}", key=f"nav_{page_name}",
                     use_container_width=True, help=desc):
            st.session_state["active_page"] = page_name
            st.rerun()

    st.divider()

    # ── Active disaster info ───────────────────────────────────────────────────
    st.markdown("### 🌊 Active Disaster")
    try:
        from database.db_manager import get_active_disasters
        disasters = get_active_disasters()
        if disasters:
            d = disasters[0]
            sev_colors = {1:"#22c55e",2:"#eab308",3:"#f97316",4:"#ef4444",5:"#7c3aed"}
            s_color = sev_colors.get(d["severity"], "#888")
            st.markdown(f"""
            <div style='background:#1E293B; border:1px solid {s_color}; border-radius:8px;
                        padding:12px; font-size:0.85rem;'>
                <b style='color:{s_color};'>🌊 {d['disaster_type']} - Sev {d['severity']}/5</b><br>
                <span style='color:#94A3B8;'>{d['name'][:40]}...</span><br>
                👥 {d['affected_people']:,} people affected
            </div>
            """, unsafe_allow_html=True)
        else:
            st.info("No active disasters")
    except Exception:
        pass

    st.divider()

    # ── Quick stats ────────────────────────────────────────────────────────────
    st.markdown("### 📊 Quick Stats")
    try:
        from database.db_manager import get_dashboard_summary
        s = get_dashboard_summary()
        col1, col2 = st.columns(2)
        col1.metric("Requests", s["total_requests"])
        col2.metric("Pending",  s["pending_requests"])
        col1.metric("Ambs Free", s["available_ambulances"])
        col2.metric("Roads [X]",  s["blocked_roads"])
    except Exception:
        pass

    st.divider()
    st.caption("ResQNet AI v1.0 | Chennai Flood Response")
    st.caption("🆘 Emergency: 108 | 🏛️ Disaster: 1800-123-0011")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE ROUTING
# ══════════════════════════════════════════════════════════════════════════════
active_page = st.session_state.get("active_page", "🏛️ Government")

if active_page == "🏛️ Government":
    from dashboards.government_dashboard import render
    render()

elif active_page == "🆘 Citizen":
    from dashboards.citizen_dashboard import render
    render()

elif active_page == "🏥 Hospital":
    from dashboards.hospital_dashboard import render
    render()

elif active_page == "🚑 Ambulance":
    from dashboards.ambulance_dashboard import render
    render()

elif active_page == "⚙️ Admin":
    from dashboards.admin_dashboard import render
    render()
