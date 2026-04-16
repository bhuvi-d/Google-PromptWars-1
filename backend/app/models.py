from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum


class WeatherState(str, Enum):
    """Represents the current weather condition at the venue."""
    CLEAR = "clear"
    RAIN = "rain"


class CrowdImpact(str, Enum):
    """Describes how a route affects overall crowd distribution."""
    RELIEVES = "Relieves Congestion"
    NEUTRAL = "Neutral"
    INCREASES = "Increases Congestion"
    EMERGENCY = "Emergency Overrides Active"


class RouteRequest(BaseModel):
    """
    Payload for requesting an optimized venue route.

    Attributes:
        start_node: Graph node ID representing the user's current position.
        end_node: Graph node ID for the desired destination.
        emergency_mode: If True, overrides all routing to the nearest egress exit.
        accessible_mode: If True, filters out all paths that include stairs or ramps.
        scenic_mode: If True, biases routing toward attraction nodes (Trophy Room, Fan Zone).
        smart_restroom: If True, auto-selects the least-congested restroom near the destination.
    """
    start_node: str = Field(..., description="Starting graph node ID (e.g. 'entrance_north')")
    end_node: str = Field(..., description="Destination graph node ID (e.g. 'food_court_1')")
    emergency_mode: bool = Field(False, description="Force routing to nearest exit.")
    accessible_mode: bool = Field(False, description="Exclude stair segments from path.")
    scenic_mode: bool = Field(False, description="Prefer routes through scenic nodes.")
    smart_restroom: bool = Field(False, description="Auto-select least-congested restroom.")


class RouteResponse(BaseModel):
    """
    The decision engine's full route recommendation response.

    Attributes:
        recommended_route: Ordered list of node IDs forming the optimal path.
        estimated_time: Human-readable walk time estimate (e.g. '8 minutes').
        estimated_distance: Human-readable distance string (e.g. '450m walk').
        confidence_score: Engine confidence 0-100 based on congestion volatility.
        crowd_impact: Whether this route relieves, is neutral to, or adds crowd pressure.
        reasoning: Conversational explanation of why this route was chosen.
        departure_time: Optional tip for optimal departure timing (food courts only).
        target_relocated: Set if the original destination was swapped for a better alternative.
    """
    recommended_route: List[str]
    estimated_time: str
    estimated_distance: str
    confidence_score: int = Field(..., ge=0, le=100)
    crowd_impact: str
    reasoning: str
    departure_time: Optional[str] = None
    target_relocated: Optional[str] = None
