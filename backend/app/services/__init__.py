"""Service layer for the backend application."""

from .event_service import create_event
from .deduplication import find_duplicate_road_issue

__all__ = ["create_event", "find_duplicate_road_issue"]
