from .feed import router as feed_router
from .worlds import router as worlds_router
from .social import router as social_router
from .auth import router as auth_router
from .agents import router as agents_router
from .proposals import router as proposals_router

__all__ = [
    "feed_router",
    "worlds_router",
    "social_router",
    "auth_router",
    "agents_router",
    "proposals_router",
]
