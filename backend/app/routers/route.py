from fastapi import APIRouter, Depends, Request
from app.models import RouteRequest, RouteResponse
from app.decision_engine import calculate_best_route
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/route", response_model=RouteResponse)
async def get_route(request: Request, req: RouteRequest):
    # Depending on rate limiting middleware in main.py, this will be protected for 10req/sec
    try:
        response = calculate_best_route(req)
        return response
    except ValueError as e:
        # Handled error like path impossible
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Routing algorithm failure: {e}")
        from fastapi import HTTPException
        raise HTTPException(status_code=500, detail="Internal Server Error during pathfinding calculations.")
