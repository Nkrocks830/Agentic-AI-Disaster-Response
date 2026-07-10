"""
ResQNet AI - Pydantic Models
All domain models with validation. Agents return these instead of plain text.
"""

from __future__ import annotations
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, model_validator


# ══════════════════════════════════════════════════════════════════════════════
# DISASTER MODELS
# ══════════════════════════════════════════════════════════════════════════════

class DisasterInput(BaseModel):
    """Raw input from citizen emergency report."""
    citizen_name:  str = Field(..., min_length=2, max_length=100)
    citizen_phone: str = Field(..., min_length=10, max_length=15)
    latitude:      float = Field(..., ge=-90, le=90)
    longitude:     float = Field(..., ge=-180, le=180)
    address:       str = Field(..., min_length=5)
    description:   str = Field(..., min_length=10)
    num_people:    int = Field(default=1, ge=1, le=1000)
    disaster_id:   Optional[int] = None


class DisasterAssessmentResult(BaseModel):
    """Output of the Disaster Assessment Agent."""
    disaster_type:     str   = Field(..., description="Type: Flood, Cyclone, Earthquake, Fire, etc.")
    severity:          int   = Field(..., ge=1, le=5, description="1=Low to 5=Extreme")
    severity_label:    str   = Field(default="")
    affected_location: str   = Field(..., description="Identified location name")
    affected_people:   int   = Field(..., ge=0)
    risk_factors:      List[str] = Field(default_factory=list)
    immediate_actions: List[str] = Field(default_factory=list)
    confidence_score:  float = Field(default=0.85, ge=0.0, le=1.0)
    reasoning:         str   = ""
    is_simulation:     bool  = False

    @model_validator(mode="after")
    def _auto_severity_label(self) -> "DisasterAssessmentResult":
        """Auto-populate severity_label from severity if not provided."""
        if not self.severity_label:
            labels = {1: "Low", 2: "Moderate", 3: "High", 4: "Critical", 5: "Extreme"}
            self.severity_label = labels.get(self.severity, "Unknown")
        return self


class DisasterContext(BaseModel):
    """Shared context passed between all agents during a pipeline run."""
    model_config = {"arbitrary_types_allowed": True}

    request_id:           Optional[int] = None
    disaster_id:          Optional[int] = None
    citizen_input:        Optional[DisasterInput] = None
    assessment:           Optional[DisasterAssessmentResult] = None
    hospital_result:      Optional[Any] = None   # HospitalAllocationResult
    route_result:         Optional[Any] = None   # RouteResult
    resource_result:      Optional[Any] = None   # ResourceAllocationResult
    communication_result: Optional[Any] = None   # CommunicationResult
    monitoring_result:    Optional[Any] = None   # MonitoringResult
    pipeline_start:       datetime = Field(default_factory=datetime.now)
    total_execution_ms:   int = 0
    mode:                 str = "live"            # "live" | "simulation"
