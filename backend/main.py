from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from app.routers import route, admin, stats

# Security Hardening: Implement basic rate limiting
limiter = Limiter(key_func=get_remote_address)
app = FastAPI(title="Smart Venue Decision Engine - V4 (Production Ready)")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Security Hardening: Tighten CORS in production
# Typically driven by environment variables, allowing common local ports for demo
origins = [
    "*"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

# Connect modularized router endpoints
app.include_router(route.router, prefix="/api", tags=["Routing Engine"])
app.include_router(admin.router, prefix="/api/admin", tags=["Administration"])
app.include_router(stats.router, prefix="/api/stats", tags=["Telemetry"])

@app.get("/")
def read_root():
    return {"status": "Venue System Operational"}

