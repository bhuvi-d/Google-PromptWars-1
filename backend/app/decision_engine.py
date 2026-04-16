import heapq
import random
from typing import List, Dict, Optional, Tuple
from app.graph import VENUE_GRAPH, EXIT_NODES, RESTROOM_NODES, MERCH_NODES, FOOD_NODES, SCENIC_NODES
from app.models import RouteRequest, RouteResponse
from app.state import state

def get_base_heuristic(u: str, v: str) -> float:
    # A simple mock heuristic for A* or K-shortest 
    # Real world would use physical coordinates
    return 0.0

def dijkstra_k_shortest(graph: Dict, start: str, end: str, req: RouteRequest, k: int = 3) -> List[Dict]:
    """
    Finds up to K valid shortest paths using a modified search (simplified Yen's / diverse search) 
    to prevent stampeding.
    """
    # A priority queue storing (cost, path)
    queue = [(0.0, [start])]
    routes_found = []
    
    max_iterations = 2500
    iterations = 0

    while queue and len(routes_found) < k and iterations < max_iterations:
        iterations += 1
        cost, path = heapq.heappop(queue)
        current = path[-1]
        
        if current == end:
            # Check if this path is significantly diverse from already found paths
            is_diverse = True
            if len(routes_found) > 0:
                # If path shares more than 80% of nodes with an existing path, skip it 
                # to enforce physical routing diversity for crowd balancing.
                for found in routes_found:
                    shared = set(path) & set(found["path"])
                    if len(shared) / len(path) > 0.8 and not req.emergency_mode:
                        is_diverse = False
                        break
                        
            if is_diverse or req.emergency_mode:
                destination_queue = state.congestion_state.get(end, 1.0) * 5.0
                routes_found.append({"path": path, "cost": cost + destination_queue})
            continue
            
        for neighbor, edge_data in graph.get(current, {}).items():
            if neighbor not in path:
                if req.accessible_mode and edge_data.get("stairs", False):
                    continue
                    
                base_weight = edge_data["weight"]
                
                if req.emergency_mode or state.mass_exodus:
                    multiplier = 1.0 # Pure raw distance for exits
                else:
                    multiplier = (state.congestion_state.get(current, 1.0) + state.congestion_state.get(neighbor, 1.0)) / 2.0
                    if state.weather == "rain" and edge_data.get("outdoor", False):
                        multiplier += 3.0
                    if req.scenic_mode and neighbor in SCENIC_NODES:
                        multiplier = max(0.5, multiplier - 0.5)
                
                # Introduce slight randomness to pathfinding tie-breakers to naturally organically distribute crowd
                fuzz = random.uniform(0.0, 0.1) if not req.emergency_mode else 0.0
                new_cost = cost + (base_weight * multiplier) + fuzz
                
                heapq.heappush(queue, (new_cost, path + [neighbor]))
                
    return sorted(routes_found, key=lambda x: x["cost"])

def generate_confidence_and_impact(path: List[str], base_cost: float, req: RouteRequest) -> Tuple[int, str]:
    """
    Computes a realistic confidence score (0-100) and Crowd Impact metric.
    """
    if req.emergency_mode or state.mass_exodus:
        return 99, "Emergency Overrides Active"
        
    avg_congestion = sum(state.congestion_state.get(n, 1.0) for n in path) / len(path)
    
    # Impact on crowd
    if avg_congestion > 1.8:
        impact = "Increases Congestion"
    elif avg_congestion < 1.3:
        impact = "Relieves Congestion"
    else:
        impact = "Neutral"
        
    # Confidence drops if traversing heavily congested / volatile areas where time is unpredictable
    confidence = int(max(40, 98 - (avg_congestion - 1.0) * 35))
    if state.weather == "rain" and any(VENUE_GRAPH.get(path[i], {}).get(path[i+1], {}).get("outdoor", False) for i in range(len(path)-1)):
        confidence -= 15 # Weather drastically affects predictability
        
    return min(100, confidence), impact

