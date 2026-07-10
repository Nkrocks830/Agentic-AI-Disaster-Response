"""
ResQNet AI - Monitoring Agent
Single Responsibility: Monitor all resources and trigger replanning when conditions change.
"""

from agents.base_agent import BaseAgent
from models.disaster_models import DisasterContext
from models.agent_models import MonitoringResult, MonitoringAlert
from database import db_manager as db
from datetime import datetime


class MonitoringAgent(BaseAgent):
    """
    Agent 6: Monitoring
    Continuously monitors hospitals, roads, and resources for condition changes.
    Triggers replanning alerts when thresholds are exceeded.
    """

    def __init__(self):
        super().__init__("monitoring")

    def run_live(self, context: DisasterContext) -> DisasterContext:
        # Monitoring uses the same logic in both modes (DB-driven)
        return self._do_monitoring(context, is_sim=False)

    def run_simulation(self, context: DisasterContext) -> DisasterContext:
        return self._do_monitoring(context, is_sim=True)

    def _do_monitoring(self, context: DisasterContext, is_sim: bool) -> DisasterContext:
        self._start_timer()
        alerts = []

        # ── Monitor Hospitals ──────────────────────────────────────────────────
        hospitals = db.get_all_hospitals()
        for h in hospitals:
            total = h.get("total_beds", 1) or 1
            avail = h.get("available_beds", 0)
            occupancy_pct = ((total - avail) / total) * 100

            if occupancy_pct >= 95:
                alerts.append(MonitoringAlert(
                    alert_type="hospital_full",
                    severity=5,
                    entity_type="hospital",
                    entity_id=h["id"],
                    entity_name=h["name"],
                    message=f"🏥 CRITICAL: {h['name']} is at {occupancy_pct:.0f}% capacity ({avail} beds remaining). Auto-reassignment triggered.",
                    action_taken="Marked as 'At Capacity'. New requests diverted to fallback hospitals.",
                ))
                db.update_hospital_status(h["id"], "At Capacity")
            elif occupancy_pct >= 80:
                alerts.append(MonitoringAlert(
                    alert_type="hospital_high_occupancy",
                    severity=3,
                    entity_type="hospital",
                    entity_id=h["id"],
                    entity_name=h["name"],
                    message=f"[!]️ WARNING: {h['name']} at {occupancy_pct:.0f}% capacity. {avail} beds available.",
                    action_taken="Flagged for monitoring.",
                ))

        # ── Monitor Roads ──────────────────────────────────────────────────────
        blocked = db.get_blocked_roads()
        critical_roads = [r for r in blocked if r.get("severity", 0) >= 4]

        if len(blocked) >= 10:
            alerts.append(MonitoringAlert(
                alert_type="mass_road_closure",
                severity=4,
                entity_type="road",
                entity_id=0,
                entity_name="Road Network",
                message=f"🚧 CRITICAL: {len(blocked)} roads blocked. {len(critical_roads)} are severity 4+. Route recalculation required.",
                action_taken="Road Intelligence Agent notified for route replanning.",
            ))

        # ── Monitor Resources ──────────────────────────────────────────────────
        all_resources = db.get_all_resources()
        available = [r for r in all_resources if r["status"] == "Available"]
        deployed = [r for r in all_resources if r["status"] == "Deployed"]
        ambulances = db.get_available_ambulances()

        if len(ambulances) == 0:
            alerts.append(MonitoringAlert(
                alert_type="resource_exhausted",
                severity=5,
                entity_type="ambulance",
                entity_id=0,
                entity_name="Ambulance Fleet",
                message="🚑 CRITICAL: All ambulances are dispatched. No ambulances available for new requests!",
                action_taken="Authorities notified. Requesting mutual aid from neighboring districts.",
            ))
        elif len(ambulances) <= 2:
            alerts.append(MonitoringAlert(
                alert_type="resource_low",
                severity=3,
                entity_type="ambulance",
                entity_id=0,
                entity_name="Ambulance Fleet",
                message=f"[!]️ LOW: Only {len(ambulances)} ambulance(s) available.",
                action_taken="Mutual aid request prepared.",
            ))

        if len(available) == 0 and len(all_resources) > 0:
            alerts.append(MonitoringAlert(
                alert_type="resource_exhausted",
                severity=5,
                entity_type="resource",
                entity_id=0,
                entity_name="Emergency Resources",
                message="🆘 CRITICAL: All rescue resources are deployed. No reserve capacity.",
                action_taken="Emergency resource request sent to state authorities.",
            ))

        # ── Determine if replanning needed ────────────────────────────────────
        critical_alerts = [a for a in alerts if a.severity >= 4]
        replan = len(critical_alerts) > 0
        replan_reason = " | ".join(a.alert_type for a in critical_alerts) if replan else ""

        # ── System health ─────────────────────────────────────────────────────
        if len(critical_alerts) >= 3:
            health = "Critical"
        elif len(critical_alerts) >= 1:
            health = "Degraded"
        else:
            health = "Operational"

        elapsed = self._elapsed_ms()

        result = MonitoringResult(
            alerts=alerts,
            replan_triggered=replan,
            replan_reason=replan_reason,
            hospitals_checked=len(hospitals),
            roads_checked=len(blocked),
            resources_checked=len(all_resources),
            system_health=health,
            reasoning=f"{'[SIMULATION] ' if is_sim else ''}Checked {len(hospitals)} hospitals, {len(blocked)} blocked roads, "
                      f"{len(all_resources)} resources. Found {len(alerts)} alert(s). System health: {health}.",
            is_simulation=is_sim,
        )

        context.monitoring_result = result

        prefix = "[SIM] " if is_sim else ""
        self._log(
            action="monitor_system",
            decision=f"{prefix}System: {health} | {len(alerts)} alerts | Replan: {replan}",
            reasoning=result.reasoning,
            request_id=context.request_id,
            disaster_id=context.disaster_id,
            input_data={"hospitals": len(hospitals), "roads": len(blocked), "resources": len(all_resources)},
            output_data={"alerts": len(alerts), "health": health, "replan": replan},
            execution_time_ms=elapsed,
        )
        return context
