"""Re-export request dependencies for routers."""
from app.deps import facts, get_db, jobs, location_views, meetings, people, projects

__all__ = [
    "facts",
    "get_db",
    "jobs",
    "location_views",
    "meetings",
    "people",
    "projects",
]
