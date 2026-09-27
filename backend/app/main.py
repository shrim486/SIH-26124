from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import (
    auth,
    events,
    government,
    routes,
    traffic,
    user,
    video_analysis,
    analysis_results,
    operations,
    camera_live,
)


@asynccontextmanager
async def lifespan(app):
    from app.db.database import Base, engine, ensure_sqlite_schema_compatibility
    from app import models
    Base.metadata.create_all(bind=engine)
    ensure_sqlite_schema_compatibility()
    yield


app = FastAPI(
    title="UrbanIQ API",
    description="Urban Intelligence Platform API",
    version="1.0.0",
    lifespan=lifespan,
)


@app.middleware('http')
async def private_response_headers(request, call_next):
    response = await call_next(request)
    if request.url.path.startswith(('/api/v1/government', '/api/v1/video-analysis', '/api/v1/events')):
        response.headers['Cache-Control'] = 'private, no-store'
        response.headers['Pragma'] = 'no-cache'
        response.headers['X-Content-Type-Options'] = 'nosniff'
    return response


# ============================================================
# CORS
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:5175",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
        "http://127.0.0.1:5175",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=['X-Captured-At', 'X-Received-At', 'X-Frame-Processing'],
)

# ============================================================
# API ROUTES
# ============================================================

API_PREFIX = "/api/v1"

app.include_router(
    auth.router,
    prefix=API_PREFIX,
)

app.include_router(
    events.router,
    prefix=API_PREFIX,
)

app.include_router(
    government.router,
    prefix=API_PREFIX,
)

app.include_router(
    routes.router,
    prefix=API_PREFIX,
)

app.include_router(
    traffic.router,
    prefix=API_PREFIX,
)

app.include_router(
    user.router,
    prefix=API_PREFIX,
)

app.include_router(
    video_analysis.router,
    prefix=API_PREFIX,
)
app.include_router(analysis_results.router, prefix=API_PREFIX)
app.include_router(operations.router, prefix=API_PREFIX)
app.include_router(camera_live.router, prefix=API_PREFIX)


# ============================================================
# ROOT / HEALTH
# ============================================================

@app.get("/")
def root():
    return {
        "message": "UrbanIQ API is running",
        "status": "online",
    }


@app.get("/health")
def health():
    return {
        "status": "healthy",
    }
