import random
from typing import Dict
from app.graph import VENUE_GRAPH

class SystemState:
    def __init__(self):
        self.weather: str = "clear"
        self.mass_exodus: bool = False
        self.current_attendance: int = 48500
        # Congestion float multipliers (1.0 = clear, >2.0 = highly congested)
        self.congestion_state: Dict[str, float] = {node: random.uniform(1.0, 1.2) for node in VENUE_GRAPH}
        self.old_congestion_state: Dict[str, float] = {node: self.congestion_state[node] for node in VENUE_GRAPH}

# Global singleton representing active state 
# (in a production multi-worker setup, this goes to Firestore/Redis)
state = SystemState()
