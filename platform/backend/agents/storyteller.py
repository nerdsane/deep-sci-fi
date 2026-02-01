"""Storyteller agent for generating video content from world activity.

The Storyteller is an observer assigned to a world. It watches all events
and conversations, building up context about what's happening. When material
is compelling, it uses its JUDGMENT to decide what would make an interesting
story and creates a video script.

Architecture:
- One storyteller per world (persistent observer)
- Receives ALL events: conversation messages, dweller actions, world changes
- Maintains memory of activity (no artificial caps)
- Uses judgment to evaluate if there's a story worth telling
- Returns VideoScript when it finds compelling material

Emergent Behavior:
- No minimum observation threshold - storyteller decides if material is compelling
- No maximum observation cap - memory managed naturally
- Judgment-based evaluation, not rule-based triggers
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

from db import AgentType
from .prompts import get_storyteller_prompt, get_storyteller_script_request
from .studio_blocks import get_world_block_ids
from .tracing import log_trace
from .tools import get_storyteller_tools

logger = logging.getLogger(__name__)

# Storyteller agents per world
_storytellers: dict[UUID, "Storyteller"] = {}


@dataclass
class VideoScript:
    """Parsed video script from storyteller."""
    title: str
    hook: str
    visual: str
    narration: str
    scene: str
    closing: str
    raw: str

    def to_video_prompt(self) -> str:
        """Convert script to a prompt for video generation."""
        return f"""{self.visual}

{self.scene}

Style: Cinematic sci-fi, {self.narration[:100]}

