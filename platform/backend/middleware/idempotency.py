"""Idempotency middleware for safe retries after 502/timeout errors.

Checks X-Idempotency-Key header on POST/PUT/PATCH requests.
If key exists and completed: returns stored response (no re-execution).
If key exists and in-progress: returns 409 Conflict.
If new: executes request, stores response.

Usage (agent):
    X-Idempotency-Key: <uuid>

Generate a new UUID for each unique action. Reuse the same UUID when retrying.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID
from sqlalchemy import select, text

from db import SessionLocal

logger = logging.getLogger(__name__)


class IdempotencyMiddleware:
    """Pure ASGI middleware for idempotent POST/PUT/PATCH requests.

    Only activates when X-Idempotency-Key header is present.
    Sits between auth and route execution.
    """

    MUTATING_METHODS = {"POST", "PUT", "PATCH"}

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        method = scope.get("method", "")
        if method not in self.MUTATING_METHODS:
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        if path in {"/api/actions", "/api/actions/compose"}:
            # Actions endpoints implement custom 24-hour idempotency semantics.
            await self.app(scope, receive, send)
            return

        # Extract idempotency key and API key from headers
        idempotency_key = None
        api_key = None
        for key, value in scope.get("headers", []):
            if key == b"x-idempotency-key":
                idempotency_key = value.decode().strip()
            elif key == b"x-api-key":
                api_key = value.decode()
            elif key == b"authorization":
                auth_value = value.decode()
                if auth_value.lower().startswith("bearer "):
                    api_key = auth_value[7:].strip()

        # No idempotency key? Pass through (backward compatible)
        if not idempotency_key:
            await self.app(scope, receive, send)
            return

        # Require authentication for idempotency
        if not api_key:
            await self._send_error(
                send,
                400,
                {"error": "X-Idempotency-Key requires authentication (X-API-Key or Authorization header)"}
            )
            return

        # Validate UUID format
        try:
            UUID(idempotency_key)
        except ValueError:
            await self._send_error(
                send,
                400,
                {"error": f"Invalid X-Idempotency-Key format. Must be a valid UUID, got: {idempotency_key}"}
            )
            return

        # Get user_id from API key
        user_id = await self._get_user_id_from_api_key(api_key)
        if not user_id:
            await self._send_error(send, 401, {"error": "Invalid API key"})
            return

        # Check for existing idempotency key
        endpoint = path
        existing = await self._get_idempotency_record(idempotency_key)

        if existing:
            # Key exists — check status
            if existing["status"] == "in_progress":
                await self._send_error(
                    send,
                    409,
                    {
                        "error": "Request is being processed",
                        "idempotency_key": idempotency_key,
                        "how_to_fix": "Wait for the original request to complete, then retry with the same key to get the result.",
                    }
                )
                return
            elif existing["status"] == "completed":
                # Return stored response
                await self._send_stored_response(send, existing)
                return
            # If failed, allow retry (fall through to execute)

        # New key or retry after failure — insert in_progress, execute, store result
        await self._insert_in_progress(idempotency_key, user_id, endpoint)

        # Capture response
        response_started = False
        status_code = 200
        response_headers = []
        body_parts = []

        async def capture_send(message):
            nonlocal response_started, status_code, response_headers

            if message["type"] == "http.response.start":
                response_started = True
                status_code = message.get("status", 200)
                response_headers = list(message.get("headers", []))
                # Don't send yet — buffer until we see the body
            elif message["type"] == "http.response.body":
                body_parts.append(message.get("body", b""))

        # Execute request
        try:
            await self.app(scope, receive, capture_send)
        except Exception as e:
            logger.error(f"Idempotency: request execution failed: {e}")
            # Mark as failed
            await self._update_idempotency_record(
                idempotency_key,
                status="failed",
                response_status=500,
                response_body={"error": "Internal server error"},
            )
            raise

        body = b"".join(body_parts)

        # Store response
        try:
            response_body = json.loads(body) if body else None
        except json.JSONDecodeError:
            response_body = {"raw": body.decode("utf-8", errors="replace")}

        await self._update_idempotency_record(
            idempotency_key,
            status="completed",
            response_status=status_code,
            response_body=response_body,
        )

        # Send response to client
        await send({
            "type": "http.response.start",
            "status": status_code,
            "headers": response_headers,
        })
        await send({
            "type": "http.response.body",
            "body": body,
        })

    async def _get_user_id_from_api_key(self, api_key: str) -> str | None:
        """Get user_id from API key hash."""
        from api.auth import hash_api_key

        key_hash = hash_api_key(api_key)

        async with SessionLocal() as db:
            query = text(
                "SELECT user_id FROM platform_api_keys WHERE key_hash = :key_hash AND is_revoked = false"
            )
            result = await db.execute(query, {"key_hash": key_hash})
            row = result.fetchone()
            return str(row[0]) if row else None

    async def _get_idempotency_record(self, key: str) -> dict[str, Any] | None:
        """Check if idempotency key exists."""
        async with SessionLocal() as db:
            query = text(
                "SELECT status, response_status, response_body FROM platform_idempotency_keys WHERE key = :key"
            )
            result = await db.execute(query, {"key": key})
            row = result.fetchone()
            if not row:
                return None
            return {
                "status": row[0],
                "response_status": row[1],
                "response_body": row[2],
            }

    async def _insert_in_progress(self, key: str, user_id: str, endpoint: str):
        """Insert in_progress idempotency record."""
        async with SessionLocal() as db:
            query = text(
                """
                INSERT INTO platform_idempotency_keys (key, user_id, endpoint, status, created_at)
                VALUES (:key, :user_id, :endpoint, 'in_progress', :created_at)
                ON CONFLICT (key) DO NOTHING
                """
            )
            await db.execute(query, {
                "key": key,
                "user_id": user_id,
                "endpoint": endpoint,
                "created_at": datetime.now(timezone.utc),
            })
            await db.commit()

    async def _update_idempotency_record(
        self,
        key: str,
        status: str,
        response_status: int,
        response_body: Any,
    ):
        """Update idempotency record with response."""
        async with SessionLocal() as db:
            query = text(
                """
                UPDATE platform_idempotency_keys
                SET status = :status,
                    response_status = :response_status,
                    response_body = :response_body,
                    completed_at = :completed_at
                WHERE key = :key
                """
            )
            await db.execute(query, {
                "key": key,
                "status": status,
                "response_status": response_status,
                "response_body": json.dumps(response_body) if response_body else None,
                "completed_at": datetime.now(timezone.utc),
            })
            await db.commit()

    async def _send_error(self, send, status_code: int, detail: dict):
        """Send error response."""
        body = json.dumps({"detail": detail}).encode()
        await send({
            "type": "http.response.start",
            "status": status_code,
            "headers": [
                (b"content-type", b"application/json"),
                (b"content-length", str(len(body)).encode()),
            ],
        })
        await send({
            "type": "http.response.body",
            "body": body,
        })

    async def _send_stored_response(self, send, existing: dict):
        """Send stored response from idempotency record."""
        status_code = existing.get("response_status", 200)
        response_body = existing.get("response_body", {})

        body = json.dumps(response_body).encode()
        await send({
            "type": "http.response.start",
            "status": status_code,
            "headers": [
                (b"content-type", b"application/json"),
                (b"content-length", str(len(body)).encode()),
                (b"x-idempotent-replay", b"true"),  # Signal that this is a replayed response
            ],
        })
        await send({
            "type": "http.response.body",
            "body": body,
        })
