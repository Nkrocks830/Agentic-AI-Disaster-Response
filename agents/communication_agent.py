"""
ResQNet AI - Communication Agent
Single Responsibility: Generate and send notifications to all stakeholders.
"""

import json
from agents.base_agent import BaseAgent
from models.disaster_models import DisasterContext
from models.communication_models import CommunicationResult, NotificationItem
from database import db_manager as db


COMM_PROMPT = """You are the Communication Agent for ResQNet AI emergency response.
Generate appropriate notifications for all stakeholders.

SITUATION:
- Disaster: {disaster_type}, Severity {severity}/5 ({severity_label})
- Location: {location}
- Citizen: {citizen_name} ({citizen_phone}) - {num_people} people
- Assigned Hospital: {hospital_name} ({hospital_phone})
- Ambulance: {ambulance_num} - Driver: {driver_name} ({driver_phone})
- ETA: {eta} minutes
- Route Risk: {route_risk}
- Resources Deployed: {resources}

Generate notifications for each stakeholder. Keep messages concise, professional, and actionable.

Respond ONLY with valid JSON:
{{
  "public_safety_alert": "<broadcast message for general public>",
  "hospital_notice": "<message to hospital staff>",
  "ambulance_dispatch_msg": "<message to ambulance driver>",
  "authority_briefing": "<message to disaster management authority>",
  "citizen_notification": "<message to affected citizen>",
  "reasoning": "<brief explanation>"
}}
"""


