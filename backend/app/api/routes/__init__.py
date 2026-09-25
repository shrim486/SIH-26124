from .auth import router as auth_router
from .events import router as events_router
from .government import router as government_router
from .routes import router as routes_router
from .traffic import router as traffic_router
from .user import router as user_router


__all__ = [
    "auth_router",
    "events_router",
    "government_router",
    "routes_router",
    "traffic_router",
    "user_router",
]