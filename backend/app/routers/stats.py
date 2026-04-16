import random
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
import asyncio
import json
from app.state import state
from app.graph import EXIT_NODES

router = APIRouter()

def process_stats_tick():
    # Fluctuate attendance
    diff = random.randint(-15, 25)
    if state.mass_exodus: 
        diff -= random.randint(150, 450)
    state.current_attendance = max(0, state.current_attendance + diff)
    state.current_attendance = min(60000, state.current_attendance) 
    
    heatmap_data = []
    
    for node in state.congestion_state:
        old_val = state.congestion_state[node]
        state.old_congestion_state[node] = old_val
        
        if state.current_attendance == 0 and not state.mass_exodus:
            state.current_attendance = 45000 # Refill simulation
             
        if state.mass_exodus and node in EXIT_NODES:
            state.congestion_state[node] = min(3.0, state.congestion_state[node] + 0.1)
        else:
            state.congestion_state[node] += random.uniform(-0.1, 0.1)
            
        state.congestion_state[node] = max(1.0, min(3.0, state.congestion_state[node]))
        
        delta = state.congestion_state[node] - old_val
        trend = "Stable ➡️"
        if delta > 0.03: trend = "Filling ⬆️"
        elif delta < -0.03: trend = "Emptying ⬇️"
        
        people_count = int((state.congestion_state[node] - 0.9) * 2000)
        
        heatmap_data.append({
            "id": node, 
            "density": round(state.congestion_state[node], 2),
            "people": max(0, people_count),
            "trend": trend
        })
        
    return {
        "attendance": state.current_attendance,
        "mass_exodus": state.mass_exodus,
        "heatmap": heatmap_data
    }

@router.get("")
async def get_stats_polling():
    """Fallback HTTP endpoint for polling."""
    return process_stats_tick()

@router.get("/stream")
async def stream_stats():
    """
    Server-Sent Events (SSE) endpoint for realtime telemetry.
    Radically reduces HTTP overhead during massive connections.
    """
    async def event_generator():
        while True:
            data = process_stats_tick()
            yield f"data: {json.dumps(data)}\n\n"
            await asyncio.sleep(2.0)
            
    return StreamingResponse(event_generator(), media_type="text/event-stream")