class CommunicationAgent(BaseAgent):
    """
    Agent 5: Communication
    Generates and dispatches notifications to all parties.
    """

    def __init__(self):
        super().__init__("communication")

    def run_live(self, context: DisasterContext) -> DisasterContext:
        assessment = context.assessment
        inp = context.citizen_input
        if not assessment or not inp:
            return context

        hosp = context.hospital_result.allocated_hospital if context.hospital_result else None
        amb = context.resource_result.assigned_ambulance if context.resource_result else None
        route = context.route_result

        prompt = COMM_PROMPT.format(
            disaster_type=assessment.disaster_type,
            severity=assessment.severity,
            severity_label=assessment.severity_label,
            location=inp.address,
            citizen_name=inp.citizen_name,
            citizen_phone=inp.citizen_phone,
            num_people=inp.num_people,
            hospital_name=hosp.name if hosp else "TBD",
            hospital_phone=hosp.contact_phone if hosp else "N/A",
            ambulance_num=amb.vehicle_number if amb else "TBD",
            driver_name=amb.driver_name if amb else "TBD",
            driver_phone=amb.driver_phone if amb else "TBD",
            eta=amb.eta_minutes if amb else "Unknown",
            route_risk=route.route_risk_level if route else "Unknown",
            resources=len(context.resource_result.assigned_resources) if context.resource_result else 0,
        )

        parsed, elapsed_ms, _ = self._call_gemini(prompt)

        if parsed:
            result = self._build_result_from_parsed(parsed, context)
        else:
            result = self._simulate_notifications(context)

        context.communication_result = result
        self._persist_notifications(context, result)

        self._log(
            action="send_notifications",
            decision=f"Sent {result.total_notified} notifications | Alert issued: {bool(result.public_safety_alert)}",
            reasoning=result.reasoning,
            request_id=context.request_id,
            disaster_id=context.disaster_id,
            input_data={"severity": assessment.severity, "citizen": inp.citizen_name},
            output_data={"total_notified": result.total_notified},
            execution_time_ms=elapsed_ms,
        )
        return context

    def run_simulation(self, context: DisasterContext) -> DisasterContext:
        self._start_timer()
        result = self._simulate_notifications(context)
        elapsed = self._elapsed_ms()
        context.communication_result = result
        self._persist_notifications(context, result)

        self._log(
            action="send_notifications",
            decision=f"[SIM] {result.total_notified} notifications dispatched",
            reasoning=result.reasoning,
            request_id=context.request_id,
            disaster_id=context.disaster_id,
            input_data={},
            output_data={"total_notified": result.total_notified},
            execution_time_ms=elapsed,
        )
        return context

    def _simulate_notifications(self, context: DisasterContext) -> CommunicationResult:
        assessment = context.assessment
        inp = context.citizen_input
        hosp = context.hospital_result.allocated_hospital if context.hospital_result else None
        amb = context.resource_result.assigned_ambulance if context.resource_result else None
        route = context.route_result
        sev = assessment.severity if assessment else 2
        d_type = assessment.disaster_type if assessment else "Flood"

        hospital_name = hosp.name if hosp else "Nearest Hospital"
        amb_num = amb.vehicle_number if amb else "N/A"
        driver = amb.driver_name if amb else "N/A"
        driver_phone = amb.driver_phone if amb else "N/A"
        eta = amb.eta_minutes if amb else 15
        citizen_name = inp.citizen_name if inp else "Citizen"
        citizen_phone = inp.citizen_phone if inp else "N/A"
        location = inp.address if inp else "Unknown"
        num_people = inp.num_people if inp else 1

        public_alert = (
            f"🚨 RESQNET EMERGENCY ALERT - Chennai {d_type.upper()}\n"
            f"Active emergency at {location}. Ambulance {amb_num} dispatched.\n"
            f"Avoid area. Nearest shelter: Jawaharlal Nehru Indoor Stadium.\n"
            f"Emergency: 108 | Disaster Hotline: 1800-123-0011"
        )

        hospital_notice = (
            f"📋 INCOMING PATIENT ALERT - ResQNet AI\n"
            f"Prepare for {num_people} patient(s) from {location}.\n"
            f"Disaster Type: {d_type} | Severity: {sev}/5\n"
            f"Ambulance {amb_num} en route - ETA: {eta} minutes.\n"
            f"Reserve beds and {'ICU' if sev >= 3 else 'general ward'} as allocated."
        )

        ambulance_msg = (
            f"🚑 DISPATCH ORDER - ResQNet AI\n"
            f"Driver {driver}: Proceed to {location} immediately.\n"
            f"Patient: {citizen_name} ({citizen_phone}) - {num_people} person(s)\n"
            f"Destination: {hospital_name}\n"
            f"Route Risk: {route.route_risk_level if route else 'High'} - Use safe route provided.\n"
            f"Priority: {'CRITICAL' if sev >= 4 else 'HIGH' if sev >= 3 else 'NORMAL'}"
        )

        authority_msg = (
            f"📊 INCIDENT BRIEFING - ResQNet AI Orchestrator\n"
            f"Incident Type: {d_type} | Severity: {assessment.severity_label if assessment else 'High'}\n"
            f"Location: {location} | Affected: {num_people} persons\n"
            f"Response: Ambulance {amb_num} + {len(context.resource_result.assigned_resources) if context.resource_result else 0} additional resource(s)\n"
            f"Hospital: {hospital_name}\n"
            f"Agent pipeline execution: COMPLETE"
        )

        citizen_msg = (
            f"[DONE] HELP IS ON THE WAY - ResQNet AI\n"
            f"Dear {citizen_name}, your emergency request has been received.\n"
            f"Ambulance {amb_num} is heading to you. ETA: {eta} minutes.\n"
            f"Driver: {driver} - {driver_phone}\n"
            f"You will be taken to: {hospital_name}\n"
            f"Stay safe and remain visible."
        )

        notifications = [
            NotificationItem(recipient_type="citizen",    recipient_name=citizen_name, channel="sms",       message=citizen_msg),
            NotificationItem(recipient_type="hospital",   recipient_name=hospital_name,channel="app",       message=hospital_notice, recipient_id=hosp.hospital_id if hosp else 0),
            NotificationItem(recipient_type="ambulance",  recipient_name=driver,        channel="app",       message=ambulance_msg, recipient_id=amb.ambulance_id if amb else 0),
            NotificationItem(recipient_type="authority",  recipient_name="Disaster Management Authority", channel="email", message=authority_msg),
            NotificationItem(recipient_type="public",     recipient_name="General Public", channel="broadcast", message=public_alert),
        ]

        return CommunicationResult(
            notifications=notifications,
            public_safety_alert=public_alert,
            hospital_notice=hospital_notice,
            ambulance_dispatch_msg=ambulance_msg,
            authority_briefing=authority_msg,
            total_notified=len(notifications),
            reasoning=f"[SIMULATION] Generated {len(notifications)} notifications for {d_type} severity {sev} event at {location}.",
            is_simulation=True,
        )

    def _build_result_from_parsed(self, parsed: dict, context: DisasterContext) -> CommunicationResult:
        inp = context.citizen_input
        hosp = context.hospital_result.allocated_hospital if context.hospital_result else None
        amb = context.resource_result.assigned_ambulance if context.resource_result else None

        notifications = [
            NotificationItem(recipient_type="citizen",   recipient_name=inp.citizen_name if inp else "", channel="sms",       message=parsed.get("citizen_notification", "")),
            NotificationItem(recipient_type="hospital",  recipient_name=hosp.name if hosp else "",      channel="app",       message=parsed.get("hospital_notice", ""), recipient_id=hosp.hospital_id if hosp else 0),
            NotificationItem(recipient_type="ambulance", recipient_name=amb.driver_name if amb else "",  channel="app",       message=parsed.get("ambulance_dispatch_msg", ""), recipient_id=amb.ambulance_id if amb else 0),
            NotificationItem(recipient_type="authority", recipient_name="Authority",                     channel="email",     message=parsed.get("authority_briefing", "")),
            NotificationItem(recipient_type="public",    recipient_name="General Public",                channel="broadcast", message=parsed.get("public_safety_alert", "")),
        ]
        return CommunicationResult(
            notifications=notifications,
            public_safety_alert=parsed.get("public_safety_alert", ""),
            hospital_notice=parsed.get("hospital_notice", ""),
            ambulance_dispatch_msg=parsed.get("ambulance_dispatch_msg", ""),
            authority_briefing=parsed.get("authority_briefing", ""),
            total_notified=len(notifications),
            reasoning=parsed.get("reasoning", ""),
            is_simulation=False,
        )

    def _persist_notifications(self, context: DisasterContext, result: CommunicationResult):
        for n in result.notifications:
            db.create_notification({
                "request_id": context.request_id,
                "recipient_type": n.recipient_type,
                "recipient_id": n.recipient_id,
                "recipient_name": n.recipient_name,
                "message": n.message,
                "channel": n.channel,
            })
