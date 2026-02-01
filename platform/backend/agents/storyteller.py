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
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from letta_client import Letta

from .prompts import get_storyteller_prompt, get_storyteller_script_request

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
            base_url = os.getenv("LETTA_BASE_URL", "http://localhost:8283")
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

        agent = client.agents.create(
            name=agent_name,
            model="anthropic/claude-opus-4-5-20251101",
            embedding="openai/text-embedding-ada-002",
            system=system_prompt,
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
        """Ask the storyteller if there's a story worth telling.

        The storyteller reviews its observations and uses JUDGMENT to decide
        whether there's compelling material for a video. No minimum observation
        threshold - if something is compelling, tell the story.

        Returns a VideoScript if yes, None if not yet.
        """
        # No minimum threshold - let the agent decide
        # Even a single powerful observation could be a story
        if not self.observations:
            logger.debug("No observations yet")
            return None

        try:
            agent_id = await self._ensure_agent()
            client = self._get_client()

            # Format all observations for the storyteller
            observations_text = self._format_observations()

            # Judgment-based prompt - agent decides if material is compelling
            prompt = f"""OBSERVED ACTIVITY:
{observations_text}

You've observed this activity in {self.world_name}.

IS THERE A STORY WORTH TELLING RIGHT NOW?

Consider:
- Emotional resonance of what you've witnessed
- Dramatic tension or resolution present
- Visual potential for a short video
- Whether waiting might yield better material

If the material IS compelling, write a video script in this EXACT format:

TITLE: [evocative title, 3-6 words]
HOOK: [one sentence that makes viewers need to watch]
VISUAL: [opening shot - cinematic and specific]
NARRATION: [2-3 sentences of voiceover]
SCENE: [the key visual moment - characters, setting, mood, lighting]
CLOSING: [final image or moment that lingers]

If the material is NOT YET compelling, respond with:
NOT YET - [brief reason why, and what you're waiting for]

Trust your judgment. Quality over quantity."""

            logger.info(f"Storyteller evaluating {len(self.observations)} observations")

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
                logger.warning("No response from storyteller evaluation")
                return None

            logger.info(f"Storyteller response: {response_text[:200]}...")

            # Check if storyteller decided to wait
            if response_text.strip().upper().startswith("NOT YET"):
                logger.info(f"Storyteller decided to wait: {response_text[:100]}")
                return None

            # Try to parse a script
            script = self._parse_script(response_text)
            if script:
                logger.info(f"Storyteller created script: {script.title}")
                self.last_story_time = datetime.utcnow()
                self.stories_created += 1
                # Keep some observations for continuity, but clear most
                # after creating a story to avoid telling the same story twice
                self.observations = self.observations[-5:]
            return script

        except Exception as e:
            logger.error(f"Error in storyteller evaluation: {e}", exc_info=True)
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
