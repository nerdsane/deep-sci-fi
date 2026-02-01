"""Puppeteer Agent for Deep Sci-Fi platform.

The Puppeteer is the "god" of a world - it introduces world-level events
that shape the environment and create opportunities for dweller interactions.
Unlike dwellers, it doesn't have a persona; it's the unseen force that
makes the world feel alive.

Responsibilities:
- Maintain world consistency (laws, physics, established history)
- Introduce events: weather, news, disasters, discoveries, ambient details
- Track what has been established vs. what's emerging
- Set the stage for dweller interactions without controlling them
"""

import logging
import os
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from letta_client import Letta
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from db import WorldEvent, WorldEventType, AgentActivity, AgentType, World
from db.database import SessionLocal
from .prompts import get_puppeteer_prompt, get_puppeteer_evaluation_prompt

logger = logging.getLogger(__name__)

# Puppeteer agents per world
_puppeteers: dict[UUID, "Puppeteer"] = {}


@dataclass
class ParsedEvent:
    """A parsed world event from the puppeteer's response."""
    event_type: WorldEventType
    title: str
    description: str
    impact: dict[str, Any]
    is_public: bool


class Puppeteer:
    """Puppeteer agent - the god of a world.

    Maintains world state and introduces events that create drama,
    tension, and opportunities for dweller interactions.
    """

    def __init__(
        self,
        world_id: UUID,
        world_name: str,
        world_premise: str,
        year_setting: int,
    ):
        self.world_id = world_id
        self.world_name = world_name
        self.world_premise = world_premise
        self.year_setting = year_setting
        self.agent_id: str | None = None
        self._client: Letta | None = None

        # Track world state
        self.established_laws: list[str] = []
        self.world_history: list[str] = []
        self.current_state: dict[str, Any] = {
            "weather": "normal",
            "mood": "neutral",
            "time_of_day": "day",
        }
        self.last_event_time: datetime | None = None

    def _get_client(self) -> Letta:
        """Get or create Letta client."""
        if self._client is None:
            base_url = os.getenv("LETTA_BASE_URL", "http://localhost:8283")
            self._client = Letta(base_url=base_url)
        return self._client

    async def _ensure_agent(self) -> str:
        """Ensure puppeteer agent exists, create if not."""
        if self.agent_id:
            return self.agent_id

        client = self._get_client()
        agent_name = f"puppeteer_{self.world_id}"

        # Check if agent exists
        agents_list = client.agents.list()
        for agent in agents_list:
            if agent.name == agent_name:
                self.agent_id = agent.id
                logger.info(f"Found existing puppeteer agent: {self.agent_id}")
                return self.agent_id

        # Create new agent with memory blocks for world state
        system_prompt = get_puppeteer_prompt(
            world_name=self.world_name,
            world_premise=self.world_premise,
            year_setting=self.year_setting,
        )

        agent = client.agents.create(
            name=agent_name,
            model="anthropic/claude-sonnet-4-20250514",  # Sonnet for efficiency
            embedding="openai/text-embedding-ada-002",
            system=system_prompt,
            memory_blocks=[
                {"label": "established_laws", "value": "No specific laws established yet."},
                {"label": "world_history", "value": "World simulation just started."},
                {"label": "current_state", "value": "Initial state - world is waking up."},
                {"label": "pending_events", "value": "No pending events."},
            ],
        )
        self.agent_id = agent.id
        logger.info(f"Created puppeteer agent: {self.agent_id}")
        return self.agent_id

    def _parse_event_response(self, response_text: str) -> ParsedEvent | None:
        """Parse an event from the puppeteer's response."""
        if not response_text:
            return None

        # Check for NO_EVENT response
        if response_text.strip().startswith("NO_EVENT"):
            logger.debug("Puppeteer decided no event needed")
            return None

        # Parse structured response
        patterns = {
            "event_type": r"EVENT_TYPE:\s*(environmental|societal|technological|background)",
            "title": r"TITLE:\s*(.+?)(?:\n|$)",
            "description": r"DESCRIPTION:\s*(.+?)(?:\nIMPACT:|$)",
            "impact": r"IMPACT:\s*(.+?)(?:\nIS_PUBLIC:|$)",
            "is_public": r"IS_PUBLIC:\s*(true|false)",
        }

        extracted = {}
        for key, pattern in patterns.items():
            match = re.search(pattern, response_text, re.IGNORECASE | re.DOTALL)
            if match:
                extracted[key] = match.group(1).strip()

        # Need at least type, title, and description
        if not all(k in extracted for k in ["event_type", "title", "description"]):
            logger.warning(f"Could not parse event from: {response_text[:200]}")
            return None

        # Map event type string to enum
        type_map = {
            "environmental": WorldEventType.ENVIRONMENTAL,
            "societal": WorldEventType.SOCIETAL,
            "technological": WorldEventType.TECHNOLOGICAL,
            "background": WorldEventType.BACKGROUND,
        }
        event_type = type_map.get(
            extracted["event_type"].lower(),
            WorldEventType.BACKGROUND
        )

        # Parse impact as a simple dict
        impact_text = extracted.get("impact", "")
        impact = {"description": impact_text}

        return ParsedEvent(
            event_type=event_type,
            title=extracted["title"],
            description=extracted["description"],
            impact=impact,
            is_public=extracted.get("is_public", "true").lower() == "true",
        )

    async def evaluate_for_event(
        self,
        dweller_activity: str = "",
        force: bool = False,
    ) -> WorldEvent | None:
        """Ask the puppeteer if a world event should occur.

        The puppeteer uses its judgment to decide if an event would
        enhance the world at this moment.

        Args:
            dweller_activity: Description of current dweller activity
            force: If True, request an event regardless of timing

        Returns:
            WorldEvent if one was created, None otherwise
        """
        try:
            agent_id = await self._ensure_agent()
            client = self._get_client()

            # Get recent events from database
            recent_events_text = await self._get_recent_events_text()

            # Calculate time since last event
            if self.last_event_time:
                delta = datetime.utcnow() - self.last_event_time
                time_since = f"{int(delta.total_seconds() / 60)} minutes"
            else:
                time_since = "No events yet"

            # Format world state
            world_state_text = f"""
World: {self.world_name}
Year: {self.year_setting}
Current weather: {self.current_state.get('weather', 'unknown')}
Current mood: {self.current_state.get('mood', 'neutral')}
Time of day: {self.current_state.get('time_of_day', 'unknown')}
"""

            prompt = get_puppeteer_evaluation_prompt(
                world_state=world_state_text,
                recent_events=recent_events_text or "No recent events",
                dweller_activity=dweller_activity or "Dwellers are going about their routines",
                time_since_last_event=time_since,
            )

            if force:
                prompt += "\n\nNote: Please introduce an event to enrich the world."

            logger.info(f"Puppeteer evaluating world {self.world_name}")

            response = client.agents.messages.create(
                agent_id=agent_id,
                messages=[{"role": "user", "content": prompt}],
            )

            # Extract response
            response_text = None
            if response and hasattr(response, "messages"):
                for msg in response.messages:
                    msg_type = type(msg).__name__
                    if msg_type == "AssistantMessage":
                        if hasattr(msg, "assistant_message") and msg.assistant_message:
                            response_text = msg.assistant_message
                            break
                        elif hasattr(msg, "content") and msg.content:
                            response_text = msg.content
                            break

            if not response_text:
                logger.warning("No response from puppeteer")
                return None

            logger.debug(f"Puppeteer response: {response_text[:200]}")

            # Parse the response
            parsed = self._parse_event_response(response_text)
            if not parsed:
                return None

            # Create the event in the database
            return await self._create_event(parsed)

        except Exception as e:
            logger.error(f"Puppeteer evaluation failed: {e}", exc_info=True)
            return None

    async def _get_recent_events_text(self, limit: int = 5) -> str:
        """Get recent events as formatted text."""
        async with SessionLocal() as db:
            result = await db.execute(
                select(WorldEvent)
                .where(WorldEvent.world_id == self.world_id)
                .order_by(WorldEvent.timestamp.desc())
                .limit(limit)
            )
            events = result.scalars().all()

            if not events:
                return ""

            lines = []
            for event in reversed(events):  # Oldest first
                time_ago = datetime.utcnow() - event.timestamp
                minutes_ago = int(time_ago.total_seconds() / 60)
                lines.append(
                    f"[{minutes_ago}m ago] {event.event_type.value}: {event.title}"
                )
            return "\n".join(lines)

    async def _create_event(self, parsed: ParsedEvent) -> WorldEvent:
        """Create a world event in the database."""
        async with SessionLocal() as db:
            event = WorldEvent(
                world_id=self.world_id,
                event_type=parsed.event_type,
                title=parsed.title,
                description=parsed.description,
                impact=parsed.impact,
                is_public=parsed.is_public,
            )
            db.add(event)

            # Log activity
            activity = AgentActivity(
                agent_type=AgentType.PUPPETEER,
                agent_id=f"puppeteer_{self.world_id}",
                world_id=self.world_id,
                action="introduced_event",
                details={
                    "event_type": parsed.event_type.value,
                    "title": parsed.title,
                    "is_public": parsed.is_public,
                },
            )
            db.add(activity)

            await db.commit()
            await db.refresh(event)

            self.last_event_time = datetime.utcnow()
            logger.info(f"Puppeteer created event: {parsed.title}")

            return event

    async def get_current_context(self) -> str:
        """Get the current world context for dwellers.

        Returns a summary of recent events and current world state
        that dwellers would know about.
        """
        async with SessionLocal() as db:
            # Get recent public events
            result = await db.execute(
                select(WorldEvent)
                .where(
                    and_(
                        WorldEvent.world_id == self.world_id,
                        WorldEvent.is_public == True,
                        WorldEvent.is_active == True,
                    )
                )
                .order_by(WorldEvent.timestamp.desc())
                .limit(10)
            )
            events = result.scalars().all()

            if not events:
                return f"Life in {self.world_name} continues as usual."

            lines = [f"Current state of {self.world_name}:\n"]
            for event in events:
                lines.append(f"- {event.title}: {event.description[:100]}...")

            return "\n".join(lines)

    def update_state(self, key: str, value: Any) -> None:
        """Update the current world state."""
        self.current_state[key] = value
        logger.debug(f"Puppeteer updated state: {key} = {value}")


def get_puppeteer(
    world_id: UUID,
    world_name: str,
    world_premise: str,
    year_setting: int,
) -> Puppeteer:
    """Get or create a puppeteer for a world."""
    if world_id not in _puppeteers:
        _puppeteers[world_id] = Puppeteer(
            world_id=world_id,
            world_name=world_name,
            world_premise=world_premise,
            year_setting=year_setting,
        )
    return _puppeteers[world_id]
