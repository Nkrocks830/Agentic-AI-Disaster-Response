"""
ResQNet AI - Emergency Resource Agent
Single Responsibility: Allocate ambulances and other rescue resources based on severity.
"""

import json
import math
from typing import List, Optional

from agents.base_agent import BaseAgent
from models.disaster_models import DisasterContext
from models.resource_models import ResourceAllocationResult, AmbulanceInfo, ResourceItem
from database import db_manager as db


RESOURCE_PROMPT = """You are the Emergency Resource Agent for ResQNet AI.
Allocate the appropriate emergency resources based on the disaster assessment.

DISASTER ASSESSMENT:
Type: {disaster_type}
Severity: {severity}/5 ({severity_label})
Location: {location}
Affected People: {num_people}

AVAILABLE AMBULANCES:
{ambulances_json}

AVAILABLE RESCUE RESOURCES:
{resources_json}

Rules:
- Severity 1-2: 1 ambulance only
- Severity 3: 1 ambulance + 1 rescue team
- Severity 4: 2 ambulances + rescue team + boat (if flood)
- Severity 5: All available resources nearest to scene

Respond ONLY with valid JSON:
{{
  "assigned_ambulance_id": <int>,
  "assigned_resource_ids": [<int>, ...],
  "priority_level": "Normal|High|Critical",
  "ambulance_eta_minutes": <int>,
  "allocation_reason": "<reason>",
  "reasoning": "<detailed reasoning>"
}}
"""


def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))


