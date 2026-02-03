from .feed import router as feed_router
from .worlds import router as worlds_router
from .social import router as social_router
from .auth import router as auth_router
from .proposals import router as proposals_router
from .dwellers import router as dwellers_router
from .aspects import router as aspects_router
from .agents import router as agents_router
from .platform import router as platform_router
from .suggestions import router as suggestions_router
from .events import router as events_router
from .actions import router as actions_router
from .notifications import router as notifications_router

__all__ = [
    "feed_router",
    "worlds_router",
    "social_router",
    "auth_router",
    "proposals_router",
    "dwellers_router",
    "aspects_router",
    "agents_router",
    "platform_router",
    "suggestions_router",
    "events_router",
    "actions_router",
    "notifications_router",
]
