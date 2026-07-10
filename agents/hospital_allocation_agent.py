"""
ResQNet AI - Hospital Allocation Agent
Single Responsibility: Find and allocate the best available hospital.
Handles reassignment when a hospital reaches full capacity.
"""

import json
import math
from typing import List, Optional

from agents.base_agent import BaseAgent
from models.disaster_models import DisasterContext
from models.hospital_models import HospitalAllocationResult, HospitalInfo
from database import db_manager as db


HOSPITAL_PROMPT = """You are the Hospital Allocation Agent for ResQNet AI.
Given a disaster assessment and hospital availability data, allocate the most suitable hospital.

DISASTER ASSESSMENT:
Type: {disaster_type}
Severity: {severity}/5 ({severity_label})
Location: {location} (Lat: {lat}, Lon: {lon})
Affected People: {num_people}

AVAILABLE HOSPITALS (sorted by distance):
{hospitals_json}

Rules:
- Prioritize closest hospital with sufficient beds
- For severity >= 4 (Critical/Extreme), require ICU availability
- If closest hospital is at > 90% capacity, choose next best
- Reserve ICU beds for severity >= 3 cases with 1+ people requiring intensive care

Respond ONLY with valid JSON:
{{
  "allocated_hospital_id": <int>,
  "beds_to_reserve": <int>,
  "icu_to_reserve": <int>,
  "priority_score": <float 0-10>,
  "requires_icu": <bool>,
  "estimated_wait_minutes": <int>,
  "allocation_reason": "<reason>",
  "fallback_hospital_ids": [<int>, ...],
  "reasoning": "<detailed reasoning>"
}}
"""


