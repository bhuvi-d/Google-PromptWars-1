from pydantic import BaseModel, Field
from typing import List, Optional

class RouteRequest(BaseModel):
    start_node: str = Field(...)
    end_node: str = Field(...)
    emergency_mode: bool = False
    accessible_mode: bool = False
    scenic_mode: bool = False
    smart_restroom: bool = False

class RouteResponse(BaseModel):
    recommended_route: List[str]
    estimated_time: str
    estimated_distance: str
    confidence_score: int
    crowd_impact: str  # "Reduces Congestion", "Neutral", "Increases Congestion"
    reasoning: str
    departure_time: Optional[str] = None
    target_relocated: Optional[str] = None
