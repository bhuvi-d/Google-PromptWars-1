from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.config import settings
from app.routers import route, admin, stats

# Security: API-level rate limiting
limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title=settings.PROJECT_TITLE,
    description=(
        "Advanced AI-powered Smart Venue Intelligence Platform. "
        "Engineered with a multi-service Google Cloud architecture: "
        "Firestore (Live State), BigQuery (Analytical History), "
        "Vertex AI Gemini (Decision Intelligence), and Cloud Logging."
    ),
    version=settings.PROJECT_VERSION,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Efficiency: Gzip Compression for reduced network overhead
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Security: Cross-Origin Resource Sharing
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

# Efficiency: Simple Middleware to inject Cache-Control headers for telemetry
@app.middleware("http")
async def add_cache_control_header(request: Request, call_next):
    response: Response = await call_next(request)
    if request.url.path.startswith("/api/stats"):
        # Telemetry is highly dynamic, but 1s cache helps de-duplicate rapid polling
        response.headers["Cache-Control"] = "public, max-age=1"
    return response

# Modular router registration
app.include_router(route.router, prefix="/api", tags=["Routing Engine"])
app.include_router(admin.router, prefix="/api/admin", tags=["Administration"])
app.include_router(stats.router, prefix="/api/stats", tags=["Telemetry"])


@app.get("/", tags=["Health"])
def read_root():
    return {"status": "Venue System Operational", "version": settings.PROJECT_VERSION}
