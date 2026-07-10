"""
ResQNet AI - Analytics Service
Generates Plotly charts for all dashboards.
"""

import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
from typing import List, Dict, Any


# ── Color palette ──────────────────────────────────────────────────────────────
PALETTE = ["#00D4FF", "#FF4B4B", "#10B981", "#F59E0B", "#7C3AED", "#EC4899"]
BG_COLOR = "#0F172A"
CARD_COLOR = "#1E293B"
TEXT_COLOR = "#E2E8F0"

PLOTLY_DARK_LAYOUT = dict(
    paper_bgcolor=BG_COLOR,
    plot_bgcolor=CARD_COLOR,
    font_color=TEXT_COLOR,
    title_font_color=TEXT_COLOR,
    margin=dict(l=20, r=20, t=50, b=30),
    legend=dict(bgcolor=CARD_COLOR, font_color=TEXT_COLOR),
)


def hospital_capacity_chart(hospitals: List[Dict]) -> go.Figure:
    """Grouped bar chart - beds and ICU availability per hospital."""
    names = [h["name"].split("-")[0].strip()[:22] for h in hospitals]
    available_beds = [h["available_beds"] for h in hospitals]
    total_beds = [h["total_beds"] for h in hospitals]
    available_icu = [h["available_icu"] for h in hospitals]
    total_icu = [h["total_icu"] for h in hospitals]

    fig = go.Figure()
    fig.add_trace(go.Bar(name="Beds Used", x=names,
                         y=[t - a for t, a in zip(total_beds, available_beds)],
                         marker_color="#EF4444", text=[f"{t-a}" for t, a in zip(total_beds, available_beds)],
                         textposition="inside"))
    fig.add_trace(go.Bar(name="Beds Available", x=names,
                         y=available_beds, marker_color="#10B981",
                         text=available_beds, textposition="inside"))
    fig.add_trace(go.Bar(name="ICU Available", x=names,
                         y=available_icu, marker_color="#00D4FF",
                         text=available_icu, textposition="inside"))

    fig.update_layout(
        barmode="stack",
        title="🏥 Hospital Capacity Overview",
        xaxis_title="Hospital",
        yaxis_title="Beds",
        **PLOTLY_DARK_LAYOUT
    )
    return fig


def request_status_pie(requests: List[Dict]) -> go.Figure:
    """Pie chart of emergency request statuses."""
    status_counts: Dict[str, int] = {}
    for r in requests:
        s = r.get("status", "Pending")
        status_counts[s] = status_counts.get(s, 0) + 1

    colors = {"Pending": "#EF4444", "Processing": "#F59E0B",
              "Dispatched": "#00D4FF", "Resolved": "#10B981"}
    labels = list(status_counts.keys())
    values = list(status_counts.values())
    chart_colors = [colors.get(l, "#7C3AED") for l in labels]

    fig = go.Figure(go.Pie(
        labels=labels, values=values,
        hole=0.5,
        marker_colors=chart_colors,
        textinfo="label+percent",
        hovertemplate="<b>%{label}</b><br>Count: %{value}<br>%{percent}<extra></extra>",
    ))
    fig.update_layout(
        title="📊 Emergency Request Status",
        **PLOTLY_DARK_LAYOUT,
    )
    return fig


def resource_utilization_chart(resources: List[Dict], ambulances: List[Dict]) -> go.Figure:
    """Horizontal bar chart of resource utilization."""
    categories = []
    available = []
    deployed = []

    # Ambulances
    avail_amb = sum(1 for a in ambulances if a["status"] == "Available")
    dep_amb = len(ambulances) - avail_amb
    categories.append("Ambulances")
    available.append(avail_amb)
    deployed.append(dep_amb)

    # Other resources by type
    resource_types: Dict[str, Dict] = {}
    for r in resources:
        rt = r.get("resource_type", "Other")
        if rt not in resource_types:
            resource_types[rt] = {"available": 0, "deployed": 0}
        if r["status"] == "Available":
            resource_types[rt]["available"] += 1
        else:
            resource_types[rt]["deployed"] += 1

    for rt, counts in resource_types.items():
        categories.append(rt)
        available.append(counts["available"])
        deployed.append(counts["deployed"])

    fig = go.Figure()
    fig.add_trace(go.Bar(name="Available", y=categories, x=available,
                         orientation="h", marker_color="#10B981",
                         text=available, textposition="auto"))
    fig.add_trace(go.Bar(name="Deployed", y=categories, x=deployed,
                         orientation="h", marker_color="#EF4444",
                         text=deployed, textposition="auto"))

    fig.update_layout(
        barmode="stack",
        title="🚑 Resource Utilization",
        xaxis_title="Count",
        **PLOTLY_DARK_LAYOUT,
    )
    return fig


