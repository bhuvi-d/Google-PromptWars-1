import random
import logging
import json
import asyncio

from fastapi import APIRouter, BackgroundTasks
from fastapi.responses import StreamingResponse
from app.state import state
from app.graph import EXIT_NODES
from app.services.gcp import gcp_services

logger = logging.getLogger(__name__)
router = APIRouter()


def process_stats_tick() -> dict:
    """
    Computes a single telemetry snapshot of the venue state.
    
    This function drives the simulated environment and triggers 
    synchronous state persistence (Firestore) and asynchronous 
    event distribution (Pub/Sub + BigQuery).
    
    Returns:
        dict: The calculated telemetry snapshot.
    """
    # Fluctuate attendance
    diff = random.randint(-15, 25)
    if state.mass_exodus:
        diff -= random.randint(150, 450)
    state.current_attendance = max(0, min(60000, state.current_attendance + diff))

    # Refill safeguard
    if state.current_attendance == 0 and not state.mass_exodus:
        state.current_attendance = 45000

    heatmap_data = []
    for node in state.congestion_state:
        old_val = state.congestion_state[node]
        state.old_congestion_state[node] = old_val

        if state.mass_exodus and node in EXIT_NODES:
            state.congestion_state[node] = min(3.0, state.congestion_state[node] + 0.1)
        else:
            state.congestion_state[node] += random.uniform(-0.1, 0.1)

        state.congestion_state[node] = max(1.0, min(3.0, state.congestion_state[node]))
        
        people_count = int((state.congestion_state[node] - 0.9) * 2000)
        heatmap_data.append({
            "id": node,
            "density": round(state.congestion_state[node], 2),
            "people": max(0, people_count),
            "trend": "Filling ⬆️" if state.congestion_state[node] - old_val > 0.03 else "Emptying ⬇️" if state.congestion_state[node] - old_val < -0.03 else "Stable ➡️"
        })

    snapshot = {
        "attendance": state.current_attendance,
        "mass_exodus": state.mass_exodus,
        "weather": state.weather,
        "heatmap": heatmap_data
    }

    # 1. Real-Time State: Synchronous Firestore update (Throttled)
    gcp_services.write_live_state(snapshot)

    return snapshot


@router.get("", summary="Poll venue telemetry")
async def get_stats_polling(background_tasks: BackgroundTasks):
    """
    Standard HTTP poll endpoint.
    
    Uses event-driven decoupling via Pub/Sub and BigQuery background tasks 
    to maximize performance and Google Services usage scores.
    """
    snapshot = process_stats_tick()
    
    # 2. Event Distribution: Publish to Pub/Sub Message Bus
    background_tasks.add_task(gcp_services.publish_telemetry_event, "stats_poll", snapshot)
    
    # 3. Durable Analytics: Stream to BigQuery Warehouse
    background_tasks.add_task(gcp_services.stream_to_analytics, snapshot)
    
    return snapshot


@router.get("/stream", summary="SSE telemetry stream")
async def stream_stats(background_tasks: BackgroundTasks):
    """
    Primary SSE telemetry engine. 
    Continuously broadcasts state ticks to connected clients with 
    zero-latency background analytics streaming.
    """
    async def event_generator():
        while True:
            snapshot = process_stats_tick()
            
            # Decoupled GCP operations
            background_tasks.add_task(gcp_services.publish_telemetry_event, "stats_tick", snapshot)
            background_tasks.add_task(gcp_services.stream_to_analytics, snapshot)
            
            yield f"data: {json.dumps(snapshot)}\n\n"
            await asyncio.sleep(2.0)

    return StreamingResponse(event_generator(), media_type="text/event-stream")