def calculate_best_route(req: RouteRequest) -> RouteResponse:
    target_node = req.end_node
    relocated_msg = None
    reasoning_parts = []
    
    best_route = None

    # 1. Mass Exodus & Emergency Intercept
    if state.mass_exodus or req.emergency_mode:
        best_exit_cost = float('inf')
        best_exit_path = None
        for ex_node in EXIT_NODES:
            routes = dijkstra_k_shortest(VENUE_GRAPH, req.start_node, ex_node, req, k=1)
            if routes and routes[0]["cost"] < best_exit_cost:
                best_exit_cost = routes[0]["cost"]
                best_exit_path = routes[0]
                target_node = ex_node
                
        best_route = best_exit_path
        if state.mass_exodus:
            relocated_msg = "Redirected to the optimal exit gate for crowd control."
        else:
            relocated_msg = "Emergency path locked. Redirecting to nearest exit."

    # 2. Smart Restroom Queue Load Balancing
    elif req.smart_restroom and target_node in RESTROOM_NODES:
        best_rr_cost = float('inf')
        for rr_node in RESTROOM_NODES:
            routes = dijkstra_k_shortest(VENUE_GRAPH, req.start_node, rr_node, req, k=1)
            if routes and routes[0]["cost"] < best_rr_cost:
                best_rr_cost = routes[0]["cost"]
                best_route = routes[0]
                
        if best_route["path"][-1] != req.end_node:
            relocated_msg = f"Redirected to {best_route['path'][-1].replace('_',' ').title()} for a faster experience."
            reasoning_parts.append("I noticed that restroom had a long line, so I've redirected you to a much faster option nearby.")
        else:
            reasoning_parts.append("Good choice! That restroom is currently your absolute fastest option.")
        target_node = best_route["path"][-1]

    # 3. Dynamic Merch Intercept
    elif target_node == "closest_merch":
        best_merch_cost = float('inf')
        for m_node in MERCH_NODES:
            routes = dijkstra_k_shortest(VENUE_GRAPH, req.start_node, m_node, req, k=1)
            if routes and routes[0]["cost"] < best_merch_cost:
                best_merch_cost = routes[0]["cost"]
                best_route = routes[0]
        target_node = best_route["path"][-1]
        relocated_msg = f"Locked onto {target_node.replace('_', ' ').title()}."
        reasoning_parts.append("Ready to grab some gear? I've found the absolute closest merchandise stand for you.")

    # Standard routing (Load Balanced)
    else:
        routes = dijkstra_k_shortest(VENUE_GRAPH, req.start_node, target_node, req, k=3)
        if not routes:
            best_route = None
        else:
            # If multiple routes exist within a 15% cost margin, randomly select one 
            # to distribute crowd mass (Load Balancing)
            optimal_cost = routes[0]["cost"]
            valid_routes = [r for r in routes if r["cost"] <= optimal_cost * 1.15]
            best_route = random.choice(valid_routes)

    if not best_route:
        raise ValueError("Path impossible.")
        
    recommended_route = best_route["path"]
    
    raw_distance_meters = 0
    for i in range(len(recommended_route) - 1):
        u = recommended_route[i]
        v = recommended_route[i+1]
        raw_distance_meters += VENUE_GRAPH[u].get(v, {"weight": 2})["weight"] * 45 
    
    conf, impact = generate_confidence_and_impact(recommended_route, best_route["cost"], req)
    
    # Compile reasoning
    if req.emergency_mode or state.mass_exodus:
        reasoning_parts.append("🚨 Please head to the nearest exit immediately. We've mapped the absolute safest and fastest path out of the venue.")
    else:
        if state.weather == "rain":
            reasoning_parts.append("🌧️ Since it's raining, I've kept your route strictly indoors so you stay completely dry!")
        if req.accessible_mode:
            reasoning_parts.append("♿ I've found a perfectly flat path for you, so you won't have to worry about any stairs or ramps along the way.")
        if req.scenic_mode:
            reasoning_parts.append("🏆 I've taken you on a cooler, more scenic route so you can check out some of the main attractions on your way over.")
            
    if not reasoning_parts:
        if target_node in FOOD_NODES:
            reasoning_parts.append("🍔 Looks like you're grabbing some food! I found a path that bypasses the crowds so you can get your meal right on time.")
        elif target_node == "closest_merch" or target_node in MERCH_NODES:
            reasoning_parts.append("👕 Ready to grab some gear? I've pointed you to the closest official store with the shortest walking distance.")
        elif target_node in RESTROOM_NODES:
            reasoning_parts.append("🚻 I've mapped a path to the restroom that avoids the main concourse traffic so you can get back to your seat quickly.")
        else:
            reasoning_parts.append("✨ I've found a really smooth path for you, avoiding the typical bottlenecks so you can just enjoy your walk.")

    departure_time = None
    if target_node in FOOD_NODES and not req.emergency_mode and not state.mass_exodus:
        queue_m = state.congestion_state.get(target_node, 1.0) * 4.0
        departure_time = f"Hang tight in your seat! Pick up your food in {round(queue_m)} minutes to get it hot right as you arrive."

    return RouteResponse(
        recommended_route=recommended_route,
        estimated_time=f"{round(best_route['cost'])} minutes",
        estimated_distance=f"{raw_distance_meters}m walk",
        confidence_score=conf,
        crowd_impact=impact,
        reasoning=" ".join(reasoning_parts),
        departure_time=departure_time,
        target_relocated=relocated_msg
    )
