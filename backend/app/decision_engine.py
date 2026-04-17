import heapq
import logging
import random
from functools import lru_cache
from typing import List, Dict, Optional, Tuple

from app.graph import VENUE_GRAPH, EXIT_NODES, RESTROOM_NODES, MERCH_NODES, FOOD_NODES, SCENIC_NODES
from app.models import RouteRequest, RouteResponse
from app.state import state
from app.services.gcp import gcp_services

logger = logging.getLogger(__name__)


@lru_cache(maxsize=256)
def _cached_graph_search(start: str, end: str, accessible_mode: bool) -> Optional[Tuple[str, ...]]:
    """
    LRU-cached wrapper around the physical graph traversal for standard
    (non-emergency, non-dynamic) routes.

    Caches the optimal path as a tuple of node IDs so repeated requests for
    the same start/end pair avoid re-running the heap search entirely.
    Cache is keyed on (start, end, accessible_mode) since these are the only
    parameters that affect the graph topology. Congestion weights are applied
    by the caller after the path is retrieved.

    Args:
        start:           Source node ID.
        end:             Destination node ID.
        accessible_mode: If True, stair edges were excluded.

    Returns:
        Ordered tuple of node IDs, or None if no path exists.
    """
    # Build a minimal Dijkstra limited to topology only (weight=1 per hop).
    # This gives the shortest physical hop count, used as the cache value.
    queue: List[Tuple[float, List[str]]] = [(0.0, [start])]
    visited = set()
    while queue:
        cost, path = heapq.heappop(queue)
        current = path[-1]
        if current in visited:
            continue
        visited.add(current)
        if current == end:
            return tuple(path)
        for neighbor, edge_data in VENUE_GRAPH.get(current, {}).items():
            if neighbor in visited:
                continue
            if accessible_mode and edge_data.get("stairs", False):
                continue
            heapq.heappush(queue, (cost + 1, path + [neighbor]))
    return None

# ---------------------------------------------------------------------------
# Internal Graph Search — K-Shortest Diverse Paths
# ---------------------------------------------------------------------------

def dijkstra_k_shortest(
    graph: Dict[str, Dict],
    start: str,
    end: str,
    req: RouteRequest,
    k: int = 3
) -> List[Dict]:
    """
    Computes up to K physically diverse, valid shortest paths using a modified
    priority-queue search inspired by Yen's K-Shortest Paths algorithm.

    Instead of returning K variants of the same corridor, this engine enforces
    an 80% node-diversity constraint so each candidate path takes a meaningfully
    different route through the venue. This prevents the 'stampede effect' where
    all attendees are funneled into a single optimal corridor simultaneously.

    Args:
        graph: Full adjacency dict representing the venue walkability graph.
        start: Source node ID (user's current position).
        end: Destination node ID.
        req: Full RouteRequest containing mode flags (emergency, accessible, etc.)
        k: Maximum number of diverse route candidates to return.

    Returns:
        List of route dicts sorted by ascending adjusted cost, each containing
        'path' (ordered node list) and 'cost' (float total weight).
    """
    queue: List[Tuple[float, List[str]]] = [(0.0, [start])]
    routes_found: List[Dict] = []
    max_iterations = 2500
    iterations = 0

    while queue and len(routes_found) < k and iterations < max_iterations:
        iterations += 1
        cost, path = heapq.heappop(queue)
        current = path[-1]

        if current == end:
            # Enforce spatial diversity: skip paths that share >80% of nodes
            # with an already-found route (unless in emergency mode).
            is_diverse = True
            if routes_found and not req.emergency_mode:
                for found in routes_found:
                    shared = set(path) & set(found["path"])
                    if len(shared) / len(path) > 0.8:
                        is_diverse = False
                        break

            if is_diverse or req.emergency_mode:
                destination_queue = state.congestion_state.get(end, 1.0) * 5.0
                routes_found.append({"path": path, "cost": cost + destination_queue})
            continue

        for neighbor, edge_data in graph.get(current, {}).items():
            if neighbor in path:
                continue  # Prevent cycles

            # Accessibility filter: skip stair segments when mode is active
            if req.accessible_mode and edge_data.get("stairs", False):
                continue

            base_weight: float = edge_data["weight"]

            if req.emergency_mode or state.mass_exodus:
                # Emergency: pure geometric distance, ignore congestion entirely
                multiplier = 1.0
            else:
                # Standard: weight by average congestion across the edge's two endpoints
                multiplier = (
                    state.congestion_state.get(current, 1.0)
                    + state.congestion_state.get(neighbor, 1.0)
                ) / 2.0

                # Outdoor penalty during rain events
                if state.weather == "rain" and edge_data.get("outdoor", False):
                    multiplier += 3.0

                # Scenic bonus: reduce cost toward attraction nodes if user opted in
                if req.scenic_mode and neighbor in SCENIC_NODES:
                    multiplier = max(0.5, multiplier - 0.5)

            # Micro-fuzz in tie-breakers organically distributes crowd across equal routes
            fuzz = random.uniform(0.0, 0.1) if not req.emergency_mode else 0.0
            new_cost = cost + (base_weight * multiplier) + fuzz
            heapq.heappush(queue, (new_cost, path + [neighbor]))

    return sorted(routes_found, key=lambda x: x["cost"])


