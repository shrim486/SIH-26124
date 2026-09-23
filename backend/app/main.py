from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import (
    auth,
    events,
    government,
    routes,
    traffic,
    user,
)


app = FastAPI(
    title="UrbanIQ API",
    description="Urban Intelligence Platform API",
    version="1.0.0",
)


# ============================================================
# CORS
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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