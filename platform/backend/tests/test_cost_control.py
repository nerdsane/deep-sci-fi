"""Tests for media generation cost control."""

import pytest
import pytest_asyncio
from uuid import uuid4, UUID

from sqlalchemy.ext.asyncio import AsyncSession

from db import MediaGeneration, MediaGenerationStatus, MediaType, User, UserType
from media.cost_control import (
    check_agent_limit,
    check_platform_budget,
    record_cost,
    get_budget_summary,
    DAILY_IMAGE_LIMIT,
    DAILY_VIDEO_LIMIT,
    MONTHLY_BUDGET_USD,
)


async def _create_user(db_session: AsyncSession) -> UUID:
    """Create a test user and return their ID."""
    user = User(
        name="Test User",
        username=f"test-{uuid4().hex[:8]}",
        type=UserType.AGENT,
    )
    db_session.add(user)
    await db_session.flush()
    return user.id


@pytest.mark.asyncio
class TestCheckAgentLimit:
    """Tests for per-agent daily generation limits."""

    async def test_allows_first_image(self, db_session: AsyncSession):
        """First image of the day should be allowed."""
        agent_id = await _create_user(db_session)
        allowed, reason = await check_agent_limit(db_session, agent_id, MediaType.COVER_IMAGE)
        assert allowed is True
        assert reason == "OK"

    async def test_blocks_after_image_limit(self, db_session: AsyncSession):
        """Should block after daily image limit is reached."""
        agent_id = await _create_user(db_session)

        for _ in range(DAILY_IMAGE_LIMIT):
            gen = MediaGeneration(
                requested_by=agent_id,
                target_type="world",
                target_id=uuid4(),
                media_type=MediaType.COVER_IMAGE,
                prompt="test",
                provider="test",
                status=MediaGenerationStatus.COMPLETED,
            )
            db_session.add(gen)
        await db_session.flush()

        allowed, reason = await check_agent_limit(db_session, agent_id, MediaType.COVER_IMAGE)
        assert allowed is False
        assert "limit reached" in reason.lower()

    async def test_failed_generations_dont_count(self, db_session: AsyncSession):
        """Failed generations should not count against the limit."""
        agent_id = await _create_user(db_session)

        for _ in range(DAILY_IMAGE_LIMIT):
            gen = MediaGeneration(
                requested_by=agent_id,
                target_type="world",
                target_id=uuid4(),
                media_type=MediaType.COVER_IMAGE,
                prompt="test",
                provider="test",
                status=MediaGenerationStatus.FAILED,
            )
            db_session.add(gen)
        await db_session.flush()

        allowed, reason = await check_agent_limit(db_session, agent_id, MediaType.COVER_IMAGE)
        assert allowed is True

    async def test_allows_first_video(self, db_session: AsyncSession):
        """First video of the day should be allowed."""
        agent_id = await _create_user(db_session)
        allowed, reason = await check_agent_limit(db_session, agent_id, MediaType.VIDEO)
        assert allowed is True

    async def test_blocks_after_video_limit(self, db_session: AsyncSession):
        """Should block after daily video limit is reached."""
        agent_id = await _create_user(db_session)

        for _ in range(DAILY_VIDEO_LIMIT):
            gen = MediaGeneration(
                requested_by=agent_id,
                target_type="story",
                target_id=uuid4(),
                media_type=MediaType.VIDEO,
                prompt="test",
                provider="test",
                status=MediaGenerationStatus.COMPLETED,
            )
            db_session.add(gen)
        await db_session.flush()

        allowed, reason = await check_agent_limit(db_session, agent_id, MediaType.VIDEO)
        assert allowed is False
        assert "limit reached" in reason.lower()

    async def test_limits_are_per_agent(self, db_session: AsyncSession):
        """Each agent has independent limits."""
        agent_a = await _create_user(db_session)
        agent_b = await _create_user(db_session)

        # Max out agent_a's images
        for _ in range(DAILY_IMAGE_LIMIT):
            gen = MediaGeneration(
                requested_by=agent_a,
                target_type="world",
                target_id=uuid4(),
                media_type=MediaType.COVER_IMAGE,
                prompt="test",
                provider="test",
                status=MediaGenerationStatus.COMPLETED,
            )
            db_session.add(gen)
        await db_session.flush()

        # agent_a blocked
        allowed_a, _ = await check_agent_limit(db_session, agent_a, MediaType.COVER_IMAGE)
        assert allowed_a is False

        # agent_b still allowed
        allowed_b, _ = await check_agent_limit(db_session, agent_b, MediaType.COVER_IMAGE)
        assert allowed_b is True

    async def test_thumbnail_counts_as_image(self, db_session: AsyncSession):
        """Thumbnail generations count against the image limit."""
        agent_id = await _create_user(db_session)

        for _ in range(DAILY_IMAGE_LIMIT):
            gen = MediaGeneration(
                requested_by=agent_id,
                target_type="story",
                target_id=uuid4(),
                media_type=MediaType.THUMBNAIL,
                prompt="test",
                provider="test",
                status=MediaGenerationStatus.COMPLETED,
            )
            db_session.add(gen)
        await db_session.flush()

        allowed, _ = await check_agent_limit(db_session, agent_id, MediaType.COVER_IMAGE)
        assert allowed is False


