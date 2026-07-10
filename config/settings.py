"""
ResQNet AI - Application Configuration
Centralizes all settings, constants, and environment loading.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# ── Load .env file ──────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

# ── API Configuration ────────────────────────────────────────────────────────
GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL: str = "gemini-2.0-flash"          # Primary model
GEMINI_MODEL_FALLBACK: str = "gemini-1.5-flash" # Fallback if primary unavailable

# ── Database ─────────────────────────────────────────────────────────────────
DATABASE_PATH: str = str(BASE_DIR / os.getenv("DATABASE_PATH", "resqnet.db"))

# ── App Meta ──────────────────────────────────────────────────────────────────
APP_TITLE: str = os.getenv("APP_TITLE", "ResQNet AI")
APP_VERSION: str = os.getenv("APP_VERSION", "1.0.0")
APP_MODE: str = os.getenv("APP_MODE", "live")   # "live" | "simulation"
DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"

# ── Chennai Flood Scenario - Default Map Center ───────────────────────────────
DEFAULT_MAP_CENTER: tuple = (13.0827, 80.2707)  # Chennai city center
DEFAULT_MAP_ZOOM: int = 12

# ── Disaster Types ────────────────────────────────────────────────────────────
DISASTER_TYPES = ["Flood", "Cyclone", "Earthquake", "Fire", "Landslide", "Tsunami"]

# ── Severity Levels ───────────────────────────────────────────────────────────
SEVERITY_LEVELS = {
    1: {"label": "Low",      "color": "#22c55e", "emoji": "🟢"},
    2: {"label": "Moderate", "color": "#f59e0b", "emoji": "🟡"},
    3: {"label": "High",     "color": "#f97316", "emoji": "🟠"},
    4: {"label": "Critical", "color": "#ef4444", "emoji": "🔴"},
    5: {"label": "Extreme",  "color": "#7c3aed", "emoji": "🟣"},
}

# ── Resource Types ────────────────────────────────────────────────────────────
RESOURCE_TYPES = ["Ambulance", "Rescue Boat", "Fire Truck", "Rescue Team", "Helicopter"]

# ── Hospital Status ───────────────────────────────────────────────────────────
HOSPITAL_STATUSES = ["Operational", "At Capacity", "Overloaded", "Offline"]

# ── Road Condition Flags ──────────────────────────────────────────────────────
ROAD_CONDITIONS = ["Clear", "Blocked", "Flooded", "Damaged", "Collapsed"]

# ── Agent Names ───────────────────────────────────────────────────────────────
AGENT_NAMES = {
    "orchestrator":         "Orchestrator Agent",
    "disaster_assessment":  "Disaster Assessment Agent",
    "hospital_allocation":  "Hospital Allocation Agent",
    "road_intelligence":    "Road Intelligence Agent",
    "resource":             "Emergency Resource Agent",
    "communication":        "Communication Agent",
    "monitoring":           "Monitoring Agent",
}

# ── Gemini Request Settings ───────────────────────────────────────────────────
GEMINI_TEMPERATURE: float = 0.3       # Lower = more deterministic for safety-critical tasks
GEMINI_MAX_TOKENS: int = 8192
GEMINI_TIMEOUT: int = 30              # seconds

# ── Timing ────────────────────────────────────────────────────────────────────
MONITORING_INTERVAL_SECONDS: int = 30   # How often Monitoring Agent re-checks
AUTO_REFRESH_INTERVAL: int = 15         # Dashboard auto-refresh (seconds)

# ── Color Palette ─────────────────────────────────────────────────────────────
COLORS = {
    "primary":    "#FF4B4B",
    "secondary":  "#1E3A5F",
    "accent":     "#00D4FF",
    "warning":    "#F59E0B",
    "danger":     "#EF4444",
    "success":    "#10B981",
    "bg_dark":    "#0F172A",
    "bg_card":    "#1E293B",
    "text_light": "#E2E8F0",
}

# ── Chennai Area Bounds (for map validation) ───────────────────────────────────
CHENNAI_BOUNDS = {
    "lat_min": 12.85, "lat_max": 13.25,
    "lon_min": 80.05, "lon_max": 80.45,
}
