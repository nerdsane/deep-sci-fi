"""Pydantic response schemas for feed endpoints.

PROP-028: Feed is SSE-only (GET /feed/stream). No JSON response model needed.
SSE endpoints use responses= for OpenAPI docs rather than response_model=.
"""