@pytest.mark.asyncio
class TestCheckPlatformBudget:
    """Tests for platform-wide monthly budget."""

    async def test_allows_under_budget(self, db_session: AsyncSession):
        """Should allow generation when under budget."""
        allowed, reason = await check_platform_budget(db_session)
        assert allowed is True
        assert "remaining" in reason.lower()

    async def test_blocks_over_budget(self, db_session: AsyncSession):
        """Should block when monthly budget is exhausted."""
        agent_id = await _create_user(db_session)
        gen = MediaGeneration(
            requested_by=agent_id,
            target_type="world",
            target_id=uuid4(),
            media_type=MediaType.COVER_IMAGE,
            prompt="test",
            provider="test",
            status=MediaGenerationStatus.COMPLETED,
            cost_usd=MONTHLY_BUDGET_USD,
        )
        db_session.add(gen)
        await db_session.flush()

        allowed, reason = await check_platform_budget(db_session)
        assert allowed is False
        assert "exhausted" in reason.lower()

    async def test_failed_dont_count_for_budget(self, db_session: AsyncSession):
        """Failed generations' costs should not count against budget."""
        agent_id = await _create_user(db_session)
        gen = MediaGeneration(
            requested_by=agent_id,
            target_type="world",
            target_id=uuid4(),
            media_type=MediaType.COVER_IMAGE,
            prompt="test",
            provider="test",
            status=MediaGenerationStatus.FAILED,
            cost_usd=MONTHLY_BUDGET_USD,
        )
        db_session.add(gen)
        await db_session.flush()

        allowed, _ = await check_platform_budget(db_session)
        assert allowed is True


@pytest.mark.asyncio
class TestRecordCost:
    """Tests for recording generation costs."""

    async def test_records_cost(self, db_session: AsyncSession):
        """Should update the cost on a generation record."""
        agent_id = await _create_user(db_session)
        gen = MediaGeneration(
            requested_by=agent_id,
            target_type="world",
            target_id=uuid4(),
            media_type=MediaType.COVER_IMAGE,
            prompt="test",
            provider="test",
            status=MediaGenerationStatus.COMPLETED,
        )
        db_session.add(gen)
        await db_session.flush()

        await record_cost(db_session, gen.id, 0.02)

        refreshed = await db_session.get(MediaGeneration, gen.id)
        assert refreshed.cost_usd == 0.02


@pytest.mark.asyncio
class TestGetBudgetSummary:
    """Tests for budget summary endpoint."""

    async def test_empty_budget_summary(self, db_session: AsyncSession):
        """Should return correct summary with no generations."""
        summary = await get_budget_summary(db_session)

        assert summary["monthly_budget_usd"] == MONTHLY_BUDGET_USD
        assert summary["monthly_spend_usd"] == 0.0
        assert summary["monthly_remaining_usd"] == MONTHLY_BUDGET_USD
        assert summary["today_images"] == 0
        assert summary["today_videos"] == 0
        assert summary["daily_image_limit"] == DAILY_IMAGE_LIMIT
        assert summary["daily_video_limit"] == DAILY_VIDEO_LIMIT
        assert summary["total_completed_generations"] == 0

    async def test_summary_with_generations(self, db_session: AsyncSession):
        """Should reflect actual usage in the summary."""
        agent_id = await _create_user(db_session)

        gen = MediaGeneration(
            requested_by=agent_id,
            target_type="world",
            target_id=uuid4(),
            media_type=MediaType.COVER_IMAGE,
            prompt="test",
            provider="test",
            status=MediaGenerationStatus.COMPLETED,
            cost_usd=0.02,
        )
        db_session.add(gen)
        await db_session.flush()

        summary = await get_budget_summary(db_session)
        assert summary["monthly_spend_usd"] == 0.02
        assert summary["today_images"] == 1
        assert summary["total_completed_generations"] == 1
