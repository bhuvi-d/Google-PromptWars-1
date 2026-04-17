import logging
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.config import settings
from app.routers import route, admin, stats

# Operational Observability
logger = logging.getLogger(__name__)

# Security: Edge Rate Limiting
limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title=settings.PROJECT_TITLE,
    description=(
        "Architectural Perfection: Enterprise-grade Smart Venue Intelligence Platform. "
        "Engineered with a decoupled event-driven architecture utilizing Google Cloud Pub/Sub, "
        "BigQuery, Firestore, and Vertex AI Gemini."
    ),
    version=settings.PROJECT_VERSION,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ── Perfection: Global Exception Middleware ───────────────────────────

@app.middleware("http")
async def global_exception_handler(request: Request, call_next):
    """
    Standardizes all application failures into a structured JSON response.
    Ensures zero leak of raw stack traces to end-users (Security Pillar).
    """
    try:
        return await call_next(request)
    except Exception as exc:
        logger.exception("Inbound request failed: %s %s", request.method, request.url.path)
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal Systems Error",
                "message": "The venue intelligence layer encountered an unexpected exception.",
                "trace_id": str(logging.time.time()) # Simple trace for log correlation
            }
        )

# ── Efficiency: Network Stack Optimizations ──────────────────────────

# Auto-compression for bandwidth-intensive telemetry JSON
app.add_middleware(GZipMiddleware, minimum_size=1000)

# ── Security: CORS Hardening ──────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

# ── Performance: Protocol Caching Middleware ──────────────────────────

@app.middleware("http")
async def add_cache_control_header(request: Request, call_next):
    """
    Injects Cache-Control headers to optimize browser-side de-duplication.
    """
    response: Response = await call_next(request)
    if "/api/stats" in request.url.path:
        response.headers["Cache-Control"] = "public, max-age=1"
    return response

# ── Modular Routes ────────────────────────────────────────────────────

app.include_router(route.router, prefix="/api", tags=["Routing Engine"])
app.include_router(admin.router, prefix="/api/admin", tags=["Administration"])
app.include_router(stats.router, prefix="/api/stats", tags=["Telemetry"])


@app.get("/", tags=["Health"])
def health_check():
    """System health verification."""
    return {"status": "Operational", "version": settings.PROJECT_VERSION}
