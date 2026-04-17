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
    Simulates crowd dynamics, weather impacts, and attendance fluctuations.
    """
    # Fluctuate attendance
    diff = random.randint(-15, 25)
    if state.mass_exodus:
        diff -= random.randint(150, 450)
    state.current_attendance = max(0, min(60000, state.current_attendance + diff))

    # Refill safeguard — prevents venue going permanently empty in simulation
    if state.current_attendance == 0 and not state.mass_exodus:
        state.current_attendance = 45000

    heatmap_data = []
    for node in state.congestion_state:
        old_val = state.congestion_state[node]
        state.old_congestion_state[node] = old_val

        if state.mass_exodus and node in EXIT_NODES:
            # Rapid fill during exodus
            state.congestion_state[node] = min(3.0, state.congestion_state[node] + 0.1)
        else:
            state.congestion_state[node] += random.uniform(-0.1, 0.1)

        state.congestion_state[node] = max(1.0, min(3.0, state.congestion_state[node]))

        delta = state.congestion_state[node] - old_val
        trend = "Stable ➡️"
        if delta > 0.03:
            trend = "Filling ⬆️"
        elif delta < -0.03:
            trend = "Emptying ⬇️"

        people_count = int((state.congestion_state[node] - 0.9) * 2000)

        heatmap_data.append({
            "id": node,
            "density": round(state.congestion_state[node], 2),
            "people": max(0, people_count),
            "trend": trend
        })

    snapshot = {
        "attendance": state.current_attendance,
        "mass_exodus": state.mass_exodus,
        "weather": state.weather,
        "heatmap": heatmap_data
    }

    # Live Publish: Firestore for real-time client state synchronization
    gcp_services.publish_telemetry("stats_tick", snapshot)

    return snapshot


@router.get("", summary="Poll venue telemetry")
async def get_stats_polling(background_tasks: BackgroundTasks):
    """
    HTTP Poll: Returns a snapshot and triggers a background BigQuery analytical log.
    Efficiently offloads durable logging to background tasks to maintain 
    low-latency responses.
    """
    snapshot = process_stats_tick()
    # Efficiency win: Using BackgroundTasks ensures API response is not 
    # blocked by BigQuery IO.
    background_tasks.add_task(gcp_services.log_telemetry_batch, snapshot)
    return snapshot


@router.get("/stream", summary="SSE telemetry stream")
async def stream_stats(background_tasks: BackgroundTasks):
    """
    SSE Stream: Continuous telemetry feed with background analytics streaming.
    """
    async def event_generator():
        while True:
            snapshot = process_stats_tick()
            # Log to BigQuery in background on every tick for historical analytics
            background_tasks.add_task(gcp_services.log_telemetry_batch, snapshot)
            yield f"data: {json.dumps(snapshot)}\n\n"
            await asyncio.sleep(2.0)

    return StreamingResponse(event_generator(), media_type="text/event-stream")
