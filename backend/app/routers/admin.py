import logging
from fastapi import APIRouter, HTTPException, Depends, Header
from app.state import state
from app.services.gcp import gcp_services

logger = logging.getLogger(__name__)
router = APIRouter()


def verify_admin(authorization: str = Header(None)) -> bool:
    """
    Dependency that validates an admin bearer token on protected endpoints.

    In production (USE_REAL_GCP=true), validates a real Firebase ID token
    via the Firebase Admin SDK. In development, accepts the mock token.

    Args:
        authorization: The raw Authorization header value (e.g. "Bearer <token>").

    Raises:
        HTTPException: 403 if token is present but invalid.

    Returns:
        True if the request is authorized.
    """
    if authorization:
        token = authorization.replace("Bearer ", "").strip()
        if not gcp_services.verify_token(token):
            logger.warning("Unauthorized admin access attempt blocked.")
            raise HTTPException(status_code=403, detail="Invalid Admin Token")
        logger.info("Admin token validated successfully.")
    return True


@router.post("/weather")
async def toggle_weather(state_val: str, admin: bool = Depends(verify_admin)):
    """
    Toggles simulated weather conditions across the venue.

    Accepted values: 'rain' or 'clear'. Rain multiplies outdoor path
    weights, driving the routing engine to prefer covered concourses.

    Args:
        state_val: Target weather state — 'rain' or 'clear'.

    Returns:
        dict: Confirmed new weather state.
    """
    state.weather = "rain" if state_val == "rain" else "clear"
    gcp_services.publish_telemetry("weather_update", {"weather": state.weather})
    logger.info("Weather state updated: %s", state.weather)
    return {"weather": state.weather}


@router.post("/exodus")
async def toggle_exodus(state_val: str, admin: bool = Depends(verify_admin)):
    """
    Activates or deactivates the Mass Exodus emergency protocol.

    When active, all routing overrides normal pathfinding and forces
    attendees toward the nearest physical egress exit at maximum priority.

    Args:
        state_val: 'active' to trigger evacuation, any other value to clear it.

    Returns:
        dict: Confirmed exodus state.
    """
    state.mass_exodus = (state_val == "active")
    gcp_services.publish_telemetry("exodus_update", {"mass_exodus": state.mass_exodus})
    logger.info("Mass Exodus protocol set: %s", state.mass_exodus)
    return {"exodus": state.mass_exodus}


@router.post("/trigger-congestion")
async def trigger_congestion(
    node: str,
    severity: float = 3.0,
    admin: bool = Depends(verify_admin)
):
    """
    Manually injects a congestion spike at a specific venue node.

    Used by venue operations staff to mark a real-world bottleneck.
    The decision engine immediately increases path cost through this node,
    automatically rerouting pending navigation requests away from it.

    Args:
        node: The graph node ID to mark as congested.
        severity: Congestion multiplier (1.0 = clear, 3.0 = maximum congestion).

    Returns:
        dict: Confirmation with targeted node and applied severity.
    """
    if node not in state.congestion_state:
        logger.warning("Congestion trigger attempted on unknown node: %s", node)
        raise HTTPException(status_code=400, detail=f"Node '{node}' does not exist in venue graph.")
    state.congestion_state[node] = max(1.0, min(3.0, severity))
    gcp_services.publish_telemetry("congestion_spike", {"node": node, "severity": severity})
    logger.info("Congestion spike injected: node=%s severity=%.1f", node, severity)
    return {"status": "success", "node": node, "severity": severity}
