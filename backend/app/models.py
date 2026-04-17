from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
from enum import Enum

class RoutingStrategy(str, Enum):
    """Available routing optimization modes."""
    SHORTEST = "shortest"
    SCENIC = "scenic"
    ACCESSIBLE = "accessible"
    CROWD_AWARE = "crowd_aware"

class RouteRequest(BaseModel):
    """
    Validation schema for inbound routing requests.
    Strictly forbids extra fields to ensure API integrity.
    """
    model_config = ConfigDict(extra="forbid")

    start_node: str = Field(..., description="UUID or ID of the starting location node.")
    end_node: str = Field(..., description="UUID or ID of the destination node.")
    accessible_mode: bool = Field(default=False, description="Exclude stairs and steep gradients.")
    scenic_mode: bool = Field(default=False, description="Prioritize landmark proximity.")
    emergency_mode: bool = Field(default=False, description="Priority medical or security override.")
    smart_restroom: bool = Field(default=False, description="Reroute to restrooms with lowest predicted queue.")

class RouteResponse(BaseModel):
    """
    Structured response for calculated navigational paths.
    Includes AI reasoning and movement estimations.
    """
    model_config = ConfigDict(extra="forbid")

    recommended_route: List[str] = Field(..., description="Ordered list of node IDs to follow.")
    estimated_time: str = Field(..., description="Human-readable duration estimate (e.g. '5 mins').")
    estimated_distance: str = Field(..., description="Walking distance in meters.")
    confidence_score: int = Field(..., ge=0, le=100, description="Heuristic reliability index (0-100).")
    crowd_impact: str = Field(..., description="Qualitative crowd density status ('Light', 'Heavy').")
    reasoning: str = Field(..., description="Conversational explanation of the route choice (Inc. AI Tip).")
    departure_time: Optional[str] = Field(None, description="Recommended departure window for low congestion.")
    target_relocated: Optional[str] = Field(None, description="Notice if destination node moved (e.g. mobile food truck).")

class AdminOverride(BaseModel):
    """Schema for global state overrides triggered by administrators."""
    model_config = ConfigDict(extra="forbid")

    mass_exodus: Optional[bool] = None
    weather_pattern: Optional[str] = None
    manual_congestion: Optional[dict] = None # e.g. {"node_a": 3.0}