class ResourceAgent(BaseAgent):
    """
    Agent 4: Emergency Resource Allocation
    Dispatches ambulances, boats, fire trucks, and rescue teams.
    """

    def __init__(self):
        super().__init__("resource")

    def run_live(self, context: DisasterContext) -> DisasterContext:
        assessment = context.assessment
        inp = context.citizen_input
        if not assessment or not inp:
            return context

        ambulances = db.get_available_ambulances()
        resources = db.get_available_resources()
        hosp = context.hospital_result.allocated_hospital if context.hospital_result else None

        # Enrich with distances
        ambs_payload = [
            {
                "id": a["id"], "vehicle_number": a["vehicle_number"],
                "driver_name": a["driver_name"], "driver_phone": a["driver_phone"],
                "status": a["status"], "fuel_level": a.get("fuel_level", 100),
                "distance_km": round(_haversine(inp.latitude, inp.longitude, a["latitude"], a["longitude"]), 2),
            }
            for a in ambulances
        ]
        ambs_payload.sort(key=lambda x: x["distance_km"])

        res_payload = [
            {
                "id": r["id"], "name": r["name"], "type": r["resource_type"],
                "location": r["location_name"], "capacity": r["capacity"],
                "distance_km": round(_haversine(inp.latitude, inp.longitude, r["latitude"], r["longitude"]), 2),
            }
            for r in resources
        ]

        prompt = RESOURCE_PROMPT.format(
            disaster_type=assessment.disaster_type,
            severity=assessment.severity,
            severity_label=assessment.severity_label,
            location=inp.address,
            num_people=inp.num_people,
            ambulances_json=json.dumps(ambs_payload[:6], indent=2),
            resources_json=json.dumps(res_payload[:8], indent=2),
        )

        parsed, elapsed_ms, _ = self._call_gemini(prompt)

        if parsed:
            result = self._build_result_from_parsed(parsed, ambulances, resources, inp)
        else:
            result = self._simulate_allocation(context, ambulances, resources)

        context.resource_result = result
        self._persist_allocation(context, result)

        self._log(
            action="allocate_resources",
            decision=f"Ambulance: {result.assigned_ambulance.vehicle_number if result.assigned_ambulance else 'None'} | Resources: {result.total_resources_deployed} | ETA: {result.ambulance_eta_minutes} min",
            reasoning=result.reasoning,
            request_id=context.request_id,
            disaster_id=context.disaster_id,
            input_data={"severity": assessment.severity, "num_people": inp.num_people},
            output_data={"ambulance_id": result.assigned_ambulance.ambulance_id if result.assigned_ambulance else None},
            execution_time_ms=elapsed_ms,
        )
        return context

    def run_simulation(self, context: DisasterContext) -> DisasterContext:
        if not context.citizen_input:
            return context

        self._start_timer()
        ambulances = db.get_available_ambulances()
        resources = db.get_available_resources()
        result = self._simulate_allocation(context, ambulances, resources)
        elapsed = self._elapsed_ms()
        context.resource_result = result
        self._persist_allocation(context, result)

        self._log(
            action="allocate_resources",
            decision=f"[SIM] Amb: {result.assigned_ambulance.vehicle_number if result.assigned_ambulance else 'None'} | {result.total_resources_deployed} resources",
            reasoning=result.reasoning,
            request_id=context.request_id,
            disaster_id=context.disaster_id,
            input_data={},
            output_data={},
            execution_time_ms=elapsed,
        )
        return context

    def _simulate_allocation(self, context: DisasterContext, ambulances: list, resources: list) -> ResourceAllocationResult:
        inp = context.citizen_input
        assessment = context.assessment
        severity = assessment.severity if assessment else 2
        disaster_type = assessment.disaster_type if assessment else "Flood"

        # Sort ambulances by distance
        sorted_ambs = sorted(
            ambulances,
            key=lambda a: _haversine(inp.latitude, inp.longitude, a["latitude"], a["longitude"]) if inp else 0
        )

        assigned_amb = None
        if sorted_ambs:
            a = sorted_ambs[0]
            dist = _haversine(inp.latitude, inp.longitude, a["latitude"], a["longitude"])
            eta = int((dist / 35) * 60) + 3
            assigned_amb = AmbulanceInfo(
                ambulance_id=a["id"],
                vehicle_number=a["vehicle_number"],
                driver_name=a["driver_name"],
                driver_phone=a["driver_phone"],
                latitude=a["latitude"],
                longitude=a["longitude"],
                status=a["status"],
                fuel_level=a.get("fuel_level", 100),
                distance_km=round(dist, 2),
                eta_minutes=eta,
            )

        # Select additional resources based on severity
        assigned_resources: List[ResourceItem] = []
        if severity >= 3:
            rescue_teams = [r for r in resources if r["resource_type"] == "Rescue Team"]
            if rescue_teams:
                r = rescue_teams[0]
                dist = _haversine(inp.latitude, inp.longitude, r["latitude"], r["longitude"]) if inp else 0
                assigned_resources.append(ResourceItem(
                    resource_id=r["id"], name=r["name"], resource_type=r["resource_type"],
                    location_name=r["location_name"], latitude=r["latitude"], longitude=r["longitude"],
                    status=r["status"], capacity=r["capacity"],
                    operator_name=r.get("operator_name", ""),
                    operator_phone=r.get("operator_phone", ""),
                    distance_km=round(dist, 2), eta_minutes=int(dist / 30 * 60) + 5,
                ))

        if severity >= 4 and disaster_type == "Flood":
            boats = [r for r in resources if r["resource_type"] == "Rescue Boat"]
            if boats:
                r = boats[0]
                dist = _haversine(inp.latitude, inp.longitude, r["latitude"], r["longitude"]) if inp else 0
                assigned_resources.append(ResourceItem(
                    resource_id=r["id"], name=r["name"], resource_type=r["resource_type"],
                    location_name=r["location_name"], latitude=r["latitude"], longitude=r["longitude"],
                    status=r["status"], capacity=r["capacity"],
                    operator_name=r.get("operator_name", ""),
                    operator_phone=r.get("operator_phone", ""),
                    distance_km=round(dist, 2), eta_minutes=int(dist / 20 * 60) + 10,
                ))

        if severity == 5:
            fire_trucks = [r for r in resources if r["resource_type"] == "Fire Truck"]
            if fire_trucks:
                r = fire_trucks[0]
                dist = _haversine(inp.latitude, inp.longitude, r["latitude"], r["longitude"]) if inp else 0
                assigned_resources.append(ResourceItem(
                    resource_id=r["id"], name=r["name"], resource_type=r["resource_type"],
                    location_name=r["location_name"], latitude=r["latitude"], longitude=r["longitude"],
                    status=r["status"], capacity=r["capacity"],
                    operator_name=r.get("operator_name", ""),
                    operator_phone=r.get("operator_phone", ""),
                    distance_km=round(dist, 2), eta_minutes=int(dist / 40 * 60) + 5,
                ))

        priority = "Normal" if severity <= 2 else "High" if severity <= 3 else "Critical"

        return ResourceAllocationResult(
            assigned_ambulance=assigned_amb,
            assigned_resources=assigned_resources,
            ambulance_eta_minutes=assigned_amb.eta_minutes if assigned_amb else 0,
            priority_level=priority,
            allocation_reason=f"Severity {severity} - deployed {1 + len(assigned_resources)} units",
            total_resources_deployed=1 + len(assigned_resources),
            reasoning=f"[SIMULATION] Assigned nearest ambulance ({assigned_amb.vehicle_number if assigned_amb else 'None'}) "
                      f"and {len(assigned_resources)} additional resource(s) for severity {severity} {disaster_type}.",
            is_simulation=True,
        )

    def _build_result_from_parsed(self, parsed: dict, ambulances: list, resources: list, inp) -> ResourceAllocationResult:
        amb_id = parsed.get("assigned_ambulance_id")
        assigned_amb = None
        for a in ambulances:
            if a["id"] == amb_id:
                dist = _haversine(inp.latitude, inp.longitude, a["latitude"], a["longitude"])
                eta = int(dist / 35 * 60) + 3
                assigned_amb = AmbulanceInfo(
                    ambulance_id=a["id"], vehicle_number=a["vehicle_number"],
                    driver_name=a["driver_name"], driver_phone=a["driver_phone"],
                    latitude=a["latitude"], longitude=a["longitude"],
                    status=a["status"], fuel_level=a.get("fuel_level", 100),
                    distance_km=round(dist, 2), eta_minutes=eta,
                )
                break

        assigned_resources = []
        for r in resources:
            if r["id"] in parsed.get("assigned_resource_ids", []):
                dist = _haversine(inp.latitude, inp.longitude, r["latitude"], r["longitude"])
                assigned_resources.append(ResourceItem(
                    resource_id=r["id"], name=r["name"], resource_type=r["resource_type"],
                    location_name=r["location_name"], latitude=r["latitude"], longitude=r["longitude"],
                    status=r["status"], capacity=r["capacity"],
                    operator_name=r.get("operator_name", ""),
                    operator_phone=r.get("operator_phone", ""),
                    distance_km=round(dist, 2), eta_minutes=int(dist / 30 * 60),
                ))

        return ResourceAllocationResult(
            assigned_ambulance=assigned_amb,
            assigned_resources=assigned_resources,
            ambulance_eta_minutes=parsed.get("ambulance_eta_minutes", 15),
            priority_level=parsed.get("priority_level", "Normal"),
            allocation_reason=parsed.get("allocation_reason", ""),
            total_resources_deployed=1 + len(assigned_resources),
            reasoning=parsed.get("reasoning", ""),
            is_simulation=False,
        )

    def _persist_allocation(self, context: DisasterContext, result: ResourceAllocationResult):
        """
        Record the tentative ambulance assignment on the request WITHOUT dispatching.
        Actual dispatch happens only when the hospital clicks Accept.
        This keeps the ambulance in 'Available' status until confirmed.
        """
        if result.assigned_ambulance and context.request_id:
            # Store the tentative ambulance on the request but keep status = Processing
            # Do NOT call dispatch_ambulance() here — that changes ambulance status to Dispatched
            db.update_request_status(
                context.request_id, "Processing",
                assigned_ambulance_id=result.assigned_ambulance.ambulance_id,
                eta_minutes=result.ambulance_eta_minutes,
            )

        # Deploy additional rescue resources (boats, teams, fire trucks) immediately
        for res in result.assigned_resources:
            if context.disaster_id:
                db.deploy_resource(res.resource_id, context.disaster_id)

