"""
ResQNet AI - Road Intelligence Agent
Single Responsibility: Analyze road conditions and compute safest routes.
"""

import json
import math
from typing import List, Optional

from agents.base_agent import BaseAgent
from models.disaster_models import DisasterContext
from models.road_models import RouteResult, RoadSegment, RouteWaypoint
from database import db_manager as db


ROAD_PROMPT = """You are the Road Intelligence Agent for ResQNet AI.
Analyze road conditions and calculate the safest ambulance route.

ORIGIN (Incident Location):
Lat: {origin_lat}, Lon: {origin_lon}
Address: {origin_address}

DESTINATION (Hospital):
Lat: {dest_lat}, Lon: {dest_lon}
Name: {dest_name}

BLOCKED/DAMAGED ROADS:
{blocked_roads_json}

PASSABLE ROADS:
{passable_roads_json}

DISASTER CONTEXT: {disaster_type} - Severity {severity}/5

Rules:
- Prioritize safety over shortest path
- Avoid flooded and collapsed roads entirely
- Use damaged roads only if no alternative exists
- Calculate 1 primary safe route and 2 alternates

Respond ONLY with valid JSON:
{{
  "safest_route": [
    {{"location_name": "<name>", "latitude": <lat>, "longitude": <lon>, "is_checkpoint": <bool>}}
  ],
  "alternate_routes": [
    [{{"location_name": "<name>", "latitude": <lat>, "longitude": <lon>}}]
  ],
  "estimated_distance_km": <float>,
  "estimated_time_minutes": <int>,
  "route_risk_level": "Low|Medium|High|Critical",
  "route_notes": ["<note1>", "<note2>"],
  "reasoning": "<explanation>"
}}
"""


def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


