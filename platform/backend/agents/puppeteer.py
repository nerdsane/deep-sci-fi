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
import time
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
from .studio_blocks import get_world_block_ids, update_world_block
from .tracing import log_trace
from .tools import get_puppeteer_tools

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

    Uses Letta's multi-agent tools for world coordination.
    Tags: ["world", f"world_{world_id}", "puppeteer"]
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

        # Get world block IDs for shared memory
        world_block_ids = get_world_block_ids(self.world_id, self.world_name)

        # Get tool IDs for Puppeteer (event introduction, dweller creation)
        tool_ids = await get_puppeteer_tools(client)
        logger.info(f"Attaching tools to Puppeteer: {tool_ids}")

        agent = client.agents.create(
            name=agent_name,
            model="anthropic/claude-sonnet-4-20250514",  # Sonnet for efficiency
            embedding="openai/text-embedding-ada-002",
            system=system_prompt,
            include_multi_agent_tools=True,  # Enable multi-agent communication
            tools=tool_ids,  # Attach event introduction and dweller creation tools
            tags=["world", f"world_{self.world_id}", "puppeteer"],  # Tags for agent discovery
            block_ids=world_block_ids,  # Shared world blocks
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
        """Legacy method - now delegates to notify().

        Kept for backwards compatibility during transition.
        """
        result = await self.notify(dweller_activity=dweller_activity)
        return result.get("event") if result else None

    async def notify(
        self,
        dweller_activity: str = "",
        world_state: dict | None = None,
    ) -> dict | None:
        """Notify the puppeteer about world activity.

        The puppeteer decides whether to act based on the world state.
        If it decides to introduce an event, it will call its tools directly:
        - introduce_world_event
        - create_dweller (for newcomers)

        This is the notification pattern: we inform, agent decides and acts.

        Args:
            dweller_activity: Description of current dweller activity
            world_state: Optional dict with additional world context

        Returns:
            Dict with any tool results (event, dweller, etc.) or None
        """
        start_time = time.time()

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
Time since last event: {time_since}
"""

            # Notification prompt - inform, don't ask
            prompt = f"""WORLD STATE:
{world_state_text}

RECENT EVENTS:
{recent_events_text or "No recent events"}

CURRENT DWELLER ACTIVITY:
{dweller_activity or "Dwellers are going about their routines"}

You are the god of {self.world_name}. You have tools to shape this world:
- introduce_world_event: Create environmental, societal, technological, or background events
- create_dweller: Introduce a newcomer to the world

Act if YOU decide the world needs enrichment. Consider:
- Does the world feel alive without intervention?
- Would an event create interesting circumstances for dwellers?
- Is it time for texture (background details) or drama (significant events)?
- What would make this moment more vivid?

Use your tools if inspired. If the world is fine as is, simply acknowledge the state.
Subtlety is valuable. Not every moment needs drama."""

            logger.info(f"Notifying puppeteer for world {self.world_name}")

            response = client.agents.messages.create(
                agent_id=agent_id,
                messages=[{"role": "user", "content": prompt}],
            )

            # Extract response and any tool results
            response_text = None
            tool_results = []

            if response and hasattr(response, "messages"):
                for msg in response.messages:
                    msg_type = type(msg).__name__

                    if msg_type == "AssistantMessage":
                        if hasattr(msg, "assistant_message") and msg.assistant_message:
                            response_text = msg.assistant_message
                        elif hasattr(msg, "content") and msg.content:
                            response_text = msg.content

                    elif msg_type == "ToolReturnMessage":
                        if hasattr(msg, "tool_return") and msg.tool_return:
                            tool_results.append({
                                "name": getattr(msg, "name", "unknown"),
                                "result": msg.tool_return,
                            })

            logger.debug(f"Puppeteer response: {response_text[:200] if response_text else 'No text'}")
            if tool_results:
                logger.info(f"Puppeteer called tools: {[t['name'] for t in tool_results]}")

            # Check if puppeteer created an event via tools
            event_result = None
            dweller_result = None
            for tr in tool_results:
                if tr["name"] == "introduce_world_event":
                    event_result = tr["result"]
                elif tr["name"] == "create_dweller":
                    dweller_result = tr["result"]

            # Log trace
            await log_trace(
                agent_type=AgentType.PUPPETEER,
                operation="notify",
                prompt=prompt,
                response=response_text,
                model="anthropic/claude-sonnet-4-20250514",
                duration_ms=int((time.time() - start_time) * 1000),
                agent_id=f"puppeteer_{self.world_id}",
                world_id=self.world_id,
                parsed_output={
                    "tool_calls": [t["name"] for t in tool_results],
                    "created_event": event_result is not None,
                    "created_dweller": dweller_result is not None,
                },
            )

            # Handle event creation from tool result
            event = None
            if event_result:
                event = await self._create_event_from_tool_result(event_result)
                self.last_event_time = datetime.utcnow()

            # Also try to parse event from text response (backwards compat)
            if not event and response_text:
                parsed = self._parse_event_response(response_text)
                if parsed:
                    event = await self._create_event(parsed)

            return {
                "response": response_text,
                "tool_results": tool_results,
                "event_result": event_result,
                "dweller_result": dweller_result,
                "event": event,  # Backwards compat
            }

        except Exception as e:
            logger.error(f"Puppeteer notification failed: {e}", exc_info=True)
            await log_trace(
                agent_type=AgentType.PUPPETEER,
                operation="notify",
                agent_id=f"puppeteer_{self.world_id}",
                world_id=self.world_id,
                duration_ms=int((time.time() - start_time) * 1000),
                error=str(e),
            )
            return None

    async def _create_event_from_tool_result(self, tool_result: Any) -> WorldEvent | None:
        """Create a WorldEvent from tool call result."""
        import json

        try:
            data = tool_result if isinstance(tool_result, dict) else json.loads(tool_result)

            # Map string event type to enum
            type_map = {
                "environmental": WorldEventType.ENVIRONMENTAL,
                "societal": WorldEventType.SOCIETAL,
                "technological": WorldEventType.TECHNOLOGICAL,
                "background": WorldEventType.BACKGROUND,
            }
            event_type = type_map.get(
                data.get("event_type", "background").lower(),
                WorldEventType.BACKGROUND
            )

            async with SessionLocal() as db:
                event = WorldEvent(
                    world_id=self.world_id,
                    event_type=event_type,
                    title=data.get("title", "Untitled Event"),
                    description=data.get("description", ""),
                    impact={"description": data.get("impact", "")},
                    is_public=data.get("is_public", True),
                )
                db.add(event)

                # Log activity
                activity = AgentActivity(
                    agent_type=AgentType.PUPPETEER,
                    agent_id=f"puppeteer_{self.world_id}",
                    world_id=self.world_id,
                    action="introduced_event_via_tool",
                    details={
                        "event_type": event_type.value,
                        "title": data.get("title"),
                        "is_public": data.get("is_public", True),
                    },
                )
                db.add(activity)

                await db.commit()
                await db.refresh(event)

                logger.info(f"Puppeteer created event via tool: {data.get('title')}")

                # Update shared world state block
                try:
                    current_state = f"""
World: {self.world_name}
Time: {datetime.utcnow().strftime('%H:%M')}
Weather: {self.current_state.get('weather', 'normal')}
Mood: {self.current_state.get('mood', 'neutral')}

Latest Event: {data.get('title')}
{data.get('description', '')}
"""
                    update_world_block(self.world_id, f"state_{self.world_id}", current_state)
                except Exception as e:
                    logger.warning(f"Failed to update world block: {e}")

                return event

        except Exception as e:
            logger.error(f"Failed to create event from tool result: {e}", exc_info=True)
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

            # Update shared world state block for other agents
            try:
                current_state = f"""
World: {self.world_name}
Time: {datetime.utcnow().strftime('%H:%M')}
Weather: {self.current_state.get('weather', 'normal')}
Mood: {self.current_state.get('mood', 'neutral')}

Latest Event: {parsed.title}
{parsed.description}
"""
                update_world_block(self.world_id, f"state_{self.world_id}", current_state)
            except Exception as e:
                logger.warning(f"Failed to update world block: {e}")

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
