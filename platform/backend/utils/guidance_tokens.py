"""JWT utilities for story writing guidance token enforcement."""

import base64
import hashlib
import hmac
import json
import os
from datetime import timedelta
from typing import Any
from uuid import uuid4

from utils.clock import now as utc_now

TOKEN_TTL_MINUTES = 10


class GuidanceTokenError(Exception):
    """Base exception for guidance token failures."""


class GuidanceTokenInvalidError(GuidanceTokenError):
    """Token is malformed or signature validation failed."""


class GuidanceTokenExpiredError(GuidanceTokenError):
    """Token has expired."""


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def _guidance_token_secret() -> bytes:
    secret = os.getenv("GUIDANCE_TOKEN_SECRET")
    if secret:
        return secret.encode("utf-8")

    if os.getenv("TESTING", "").lower() == "true":
        return b"test-guidance-token-secret"

    raise RuntimeError("GUIDANCE_TOKEN_SECRET is required for guidance token signing")


def hash_guidance_token(token: str) -> str:
    """Return SHA256 hash of a raw guidance token."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_guidance_token(guidance_version: str) -> str:
    """Create a signed short-lived JWT proving guidance access."""
    now = utc_now()
    payload = {
        "guidance_version": guidance_version,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=TOKEN_TTL_MINUTES)).timestamp()),
        "jti": str(uuid4()),
    }
    header = {"alg": "HS256", "typ": "JWT"}

    encoded_header = _b64url_encode(
        json.dumps(header, separators=(",", ":"), sort_keys=True).encode("utf-8")
    )
    encoded_payload = _b64url_encode(
        json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    )
    signing_input = f"{encoded_header}.{encoded_payload}"
    signature = hmac.new(
        _guidance_token_secret(),
        signing_input.encode("ascii"),
        hashlib.sha256,
    ).digest()

    return f"{signing_input}.{_b64url_encode(signature)}"


def validate_guidance_token(token: str) -> dict[str, Any]:
    """Validate token signature/expiry and return token payload."""
    if not token:
        raise GuidanceTokenInvalidError("Invalid token")

    parts = token.split(".")
    if len(parts) != 3:
        raise GuidanceTokenInvalidError("Invalid token")

    encoded_header, encoded_payload, encoded_signature = parts
    signing_input = f"{encoded_header}.{encoded_payload}"

    try:
        header = json.loads(_b64url_decode(encoded_header))
        payload = json.loads(_b64url_decode(encoded_payload))
        signature = _b64url_decode(encoded_signature)
    except Exception as exc:
        raise GuidanceTokenInvalidError("Invalid token") from exc

    if not isinstance(header, dict) or header.get("alg") != "HS256":
        raise GuidanceTokenInvalidError("Invalid token")
    if not isinstance(payload, dict):
        raise GuidanceTokenInvalidError("Invalid token")

    expected_signature = hmac.new(
        _guidance_token_secret(),
        signing_input.encode("ascii"),
        hashlib.sha256,
    ).digest()
    if not hmac.compare_digest(signature, expected_signature):
        raise GuidanceTokenInvalidError("Invalid token")

    exp = payload.get("exp")
    if not isinstance(exp, (int, float)):
        raise GuidanceTokenInvalidError("Invalid token")

    now_ts = int(utc_now().timestamp())
    if now_ts >= int(exp):
        raise GuidanceTokenExpiredError("Token expired")

    guidance_version = payload.get("guidance_version")
    jti = payload.get("jti")
    iat = payload.get("iat")
    if not isinstance(guidance_version, str) or not guidance_version:
        raise GuidanceTokenInvalidError("Invalid token")
    if not isinstance(jti, str) or not jti:
        raise GuidanceTokenInvalidError("Invalid token")
    if not isinstance(iat, (int, float)):
        raise GuidanceTokenInvalidError("Invalid token")

    return payload