def severity_distribution_chart(requests: List[Dict]) -> go.Figure:
    """Bar chart of severity distribution."""
    sev_counts = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    for r in requests:
        sev = r.get("severity", 1)
        if sev in sev_counts:
            sev_counts[sev] += 1

    labels = ["Low (1)", "Moderate (2)", "High (3)", "Critical (4)", "Extreme (5)"]
    values = list(sev_counts.values())
    colors = ["#22c55e", "#eab308", "#f97316", "#ef4444", "#7c3aed"]

    fig = go.Figure(go.Bar(
        x=labels, y=values,
        marker_color=colors,
        text=values, textposition="auto",
    ))
    fig.update_layout(
        title="⚡ Severity Distribution",
        xaxis_title="Severity Level",
        yaxis_title="Number of Requests",
        **PLOTLY_DARK_LAYOUT,
    )
    return fig


def road_condition_chart(roads: List[Dict]) -> go.Figure:
    """Pie chart of road conditions."""
    condition_counts: Dict[str, int] = {}
    for r in roads:
        c = r.get("condition", "Clear")
        condition_counts[c] = condition_counts.get(c, 0) + 1

    colors_map = {
        "Clear": "#10B981", "Blocked": "#EF4444",
        "Flooded": "#3B82F6", "Damaged": "#F59E0B", "Collapsed": "#7C3AED"
    }
    labels = list(condition_counts.keys())
    values = list(condition_counts.values())
    chart_colors = [colors_map.get(l, "#6B7280") for l in labels]

    fig = go.Figure(go.Pie(
        labels=labels, values=values,
        hole=0.4, marker_colors=chart_colors,
        textinfo="label+value",
    ))
    fig.update_layout(
        title="🛣️ Road Network Conditions",
        **PLOTLY_DARK_LAYOUT,
    )
    return fig


def agent_timeline_chart(logs: List[Dict]) -> go.Figure:
    """Gantt-style chart of agent execution times."""
    if not logs:
        fig = go.Figure()
        fig.update_layout(title="No agent logs yet", **PLOTLY_DARK_LAYOUT)
        return fig

    # Take last 20 logs
    recent = logs[-20:]
    agents = [l["agent_name"] for l in recent]
    times = [l.get("execution_time_ms", 0) for l in recent]
    statuses = [l.get("status", "success") for l in recent]
    colors = ["#10B981" if s == "success" else "#EF4444" for s in statuses]

    fig = go.Figure(go.Bar(
        y=agents, x=times, orientation="h",
        marker_color=colors,
        text=[f"{t}ms" for t in times],
        textposition="auto",
        hovertemplate="<b>%{y}</b><br>Time: %{x}ms<extra></extra>",
    ))
    fig.update_layout(
        title="⚡ Agent Execution Times (Recent)",
        xaxis_title="Execution Time (ms)",
        **PLOTLY_DARK_LAYOUT,
    )
    return fig


def hospital_occupancy_gauge(hospital: Dict) -> go.Figure:
    """Gauge chart for a single hospital's bed occupancy."""
    total = hospital.get("total_beds", 1)
    avail = hospital.get("available_beds", 0)
    used = total - avail
    pct = (used / max(total, 1)) * 100

    color = "#10B981" if pct < 70 else "#F59E0B" if pct < 90 else "#EF4444"

    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=pct,
        number={"suffix": "%", "font": {"color": TEXT_COLOR}},
        delta={"reference": 70, "increasing": {"color": "#EF4444"}, "decreasing": {"color": "#10B981"}},
        gauge={
            "axis": {"range": [0, 100], "tickcolor": TEXT_COLOR},
            "bar": {"color": color},
            "bgcolor": CARD_COLOR,
            "steps": [
                {"range": [0, 70], "color": "#1E3A5F"},
                {"range": [70, 90], "color": "#3D2B00"},
                {"range": [90, 100], "color": "#3D0000"},
            ],
            "threshold": {
                "line": {"color": "#EF4444", "width": 4},
                "thickness": 0.75, "value": 90,
            },
        },
        title={"text": f"Bed Occupancy<br><sub>{used}/{total} beds used</sub>",
               "font": {"color": TEXT_COLOR}},
    ))
    fig.update_layout(**PLOTLY_DARK_LAYOUT)
    return fig


def requests_over_time_chart(requests: List[Dict]) -> go.Figure:
    """Line chart of emergency requests arriving over time."""
    if not requests:
        fig = go.Figure()
        fig.update_layout(title="No requests yet", **PLOTLY_DARK_LAYOUT)
        return fig

    try:
        df = pd.DataFrame(requests)
        df["created_at"] = pd.to_datetime(df["created_at"])
        df["hour"] = df["created_at"].dt.floor("H")
        hourly = df.groupby("hour").size().reset_index(name="count")

        fig = go.Figure(go.Scatter(
            x=hourly["hour"], y=hourly["count"],
            mode="lines+markers",
            line=dict(color="#00D4FF", width=3),
            marker=dict(size=8, color="#FF4B4B"),
            fill="tozeroy",
            fillcolor="rgba(0, 212, 255, 0.1)",
        ))
        fig.update_layout(
            title="📈 Emergency Requests Over Time",
            xaxis_title="Time",
            yaxis_title="Requests",
            **PLOTLY_DARK_LAYOUT,
        )
    except Exception:
        fig = go.Figure()
        fig.update_layout(title="Request timeline unavailable", **PLOTLY_DARK_LAYOUT)
    return fig
