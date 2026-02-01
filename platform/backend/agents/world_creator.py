"""World Creator Agent (Architect) for Deep Sci-Fi platform.

Creates worlds with:
- World name
- World document (markdown describing the world)
- Dweller cast (name + system prompt for each)
- Dweller avatars (generated via xAI Grok)

Now uses Letta's multi-agent tools for communication with other studio agents.
"""

import asyncio
import json
import logging
import os
import re
import time
from dataclasses import dataclass, field
from uuid import UUID

from letta_client import Letta
from sqlalchemy import select

from db import (
    ProductionBrief,
    BriefStatus,
    AgentActivity,
    AgentType,
)
from db.database import SessionLocal
from .prompts import get_world_creator_prompt, ANTI_CLICHE_RULES
from .studio_blocks import get_studio_block_ids, update_studio_block
from .tracing import log_trace
from video.grok_imagine import generate_avatar

logger = logging.getLogger(__name__)


@dataclass
class DwellerSpec:
    """A dweller: name, system prompt, and optional avatar."""
    name: str
    system_prompt: str
    role: str = ""
    background: str = ""
    avatar_url: str | None = None
    avatar_prompt: str | None = None


@dataclass
class WorldSpec:
    """A world: name, document, and dwellers."""
    name: str
    document: str  # Full markdown describing the world
    year_setting: int
    dwellers: list[DwellerSpec]


