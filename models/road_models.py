"""
ResQNet AI - Road / Route Pydantic Models
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class RoadSegment(BaseModel):
    """A single road segment with condition info."""
    road_id:        int
    road_name:      str
    from_location:  str
    to_location:    str
    from_lat:       float
    from_lon:       float
    to_lat:         float
    to_lon:         float
    condition:      str   # Clear|Blocked|Flooded|Damaged|Collapsed
    blockage_reason: Optional[str] = None
    severity:       int = 0
    is_passable:    bool = True


class RouteWaypoint(BaseModel):
    """One stop on a calculated route."""
    location_name: str
    latitude:      float
    longitude:     float
    is_checkpoint: bool = False


class RouteResult(BaseModel):
    """Output of the Road Intelligence Agent."""
    origin_lat:          float
    origin_lon:          float
    destination_lat:     float
    destination_lon:     float
    origin_name:         str = ""
    destination_name:    str = ""
    safest_route:        List[RouteWaypoint] = Field(default_factory=list)
    alternate_routes:    List[List[RouteWaypoint]] = Field(default_factory=list)
    blocked_roads:       List[RoadSegment] = Field(default_factory=list)
    estimated_distance_km: float = 0.0
    estimated_time_minutes: int = 0
    route_risk_level:    str = "Low"    # Low|Medium|High|Critical
    route_notes:         List[str] = Field(default_factory=list)
    reasoning:           str = ""
    is_simulation:       bool = False
