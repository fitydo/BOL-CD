"""
BOL-CD Condensed Alert API Main Application
"""
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from contextlib import asynccontextmanager
import time
import logging
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

from src.bolcd.db import init_db
from src.bolcd.api.v1.alerts import router as alerts_router
from src.bolcd.api.v1.ingest import router as ingest_router
from src.bolcd.metrics.condense_metrics import api_request_duration

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    logger.info("Starting BOL-CD Condensed Alert API...")
    init_db()
    logger.info("Database initialized")
    
    yield
    
    # Shutdown
    logger.info("Shutting down BOL-CD API...")

# Create FastAPI app
app = FastAPI(
    title="BOL-CD Condensed Alert API",
    description="Alert suppression with false suppression validation and late replay",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Middleware for request timing
@app.middleware("http")
async def add_metrics(request: Request, call_next):
    """Add request metrics"""
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time
    
    # Record metrics
    api_request_duration.labels(
        endpoint=request.url.path,
        method=request.method,
        status=response.status_code
    ).observe(duration)
    
    # Add response headers
    response.headers["X-Process-Time"] = str(duration)
    return response

# Health check
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "bolcd-condensed-api",
        "version": "1.0.0"
    }

# Metrics endpoint
@app.get("/metrics", response_class=PlainTextResponse)
async def metrics():
    """Prometheus metrics endpoint"""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

# Include routers
app.include_router(alerts_router)
app.include_router(ingest_router)

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "service": "BOL-CD Condensed Alert API",
        "version": "1.0.0",
        "endpoints": {
            "alerts": "/v1/alerts",
            "late_replay": "/v1/alerts/late",
            "explain": "/v1/alerts/{alert_id}/explain",
            "stats": "/v1/alerts/stats",
            "ingest": "/v1/ingest",
            "health": "/health",
            "metrics": "/metrics",
            "docs": "/docs"
        },
        "features": [
            "Alert suppression with edge-based rules",
            "False suppression validation",
            "Late replay for important suppressed alerts",
            "API key authentication with scoped access",
            "Prometheus metrics",
            "Full audit trail"
        ]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