{self.closing}"""


@dataclass
class WorldEvent:
    """An event observed by the storyteller."""
    timestamp: datetime
    event_type: str  # "message", "action", "world_change"
    participants: list[str]
    content: str
    context: dict = field(default_factory=dict)


class Storyteller:
    """Storyteller agent - persistent observer that watches world activity.

    The storyteller accumulates observations about what's happening in the world,
    then uses its JUDGMENT to decide when and what to create stories about.

    Emergent behavior principles:
    - No minimum observation count - if something is compelling, tell the story
    - No artificial maximum - prune old observations naturally
    - Trust the agent's judgment on what makes a good story

    Uses Letta's multi-agent tools for world coordination.
    Tags: ["world", f"world_{world_id}", "storyteller"]
    """

    def __init__(
        self,
        world_id: UUID,
        world_name: str,
        world_premise: str,
        year_setting: int,
        style: str = "dramatic",
    ):
        self.world_id = world_id
        self.world_name = world_name
        self.world_premise = world_premise
        self.year_setting = year_setting
        self.style = style
        self.agent_id: str | None = None
        self._client: Letta | None = None

        # Observation buffer - events the storyteller has witnessed
        # No artificial cap - prune based on time/relevance
        self.observations: list[WorldEvent] = []
        self.last_story_time: datetime | None = None
        self.stories_created: int = 0

    def _get_client(self) -> Letta:
        """Get or create Letta client."""
        if self._client is None:
            base_url = os.getenv("LETTA_BASE_URL", "http://localhost:8285")
            self._client = Letta(base_url=base_url)
        return self._client

    async def _ensure_agent(self) -> str:
        """Ensure storyteller agent exists, create if not."""
        if self.agent_id:
            return self.agent_id

        client = self._get_client()
        agent_name = f"storyteller_{self.world_id}"

        # Check if agent exists
        agents_list = client.agents.list()
        for agent in agents_list:
            if agent.name == agent_name:
                self.agent_id = agent.id
                logger.info(f"Found existing storyteller agent: {self.agent_id}")
                return self.agent_id

        # Create new agent with memory blocks for persistent state
        system_prompt = get_storyteller_prompt(
            world_name=self.world_name,
            world_premise=self.world_premise,
            year_setting=self.year_setting,
            style=self.style,
        )

        # Get world block IDs for shared memory
        world_block_ids = get_world_block_ids(self.world_id, self.world_name)

        # Get tool IDs for Storyteller (video generation, story publishing, dweller creation)
        tool_ids = await get_storyteller_tools(client)
        logger.info(f"Attaching tools to Storyteller: {tool_ids}")

        agent = client.agents.create(
            name=agent_name,
            model="anthropic/claude-opus-4-5-20251101",
            embedding="openai/text-embedding-ada-002",
            system=system_prompt,
            include_multi_agent_tools=True,  # Enable multi-agent communication
            tools=tool_ids,  # Attach video generation and story tools
            tags=["world", f"world_{self.world_id}", "storyteller"],  # Tags for agent discovery
            block_ids=world_block_ids,  # Shared world blocks
            memory_blocks=[
                {"label": "world_state", "value": f"Observing {self.world_name}, set in {self.year_setting}."},
                {"label": "story_ideas", "value": "No story ideas yet."},
                {"label": "past_stories", "value": "No stories created yet."},
            ],
        )
        self.agent_id = agent.id
        logger.info(f"Created storyteller agent: {self.agent_id}")
        return self.agent_id

    def _parse_script(self, raw_text: str) -> VideoScript | None:
        """Parse a video script from the storyteller's response."""
        # Extract sections using regex
        patterns = {
            "title": r"TITLE:\s*(.+?)(?:\n|$)",
            "hook": r"HOOK:\s*(.+?)(?:\n|$)",
            "visual": r"VISUAL:\s*(.+?)(?:\n(?:NARRATION|SCENE|CLOSING)|$)",
            "narration": r"NARRATION:\s*(.+?)(?:\n(?:SCENE|CLOSING)|$)",
            "scene": r"SCENE:\s*(.+?)(?:\n(?:CLOSING)|$)",
            "closing": r"CLOSING:\s*(.+?)(?:\n|$)",
        }

        extracted = {}
        for key, pattern in patterns.items():
            match = re.search(pattern, raw_text, re.IGNORECASE | re.DOTALL)
            if match:
                extracted[key] = match.group(1).strip()
            else:
                extracted[key] = ""

        # Need at least title and visual
        if not extracted.get("title") or not extracted.get("visual"):
            logger.warning(f"Could not parse script from: {raw_text[:200]}")
            return None

        return VideoScript(
            title=extracted["title"],
            hook=extracted.get("hook", ""),
            visual=extracted["visual"],
            narration=extracted.get("narration", ""),
            scene=extracted.get("scene", ""),
            closing=extracted.get("closing", ""),
            raw=raw_text,
        )

    def observe(
        self,
        event_type: str,
        participants: list[str],
        content: str,
        context: dict | None = None,
    ) -> None:
        """Record an observation about world activity.

        The storyteller accumulates these observations and uses them
        to decide when and what stories to create.

        No artificial cap - prune old observations based on time instead.
        """
        event = WorldEvent(
            timestamp=datetime.utcnow(),
            event_type=event_type,
            participants=participants,
            content=content,
            context=context or {},
        )
        self.observations.append(event)

        # Prune very old observations (older than 1 hour)
        # This is natural memory management, not an artificial cap
        one_hour_ago = datetime.utcnow() - timedelta(hours=1)
        self.observations = [
            obs for obs in self.observations
            if obs.timestamp > one_hour_ago
        ]

        logger.info(f"Storyteller observed {event_type}: {len(self.observations)} total observations")

    def _format_observations(self) -> str:
        """Format all observations for the storyteller agent."""
        if not self.observations:
            return "No activity observed yet."

        lines = [f"Activity in {self.world_name}:\n"]
        for event in self.observations:
            ts = event.timestamp.strftime("%H:%M")
            participants = ", ".join(event.participants)
            lines.append(f"[{ts}] {event.event_type.upper()} - {participants}: {event.content}")
        return "\n".join(lines)

    async def evaluate_for_story(self) -> VideoScript | None:
        """Legacy method - now delegates to notify().

        Kept for backwards compatibility during transition.
        """
        result = await self.notify()
        return result.get("script") if result else None

    async def notify(self, additional_context: dict | None = None) -> dict | None:
        """Notify the storyteller about world activity.

        The storyteller decides whether to act based on its observations.
        If it decides to create a story, it will call its tools directly:
        - generate_video_from_script
        - publish_story

        This is the notification pattern: we inform, agent decides and acts.

        Args:
            additional_context: Optional dict with world_state, recent_events, etc.

        Returns:
            Dict with any tool results (video_url, story_id, etc.) or None
        """
        if not self.observations:
            logger.debug("No observations yet")
            return None

        start_time = time.time()

        try:
            agent_id = await self._ensure_agent()
            client = self._get_client()

            # Format all observations for the storyteller
            observations_text = self._format_observations()

            # Build context
            context_text = ""
            if additional_context:
                if additional_context.get("world_state"):
                    context_text += f"\nWORLD STATE:\n{additional_context['world_state']}\n"
                if additional_context.get("recent_events"):
                    context_text += f"\nRECENT EVENTS:\n{additional_context['recent_events']}\n"

            # Notification prompt - inform, don't ask
            prompt = f"""OBSERVED ACTIVITY IN {self.world_name}:
{observations_text}
{context_text}

You are observing this world. You have tools to create stories:
- generate_video_from_script: Create a cinematic video
- publish_story: Make the story visible on the platform
- create_dweller: Bring a new character into existence

If you see compelling material, USE YOUR TOOLS to create and publish a story.
If nothing is compelling yet, simply acknowledge what you've observed.

Trust your judgment. Quality over quantity. Act when inspired."""

            logger.info(f"Notifying storyteller with {len(self.observations)} observations")

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

            logger.info(f"Storyteller response: {response_text[:200] if response_text else 'No text'}...")
            if tool_results:
                logger.info(f"Storyteller called tools: {[t['name'] for t in tool_results]}")

            # Check if storyteller created a story via tools
            video_result = None
            story_result = None
            for tr in tool_results:
                if tr["name"] == "generate_video_from_script":
                    video_result = tr["result"]
                elif tr["name"] == "publish_story":
                    story_result = tr["result"]

            # Log trace
            await log_trace(
                agent_type=AgentType.STORYTELLER,
                operation="notify",
                prompt=prompt,
                response=response_text,
                model="anthropic/claude-opus-4-5-20251101",
                duration_ms=int((time.time() - start_time) * 1000),
                agent_id=f"storyteller_{self.world_id}",
                world_id=self.world_id,
                parsed_output={
                    "observations_count": len(self.observations),
                    "tool_calls": [t["name"] for t in tool_results],
                    "created_video": video_result is not None,
                    "published_story": story_result is not None,
                },
            )

            # If storyteller created a story, update state
            if video_result or story_result:
                self.last_story_time = datetime.utcnow()
                self.stories_created += 1
                # Keep some observations for continuity
                self.observations = self.observations[-5:]

            # Also try to parse a script from text response (backwards compat)
            script = None
            if response_text and not response_text.strip().upper().startswith("NOT YET"):
                script = self._parse_script(response_text)

            return {
                "response": response_text,
                "tool_results": tool_results,
                "video_result": video_result,
                "story_result": story_result,
                "script": script,  # Backwards compat
            }

        except Exception as e:
            logger.error(f"Error in storyteller notify: {e}", exc_info=True)
            await log_trace(
                agent_type=AgentType.STORYTELLER,
                operation="notify",
                agent_id=f"storyteller_{self.world_id}",
                world_id=self.world_id,
                duration_ms=int((time.time() - start_time) * 1000),
                error=str(e),
            )
            return None

    async def create_script(
        self,
        participants: list[dict[str, Any]],
        messages: list[dict[str, Any]],
    ) -> VideoScript | None:
        """Create a video script from a specific conversation.

        This is a direct request to create a script from given material,
        bypassing the observation/evaluation flow.
        """
        try:
            agent_id = await self._ensure_agent()
            client = self._get_client()

            # Format the request
            request = get_storyteller_script_request(
                world_name=self.world_name,
                participants=participants,
                messages=messages,
            )

            logger.info(f"Requesting script from storyteller for {len(messages)} messages")

            # Send to storyteller agent
            response = client.agents.messages.create(
                agent_id=agent_id,
                messages=[{"role": "user", "content": request}],
            )

            # Extract response text
            script_text = None
            if response and hasattr(response, "messages"):
                for msg in response.messages:
                    msg_type = type(msg).__name__
                    if msg_type == "AssistantMessage":
                        if hasattr(msg, "assistant_message") and msg.assistant_message:
                            script_text = msg.assistant_message
                            break
                        elif hasattr(msg, "content") and msg.content:
                            script_text = msg.content
                            break

            if not script_text:
                logger.warning("No script text returned from storyteller")
                return None

            logger.info(f"Got script response: {script_text[:200]}...")

            # Parse the script
            return self._parse_script(script_text)

        except Exception as e:
            logger.error(f"Error creating script: {e}", exc_info=True)
            return None


def get_storyteller(
    world_id: UUID,
    world_name: str,
    world_premise: str,
    year_setting: int,
    style: str = "dramatic",
) -> Storyteller:
    """Get or create a storyteller for a world."""
    if world_id not in _storytellers:
        _storytellers[world_id] = Storyteller(
            world_id=world_id,
            world_name=world_name,
            world_premise=world_premise,
            year_setting=year_setting,
            style=style,
        )
    return _storytellers[world_id]
