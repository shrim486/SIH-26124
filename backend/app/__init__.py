"""Application package for the backend."""

__all__ = ["create_app"]


def create_app():
    from fastapi import FastAPI
    from .api.routes import events_router, government_router, user_router

    app = FastAPI(title="SIH Backend")
    app.include_router(events_router)
    app.include_router(government_router)
    app.include_router(user_router)
    return app