def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance in km between two coordinates."""
    R = 6371
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))


def _build_hospital_info(h: dict, distance_km: float) -> HospitalInfo:
    specs = h.get("specializations", "[]")
    if isinstance(specs, str):
        try:
            specs = json.loads(specs)
        except Exception:
            specs = []
    return HospitalInfo(
        hospital_id=h["id"],
        name=h["name"],
        address=h["address"],
        latitude=h["latitude"],
        longitude=h["longitude"],
        available_beds=h["available_beds"],
        available_icu=h["available_icu"],
        available_doctors=h.get("available_doctors", 0),
        status=h["status"],
        specializations=specs,
        distance_km=round(distance_km, 2),
        contact_phone=h.get("contact_phone", ""),
    )


class HospitalAllocationAgent(BaseAgent):
    """
    Agent 2: Hospital Allocation
    Finds and reserves hospital capacity for incoming casualties.
    """

    def __init__(self):
        super().__init__("hospital_allocation")

    def run_live(self, context: DisasterContext) -> DisasterContext:
        assessment = context.assessment
        inp = context.citizen_input
        if not assessment or not inp:
            return context

        hospitals = db.get_available_hospitals()
        if not hospitals:
            return context

        # Enrich with distances
        hospitals_with_dist = [
            (h, _haversine(inp.latitude, inp.longitude, h["latitude"], h["longitude"]))
            for h in hospitals
        ]
        hospitals_with_dist.sort(key=lambda x: x[1])

        hospitals_payload = [
            {
                "id": h["id"],
                "name": h["name"],
                "distance_km": round(d, 2),
                "available_beds": h["available_beds"],
                "available_icu": h["available_icu"],
                "status": h["status"],
                "specializations": json.loads(h.get("specializations", "[]")) if isinstance(h.get("specializations"), str) else h.get("specializations", []),
            }
            for h, d in hospitals_with_dist[:8]
        ]

        prompt = HOSPITAL_PROMPT.format(
            disaster_type=assessment.disaster_type,
            severity=assessment.severity,
            severity_label=assessment.severity_label,
            location=inp.address,
            lat=inp.latitude,
            lon=inp.longitude,
            num_people=inp.num_people,
            hospitals_json=json.dumps(hospitals_payload, indent=2),
        )

        parsed, elapsed_ms, _ = self._call_gemini(prompt)

        if parsed:
            result = self._build_result_from_parsed(parsed, hospitals_with_dist)
        else:
            result = self._simulate_allocation(context, hospitals_with_dist)

        context.hospital_result = result
        self._persist_allocation(context, result)

        self._log(
            action="allocate_hospital",
            decision=f"Allocated: {result.allocated_hospital.name if result.allocated_hospital else 'None'} | Beds: {result.beds_reserved}",
            reasoning=result.reasoning,
            request_id=context.request_id,
            disaster_id=context.disaster_id,
            input_data={"severity": assessment.severity, "num_people": inp.num_people},
            output_data={"hospital_id": result.allocated_hospital.hospital_id if result.allocated_hospital else None,
                         "beds": result.beds_reserved},
            execution_time_ms=elapsed_ms,
        )
        return context

    def run_simulation(self, context: DisasterContext) -> DisasterContext:
        assessment = context.assessment
        inp = context.citizen_input
        if not assessment or not inp:
            return context

        self._start_timer()
        hospitals = db.get_available_hospitals()
        hospitals_with_dist = sorted(
            [(h, _haversine(inp.latitude, inp.longitude, h["latitude"], h["longitude"]))
             for h in hospitals],
            key=lambda x: x[1]
        )

        result = self._simulate_allocation(context, hospitals_with_dist)
        elapsed = self._elapsed_ms()
        context.hospital_result = result
        self._persist_allocation(context, result)

        self._log(
            action="allocate_hospital",
            decision=f"[SIM] Allocated: {result.allocated_hospital.name if result.allocated_hospital else 'None'} | Beds: {result.beds_reserved}",
            reasoning=result.reasoning,
            request_id=context.request_id,
            disaster_id=context.disaster_id,
            input_data={"severity": assessment.severity if assessment else 0},
            output_data={"beds": result.beds_reserved},
            execution_time_ms=elapsed,
        )
        return context

    def _simulate_allocation(self, context: DisasterContext, hospitals_with_dist: list) -> HospitalAllocationResult:
        """Rule-based hospital selection."""
        assessment = context.assessment
        inp = context.citizen_input
        num_people = inp.num_people if inp else 1
        severity = assessment.severity if assessment else 2
        requires_icu = severity >= 3

        beds_needed = max(1, num_people)
        icu_needed = max(1, num_people // 4) if requires_icu else 0

        allocated = None
        fallbacks = []

        for h, dist in hospitals_with_dist:
            # Check capacity
            capacity_pct = (h["total_beds"] - h["available_beds"]) / max(h["total_beds"], 1)
            if h["available_beds"] >= beds_needed and capacity_pct < 0.95:
                if requires_icu and h["available_icu"] < icu_needed:
                    fallbacks.append(_build_hospital_info(h, dist))
                    continue
                if allocated is None:
                    allocated = _build_hospital_info(h, dist)
                else:
                    fallbacks.append(_build_hospital_info(h, dist))
            elif h["available_beds"] > 0:
                fallbacks.append(_build_hospital_info(h, dist))

        # If no perfect match, take best available
        if allocated is None and hospitals_with_dist:
            h, dist = hospitals_with_dist[0]
            allocated = _build_hospital_info(h, dist)

        # ETA based on distance
        eta = int((allocated.distance_km / 40) * 60) + 5 if allocated else 20  # 40 km/h ambulance speed

        return HospitalAllocationResult(
            allocated_hospital=allocated,
            beds_reserved=min(beds_needed, allocated.available_beds if allocated else 0),
            icu_reserved=icu_needed,
            priority_score=float(severity) * 2.0,
            allocation_reason=f"Nearest hospital with {beds_needed} bed(s) available for severity {severity} case.",
            fallback_hospitals=fallbacks[:3],
            requires_icu=requires_icu,
            estimated_wait_minutes=eta,
            reassignment_triggered=False,
            reasoning=f"[SIMULATION] Selected {allocated.name if allocated else 'No hospital'} "
                      f"({allocated.distance_km:.1f} km away) - {allocated.available_beds if allocated else 0} beds available.",
            is_simulation=True,
        )

    def _build_result_from_parsed(self, parsed: dict, hospitals_with_dist: list) -> HospitalAllocationResult:
        """Convert Gemini JSON output to HospitalAllocationResult."""
        h_id = parsed.get("allocated_hospital_id")
        allocated = None
        fallbacks = []

        for h, dist in hospitals_with_dist:
            if h["id"] == h_id:
                allocated = _build_hospital_info(h, dist)
            elif h["id"] in parsed.get("fallback_hospital_ids", []):
                fallbacks.append(_build_hospital_info(h, dist))

        if allocated is None and hospitals_with_dist:
            h, dist = hospitals_with_dist[0]
            allocated = _build_hospital_info(h, dist)

        return HospitalAllocationResult(
            allocated_hospital=allocated,
            beds_reserved=parsed.get("beds_to_reserve", 1),
            icu_reserved=parsed.get("icu_to_reserve", 0),
            priority_score=parsed.get("priority_score", 5.0),
            allocation_reason=parsed.get("allocation_reason", ""),
            fallback_hospitals=fallbacks[:3],
            requires_icu=parsed.get("requires_icu", False),
            estimated_wait_minutes=parsed.get("estimated_wait_minutes", 15),
            reasoning=parsed.get("reasoning", ""),
            is_simulation=False,
        )

    def _persist_allocation(self, context: DisasterContext, result: HospitalAllocationResult):
        """Update DB: reserve beds, link hospital to request, create patient allocation."""
        if not result.allocated_hospital:
            return
        hosp_id = result.allocated_hospital.hospital_id

        # Reserve beds in hospital table
        db.update_hospital_beds(
            hosp_id,
            beds_delta=-result.beds_reserved,
            icu_delta=-result.icu_reserved,
        )

        # Update request with hospital assignment
        if context.request_id:
            db.update_request_status(
                context.request_id,
                "Processing",
                assigned_hospital_id=hosp_id,
            )
            # Create patient allocation record
            db.create_patient_allocation(
                request_id=context.request_id,
                hospital_id=hosp_id,
                beds=result.beds_reserved,
                icu=result.icu_reserved,
                priority=6 - (context.assessment.severity if context.assessment else 3),
            )

        # Auto-reassign if hospital is now full
        hosp = db.get_hospital_by_id(hosp_id)
        if hosp and hosp["available_beds"] == 0:
            db.update_hospital_status(hosp_id, "At Capacity")
            result.reassignment_triggered = True