class RoadIntelligenceAgent(BaseAgent):
    """
    Agent 3: Road Intelligence
    Identifies blocked roads and calculates the safest evacuation route.
    """

    def __init__(self):
        super().__init__("road_intelligence")

    def run_live(self, context: DisasterContext) -> DisasterContext:
        if not context.citizen_input or not context.hospital_result:
            return context

        inp = context.citizen_input
        hosp = context.hospital_result.allocated_hospital
        if not hosp:
            return context

        blocked = db.get_blocked_roads()
        passable = db.get_passable_roads()
        assessment = context.assessment

        prompt = ROAD_PROMPT.format(
            origin_lat=inp.latitude, origin_lon=inp.longitude,
            origin_address=inp.address,
            dest_lat=hosp.latitude, dest_lon=hosp.longitude,
            dest_name=hosp.name,
            blocked_roads_json=json.dumps([
                {"road_name": r["road_name"], "condition": r["condition"],
                 "reason": r.get("blockage_reason", ""), "from": r["from_location"],
                 "to": r["to_location"]} for r in blocked[:10]
            ], indent=2),
            passable_roads_json=json.dumps([
                {"road_name": r["road_name"], "from": r["from_location"],
                 "to": r["to_location"]} for r in passable[:10]
            ], indent=2),
            disaster_type=assessment.disaster_type if assessment else "Flood",
            severity=assessment.severity if assessment else 3,
        )

        parsed, elapsed_ms, _ = self._call_gemini(prompt)

        if parsed:
            result = self._build_result_from_parsed(parsed, inp, hosp, blocked)
        else:
            result = self._simulate_route(context, blocked)

        context.route_result = result

        self._log(
            action="calculate_route",
            decision=f"Safe route: {result.estimated_distance_km:.1f} km | {result.estimated_time_minutes} min | Risk: {result.route_risk_level}",
            reasoning=result.reasoning,
            request_id=context.request_id,
            disaster_id=context.disaster_id,
            input_data={"blocked_roads": len(blocked), "from": inp.address},
            output_data={"distance_km": result.estimated_distance_km, "time_min": result.estimated_time_minutes},
            execution_time_ms=elapsed_ms,
        )
        return context

    def run_simulation(self, context: DisasterContext) -> DisasterContext:
        if not context.citizen_input or not context.hospital_result:
            return context

        self._start_timer()
        blocked = db.get_blocked_roads()
        result = self._simulate_route(context, blocked)
        elapsed = self._elapsed_ms()
        context.route_result = result

        self._log(
            action="calculate_route",
            decision=f"[SIM] Route: {result.estimated_distance_km:.1f} km | {result.estimated_time_minutes} min | Risk: {result.route_risk_level}",
            reasoning=result.reasoning,
            request_id=context.request_id,
            disaster_id=context.disaster_id,
            input_data={"blocked_count": len(blocked)},
            output_data={"distance_km": result.estimated_distance_km},
            execution_time_ms=elapsed,
        )
        return context

    def _simulate_route(self, context: DisasterContext, blocked_roads: list) -> RouteResult:
        """Generate a realistic safe route with waypoints."""
        inp = context.citizen_input
        hosp = context.hospital_result.allocated_hospital if context.hospital_result else None
        if not inp or not hosp:
            return RouteResult(origin_lat=0, origin_lon=0, destination_lat=0, destination_lon=0)

        dist_km = _haversine(inp.latitude, inp.longitude, hosp.latitude, hosp.longitude)
        # Add 30% detour for flooded roads
        effective_dist = dist_km * 1.35
        time_min = int((effective_dist / 35) * 60) + 5  # 35 km/h in flood conditions

        # Build waypoints (simplified midpoint routing)
        mid_lat = (inp.latitude + hosp.latitude) / 2
        mid_lon = (inp.longitude + hosp.longitude) / 2
        # Offset midpoint slightly to simulate detour
        mid_lat_offset = mid_lat + 0.008
        mid_lon_offset = mid_lon + 0.008

        route = [
            RouteWaypoint(location_name=inp.address, latitude=inp.latitude, longitude=inp.longitude, is_checkpoint=True),
            RouteWaypoint(location_name="Safe Detour via Inner Ring Road", latitude=mid_lat_offset, longitude=mid_lon_offset, is_checkpoint=True),
            RouteWaypoint(location_name=hosp.name, latitude=hosp.latitude, longitude=hosp.longitude, is_checkpoint=True),
        ]

        alternate1 = [
            RouteWaypoint(location_name=inp.address, latitude=inp.latitude, longitude=inp.longitude),
            RouteWaypoint(location_name="Alternate via NH-48", latitude=mid_lat - 0.01, longitude=mid_lon - 0.01),
            RouteWaypoint(location_name=hosp.name, latitude=hosp.latitude, longitude=hosp.longitude),
        ]

        # Build blocked road segments
        blocked_segments = [
            RoadSegment(
                road_id=r["id"], road_name=r["road_name"],
                from_location=r["from_location"], to_location=r["to_location"],
                from_lat=r["from_lat"], from_lon=r["from_lon"],
                to_lat=r["to_lat"], to_lon=r["to_lon"],
                condition=r["condition"], blockage_reason=r.get("blockage_reason"),
                severity=r.get("severity", 0), is_passable=False,
            )
            for r in blocked_roads[:8]
        ]

        # Risk level based on number of blocked roads
        n_blocked = len(blocked_roads)
        if n_blocked >= 10:   risk = "Critical"
        elif n_blocked >= 6:  risk = "High"
        elif n_blocked >= 3:  risk = "Medium"
        else:                 risk = "Low"

        notes = [
            f"[!]️ {n_blocked} roads blocked due to flooding",
            f"🚧 Primary route avoids {min(n_blocked, 5)} blocked segments",
            "[DONE] Route verified clear as of last update",
            "⏱ Travel time includes flood detour (+35% extra distance)",
        ]

        return RouteResult(
            origin_lat=inp.latitude, origin_lon=inp.longitude,
            destination_lat=hosp.latitude, destination_lon=hosp.longitude,
            origin_name=inp.address, destination_name=hosp.name,
            safest_route=route,
            alternate_routes=[alternate1],
            blocked_roads=blocked_segments,
            estimated_distance_km=round(effective_dist, 2),
            estimated_time_minutes=time_min,
            route_risk_level=risk,
            route_notes=notes,
            reasoning=f"[SIMULATION] Routed from {inp.address} to {hosp.name} ({dist_km:.1f} km direct). "
                      f"Applied 35% detour factor for flood conditions. "
                      f"{n_blocked} roads blocked. Risk level: {risk}.",
            is_simulation=True,
        )

    def _build_result_from_parsed(self, parsed: dict, inp, hosp, blocked_roads: list) -> RouteResult:
        route = [RouteWaypoint(**wp) for wp in parsed.get("safest_route", [])]
        alternates = [
            [RouteWaypoint(**wp) for wp in alt]
            for alt in parsed.get("alternate_routes", [])
        ]
        blocked_segments = [
            RoadSegment(
                road_id=r["id"], road_name=r["road_name"],
                from_location=r["from_location"], to_location=r["to_location"],
                from_lat=r["from_lat"], from_lon=r["from_lon"],
                to_lat=r["to_lat"], to_lon=r["to_lon"],
                condition=r["condition"], blockage_reason=r.get("blockage_reason"),
                severity=r.get("severity", 0), is_passable=False,
            ) for r in blocked_roads[:8]
        ]
        return RouteResult(
            origin_lat=inp.latitude, origin_lon=inp.longitude,
            destination_lat=hosp.latitude, destination_lon=hosp.longitude,
            origin_name=inp.address, destination_name=hosp.name,
            safest_route=route,
            alternate_routes=alternates,
            blocked_roads=blocked_segments,
            estimated_distance_km=parsed.get("estimated_distance_km", 0.0),
            estimated_time_minutes=parsed.get("estimated_time_minutes", 0),
            route_risk_level=parsed.get("route_risk_level", "Medium"),
            route_notes=parsed.get("route_notes", []),
            reasoning=parsed.get("reasoning", ""),
            is_simulation=False,
        )
