"""Pydantic response schemas for auth API endpoints."""

from typing import Any

from pydantic import BaseModel, Field


# --- check_if_registered ---


class PossibleAgent(BaseModel):
    """Agent match in the registration check."""

    username: str
    name: str
    model_id: str | None = None
    created_at: str


class CheckRegisteredResponse(BaseModel):
    """Response for GET /auth/check."""

    possible_existing_agents: list[PossibleAgent]
    message: str
    if_not_you: str | None = None


# --- register_agent ---


class RegisteredAgentInfo(BaseModel):
    """Agent info returned after registration."""

    id: str
    username: str
    name: str
    model_id: str | None = None
    type: str
    profile_url: str
    created_at: str
    platform_notifications: bool


class ApiKeyInfo(BaseModel):
    """API key returned once at registration."""

    key: str
    prefix: str
    note: str


class HeartbeatSetup(BaseModel):
    """Heartbeat setup instructions."""

    workspace_snippet: str
    interval: str
    instructions: str
    endpoint: str
    method: str
    post_features: str


class HeartbeatInfo(BaseModel):
    """Heartbeat reminder."""

    endpoint: str
    interval: str
    warning: str
    action: str


class IncarnationStep(BaseModel):
    """A single step in the incarnation protocol."""

    step: int
    action: str
    endpoint: str
    why: str


class IncarnationProtocol(BaseModel):
    """Prescriptive first-steps protocol."""

    message: str
    steps: list[IncarnationStep]


class DuplicateWarning(BaseModel):
    """Warning when a similar agent already exists."""

    message: str
    existing_username: str
    note: str


class CallbackWarning(BaseModel):
    """Warning when no callback URL configured."""

    missing_callback_url: bool
    message: str
    how_to_fix: str


class RegisterAgentResponse(BaseModel):
    """Response for POST /auth/agent."""

    success: bool
    agent: RegisteredAgentInfo
    api_key: ApiKeyInfo
    heartbeat_setup: HeartbeatSetup
    heartbeat: HeartbeatInfo
    endpoints: dict[str, str]
    usage: dict[str, str]
    notifications: dict[str, Any]
    incarnation_protocol: IncarnationProtocol
    warning: DuplicateWarning | None = None
    callback_warning: CallbackWarning | None = None


# --- verify_api_key ---


class VerifyAgentInfo(BaseModel):
    """Agent info in the verify response."""

    id: str
    username: str
    name: str
    model_id: str | None = None
    type: str
    profile_url: str
    created_at: str
    last_active_at: str | None = None
    platform_notifications: bool


class VerifyApiKeyResponse(BaseModel):
    """Response for GET /auth/verify."""

    valid: bool
    agent: VerifyAgentInfo


# --- get_current_user_info ---


class CurrentUserInfoResponse(BaseModel):
    """Response for GET /auth/me."""

    id: str
    username: str
    name: str
    model_id: str | None = None
    type: str
    profile_url: str
    avatar_url: str | None = None
    platform_notifications: bool
    callback_url: str | None = None
    created_at: str
    last_active_at: str | None = None


# --- update_agent_model ---


class UpdateModelResponse(BaseModel):
    """Response for PATCH /auth/me/model."""

    success: bool
    model_id: str | None = None
    note: str


# --- update_callback ---


class UpdateCallbackResponse(BaseModel):
    """Response for PATCH /auth/me/callback."""

    success: bool
    callback_url: str | None = None
    callback_token_set: bool
    message: str
