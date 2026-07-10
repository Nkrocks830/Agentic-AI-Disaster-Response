"""
ResQNet AI - Orchestrator Agent
Central coordinator that executes all agents in sequence,
maintains context, and logs every decision.
"""

import time
from datetime import datetime
from typing import Optional

from models.disaster_models import DisasterContext, DisasterInput
from models.agent_models import PipelineResult, AgentExecutionLog
from agents.disaster_assessment_agent import DisasterAssessmentAgent
from agents.hospital_allocation_agent import HospitalAllocationAgent
from agents.road_intelligence_agent import RoadIntelligenceAgent
from agents.resource_agent import ResourceAgent
from agents.communication_agent import CommunicationAgent
from agents.monitoring_agent import MonitoringAgent
from services.gemini_service import get_mode, get_mode_info, initialize_gemini
from database import db_manager as db


class Orchestrator:
    """
    The Orchestrator Agent coordinates the entire disaster response pipeline.

    Execution Order:
    1. Disaster Assessment Agent
    2. Hospital Allocation Agent
    3. Road Intelligence Agent
    4. Emergency Resource Agent
    5. Communication Agent
    6. Monitoring Agent

    All agents communicate only through the shared DisasterContext object.
    """

    def __init__(self):
        # Initialize Gemini and determine mode
        mode, reason = initialize_gemini()
        self.mode = mode
        self.mode_reason = reason

        # Instantiate all agents
        self.agents = {
            "disaster_assessment":  DisasterAssessmentAgent(),
            "hospital_allocation":  HospitalAllocationAgent(),
            "road_intelligence":    RoadIntelligenceAgent(),
            "resource":             ResourceAgent(),
            "communication":        CommunicationAgent(),
            "monitoring":           MonitoringAgent(),
        }

        print(f"[ORCHESTRATOR] Mode: {mode.upper()} - {reason}")

    def process_emergency(self, citizen_input: DisasterInput) -> PipelineResult:
        """
        Full pipeline execution for a new emergency request.
        Returns a PipelineResult with complete agent logs.
        """
        pipeline_start = datetime.now()
        start_ms = time.time()
        agent_logs: list[AgentExecutionLog] = []

        # ── Step 1: Create emergency request in DB ─────────────────────────────
        active_disasters = db.get_active_disasters()
        disaster_id = active_disasters[0]["id"] if active_disasters else None

        request_id = db.create_emergency_request({
            "citizen_name":  citizen_input.citizen_name,
            "citizen_phone": citizen_input.citizen_phone,
            "latitude":      citizen_input.latitude,
            "longitude":     citizen_input.longitude,
            "address":       citizen_input.address,
            "description":   citizen_input.description,
            "num_people":    citizen_input.num_people,
            "disaster_id":   disaster_id,
        })

        citizen_input.disaster_id = disaster_id

        # ── Build shared context ───────────────────────────────────────────────
        context = DisasterContext(
            request_id=request_id,
            disaster_id=disaster_id,
            citizen_input=citizen_input,
            mode=self.mode,
        )

        # ── Log orchestrator start ─────────────────────────────────────────────
        db.log_agent_execution(
            agent_name="Orchestrator Agent",
            action="pipeline_start",
            decision=f"Starting pipeline for request #{request_id} | Mode: {self.mode.upper()}",
            reasoning=f"Received emergency from {citizen_input.citizen_name} at {citizen_input.address}. "
                      f"Active disaster ID: {disaster_id}. Executing {len(self.agents)} agents in sequence.",
            request_id=request_id,
            disaster_id=disaster_id,
            input_data=citizen_input.model_dump(),
            mode=self.mode,
        )

        # ── Execute agents in order ────────────────────────────────────────────
        pipeline_order = [
            ("disaster_assessment",  "Analyzing disaster type and severity"),
            ("hospital_allocation",  "Finding and allocating nearest hospital"),
            ("road_intelligence",    "Calculating safest route"),
            ("resource",             "Dispatching ambulance and rescue resources"),
            ("communication",        "Sending notifications to all stakeholders"),
            ("monitoring",           "Monitoring system and detecting changes"),
        ]

        for agent_key, action_desc in pipeline_order:
            agent = self.agents[agent_key]
            agent_start = time.time()

            try:
                context = agent.run(context)
                agent_ms = int((time.time() - agent_start) * 1000)

                # Build log entry for pipeline result
                agent_logs.append(AgentExecutionLog(
                    request_id=request_id,
                    disaster_id=disaster_id,
                    agent_name=agent.agent_name,
                    action=action_desc,
                    decision=self._summarize_result(agent_key, context),
                    reasoning=self._get_reasoning(agent_key, context),
                    execution_time_ms=agent_ms,
                    status="success",
                    mode=self.mode,
                ))

            except Exception as e:
                agent_ms = int((time.time() - agent_start) * 1000)
                agent_logs.append(AgentExecutionLog(
                    request_id=request_id,
                    disaster_id=disaster_id,
                    agent_name=agent.agent_name,
                    action=action_desc,
                    decision=f"FAILED: {str(e)[:200]}",
                    reasoning="Agent encountered an unrecoverable error.",
                    execution_time_ms=agent_ms,
                    status="failed",
                    mode=self.mode,
                ))
                # Continue pipeline even if one agent fails
                continue

        # ── Pipeline complete ──────────────────────────────────────────────────
        total_ms = int((time.time() - start_ms) * 1000)
        context.total_execution_ms = total_ms

        # Update disaster affected count
        if disaster_id and context.assessment:
            disaster = db.get_disaster_by_id(disaster_id)
            if disaster:
                new_affected = disaster["affected_people"] + citizen_input.num_people
                db.update_disaster_severity(
                    disaster_id,
                    max(disaster["severity"], context.assessment.severity),
                    new_affected,
                )

        # Final orchestrator log
        final_status = self._build_final_status(context)
        db.log_agent_execution(
            agent_name="Orchestrator Agent",
            action="pipeline_complete",
            decision=f"Pipeline completed in {total_ms}ms | Request #{request_id} | {final_status}",
            reasoning=f"All agents executed. Mode: {self.mode.upper()}. "
                      f"Monitoring alerts: {len(context.monitoring_result.alerts) if context.monitoring_result else 0}. "
                      f"Replan needed: {context.monitoring_result.replan_triggered if context.monitoring_result else False}.",
            request_id=request_id,
            disaster_id=disaster_id,
            output_data={"total_ms": total_ms, "status": final_status},
            execution_time_ms=total_ms,
            mode=self.mode,
        )

        return PipelineResult(
            request_id=request_id,
            disaster_id=disaster_id,
            mode=self.mode,
            success=True,
            total_time_ms=total_ms,
            agent_logs=agent_logs,
            final_status=final_status,
            summary=self._build_summary(context, request_id),
            pipeline_start=pipeline_start,
            pipeline_end=datetime.now(),
        )

    def run_monitoring_check(self, disaster_id: Optional[int] = None) -> dict:
        """
        Standalone monitoring check (called periodically).
        Returns alert summary.
        """
        context = DisasterContext(disaster_id=disaster_id, mode=self.mode)
        context = self.agents["monitoring"].run(context)
        result = context.monitoring_result
        if not result:
            return {"alerts": 0, "health": "Unknown"}
        return {
            "alerts": len(result.alerts),
            "health": result.system_health,
            "replan": result.replan_triggered,
            "alert_messages": [a.message for a in result.alerts],
        }

    # ── Private helpers ────────────────────────────────────────────────────────

    def _summarize_result(self, agent_key: str, context: DisasterContext) -> str:
        try:
            if agent_key == "disaster_assessment" and context.assessment:
                a = context.assessment
                return f"{a.disaster_type} | Severity {a.severity}/5 ({a.severity_label}) | {a.affected_people} people"
            elif agent_key == "hospital_allocation" and context.hospital_result:
                h = context.hospital_result
                name = h.allocated_hospital.name if h.allocated_hospital else "None"
                return f"Allocated: {name} | Beds: {h.beds_reserved} | ICU: {h.icu_reserved}"
            elif agent_key == "road_intelligence" and context.route_result:
                r = context.route_result
                return f"Route: {r.estimated_distance_km:.1f} km | {r.estimated_time_minutes} min | Risk: {r.route_risk_level}"
            elif agent_key == "resource" and context.resource_result:
                r = context.resource_result
                amb = r.assigned_ambulance.vehicle_number if r.assigned_ambulance else "None"
                return f"Ambulance: {amb} | ETA: {r.ambulance_eta_minutes} min | Resources: {r.total_resources_deployed}"
            elif agent_key == "communication" and context.communication_result:
                c = context.communication_result
                return f"Notifications sent: {c.total_notified}"
            elif agent_key == "monitoring" and context.monitoring_result:
                m = context.monitoring_result
                return f"System: {m.system_health} | Alerts: {len(m.alerts)} | Replan: {m.replan_triggered}"
        except Exception:
            pass
        return "Completed"

    def _get_reasoning(self, agent_key: str, context: DisasterContext) -> str:
        try:
            if agent_key == "disaster_assessment" and context.assessment:
                return context.assessment.reasoning
            elif agent_key == "hospital_allocation" and context.hospital_result:
                return context.hospital_result.reasoning
            elif agent_key == "road_intelligence" and context.route_result:
                return context.route_result.reasoning
            elif agent_key == "resource" and context.resource_result:
                return context.resource_result.reasoning
            elif agent_key == "communication" and context.communication_result:
                return context.communication_result.reasoning
            elif agent_key == "monitoring" and context.monitoring_result:
                return context.monitoring_result.reasoning
        except Exception:
            pass
        return ""

    def _build_final_status(self, context: DisasterContext) -> str:
        parts = []
        if context.assessment:
            parts.append(f"Disaster: {context.assessment.disaster_type} Sev.{context.assessment.severity}")
        if context.hospital_result and context.hospital_result.allocated_hospital:
            parts.append(f"Hospital: {context.hospital_result.allocated_hospital.name}")
        if context.resource_result and context.resource_result.assigned_ambulance:
            parts.append(f"Amb: {context.resource_result.assigned_ambulance.vehicle_number}")
        if context.route_result:
            parts.append(f"Route: {context.route_result.estimated_time_minutes}min")
        return " | ".join(parts) if parts else "Pipeline Completed"

    def _build_summary(self, context: DisasterContext, request_id: int) -> str:
        lines = [f"Emergency #{request_id} Response Summary:"]
        if context.assessment:
            a = context.assessment
            lines.append(f"* Disaster: {a.disaster_type} (Severity {a.severity}/5 - {a.severity_label})")
            lines.append(f"* Affected: {a.affected_people} people at {a.affected_location}")
        if context.hospital_result and context.hospital_result.allocated_hospital:
            h = context.hospital_result
            lines.append(f"* Hospital: {h.allocated_hospital.name}")
            lines.append(f"* Beds Reserved: {h.beds_reserved} | ICU: {h.icu_reserved}")
        if context.resource_result and context.resource_result.assigned_ambulance:
            r = context.resource_result
            lines.append(f"* Ambulance: {r.assigned_ambulance.vehicle_number} - ETA {r.ambulance_eta_minutes} min")
        if context.route_result:
            rt = context.route_result
            lines.append(f"* Route: {rt.estimated_distance_km:.1f} km ({rt.estimated_time_minutes} min) - Risk: {rt.route_risk_level}")
        if context.monitoring_result:
            m = context.monitoring_result
            lines.append(f"* System Health: {m.system_health} | Alerts: {len(m.alerts)}")
        lines.append(f"* Mode: {self.mode.upper()} | Total Time: {context.total_execution_ms}ms")
        return "\n".join(lines)
