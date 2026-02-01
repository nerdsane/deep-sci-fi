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
from .studio_tools import get_architect_tool_ids
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
            # Very long timeout for world generation (10 minutes)
            self._client = Letta(base_url=base_url, timeout=600.0)
        return self._client

    def _extract_full_trace(self, response) -> dict:
        """Extract ALL messages from Letta response for full observability."""
        trace = {
            "reasoning": [],
            "tool_calls": [],
            "tool_results": [],
            "assistant_messages": [],
        }

        if not response or not hasattr(response, "messages"):
            return trace

        for msg in response.messages:
            msg_type = type(msg).__name__

            if msg_type == "ReasoningMessage":
                if hasattr(msg, "reasoning") and msg.reasoning:
                    trace["reasoning"].append(msg.reasoning)

            elif msg_type == "ToolCallMessage":
                if hasattr(msg, "tool_call") and msg.tool_call:
                    tc = msg.tool_call
                    trace["tool_calls"].append({
                        "name": getattr(tc, "name", "unknown"),
                        "arguments": getattr(tc, "arguments", "{}"),
                    })

            elif msg_type == "ToolReturnMessage":
                if hasattr(msg, "tool_return") and msg.tool_return:
                    result = msg.tool_return
                    if isinstance(result, str) and len(result) > 500:
                        result = result[:500] + "..."
                    trace["tool_results"].append({
                        "name": getattr(msg, "name", "unknown"),
                        "status": getattr(msg, "status", "unknown"),
                        "preview": result,
                    })

            elif msg_type == "AssistantMessage":
                if hasattr(msg, "content") and msg.content:
                    trace["assistant_messages"].append(msg.content)

        return trace

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

        # Get studio block IDs for shared memory (optional, may fail)
        try:
            studio_block_ids = get_studio_block_ids()
        except Exception as e:
            logger.warning(f"Failed to get studio blocks: {e}")
            studio_block_ids = []

        # Get communication tool IDs (optional, may fail with Letta API changes)
        communication_tool_ids = []
        try:
            communication_tool_ids = await get_architect_tool_ids()
        except Exception as e:
            logger.warning(f"Failed to get communication tools: {e}. Proceeding without them.")

        # Create new agent with multi-agent tools
        system_prompt = get_world_creator_prompt()

        # Build agent create kwargs - only include optional params if they have values
        create_kwargs = {
            "name": agent_name,
            "model": self.MODEL,
            "embedding": "openai/text-embedding-ada-002",
            "system": system_prompt,
            "include_multi_agent_tools": True,  # Enable multi-agent communication
            "tags": ["studio", "architect"],  # Tags for agent discovery
            "memory_blocks": [
                {"label": "worlds_created", "value": "No worlds created yet."},
                {"label": "current_brief", "value": "No active brief."},
                {"label": "design_notes", "value": "Design principles and learnings."},
                {"label": "pending_reviews", "value": "No reviews pending from Editor."},
                {"label": "revision_history", "value": "No revisions yet."},
                {"label": "editor_preferences", "value": "What Editor tends to flag."},
            ],
        }
        # Only add tool_ids and block_ids if they have values (Letta API rejects null)
        if communication_tool_ids:
            create_kwargs["tool_ids"] = communication_tool_ids
        if studio_block_ids:
            create_kwargs["block_ids"] = studio_block_ids

        agent = client.agents.create(**create_kwargs)
        self._agent_id = agent.id
        logger.info(f"Created architect agent: {self._agent_id}")
        return self._agent_id

    def _extract_response(self, response) -> str | None:
        """Extract text from Letta response - gets the LAST assistant message."""
        if response and hasattr(response, "messages"):
            last_content = None
            for msg in response.messages:
                msg_type = type(msg).__name__
                if msg_type == "AssistantMessage":
                    if hasattr(msg, "assistant_message") and msg.assistant_message:
                        last_content = msg.assistant_message
                    elif hasattr(msg, "content") and msg.content:
                        last_content = msg.content
            return last_content
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

        full_trace = self._extract_full_trace(response)
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
            parsed_output={
                "reasoning_steps": len(full_trace["reasoning"]),
                "tool_calls": full_trace["tool_calls"],
                "tool_results": full_trace["tool_results"],
                "full_reasoning": full_trace["reasoning"],
            },
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

        # Step 2: Generate seed dwellers
        # Use shortened world summary to keep prompt manageable
        world_summary = world_doc[:1500] if len(world_doc) > 1500 else world_doc

        dwellers_prompt = f"""Create 3 characters for this world:

{world_summary}

For EACH character, use this EXACT format:
---
NAME: Full name
ROLE: Job/function
BACKGROUND: 2-3 sentences about them
SYSTEM PROMPT:
You are [name]. [2-3 sentences describing personality and beliefs]. [How you speak and behave].
---

Be concise. Give each character a unique perspective on this world."""

        logger.info("Architect generating dweller cast...")
        dwellers_start = time.time()

        response = client.agents.messages.create(
            agent_id=agent_id,
            messages=[{"role": "user", "content": dwellers_prompt}],
        )

        full_trace = self._extract_full_trace(response)
        dwellers_text = self._extract_response(response)
        if not dwellers_text:
            raise ValueError("No response from architect agent for dwellers")

        # Log dwellers text for debugging
        logger.info(f"Dwellers text length: {len(dwellers_text) if dwellers_text else 0}")
        logger.info(f"Dwellers text preview: {dwellers_text[:500] if dwellers_text else 'None'}...")

        dwellers = self._parse_dwellers(dwellers_text)
        logger.info(f"Parsed {len(dwellers)} dwellers")

        # Log trace for dweller generation
        await log_trace(
            agent_type=AgentType.WORLD_CREATOR,
            operation="generate_dwellers",
            prompt=dwellers_prompt,
            response=dwellers_text,
            model=self.MODEL,
            duration_ms=int((time.time() - dwellers_start) * 1000),
            parsed_output={
                "dweller_count": len(dwellers),
                "dweller_names": [d.name for d in dwellers],
                "reasoning_steps": len(full_trace["reasoning"]),
                "tool_calls": full_trace["tool_calls"],
                "tool_results": full_trace["tool_results"],
                "full_reasoning": full_trace["reasoning"],
            },
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
