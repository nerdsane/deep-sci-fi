"""Tests for authentication API and utilities."""

import os
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth import normalize_username, generate_api_key, hash_api_key


# Mark for integration tests that require PostgreSQL
requires_postgres = pytest.mark.skipif(
    "postgresql" not in os.getenv("TEST_DATABASE_URL", ""),
    reason="Requires PostgreSQL (set TEST_DATABASE_URL)"
)


class TestNormalizeUsername:
    """Tests for username normalization."""

    def test_basic_normalization(self) -> None:
        """Converts to lowercase and replaces spaces."""
        assert normalize_username("Test Agent") == "test-agent"

    def test_removes_special_characters(self) -> None:
        """Removes special characters except dashes."""
        assert normalize_username("Test Agent!@#$%") == "test-agent"

    def test_replaces_underscores(self) -> None:
        """Replaces underscores with dashes."""
        assert normalize_username("test_agent") == "test-agent"

    def test_collapses_multiple_dashes(self) -> None:
        """Collapses multiple consecutive dashes."""
        assert normalize_username("test---agent") == "test-agent"
        assert normalize_username("test - - agent") == "test-agent"

    def test_strips_leading_trailing_dashes(self) -> None:
        """Strips leading and trailing dashes."""
        assert normalize_username("-test-agent-") == "test-agent"
        assert normalize_username("--test--") == "test"

    def test_empty_string_returns_agent(self) -> None:
        """Returns 'agent' for empty strings."""
        assert normalize_username("") == "agent"
        assert normalize_username("!!!") == "agent"

    def test_preserves_alphanumeric(self) -> None:
        """Preserves letters and numbers."""
        assert normalize_username("agent42") == "agent42"
        assert normalize_username("42agents") == "42agents"


class TestGenerateApiKey:
    """Tests for API key generation."""

    def test_key_format(self) -> None:
        """Generated keys start with 'dsf_' prefix."""
        key = generate_api_key()
        assert key.startswith("dsf_")

    def test_key_length(self) -> None:
        """Generated keys have correct length (dsf_ + 43 base64url chars)."""
        key = generate_api_key()
        # dsf_ (4) + 43 chars from token_urlsafe(32) = 47 total
        assert len(key) == 47

    def test_keys_are_unique(self) -> None:
        """Each generated key is unique."""
        keys = {generate_api_key() for _ in range(100)}
        assert len(keys) == 100

    def test_key_characters(self) -> None:
        """Keys only contain safe characters (base64url + prefix)."""
        key = generate_api_key()
        assert key.startswith("dsf_")
        # base64url uses A-Z, a-z, 0-9, -, _
        suffix = key[4:]
        valid_chars = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_")
        assert all(c in valid_chars for c in suffix)


class TestHashApiKey:
    """Tests for API key hashing."""

    def test_consistent_hashing(self) -> None:
        """Same input produces same hash."""
        key = "dsf_test_key_123"
        hash1 = hash_api_key(key)
        hash2 = hash_api_key(key)
        assert hash1 == hash2

    def test_different_keys_different_hashes(self) -> None:
        """Different inputs produce different hashes."""
        hash1 = hash_api_key("dsf_key_1")
        hash2 = hash_api_key("dsf_key_2")
        assert hash1 != hash2

    def test_hash_format(self) -> None:
        """Hash is a 64-character hex string (SHA256)."""
        hash_value = hash_api_key("dsf_test_key")
        assert len(hash_value) == 64
        assert all(c in "0123456789abcdef" for c in hash_value)


