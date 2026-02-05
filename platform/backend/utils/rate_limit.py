"""Rate limiting utilities.

Provides auth-aware rate limiters for API endpoints.
"""

from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address


def get_auth_key(request: Request) -> str:
    """Get rate limit key from API key header, falling back to IP address.

    For authenticated endpoints, we want to rate limit per-agent (API key)
    rather than per-IP. This prevents a single agent from bypassing limits
    by using multiple IPs, and allows multiple agents behind the same IP
    to each have their own limits.

    Uses first 16 chars of API key as the key to avoid storing full keys.
    Falls back to IP address for unauthenticated requests.
    """
    api_key = request.headers.get("X-API-Key", "")
    if api_key:
        # Use first 16 chars as rate limit key (enough to be unique, not full key)
        return f"auth:{api_key[:16]}"
    return get_remote_address(request)


# Auth-aware rate limiter - use for authenticated endpoints
limiter_auth = Limiter(key_func=get_auth_key)

# Standard IP-based rate limiter - use for public endpoints
limiter_ip = Limiter(key_func=get_remote_address)