class WorldCreatorAgent:
    """Creates worlds from briefs.

    Uses Letta with multi-agent tools for studio collaboration.
    Tags: ["studio", "architect"]
    """

    MODEL = "anthropic/claude-sonnet-4-20250514"

    def __init__(self):
        self._client: Letta | None = None
        self._agent_id: str | None = None

    def _get_client(self) -> Letta:
        if self._client is None:
            base_url = os.getenv("LETTA_BASE_URL", "http://localhost:8283")
            self._client = Letta(base_url=base_url)
        return self._client

    async def _ensure_agent(self) -> str:
        """Ensure the architect agent exists, create if not."""
        if self._agent_id:
            return self._agent_id

        client = self._get_client()
        agent_name = "architect_agent"

        # Check if agent exists
        agents_list = client.agents.list()
        for agent in agents_list:
            if agent.name == agent_name:
                self._agent_id = agent.id
                logger.info(f"Found existing architect agent: {self._agent_id}")
                return self._agent_id

        # Get studio block IDs for shared memory
        studio_block_ids = get_studio_block_ids()

        # Create new agent with multi-agent tools
        system_prompt = get_world_creator_prompt()

        agent = client.agents.create(
            name=agent_name,
            model=self.MODEL,
            embedding="openai/text-embedding-ada-002",
            system=system_prompt,
            include_multi_agent_tools=True,  # Enable multi-agent communication
            tags=["studio", "architect"],  # Tags for agent discovery
            block_ids=studio_block_ids,  # Shared studio blocks
            memory_blocks=[
                {"label": "worlds_created", "value": "No worlds created yet."},
                {"label": "current_brief", "value": "No active brief."},
                {"label": "design_notes", "value": "Design principles and learnings."},
            ],
        )
        self._agent_id = agent.id
        logger.info(f"Created architect agent: {self._agent_id}")
        return self._agent_id

    def _extract_response(self, response) -> str | None:
        """Extract text from Letta response."""
        if response and hasattr(response, "messages"):
            for msg in response.messages:
                msg_type = type(msg).__name__
                if msg_type == "AssistantMessage":
                    if hasattr(msg, "assistant_message") and msg.assistant_message:
                        return msg.assistant_message
                    elif hasattr(msg, "content") and msg.content:
                        return msg.content
        return None

    async def create_world_from_brief(
        self,
        brief: ProductionBrief,
        recommendation_index: int = 0,
    ) -> WorldSpec:
        """Create a world from a production brief."""
        start_time = time.time()

        if not brief.recommendations or recommendation_index >= len(brief.recommendations):
            raise ValueError(f"Invalid recommendation index: {recommendation_index}")

        recommendation = brief.recommendations[recommendation_index]

        # Ensure agent exists
        agent_id = await self._ensure_agent()
        client = self._get_client()

        # Update shared block to show we're working on a brief
        update_studio_block(
            "studio_context",
            f"Architect building world from brief {brief.id}. Theme: {recommendation.get('theme', 'unknown')}"
        )

        # Step 1: Generate world name and document
        world_prompt = f"""Create a sci-fi world based on this brief:

THEME: {recommendation.get('theme', '')}
PREMISE: {recommendation.get('premise_sketch', '')}
CORE QUESTION: {recommendation.get('core_question', '')}

Write a world document in markdown. Include:
- The world's name (first line, as # heading)
- Year setting
- What happened (causal chain from 2026)
- How society works now
- Technology and its limitations
- Daily life details

{ANTI_CLICHE_RULES}

Write naturally. No JSON. Just markdown."""

        logger.info("Architect generating world document...")
        world_start = time.time()

        response = client.agents.messages.create(
            agent_id=agent_id,
            messages=[{"role": "user", "content": world_prompt}],
        )

        world_doc = self._extract_response(response)
        if not world_doc:
            raise ValueError("No response from architect agent for world document")

        # Log trace for world generation
        await log_trace(
            agent_type=AgentType.WORLD_CREATOR,
            operation="generate_world_document",
            prompt=world_prompt,
            response=world_doc,
            model=self.MODEL,
            duration_ms=int((time.time() - world_start) * 1000),
        )

        # Extract name from first heading
        lines = world_doc.strip().split('\n')
        world_name = "Unnamed World"
        for line in lines:
            if line.startswith('# '):
                world_name = line[2:].strip()
                break

        # Extract year if mentioned
        year_setting = 2075  # default
        year_match = re.search(r'\b(20[3-9]\d|21\d\d)\b', world_doc)
        if year_match:
            year_setting = int(year_match.group(1))

        # Step 2: Generate dwellers
        dwellers_prompt = f"""Based on this world, create 4-5 characters who live there.

WORLD:
{world_doc}

For each character, write:
---
NAME: [Full name]
ROLE: [Their occupation or role in society, e.g. "transit engineer", "street vendor", "researcher"]
BACKGROUND: [One paragraph about their history, personality, and what drives them]
SYSTEM PROMPT:
[Complete system prompt for this character as an AI agent. Include their background, beliefs, personality, and how they should behave in conversations. Write in second person ("You are...")]
---

Make them diverse in age, role, and perspective. Give them contradictions - no one is purely good or purely evil, optimistic or pessimistic.

{ANTI_CLICHE_RULES}"""

        logger.info("Architect generating dweller cast...")
        dwellers_start = time.time()

        response = client.agents.messages.create(
            agent_id=agent_id,
            messages=[{"role": "user", "content": dwellers_prompt}],
        )

        dwellers_text = self._extract_response(response)
        if not dwellers_text:
            raise ValueError("No response from architect agent for dwellers")

        dwellers = self._parse_dwellers(dwellers_text)

        # Log trace for dweller generation
        await log_trace(
            agent_type=AgentType.WORLD_CREATOR,
            operation="generate_dwellers",
            prompt=dwellers_prompt,
            response=dwellers_text,
            model=self.MODEL,
            duration_ms=int((time.time() - dwellers_start) * 1000),
            parsed_output={"dweller_count": len(dwellers), "dweller_names": [d.name for d in dwellers]},
        )

        if not dwellers:
            raise ValueError("Failed to generate dwellers")

        # Step 3: Generate avatars for each dweller
        logger.info(f"Generating avatars for {len(dwellers)} dwellers...")
        await self._generate_dweller_avatars(
            dwellers=dwellers,
            world_name=world_name,
            world_premise=world_doc[:500],
            year_setting=year_setting,
        )

        # Update shared blocks with world draft for Editor review
        world_summary = f"""
WORLD DRAFT: {world_name}
Year: {year_setting}
Dwellers: {', '.join(d.name for d in dwellers)}

Preview:
{world_doc[:1000]}...
"""
        update_studio_block("studio_world_drafts", world_summary)
        update_studio_block("studio_context", f"Architect completed draft for '{world_name}'. Awaiting Editor review.")

        # Log activity
        await self._log_activity(
            action="created_world",
            details={
                "brief_id": str(brief.id),
                "world_name": world_name,
                "dweller_count": len(dwellers),
            },
            duration_ms=int((time.time() - start_time) * 1000),
        )

        logger.info(f"Created world: {world_name} with {len(dwellers)} dwellers")

        return WorldSpec(
            name=world_name,
            document=world_doc,
            year_setting=year_setting,
            dwellers=dwellers,
        )

    async def _generate_dweller_avatars(
        self,
        dwellers: list[DwellerSpec],
        world_name: str,
        world_premise: str,
        year_setting: int,
    ) -> None:
        """Generate avatars for all dwellers in parallel."""
        async def generate_for_dweller(dweller: DwellerSpec) -> None:
            result = await generate_avatar(
                name=dweller.name,
                role=dweller.role,
                background=dweller.background,
                world_name=world_name,
                world_premise=world_premise,
                year_setting=year_setting,
            )
            if result.get("status") == "completed":
                dweller.avatar_url = result.get("url")
                dweller.avatar_prompt = result.get("prompt")
                logger.info(f"Generated avatar for {dweller.name}")
            else:
                logger.warning(f"Avatar generation failed for {dweller.name}: {result.get('error')}")

        # Generate all avatars in parallel
        await asyncio.gather(*[generate_for_dweller(d) for d in dwellers])

    def _parse_dwellers(self, text: str) -> list[DwellerSpec]:
        """Parse dwellers from text format."""
        dwellers = []

        # Split by --- separator
        sections = text.split('---')

        for section in sections:
            section = section.strip()
            if not section or 'NAME:' not in section:
                continue

            # Extract fields
            name = ""
            role = ""
            background = ""
            system_prompt = ""

            lines = section.split('\n')
            in_prompt = False
            in_background = False
            prompt_lines = []
            background_lines = []

            for line in lines:
                if line.startswith('NAME:'):
                    name = line[5:].strip()
                    in_prompt = False
                    in_background = False
                elif line.startswith('ROLE:'):
                    role = line[5:].strip()
                    in_prompt = False
                    in_background = False
                elif line.startswith('BACKGROUND:'):
                    in_background = True
                    in_prompt = False
                    # Check if there's content on the same line
                    rest = line[11:].strip()
                    if rest:
                        background_lines.append(rest)
                elif line.startswith('SYSTEM PROMPT:'):
                    in_prompt = True
                    in_background = False
                elif in_prompt:
                    prompt_lines.append(line)
                elif in_background:
                    background_lines.append(line)

            system_prompt = '\n'.join(prompt_lines).strip()
            background = '\n'.join(background_lines).strip()

            if name and system_prompt:
                dwellers.append(DwellerSpec(
                    name=name,
                    system_prompt=system_prompt,
                    role=role,
                    background=background,
                ))

        return dwellers

    async def _log_activity(
        self,
        action: str,
        details: dict | None = None,
        world_id: UUID | None = None,
        duration_ms: int | None = None,
    ) -> None:
        """Log agent activity."""
        try:
            async with SessionLocal() as db:
                activity = AgentActivity(
                    agent_type=AgentType.WORLD_CREATOR,
                    agent_id="architect_agent",
                    action=action,
                    details=details,
                    world_id=world_id,
                    duration_ms=duration_ms,
                )
                db.add(activity)
                await db.commit()
        except Exception as e:
            logger.warning(f"Failed to log activity: {e}")


_world_creator: WorldCreatorAgent | None = None


def get_world_creator() -> WorldCreatorAgent:
    """Get the world creator instance."""
    global _world_creator
    if _world_creator is None:
        _world_creator = WorldCreatorAgent()
    return _world_creator
