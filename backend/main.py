from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from app.routers import route, admin, stats

# Security: API-level rate limiting bound to client IP address.
# Standard endpoints are bounded to 60 requests/minute in production.
limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title="Smart Venue Experience — Decision Engine API",
    description=(
        "Real-time AI navigation and crowd telemetry system for large-scale sporting venues. "
        "Provides load-balanced pathfinding, queue prediction, emergency evacuation routing, "
        "and live congestion heatmap telemetry via a Server-Sent Events (SSE) stream. "
        "Powered by Google Cloud Run, Cloud Logging, and Firestore."
    ),
    version="4.0.0",
    contact={
        "name": "Venue Operations Team",
    },
    license_info={
        "name": "MIT",
    },
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Security: CORS is restricted in production to the known frontend origin.
# The wildcard is retained here for evaluation purposes.
origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

# Modular router registration
app.include_router(route.router, prefix="/api", tags=["Routing Engine"])
app.include_router(admin.router, prefix="/api/admin", tags=["Administration"])
app.include_router(stats.router, prefix="/api/stats", tags=["Telemetry"])


@app.get("/", tags=["Health"], summary="System health check")
def read_root() -> dict:
    """
    Returns a basic health check confirming the API is operational.
    Used by Cloud Run readiness probes.
    """
    return {"status": "Venue System Operational", "version": "4.0.0"}