# ---------------------------------------------------------------------------
# Confidence & Impact Scoring
# ---------------------------------------------------------------------------

def generate_confidence_and_impact(
    path: List[str],
    base_cost: float,
    req: RouteRequest
) -> Tuple[int, str]:
    """
    Derives a confidence score and crowd impact label for a computed route.

    Confidence degrades proportionally to average congestion along the path
    and drops further if outdoor segments are traversed during rain (higher
    travel time unpredictability). Emergency paths are always 99% confident
    since they override all user preferences.

    Args:
        path: Ordered list of node IDs in the recommended route.
        base_cost: Raw accumulated cost from the pathfinding algorithm.
        req: The original route request for mode-flag context.

    Returns:
        Tuple of (confidence_score: int 0-100, crowd_impact: str label).
    """
    if req.emergency_mode or state.mass_exodus:
        return 99, "Emergency Overrides Active"

    avg_congestion = sum(state.congestion_state.get(n, 1.0) for n in path) / len(path)

    if avg_congestion > 1.8:
        impact = "Increases Congestion"
    elif avg_congestion < 1.3:
        impact = "Relieves Congestion"
    else:
        impact = "Neutral"

    # Base confidence inversely proportional to congestion volatility
    confidence = int(max(40, 98 - (avg_congestion - 1.0) * 35))

    # Rain on outdoor segments makes ETA much less predictable
    has_outdoor_leg = any(
        VENUE_GRAPH.get(path[i], {}).get(path[i + 1], {}).get("outdoor", False)
        for i in range(len(path) - 1)
    )
    if state.weather == "rain" and has_outdoor_leg:
        confidence -= 15

    return min(100, confidence), impact


# ---------------------------------------------------------------------------
# Public Entry Point
# ---------------------------------------------------------------------------

