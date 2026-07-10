"""
ResQNet AI - Resource Pydantic Models
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class ResourceItem(BaseModel):
    """A single resource (ambulance, boat, truck, team)."""
    resource_id:    int
    name:           str
    resource_type:  str
    location_name:  str
    latitude:       float
    longitude:      float
    status:         str
    capacity:       int
    operator_name:  str = ""
    operator_phone: str = ""
    distance_km:    float = 0.0
    eta_minutes:    int = 0


class AmbulanceInfo(BaseModel):
    """Ambulance details for dispatching."""
    ambulance_id:   int
    vehicle_number: str
    driver_name:    str
    driver_phone:   str
    latitude:       float
    longitude:      float
    status:         str
    fuel_level:     int
    distance_km:    float = 0.0
    eta_minutes:    int = 0


class ResourceAllocationResult(BaseModel):
    """Output of the Emergency Resource Agent."""
    assigned_ambulance:    Optional[AmbulanceInfo] = None
    assigned_resources:    List[ResourceItem] = Field(default_factory=list)
    ambulance_eta_minutes: int = 0
    priority_level:        str = "Normal"   # Normal | High | Critical
    allocation_reason:     str = ""
    total_resources_deployed: int = 0
    reasoning:             str = ""
    is_simulation:         bool = False
