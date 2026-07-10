"""
ResQNet AI - Disaster Assessment Agent
Analyzes citizen reports to classify disaster type, severity, affected area.
"""

import json
from typing import Any

from agents.base_agent import BaseAgent
from models.disaster_models import DisasterContext, DisasterAssessmentResult
from config.settings import SEVERITY_LEVELS


ASSESSMENT_PROMPT = """You are the Disaster Assessment Agent for ResQNet AI, an emergency response system.
Analyze the following citizen emergency report and extract structured information.

REPORT:
Location: {address} (Lat: {lat}, Lon: {lon})
Citizen: {name}
Description: {description}
Number of people affected: {num_people}

Current active disaster context: {disaster_context}

Respond ONLY with a valid JSON object in this exact format:
{{
  "disaster_type": "Flood|Cyclone|Earthquake|Fire|Landslide|Tsunami|Other",
  "severity": <integer 1-5>,
  "severity_label": "Low|Moderate|High|Critical|Extreme",
  "affected_location": "<specific area name>",
  "affected_people": <integer>,
  "risk_factors": ["<factor1>", "<factor2>", ...],
  "immediate_actions": ["<action1>", "<action2>", ...],
  "confidence_score": <float 0-1>,
  "reasoning": "<brief explanation of your assessment>"
}}

Severity Scale: 1=Low (1-5 people, minor), 2=Moderate (6-20, moderate), 
3=High (21-100, serious), 4=Critical (101-1000, major), 5=Extreme (1000+, catastrophic)
"""


class DisasterAssessmentAgent(BaseAgent):
    """
    Agent 1: Disaster Assessment
    Single Responsibility: Analyze emergency reports → produce DisasterAssessmentResult
    """

    def __init__(self):
        super().__init__("disaster_assessment")

    def run_live(self, context: DisasterContext) -> DisasterContext:
        """Use Gemini to analyze the disaster report."""
        inp = context.citizen_input
        if not inp:
            return context

        disaster = None
        if context.disaster_id:
            from database import db_manager as db
            disaster = db.get_disaster_by_id(context.disaster_id)

        prompt = ASSESSMENT_PROMPT.format(
            address=inp.address,
            lat=inp.latitude,
            lon=inp.longitude,
            name=inp.citizen_name,
            description=inp.description,
            num_people=inp.num_people,
            disaster_context=json.dumps(disaster) if disaster else "None",
        )

        parsed, elapsed_ms, raw_text = self._call_gemini(prompt)

        if parsed:
            result = DisasterAssessmentResult(
                disaster_type=parsed.get("disaster_type", "Flood"),
                severity=parsed.get("severity", 3),
                severity_label=parsed.get("severity_label", "High"),
                affected_location=parsed.get("affected_location", inp.address),
                affected_people=parsed.get("affected_people", inp.num_people),
                risk_factors=parsed.get("risk_factors", []),
                immediate_actions=parsed.get("immediate_actions", []),
                confidence_score=parsed.get("confidence_score", 0.85),
                reasoning=parsed.get("reasoning", ""),
                is_simulation=False,
            )
        else:
            # Parsing failed - fall back to simulation
            result = self._simulate_assessment(inp, context.disaster_id)

        context.assessment = result

        self._log(
            action="assess_disaster",
            decision=f"Classified as {result.disaster_type} | Severity: {result.severity}/5 | People: {result.affected_people}",
            reasoning=result.reasoning,
            request_id=context.request_id,
            disaster_id=context.disaster_id,
            input_data={"address": inp.address, "description": inp.description[:200]},
            output_data=result.model_dump(),
            execution_time_ms=elapsed_ms,
        )
        return context

    def run_simulation(self, context: DisasterContext) -> DisasterContext:
        """Deterministic assessment based on report keywords."""
        inp = context.citizen_input
        if not inp:
            return context

        self._start_timer()
        result = self._simulate_assessment(inp, context.disaster_id)
        elapsed = self._elapsed_ms()
        context.assessment = result

        self._log(
            action="assess_disaster",
            decision=f"[SIM] {result.disaster_type} | Severity {result.severity}/5 | {result.affected_people} people",
            reasoning=result.reasoning,
            request_id=context.request_id,
            disaster_id=context.disaster_id,
            input_data={"address": inp.address, "num_people": inp.num_people},
            output_data=result.model_dump(),
            execution_time_ms=elapsed,
        )
        return context

    def _simulate_assessment(self, inp: Any, disaster_id: Any) -> DisasterAssessmentResult:
        """Rule-based simulation assessment."""
        desc_lower = inp.description.lower()

        # Detect disaster type
        if any(w in desc_lower for w in ["flood", "water", "submerged", "inundated", "drowning"]):
            d_type = "Flood"
        elif any(w in desc_lower for w in ["fire", "burn", "flame", "smoke"]):
            d_type = "Fire"
        elif any(w in desc_lower for w in ["earthquake", "tremor", "collapse", "debris"]):
            d_type = "Earthquake"
        elif any(w in desc_lower for w in ["cyclone", "storm", "wind", "hurricane"]):
            d_type = "Cyclone"
        else:
            d_type = "Flood"   # default for Chennai scenario

        # Severity from number of people
        n = inp.num_people
        if n <= 2:      sev = 1
        elif n <= 5:    sev = 2
        elif n <= 15:   sev = 3
        elif n <= 50:   sev = 4
        else:           sev = 5

        # Boost severity for medical keywords
        if any(w in desc_lower for w in ["heart", "pregnant", "baby", "infant", "elderly", "critical", "unconscious"]):
            sev = min(5, sev + 1)

        labels = {1:"Low",2:"Moderate",3:"High",4:"Critical",5:"Extreme"}

        risk_factors = []
        if "water" in desc_lower or "flood" in desc_lower:
            risk_factors += ["Drowning risk", "Water-borne disease", "Electrical hazard"]
        if "elderly" in desc_lower or "child" in desc_lower:
            risk_factors.append("Vulnerable population")
        if sev >= 4:
            risk_factors.append("Mass casualty potential")

        actions = [
            "Dispatch ambulance immediately",
            f"Allocate {max(1, inp.num_people // 5)} rescue personnel",
            "Set up medical triage on-site",
            "Notify nearest hospital to prepare",
        ]
        if d_type == "Flood":
            actions.insert(0, "Deploy rescue boat if available")

        return DisasterAssessmentResult(
            disaster_type=d_type,
            severity=sev,
            severity_label=labels[sev],
            affected_location=inp.address,
            affected_people=inp.num_people,
            risk_factors=risk_factors,
            immediate_actions=actions,
            confidence_score=0.78,
            reasoning=(
                f"[SIMULATION] Based on report keywords and {inp.num_people} affected persons, "
                f"classified as severity {sev} ({labels[sev]}) {d_type}. "
                f"Location: {inp.address}."
            ),
            is_simulation=True,
        )