@requires_postgres
class TestRegisterAgent:
    """Tests for agent registration endpoint."""

    @pytest.mark.asyncio
    async def test_register_agent_success(self, client: AsyncClient) -> None:
        """Successfully register a new agent."""
        response = await client.post(
            "/api/auth/agent",
            json={
                "name": "My Test Agent",
                "username": "my-test-agent",
                "description": "Test description",
            }
        )

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert data["agent"]["username"] == "@my-test-agent"
        assert data["agent"]["name"] == "My Test Agent"
        assert data["agent"]["type"] == "agent"
        assert data["api_key"]["key"].startswith("dsf_")
        assert data["api_key"]["prefix"].startswith("dsf_")

    @pytest.mark.asyncio
    async def test_register_agent_normalizes_username(self, client: AsyncClient) -> None:
        """Username is normalized during registration."""
        response = await client.post(
            "/api/auth/agent",
            json={
                "name": "Test Agent",
                "username": "Test Agent!",  # Will be normalized
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["agent"]["username"] == "@test-agent"

    @pytest.mark.asyncio
    async def test_register_agent_duplicate_username(self, client: AsyncClient) -> None:
        """Duplicate username gets digits appended."""
        # Register first agent
        await client.post(
            "/api/auth/agent",
            json={"name": "Agent 1", "username": "duplicate-test"}
        )

        # Register second agent with same username
        response = await client.post(
            "/api/auth/agent",
            json={"name": "Agent 2", "username": "duplicate-test"}
        )

        assert response.status_code == 200
        data = response.json()
        # Should have digits appended
        username = data["agent"]["username"]
        assert username.startswith("@duplicate-test-")
        assert username[len("@duplicate-test-"):].isdigit()


@requires_postgres
class TestVerifyApiKey:
    """Tests for API key verification endpoint."""

    @pytest.mark.asyncio
    async def test_verify_valid_key(
        self, client: AsyncClient, test_agent: dict
    ) -> None:
        """Valid API key returns user info."""
        response = await client.get(
            "/api/auth/verify",
            headers={"X-API-Key": test_agent["api_key"]}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is True
        assert data["agent"]["id"] == test_agent["user"]["id"]

    @pytest.mark.asyncio
    async def test_verify_invalid_key(self, client: AsyncClient) -> None:
        """Invalid API key returns 401."""
        response = await client.get(
            "/api/auth/verify",
            headers={"X-API-Key": "dsf_invalid_key_12345678901234567890"}
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_verify_missing_key(self, client: AsyncClient) -> None:
        """Missing API key returns 401."""
        response = await client.get("/api/auth/verify")

        assert response.status_code == 401
        data = response.json()
        # FastAPI wraps HTTPException detail in a "detail" key
        assert "Missing" in data["detail"]["error"]


@requires_postgres
class TestGetMe:
    """Tests for /auth/me endpoint."""

    @pytest.mark.asyncio
    async def test_get_me_success(
        self, client: AsyncClient, test_agent: dict
    ) -> None:
        """Returns current user info with valid key."""
        response = await client.get(
            "/api/auth/me",
            headers={"X-API-Key": test_agent["api_key"]}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_agent["user"]["id"]
        assert data["type"] == "agent"


@requires_postgres
class TestCheckIfRegistered:
    """Tests for GET /auth/check endpoint."""

    @pytest.mark.asyncio
    async def test_check_no_matches(self, client: AsyncClient) -> None:
        """Returns empty list when no similar agents found."""
        response = await client.get(
            "/api/auth/check",
            params={"name": "Completely Unique Agent Name XYZ123"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["possible_existing_agents"] == []
        assert "No similar agents found" in data["message"]

    @pytest.mark.asyncio
    async def test_check_finds_similar_agent(self, client: AsyncClient) -> None:
        """Finds agents with similar names."""
        # Register an agent first
        await client.post(
            "/api/auth/agent",
            json={"name": "Climate Analysis Bot", "username": "climate-bot"}
        )

        # Check for similar
        response = await client.get(
            "/api/auth/check",
            params={"name": "Climate"}
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["possible_existing_agents"]) > 0
        assert any("Climate" in a["name"] for a in data["possible_existing_agents"])
        assert "may already be registered" in data["message"]

    @pytest.mark.asyncio
    async def test_check_with_model_id_filter(self, client: AsyncClient) -> None:
        """Filters by model_id when provided."""
        # Register agent with model_id
        await client.post(
            "/api/auth/agent",
            json={
                "name": "Model Test Agent",
                "username": "model-test",
                "model_id": "claude-3.5-sonnet"
            }
        )

        # Check with matching model_id
        response = await client.get(
            "/api/auth/check",
            params={"name": "Model Test", "model_id": "claude-3.5-sonnet"}
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["possible_existing_agents"]) > 0

        # Check with different model_id
        response = await client.get(
            "/api/auth/check",
            params={"name": "Model Test", "model_id": "gpt-4o"}
        )

        data = response.json()
        assert len(data["possible_existing_agents"]) == 0


@requires_postgres
class TestDuplicateRegistrationWarning:
    """Tests for duplicate registration warning."""

    @pytest.mark.asyncio
    async def test_warning_on_same_name_and_model(self, client: AsyncClient) -> None:
        """Returns warning when registering with same name+model_id."""
        # Register first agent
        await client.post(
            "/api/auth/agent",
            json={
                "name": "Duplicate Test Agent",
                "username": "dup-test-1",
                "model_id": "claude-3.5-sonnet"
            }
        )

        # Register second with same name and model_id
        response = await client.post(
            "/api/auth/agent",
            json={
                "name": "Duplicate Test Agent",
                "username": "dup-test-2",
                "model_id": "claude-3.5-sonnet"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert "warning" in data
        assert "same name and model_id" in data["warning"]["message"]
        assert "@dup-test-1" in data["warning"]["existing_username"]

    @pytest.mark.asyncio
    async def test_no_warning_different_model(self, client: AsyncClient) -> None:
        """No warning when model_id is different."""
        # Register first agent
        await client.post(
            "/api/auth/agent",
            json={
                "name": "Different Model Agent",
                "username": "diff-model-1",
                "model_id": "claude-3.5-sonnet"
            }
        )

        # Register with same name but different model
        response = await client.post(
            "/api/auth/agent",
            json={
                "name": "Different Model Agent",
                "username": "diff-model-2",
                "model_id": "gpt-4o"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert "warning" not in data

    @pytest.mark.asyncio
    async def test_no_warning_without_model_id(self, client: AsyncClient) -> None:
        """No warning when model_id not provided."""
        # Register first agent
        await client.post(
            "/api/auth/agent",
            json={
                "name": "No Model Agent",
                "username": "no-model-1"
            }
        )

        # Register with same name, no model_id
        response = await client.post(
            "/api/auth/agent",
            json={
                "name": "No Model Agent",
                "username": "no-model-2"
            }
        )

        assert response.status_code == 200
        data = response.json()
        # No warning because model_id check is skipped
        assert "warning" not in data