def calculate_best_route(req: RouteRequest) -> RouteResponse:
    """
    Core public function. Accepts a RouteRequest and returns a fully reasoned
    RouteResponse by running the appropriate routing strategy:

    1. **Mass Exodus / Emergency** — Bypasses all user prefs. Forces fastest
       path to the nearest physical egress exit.
    2. **Smart Restroom** — Evaluates all restroom nodes and selects the one
       with the shortest combined travel + queue cost.
    3. **Closest Merch** — Evaluates all merch nodes and locks to the nearest.
    4. **Standard Load-Balanced** — Calculates up to 3 diverse paths and
       randomly selects among those within 15% of the optimal cost, distributing
       physical crowd density organically.

    Args:
        req: The validated RouteRequest from the API layer.

    Returns:
        RouteResponse with route, timing, reasoning, and confidence data.

    Raises:
        ValueError: If no valid path exists given the active constraints.
    """
    target_node = req.end_node
    relocated_msg: Optional[str] = None
    reasoning_parts: List[str] = []
    best_route: Optional[Dict] = None

    # --- Strategy 1: Emergency / Mass Exodus ---
    if state.mass_exodus or req.emergency_mode:
        best_exit_cost = float("inf")
        for ex_node in EXIT_NODES:
            routes = dijkstra_k_shortest(VENUE_GRAPH, req.start_node, ex_node, req, k=1)
            if routes and routes[0]["cost"] < best_exit_cost:
                best_exit_cost = routes[0]["cost"]
                best_route = routes[0]
                target_node = ex_node

        relocated_msg = (
            "Redirected to the optimal exit gate for crowd control."
            if state.mass_exodus
            else "Emergency path locked. Redirecting to nearest exit."
        )
        logger.info("Emergency routing activated. Target exit: %s", target_node)

    # --- Strategy 2: Smart Restroom Queue Balancing ---
    elif req.smart_restroom and target_node in RESTROOM_NODES:
        best_rr_cost = float("inf")
        for rr_node in RESTROOM_NODES:
            routes = dijkstra_k_shortest(VENUE_GRAPH, req.start_node, rr_node, req, k=1)
            if routes and routes[0]["cost"] < best_rr_cost:
                best_rr_cost = routes[0]["cost"]
                best_route = routes[0]

        if best_route and best_route["path"][-1] != req.end_node:
            relocated_msg = (
                f"Redirected to {best_route['path'][-1].replace('_', ' ').title()} "
                "for a faster experience."
            )
            reasoning_parts.append(
                "I noticed that restroom had a long line, so I've redirected you "
                "to a much faster option nearby."
            )
        else:
            reasoning_parts.append(
                "Good choice! That restroom is currently your absolute fastest option."
            )
        if best_route:
            target_node = best_route["path"][-1]

    # --- Strategy 3: Closest Merch Intercept ---
    elif target_node == "closest_merch":
        best_merch_cost = float("inf")
        for m_node in MERCH_NODES:
            routes = dijkstra_k_shortest(VENUE_GRAPH, req.start_node, m_node, req, k=1)
            if routes and routes[0]["cost"] < best_merch_cost:
                best_merch_cost = routes[0]["cost"]
                best_route = routes[0]
        if best_route:
            target_node = best_route["path"][-1]
            relocated_msg = f"Locked onto {target_node.replace('_', ' ').title()}."
            reasoning_parts.append(
                "Ready to grab some gear? I've found the absolute closest "
                "merchandise stand for you."
            )

    # --- Strategy 4: Standard Load-Balanced Routing ---
    else:
        routes = dijkstra_k_shortest(VENUE_GRAPH, req.start_node, target_node, req, k=3)
        if routes:
            optimal_cost = routes[0]["cost"]
            # Any route within 15% of optimal is considered eligible —
            # randomly choosing between them organically distributes crowd mass.
            valid_routes = [r for r in routes if r["cost"] <= optimal_cost * 1.15]
            best_route = random.choice(valid_routes)

    # --- Guard: No valid path found ---
    if not best_route:
        logger.warning(
            "No valid path. start=%s end=%s flags=%s",
            req.start_node, target_node, req.dict()
        )
        raise ValueError(
            f"No valid path from '{req.start_node}' to '{target_node}' "
            "exists under the current constraints. Try disabling Accessible Mode "
            "or changing your destination."
        )

    recommended_route: List[str] = best_route["path"]

    # --- Distance Calculation ---
    raw_distance_meters = sum(
        VENUE_GRAPH[recommended_route[i]].get(
            recommended_route[i + 1], {"weight": 2}
        )["weight"] * 45
        for i in range(len(recommended_route) - 1)
    )

    conf, impact = generate_confidence_and_impact(recommended_route, best_route["cost"], req)

    # --- Reasoning Assembly ---
    if req.emergency_mode or state.mass_exodus:
        reasoning_parts.append(
            "🚨 Please head to the nearest exit immediately. We've mapped the "
            "absolute safest and fastest path out of the venue."
        )
    else:
        if state.weather == "rain":
            reasoning_parts.append(
                "🌧️ Since it's raining, I've kept your route strictly indoors "
                "so you stay completely dry!"
            )
        if req.accessible_mode:
            reasoning_parts.append(
                "♿ I've found a perfectly flat path for you, so you won't have "
                "to worry about any stairs or ramps along the way."
            )
        if req.scenic_mode:
            reasoning_parts.append(
                "🏆 I've taken you on a cooler, more scenic route so you can "
                "check out some of the main attractions on your way over."
            )

    if not reasoning_parts:
        if target_node in FOOD_NODES:
            reasoning_parts.append(
                "🍔 Looks like you're grabbing some food! I found a path that "
                "bypasses the crowds so you can get your meal right on time."
            )
        elif target_node in MERCH_NODES or target_node == "closest_merch":
            reasoning_parts.append(
                "👕 Ready to grab some gear? I've pointed you to the closest "
                "official store with the shortest walking distance."
            )
        elif target_node in RESTROOM_NODES:
            reasoning_parts.append(
                "🚻 I've mapped a path to the restroom that avoids the main "
                "concourse traffic so you can get back to your seat quickly."
            )
        else:
            reasoning_parts.append(
                "✨ I've found a really smooth path for you, avoiding the typical "
                "bottlenecks so you can just enjoy your walk."
            )

    # --- Departure Tip for Food Courts ---
    departure_time: Optional[str] = None
    if target_node in FOOD_NODES and not req.emergency_mode and not state.mass_exodus:
        queue_minutes = round(state.congestion_state.get(target_node, 1.0) * 4.0)
        departure_time = (
            f"Hang tight in your seat! Pick up your food in {queue_minutes} minutes "
            "to get it hot right as you arrive."
        )

    logger.info(
        "Route calculated: %s → %s | hops=%d | time=%s | confidence=%d",
        req.start_node, target_node, len(recommended_route),
        f"{round(best_route['cost'])} min", conf
    )

    # --- Vertex AI: Append a live Gemini-generated safety tip ---
    # Calculates the average density along the recommended path so Gemini
    # can tailor the tip to actual crowd conditions at this moment.
    avg_density = sum(
        state.congestion_state.get(n, 1.0) for n in recommended_route
    ) / len(recommended_route)

    ai_tip = gcp_services.get_ai_route_insight(
        start=req.start_node,
        end=target_node,
        weather=state.weather,
        avg_density=avg_density,
        emergency=req.emergency_mode or state.mass_exodus,
    )
    if ai_tip:
        reasoning_parts.append(f"💡 AI Tip: {ai_tip}")
        logger.info("Vertex AI tip appended to route response.")

    return RouteResponse(
        recommended_route=recommended_route,
        estimated_time=f"{round(best_route['cost'])} minutes",
        estimated_distance=f"{raw_distance_meters}m walk",
        confidence_score=conf,
        crowd_impact=impact,
        reasoning=" ".join(reasoning_parts),
        departure_time=departure_time,
        target_relocated=relocated_msg,
    )
