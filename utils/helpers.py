"""
ResQNet AI - Utility Helpers
"""

import math
from datetime import datetime
from typing import Any, Dict, List, Optional


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in km between two GPS points."""
    R = 6371
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))


def eta_minutes(distance_km: float, speed_kmh: float = 35.0, overhead_min: int = 3) -> int:
    """Estimate ETA given distance and average speed."""
    return int((distance_km / max(speed_kmh, 1)) * 60) + overhead_min


def format_timestamp(ts: Optional[str]) -> str:
    """Format ISO timestamp to human-readable."""
    if not ts:
        return "--"
    try:
        dt = datetime.fromisoformat(ts)
        return dt.strftime("%d %b %Y, %H:%M")
    except Exception:
        return str(ts)[:19]


def severity_to_color(severity: int) -> str:
    colors = {1:"#22c55e", 2:"#eab308", 3:"#f97316", 4:"#ef4444", 5:"#7c3aed"}
    return colors.get(severity, "#888888")


def severity_to_label(severity: int) -> str:
    labels = {1:"Low", 2:"Moderate", 3:"High", 4:"Critical", 5:"Extreme"}
    return labels.get(severity, "Unknown")


def truncate(text: str, max_len: int = 100) -> str:
    return text[:max_len] + "..." if len(text) > max_len else text


def beds_occupancy_pct(total: int, available: int) -> float:
    if total == 0:
        return 0.0
    return round(((total - available) / total) * 100, 1)
