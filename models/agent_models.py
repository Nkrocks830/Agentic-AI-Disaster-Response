"""
ResQNet AI - Agent Meta Models
Execution log, pipeline context, and monitoring models.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class AgentExecutionLog(BaseModel):
    """Full execution log for one agent run."""
    log_id:           Optional[int] = None
    request_id:       Optional[int] = None
    disaster_id:      Optional[int] = None
    agent_name:       str
    action:           str
    decision:         str
    reasoning:        str = ""
    input_summary:    str = ""
    output_summary:   str = ""
    execution_time_ms: int = 0
    status:           str = "success"   # success|failed|skipped
    mode:             str = "live"      # live|simulation
    timestamp:        datetime = Field(default_factory=datetime.now)


class MonitoringAlert(BaseModel):
    """An alert raised by the Monitoring Agent."""
    alert_type:    str         # hospital_full|road_blocked|resource_low|condition_changed
    severity:      int = 1
    entity_type:   str         # hospital|road|ambulance|resource
    entity_id:     int
    entity_name:   str
    message:       str
    action_taken:  str = ""
    timestamp:     datetime = Field(default_factory=datetime.now)


class MonitoringResult(BaseModel):
    """Output of the Monitoring Agent."""
    alerts:             List[MonitoringAlert] = Field(default_factory=list)
    replan_triggered:   bool = False
    replan_reason:      str = ""
    hospitals_checked:  int = 0
    roads_checked:      int = 0
    resources_checked:  int = 0
    system_health:      str = "Operational"   # Operational|Degraded|Critical
    reasoning:          str = ""
    is_simulation:      bool = False


class PipelineResult(BaseModel):
    """Full result of one Orchestrator pipeline run."""
    request_id:       Optional[int] = None
    disaster_id:      Optional[int] = None
    mode:             str = "live"
    success:          bool = True
    error_message:    str = ""
    total_time_ms:    int = 0
    agent_logs:       List[AgentExecutionLog] = Field(default_factory=list)
    final_status:     str = ""
    summary:          str = ""
    pipeline_start:   datetime = Field(default_factory=datetime.now)
    pipeline_end:     Optional[datetime] = None
