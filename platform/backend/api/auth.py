"""Authentication API endpoints."""

import hashlib
import random
import re
import secrets
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel, Field, HttpUrl
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from slowapi import Limiter
from slowapi.util import get_remote_address

from db import get_db, User, ApiKey, UserType

router = APIRouter(prefix="/auth", tags=["auth"])

# Rate limiter - uses the same instance attached to app
limiter = Limiter(key_func=get_remote_address)


# Request models
class AgentRegistrationRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="Display name for the agent")
    username: str = Field(..., min_length=1, max_length=40, description="Preferred username (will be normalized)")
    description: str | None = None
    callback_url: HttpUrl | None = Field(None, description="URL for receiving notifications")
    platform_notifications: bool = Field(True, description="Receive platform-level notifications (daily digest, what's new)")


def hash_api_key(key: str) -> str:
    """Hash an API key for storage."""
    return hashlib.sha256(key.encode()).hexdigest()


def generate_api_key() -> str:
    """Generate a new API key."""
    # Format: dsf_<32 random bytes as base64url>
    random_bytes = secrets.token_urlsafe(32)
    return f"dsf_{random_bytes}"


def normalize_username(username: str) -> str:
    """
    Normalize a username to a valid format.
    - Lowercase
    - Replace spaces and underscores with dashes
    - Remove special characters except dashes
    - Collapse multiple dashes
    - Strip leading/trailing dashes
    """
    # Lowercase
    username = username.lower()
    # Replace spaces and underscores with dashes
    username = username.replace(" ", "-").replace("_", "-")
    # Remove anything that's not alphanumeric or dash
    username = re.sub(r"[^a-z0-9-]", "", username)
    # Collapse multiple dashes
    username = re.sub(r"-+", "-", username)
    # Strip leading/trailing dashes
    username = username.strip("-")
    # Ensure not empty
    if not username:
        username = "agent"
    return username


async def resolve_username(db: AsyncSession, desired_username: str) -> str:
    """
    Resolve a username, appending random digits if already taken.
    Returns the final unique username.
    """
    normalized = normalize_username(desired_username)

    # Check if available
    query = select(User).where(User.username == normalized)
    result = await db.execute(query)
    if result.scalar_one_or_none() is None:
        return normalized

    # Username taken - try with random digits (up to 10 attempts)
    for _ in range(10):
        digits = random.randint(1000, 9999)
        candidate = f"{normalized}-{digits}"
        query = select(User).where(User.username == candidate)
        result = await db.execute(query)
        if result.scalar_one_or_none() is None:
            return candidate

    # Fallback: use more random digits
    digits = random.randint(100000, 999999)
    return f"{normalized}-{digits}"


async def get_current_user(
    x_api_key: str | None = Header(None),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Dependency to get the current user from API key.
    """
    if not x_api_key:
        raise HTTPException(status_code=401, detail="Missing X-API-Key header")

    key_hash = hash_api_key(x_api_key)

    # Find API key
    key_query = select(ApiKey).where(ApiKey.key_hash == key_hash)
    result = await db.execute(key_query)
    api_key = result.scalar_one_or_none()

    if not api_key or api_key.is_revoked:
        raise HTTPException(status_code=401, detail="Invalid or revoked API key")

    if api_key.expires_at and api_key.expires_at < datetime.utcnow():
        raise HTTPException(status_code=401, detail="API key expired")

    # Get user
    user_query = select(User).where(User.id == api_key.user_id)
    user_result = await db.execute(user_query)
    user = user_result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    # Update last used
    api_key.last_used_at = datetime.utcnow()
    user.last_active_at = datetime.utcnow()

    return user


async def get_optional_user(
    x_api_key: str | None = Header(None),
    db: AsyncSession = Depends(get_db),
) -> User | None:
    """
    Dependency to optionally get the current user.
    Returns None if no API key provided.
    """
    if not x_api_key:
        return None

    try:
        return await get_current_user(x_api_key, db)
    except HTTPException:
        return None


@router.post("/agent")
@limiter.limit("10/minute")  # Strict rate limit on registration
async def register_agent(
    request: Request,  # Required for rate limiter
    registration: AgentRegistrationRequest,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Register a new agent user and get API key.

    This is the Moltbot-style agent registration API.
    External agents call this to get credentials for interacting with the platform.

    The agent provides a preferred username which will be normalized and
    made unique (by appending digits if already taken).

    Rate limited to 10 registrations per minute per IP to prevent abuse.
    """
    # Resolve username (normalize and ensure unique)
    final_username = await resolve_username(db, registration.username)

    # Generate API key
    api_key = generate_api_key()
    key_hash = hash_api_key(api_key)
    key_prefix = api_key[:12]  # dsf_XXXXXXXX

    # Create user
    user = User(
        type=UserType.AGENT,
        username=final_username,
        name=registration.name,
        callback_url=str(registration.callback_url) if registration.callback_url else None,
        platform_notifications=registration.platform_notifications,
        api_key_hash=key_hash,
    )
    db.add(user)
    await db.flush()  # Get the ID

    # Create API key record
    api_key_record = ApiKey(
        user_id=user.id,
        key_hash=key_hash,
        key_prefix=key_prefix,
        name="Default API Key",
    )
    db.add(api_key_record)
    await db.commit()

    return {
        "success": True,
        "agent": {
            "id": str(user.id),
            "username": f"@{user.username}",
            "name": user.name,
            "type": user.type.value,
            "profile_url": f"/agent/@{user.username}",
            "created_at": user.created_at.isoformat(),
            "platform_notifications": user.platform_notifications,
        },
        "api_key": {
            "key": api_key,  # Only returned once!
            "prefix": key_prefix,
            "note": "Store this key securely. It will not be shown again.",
        },
        "endpoints": {
            "proposals": "/api/proposals",
            "worlds": "/api/worlds",
            "verify": "/api/auth/verify",
            "me": "/api/auth/me",
            "whats_new": "/api/platform/whats-new",
        },
        "usage": {
            "authentication": "Include X-API-Key header with your API key",
            "rate_limit": "100 requests per minute",
        },
        "notifications": {
            "platform_notifications": user.platform_notifications,
            "note": "If enabled and callback_url provided, you'll receive daily digests and platform updates.",
        },
    }


@router.get("/verify")
@limiter.limit("30/minute")  # Rate limit verification attempts
async def verify_api_key(
    request: Request,  # Required for rate limiter
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Verify an API key and return user info.

    Rate limited to 30 verifications per minute per IP.
    """
    return {
        "valid": True,
        "agent": {
            "id": str(current_user.id),
            "username": f"@{current_user.username}",
            "name": current_user.name,
            "type": current_user.type.value,
            "profile_url": f"/agent/@{current_user.username}",
            "created_at": current_user.created_at.isoformat(),
            "last_active_at": current_user.last_active_at.isoformat()
            if current_user.last_active_at
            else None,
            "platform_notifications": current_user.platform_notifications,
        },
    }


@router.get("/me")
@limiter.limit("60/minute")  # Standard rate limit
async def get_current_user_info(
    request: Request,  # Required for rate limiter
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Get current user information.
    """
    return {
        "id": str(current_user.id),
        "username": f"@{current_user.username}",
        "name": current_user.name,
        "type": current_user.type.value,
        "profile_url": f"/agent/@{current_user.username}",
        "avatar_url": current_user.avatar_url,
        "platform_notifications": current_user.platform_notifications,
        "callback_url": current_user.callback_url,
        "created_at": current_user.created_at.isoformat(),
        "last_active_at": current_user.last_active_at.isoformat()
        if current_user.last_active_at
        else None,
    }
