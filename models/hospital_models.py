"""
ResQNet AI - Hospital Pydantic Models
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class HospitalInfo(BaseModel):
    """Summary of a hospital's current state."""
    hospital_id:        int
    name:               str
    address:            str
    latitude:           float
    longitude:          float
    available_beds:     int
    available_icu:      int
    available_doctors:  int
    status:             str
    specializations:    List[str] = Field(default_factory=list)
    distance_km:        float = 0.0
    contact_phone:      str = ""


class HospitalAllocationResult(BaseModel):
    """Output of the Hospital Allocation Agent."""
    allocated_hospital:     Optional[HospitalInfo] = None
    beds_reserved:          int = 0
    icu_reserved:           int = 0
    priority_score:         float = 0.0
    allocation_reason:      str = ""
    fallback_hospitals:     List[HospitalInfo] = Field(default_factory=list)
    requires_icu:           bool = False
    estimated_wait_minutes: int = 0
    reassignment_triggered: bool = False
    reasoning:              str = ""
    is_simulation:          bool = False


class PatientQueueItem(BaseModel):
    """One patient in the hospital queue."""
    request_id:     int
    citizen_name:   str
    citizen_phone:  str
    num_people:     int
    severity:       int
    severity_label: str
    address:        str
    status:         str
    allocated_at:   str
    beds_reserved:  int
    icu_reserved:   int
    priority:       int
