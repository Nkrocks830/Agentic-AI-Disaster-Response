"""
ResQNet AI - Execution Logger
Provides structured logging utilities for the Orchestrator.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from database import db_manager as db
from models.agent_models import AgentExecutionLog


class ExecutionLogger:
    """
    Centralised execution logger used by the Orchestrator.
    Persists every agent action to the agent_logs table.
    """

    def __init__(self, request_id: Optional[int] = None, disaster_id: Optional[int] = None):
        self.request_id  = request_id
        self.disaster_id = disaster_id
        self.entries: List[AgentExecutionLog] = []

    def log(
        self,
        agent_name: str,
        action: str,
        decision: str,
        reasoning: str = "",
        input_data:  Optional[Dict] = None,
        output_data: Optional[Dict] = None,
        execution_time_ms: int = 0,
        status: str = "success",
        mode: str = "live",
    ) -> int:
        """Write one log entry to DB and buffer it in memory."""
        log_id = db.log_agent_execution(
            agent_name=agent_name,
            action=action,
            decision=decision,
            reasoning=reasoning,
            request_id=self.request_id,
            disaster_id=self.disaster_id,
            input_data=input_data,
            output_data=output_data,
            execution_time_ms=execution_time_ms,
            status=status,
            mode=mode,
        )
        self.entries.append(AgentExecutionLog(
            log_id=log_id,
            request_id=self.request_id,
            disaster_id=self.disaster_id,
            agent_name=agent_name,
            action=action,
            decision=decision,
            reasoning=reasoning,
            execution_time_ms=execution_time_ms,
            status=status,
            mode=mode,
        ))
        return log_id

    def get_summary(self) -> str:
        """Return a human-readable execution summary."""
        lines = []
        total_ms = sum(e.execution_time_ms for e in self.entries)
        for e in self.entries:
            icon = "[DONE]" if e.status == "success" else "[X]"
            lines.append(f"  {icon} [{e.execution_time_ms:4d}ms] {e.agent_name}: {e.decision[:80]}")
        lines.append(f"\n  Total pipeline time: {total_ms}ms | Agents: {len(self.entries)}")
        return "\n".join(lines)
