"""
ResQNet AI - Base Agent
Abstract base class for all agents.
Provides: timing, logging, mode awareness, error handling.
"""

import time
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, Optional

from services.gemini_service import get_mode, call_gemini
from database import db_manager as db
from config.settings import AGENT_NAMES


class BaseAgent(ABC):
    """
    Every specialized agent inherits from this class.
    Subclasses implement `run_live()` (Gemini-powered) and
    `run_simulation()` (deterministic fallback).
    """

    def __init__(self, agent_key: str):
        self.agent_key = agent_key
        self.agent_name = AGENT_NAMES.get(agent_key, agent_key)
        self.mode = get_mode()          # "live" or "simulation"
        self._start_time: float = 0.0

    # ── Timing helpers ─────────────────────────────────────────────────────────
    def _start_timer(self):
        self._start_time = time.time()

    def _elapsed_ms(self) -> int:
        return int((time.time() - self._start_time) * 1000)

    # ── Gemini call wrapper ────────────────────────────────────────────────────
    def _call_gemini(self, prompt: str) -> tuple:
        """Returns (parsed_dict, elapsed_ms, raw_text)."""
        return call_gemini(prompt)

    # ── DB logging ─────────────────────────────────────────────────────────────
    def _log(
        self,
        action: str,
        decision: str,
        reasoning: str = "",
        request_id: Optional[int] = None,
        disaster_id: Optional[int] = None,
        input_data: Optional[Dict] = None,
        output_data: Optional[Dict] = None,
        execution_time_ms: int = 0,
        status: str = "success",
    ) -> int:
        return db.log_agent_execution(
            agent_name=self.agent_name,
            action=action,
            decision=decision,
            reasoning=reasoning,
            request_id=request_id,
            disaster_id=disaster_id,
            input_data=input_data,
            output_data=output_data,
            execution_time_ms=execution_time_ms,
            status=status,
            mode=self.mode,
        )

    # ── Main entry point ───────────────────────────────────────────────────────
    def run(self, context: Any) -> Any:
        """
        Public method called by the Orchestrator.
        Dispatches to run_live() or run_simulation() based on mode.
        """
        self.mode = get_mode()   # re-check in case mode changed
        self._start_timer()
        try:
            if self.mode == "live":
                result = self.run_live(context)
            else:
                result = self.run_simulation(context)
            return result
        except Exception as e:
            # Log failure and fall back to simulation
            self._log(
                action="agent_error",
                decision=f"Agent failed: {str(e)[:200]}",
                status="failed",
                request_id=getattr(context, "request_id", None),
                disaster_id=getattr(context, "disaster_id", None),
            )
            # Attempt simulation fallback
            try:
                self.mode = "simulation"
                return self.run_simulation(context)
            except Exception as e2:
                raise RuntimeError(
                    f"{self.agent_name} failed in both live and simulation modes: {e2}"
                ) from e2

    # ── Abstract methods subclasses must implement ────────────────────────────
    @abstractmethod
    def run_live(self, context: Any) -> Any:
        """Gemini-powered execution."""
        ...

    @abstractmethod
    def run_simulation(self, context: Any) -> Any:
        """Deterministic simulation execution (no API needed)."""
        ...
