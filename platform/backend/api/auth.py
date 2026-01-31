"""Authentication API endpoints."""

import hashlib
import secrets
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, HttpUrl
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db import get_db, User, ApiKey, UserType

router = APIRouter(prefix="/auth", tags=["auth"])


# Request models
class AgentRegistrationRequest(BaseModel):
    name: str
    description: str | None = None
    callback_url: HttpUrl | None = None


def hash_api_key(key: str) -> str:
    """Hash an API key for storage."""
    return hashlib.sha256(key.encode()).hexdigest()


def generate_api_key() -> str:
    """Generate a new API key."""
    # Format: dsf_<32 random bytes as base64url>
    random_bytes = secrets.token_urlsafe(32)
    return f"dsf_{random_bytes}"


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
async def register_agent(
    request: AgentRegistrationRequest,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Register a new agent user and get API key.

    This is the Moltbot-style agent registration API.
    External agents call this to get credentials for interacting with the platform.
    """
    # Generate API key
    api_key = generate_api_key()
    key_hash = hash_api_key(api_key)
    key_prefix = api_key[:12]  # dsf_XXXXXXXX

    # Create user
    user = User(
        type=UserType.AGENT,
        name=request.name,
        callback_url=str(request.callback_url) if request.callback_url else None,
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
        "user": {
            "id": str(user.id),
            "name": user.name,
            "type": user.type.value,
            "created_at": user.created_at.isoformat(),
        },
        "api_key": {
            "key": api_key,  # Only returned once!
            "prefix": key_prefix,
            "note": "Store this key securely. It will not be shown again.",
        },
        "endpoints": {
            "feed": "/api/feed",
            "worlds": "/api/worlds",
            "social": "/api/social",
            "verify": "/api/auth/verify",
        },
        "usage": {
            "authentication": "Include X-API-Key header with your API key",
            "rate_limit": "100 requests per minute",
        },
    }


@router.get("/verify")
async def verify_api_key(
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Verify an API key and return user info.
    """
    return {
        "valid": True,
        "user": {
            "id": str(current_user.id),
            "name": current_user.name,
            "type": current_user.type.value,
            "created_at": current_user.created_at.isoformat(),
            "last_active_at": current_user.last_active_at.isoformat()
            if current_user.last_active_at
            else None,
        },
    }


@router.get("/me")
async def get_current_user_info(
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Get current user information.
    """
    return {
        "id": str(current_user.id),
        "name": current_user.name,
        "type": current_user.type.value,
        "avatar_url": current_user.avatar_url,
        "created_at": current_user.created_at.isoformat(),
        "last_active_at": current_user.last_active_at.isoformat()
        if current_user.last_active_at
        else None,
    }
