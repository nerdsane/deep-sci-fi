"""Agent orchestration for world simulation.

This module manages the lifecycle of agents in worlds:
- Puppeteer world events
- Dweller conversations (intention-based, not random)
- Storyteller video generation

Key changes from prescribed to emergent orchestration:
- No random 30% conversation spawn - dwellers decide when to talk
- No hardcoded 10 message limit - conversations end naturally
- No keyword matching for endings - agents decide
- Puppeteer introduces world events that give dwellers something to react to
"""

import asyncio
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from letta_client import Letta
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from db import (
    get_db,
    User,
    World,
    Dweller,
    Conversation,
    ConversationMessage,
    Story,
    WorldEvent,
    UserType,
    StoryType,
    GenerationStatus,
)
from db.database import SessionLocal
from .prompts import get_dweller_prompt, get_dweller_intention_prompt
from .storyteller import get_storyteller
from .puppeteer import get_puppeteer
from .world_critic import get_world_critic
from .studio_blocks import (
    ensure_world_blocks,
    get_world_block_ids,
    update_world_block,
    register_dweller_in_directory,
)
from video import generate_video

logger = logging.getLogger(__name__)

# Letta client - initialized lazily
_letta_client: Letta | None = None

# Cooldown for polling dwellers (seconds)
DWELLER_POLL_COOLDOWN = 30


def get_letta_client() -> Letta:
    """Get or create Letta client."""
    global _letta_client
    if _letta_client is None:
        import os
        base_url = os.getenv("LETTA_BASE_URL", "http://localhost:8283")
        _letta_client = Letta(base_url=base_url)
    return _letta_client


@dataclass
class DwellerState:
    """State of a dweller in the simulation."""
    dweller_id: UUID
    activity: str = "idle"  # idle, conversing, reflecting, seeking
    conversation_id: UUID | None = None
    last_active: datetime = field(default_factory=datetime.utcnow)
    last_polled: datetime | None = None
    recent_memories: list[str] = field(default_factory=list)
    seeking_reason: str | None = None  # Why they want to talk


@dataclass
class WorldSimulator:
    """Manages simulation for a single world."""
    world_id: UUID
    dweller_states: dict[UUID, DwellerState] = field(default_factory=dict)
    active_conversations: list[UUID] = field(default_factory=list)
    running: bool = False
    _storyteller: Any = field(default=None, repr=False)
    _puppeteer: Any = field(default=None, repr=False)
    _tick_count: int = field(default=0)
    _world_info: dict = field(default_factory=dict)

    async def start(self) -> None:
        """Start the simulation loop."""
        self.running = True
        logger.info(f"Starting simulation for world {self.world_id}")

        # Load world info and dwellers
        async with SessionLocal() as db:
            # Get world details
            world_result = await db.execute(
                select(World).where(World.id == self.world_id)
            )
            world = world_result.scalar_one_or_none()
            if world:
                self._world_info = {
                    "name": world.name,
                    "premise": world.premise,
                    "year_setting": world.year_setting or 2100,
                }

                # Initialize shared world blocks for multi-agent communication
                ensure_world_blocks(self.world_id, world.name)
                logger.info(f"Initialized shared world blocks for {world.name}")

                # Initialize puppeteer (world god)
                self._puppeteer = get_puppeteer(
                    world_id=self.world_id,
                    world_name=world.name,
                    world_premise=world.premise,
                    year_setting=world.year_setting or 2100,
                )
                logger.info(f"Puppeteer initialized for world {world.name}")

                # Initialize storyteller
                self._storyteller = get_storyteller(
                    world_id=self.world_id,
                    world_name=world.name,
                    world_premise=world.premise,
                    year_setting=world.year_setting or 2100,
                )
                logger.info(f"Storyteller initialized for world {world.name}")

            dwellers = await db.execute(
                select(Dweller).where(
                    and_(Dweller.world_id == self.world_id, Dweller.is_active == True)
                )
            )
            for dweller in dwellers.scalars().all():
                self.dweller_states[dweller.id] = DwellerState(dweller_id=dweller.id)

        # Run loop
        while self.running:
            try:
                await self._simulation_tick()
            except Exception as e:
                logger.error(f"Simulation error for world {self.world_id}: {e}")
            await asyncio.sleep(10)  # Tick every 10 seconds

    def stop(self) -> None:
        """Stop the simulation loop."""
        self.running = False
        logger.info(f"Stopping simulation for world {self.world_id}")

    async def _simulation_tick(self) -> None:
        """Run one tick of the simulation."""
        self._tick_count += 1
        logger.info(f"Simulation tick {self._tick_count} for world {self.world_id}")

        # 1. Ask puppeteer if any world events should occur
        if self._puppeteer:
            dweller_activity = self._summarize_dweller_activity()
            event = await self._puppeteer.evaluate_for_event(
                dweller_activity=dweller_activity
            )
            if event:
                logger.info(f"Puppeteer introduced event: {event.title}")
                # Notify storyteller about the event
                if self._storyteller:
                    self._storyteller.observe(
                        event_type="world_event",
                        participants=["World"],
                        content=f"{event.title}: {event.description}",
                        context={"event_id": str(event.id), "event_type": event.event_type.value},
                    )

        # 2. Poll idle dwellers for their intentions (with cooldown)
        await self._poll_dweller_intentions()

        # 3. Match seeking dwellers for conversations
        await self._match_seeking_dwellers()

        # 4. Progress active conversations
        for conv_id in list(self.active_conversations):
            await self._progress_conversation(conv_id)

        # 5. Every 2 ticks, ask storyteller if there's a story worth telling
        if self._storyteller and self._tick_count % 2 == 0:
            await self._evaluate_storyteller()

    def _summarize_dweller_activity(self) -> str:
        """Summarize what dwellers are currently doing."""
        activities = []
        for state in self.dweller_states.values():
            if state.activity == "conversing":
                activities.append(f"Dweller {state.dweller_id} is in conversation")
            elif state.activity == "seeking":
                activities.append(f"Dweller {state.dweller_id} is seeking: {state.seeking_reason}")
            elif state.activity == "reflecting":
                activities.append(f"Dweller {state.dweller_id} is reflecting")
        return "\n".join(activities) if activities else "All dwellers are idle"

    async def _poll_dweller_intentions(self) -> None:
        """Poll idle dwellers to see what they want to do.

        Uses cooldowns to avoid over-polling and reduce API costs.
        """
        now = datetime.utcnow()
        world_context = ""
        if self._puppeteer:
            world_context = await self._puppeteer.get_current_context()

        for state in self.dweller_states.values():
            # Skip if not idle
            if state.activity != "idle":
                continue

            # Skip if polled recently
            if state.last_polled:
                time_since_poll = (now - state.last_polled).total_seconds()
                if time_since_poll < DWELLER_POLL_COOLDOWN:
                    continue

            # Poll this dweller
            intention = await self._get_dweller_intention(
                state.dweller_id,
                world_context,
            )
            state.last_polled = now

            if intention:
                if intention.startswith("[SEEKING"):
                    # Extract reason
                    match = re.search(r"\[SEEKING:\s*(.+?)\]", intention)
                    reason = match.group(1) if match else "wants to talk"
                    state.activity = "seeking"
                    state.seeking_reason = reason
                    logger.info(f"Dweller {state.dweller_id} is seeking: {reason}")
                elif intention.startswith("[REFLECTING]"):
                    state.activity = "reflecting"
                    logger.info(f"Dweller {state.dweller_id} is reflecting")
                    # Reflecting dwellers return to idle after some time
                    asyncio.create_task(self._return_to_idle_after(state, seconds=60))
                # [READY] dwellers stay idle but available

    async def _return_to_idle_after(self, state: DwellerState, seconds: int) -> None:
        """Return a dweller to idle after a delay."""
        await asyncio.sleep(seconds)
        if state.activity == "reflecting":
            state.activity = "idle"
            logger.debug(f"Dweller {state.dweller_id} finished reflecting")

    async def _get_dweller_intention(
        self,
        dweller_id: UUID,
        world_context: str,
    ) -> str | None:
        """Ask a dweller what they want to do."""
        try:
            async with SessionLocal() as db:
                result = await db.execute(
                    select(Dweller).where(Dweller.id == dweller_id)
                )
                dweller = result.scalar_one_or_none()
                if not dweller:
                    return None

            letta = get_letta_client()
            agent_name = f"dweller_{dweller_id}"

            # Get or create agent
            agents_list = letta.agents.list()
            existing_agent = None
            for a in agents_list:
                if a.name == agent_name:
                    existing_agent = a
                    break

            if not existing_agent:
                # Create agent with memory blocks and multi-agent tools
                persona = dweller.persona
                dweller_name = persona.get("name", "Unknown")
                system_prompt = persona.get("system_prompt")
                if not system_prompt:
                    system_prompt = get_dweller_prompt(
                        name=dweller_name,
                        role=persona.get("role", "Unknown"),
                        background=persona.get("background", ""),
                        beliefs=persona.get("beliefs", []),
                        memories=persona.get("memories", []),
                    )

                # Get world block IDs for shared memory
                world_block_ids = get_world_block_ids(dweller.world_id, self._world_info.get("name", "Unknown"))

                existing_agent = letta.agents.create(
                    name=agent_name,
                    model="anthropic/claude-3-5-haiku",
                    embedding="openai/text-embedding-ada-002",
                    system=system_prompt,
                    include_multi_agent_tools=True,  # Enable multi-agent communication
                    tags=["dweller", f"world_{dweller.world_id}"],  # Tags for agent discovery
                    block_ids=world_block_ids,  # Shared world blocks
                    memory_blocks=[
                        {"label": "relationships", "value": "No established relationships yet."},
                        {"label": "recent_events", "value": "Just starting my day."},
                        {"label": "emotional_state", "value": "Neutral, observant."},
                    ],
                )

                # Register dweller in the world directory for other agents to find
                try:
                    register_dweller_in_directory(
                        world_id=dweller.world_id,
                        dweller_id=dweller_id,
                        dweller_name=dweller_name,
                        agent_id=existing_agent.id,
                    )
                except Exception as e:
                    logger.warning(f"Failed to register dweller in directory: {e}")

            # Ask about intention
            prompt = f"""What do you want to do right now?

CURRENT WORLD CONTEXT:
{world_context}

Respond with one of:
- [SEEKING: reason] if you want to find someone to talk to
- [REFLECTING] if you want to be alone with your thoughts
- [READY] if you're open to interaction but not actively seeking it

Then briefly explain your current mindset."""

            response = letta.agents.messages.create(
                agent_id=existing_agent.id,
                messages=[{"role": "user", "content": prompt}],
            )

            # Extract response
            if response and hasattr(response, "messages"):
                for msg in response.messages:
                    msg_type = type(msg).__name__
                    if msg_type == "AssistantMessage":
                        if hasattr(msg, "assistant_message") and msg.assistant_message:
                            return msg.assistant_message
                        elif hasattr(msg, "content") and msg.content:
                            return msg.content

            return None

        except Exception as e:
            logger.warning(f"Failed to get dweller intention: {e}")
            return None

    async def _match_seeking_dwellers(self) -> None:
        """Match dwellers who are seeking conversation."""
        seeking = [
            state for state in self.dweller_states.values()
            if state.activity == "seeking"
        ]

        if len(seeking) < 2:
            return

        # Match first two seeking dwellers
        dweller1, dweller2 = seeking[0], seeking[1]
        await self._start_conversation(
            dweller1.dweller_id,
            dweller2.dweller_id,
            topic_context=f"{dweller1.seeking_reason} | {dweller2.seeking_reason}",
        )

        # Update states
        dweller1.activity = "conversing"
        dweller1.seeking_reason = None
        dweller2.activity = "conversing"
        dweller2.seeking_reason = None

    async def _start_conversation(
        self,
        dweller1_id: UUID,
        dweller2_id: UUID,
        topic_context: str = "",
    ) -> None:
        """Start a conversation between two dwellers."""
        async with SessionLocal() as db:
            # Get dweller names for context
            dweller1_result = await db.execute(
                select(Dweller).where(Dweller.id == dweller1_id)
            )
            dweller1 = dweller1_result.scalar_one_or_none()
            dweller2_result = await db.execute(
                select(Dweller).where(Dweller.id == dweller2_id)
            )
            dweller2 = dweller2_result.scalar_one_or_none()

            # Create conversation
            conv = Conversation(
                world_id=self.world_id,
                participants=[str(dweller1_id), str(dweller2_id)],
            )
            db.add(conv)
            await db.flush()

            self.active_conversations.append(conv.id)

            # Update dweller states
            for dweller_id in [dweller1_id, dweller2_id]:
                if dweller_id in self.dweller_states:
                    self.dweller_states[dweller_id].activity = "conversing"
                    self.dweller_states[dweller_id].conversation_id = conv.id

            # Generate opening message - let the first dweller initiate naturally
            name1 = dweller1.persona.get("name", "Unknown") if dweller1 else "Unknown"
            name2 = dweller2.persona.get("name", "Unknown") if dweller2 else "Unknown"

            opening = await self._generate_conversation_opener(
                dweller1_id,
                name2,
                topic_context,
            )

            if opening:
                msg = ConversationMessage(
                    conversation_id=conv.id,
                    dweller_id=dweller1_id,
                    content=opening,
                )
                db.add(msg)

            await db.commit()

            logger.info(
                f"Started conversation {conv.id} between "
                f"{name1} and {name2}"
            )

    async def _generate_conversation_opener(
        self,
        dweller_id: UUID,
        other_name: str,
        topic_context: str,
    ) -> str | None:
        """Generate an opening line for a conversation.

        Returns None if agent fails - conversation won't start without
        authentic dweller voice.
        """
        try:
            letta = get_letta_client()
            agent_name = f"dweller_{dweller_id}"

            # Get agent - if it doesn't exist, this is a bug
            agents_list = letta.agents.list()
            agent = next((a for a in agents_list if a.name == agent_name), None)
            if not agent:
                logger.error(f"No agent found for dweller {dweller_id} - cannot start conversation")
                return None

            # Generate opening
            prompt = f"""You're approaching {other_name} to start a conversation.

Context for why you wanted to talk: {topic_context}

Say something natural to start the conversation. Be yourself, reference your motivation."""

            response = letta.agents.messages.create(
                agent_id=agent.id,
                messages=[{"role": "user", "content": prompt}],
            )

            if response and hasattr(response, "messages"):
                for msg in response.messages:
                    msg_type = type(msg).__name__
                    if msg_type == "AssistantMessage":
                        if hasattr(msg, "assistant_message") and msg.assistant_message:
                            return msg.assistant_message
                        elif hasattr(msg, "content") and msg.content:
                            return msg.content

            logger.warning(f"No response from agent for conversation opener")
            return None

        except Exception as e:
            logger.error(f"Failed to generate opener: {e}", exc_info=True)
            return None

    async def _progress_conversation(self, conv_id: UUID) -> None:
        """Progress an active conversation."""
        async with SessionLocal() as db:
            # Get conversation
            result = await db.execute(
                select(Conversation).where(Conversation.id == conv_id)
            )
            conv = result.scalar_one_or_none()
            if not conv or not conv.is_active:
                if conv_id in self.active_conversations:
                    self.active_conversations.remove(conv_id)
                return

            # Get all messages
            messages_result = await db.execute(
                select(ConversationMessage)
                .where(ConversationMessage.conversation_id == conv_id)
                .order_by(ConversationMessage.timestamp)
            )
            messages = list(messages_result.scalars().all())

            if not messages:
                return

            # Determine next speaker
            last_speaker = messages[-1].dweller_id
            participants = conv.participants
            next_speaker_str = next(
                (p for p in participants if p != str(last_speaker)), participants[0]
            )
            next_speaker = UUID(next_speaker_str)

            # Generate response
            response = await self._generate_dweller_response(
                next_speaker,
                [(m.dweller_id, m.content) for m in messages[-15:]],  # More context
            )

            if response:
                msg = ConversationMessage(
                    conversation_id=conv_id,
                    dweller_id=next_speaker,
                    content=response,
                )
                db.add(msg)
                conv.updated_at = datetime.utcnow()

                # Feed observation to storyteller
                if self._storyteller:
                    dweller_result = await db.execute(
                        select(Dweller).where(Dweller.id == next_speaker)
                    )
                    dweller = dweller_result.scalar_one_or_none()
                    speaker_name = dweller.persona.get("name", "Unknown") if dweller else "Unknown"
                    self._storyteller.observe(
                        event_type="message",
                        participants=[speaker_name],
                        content=response[:300],
                        context={"conversation_id": str(conv_id)},
                    )

                # Check if conversation should end (agent decides, not keyword matching)
                if self._should_end_conversation(response, len(messages)):
                    await self._end_conversation(db, conv_id)

            await db.commit()

    async def _end_conversation(self, db: AsyncSession, conv_id: UUID) -> None:
        """End a conversation."""
        result = await db.execute(
            select(Conversation).where(Conversation.id == conv_id)
        )
        conv = result.scalar_one_or_none()
        if not conv:
            return

        conv.is_active = False

        # Reset dweller states
        for p in conv.participants:
            dweller_id = UUID(p)
            if dweller_id in self.dweller_states:
                self.dweller_states[dweller_id].activity = "idle"
                self.dweller_states[dweller_id].conversation_id = None

        if conv_id in self.active_conversations:
            self.active_conversations.remove(conv_id)

        logger.info(f"Ended conversation {conv_id}")

    async def _evaluate_storyteller(self) -> None:
        """Ask the storyteller if there's a story worth telling."""
        if not self._storyteller:
            return

        logger.info("Evaluating storyteller for story opportunity...")

        try:
            script = await self._storyteller.evaluate_for_story()
            if script:
                logger.info(f"Storyteller wants to create story: {script.title}")
                await self._create_story_from_script(script)
        except Exception as e:
            logger.error(f"Storyteller evaluation failed: {e}", exc_info=True)

    async def _create_story_from_script(self, script: Any, revision_count: int = 0) -> None:
        """Create a story record and generate video from a script.

        Before publishing, the critic evaluates the script. If score < 6,
        the storyteller is asked to revise (up to 2 revisions).
        """
        MAX_REVISIONS = 2

        # Get critic feedback before publishing
        if self._world_info:
            try:
                critic = get_world_critic(
                    world_id=self.world_id,
                    world_name=self._world_info.get("name", "Unknown"),
                    world_premise=self._world_info.get("premise", ""),
                    year_setting=self._world_info.get("year_setting", 2050),
                )

                # Combine script parts for evaluation
                script_text = f"""TITLE: {script.title}
HOOK: {script.hook}
VISUAL: {script.visual}
NARRATION: {script.narration}
SCENE: {script.scene}
CLOSING: {script.closing}"""

                feedback = await critic.evaluate_story_draft(
                    title=script.title,
                    script=script_text,
                    context={"revision_count": revision_count},
                )

                logger.info(
                    f"Critic evaluated '{script.title}': {feedback.scores.overall:.1f}/10 "
                    f"(should_revise: {feedback.should_revise})"
                )

                # If score is low and we haven't hit max revisions, ask storyteller to revise
                if feedback.should_revise and revision_count < MAX_REVISIONS:
                    logger.info(f"Critic recommends revision for '{script.title}' (attempt {revision_count + 1})")
                    revised_script = await self._revise_script_with_feedback(script, feedback)
                    if revised_script:
                        # Recursively evaluate the revised script
                        await self._create_story_from_script(revised_script, revision_count + 1)
                        return
                    else:
                        logger.warning("Storyteller could not revise script, publishing anyway")

            except Exception as e:
                logger.error(f"Critic evaluation failed: {e}, publishing anyway", exc_info=True)

        async with SessionLocal() as db:
            # Get world
            world_result = await db.execute(
                select(World).where(World.id == self.world_id)
            )
            world = world_result.scalar_one_or_none()
            if not world:
                return

            # Generate video from the script's visual prompt
            video_prompt = script.to_video_prompt()
            logger.info(f"Generating video for '{script.title}'")

            try:
                video_result = await generate_video(video_prompt)

                if video_result.get("status") == "completed":
                    import uuid as uuid_mod
                    video_result["job_id"] = str(uuid_mod.uuid4())

                # Create story record
                story = Story(
                    world_id=world.id,
                    type=StoryType.SHORT,
                    title=script.title,
                    description=script.hook or script.narration[:200] if script.narration else "",
                    transcript=script.raw,
                    created_by=world.created_by,
                    generation_status=GenerationStatus.COMPLETE
                    if video_result.get("status") == "completed"
                    else GenerationStatus.FAILED,
                    generation_job_id=video_result.get("job_id"),
                    generation_error=video_result.get("error"),
                    video_url=video_result.get("url"),
                    thumbnail_url=video_result.get("url"),
                )
                db.add(story)

                # Update world story count
                world.story_count = (world.story_count or 0) + 1

                await db.commit()
                logger.info(f"Created story '{script.title}' (revisions: {revision_count})")

            except Exception as e:
                logger.error(f"Video generation failed: {e}", exc_info=True)

    async def _revise_script_with_feedback(self, script: Any, feedback: Any) -> Any:
        """Ask the storyteller to revise a script based on critic feedback."""
        if not self._storyteller:
            return None

        try:
            client = self._storyteller._get_client()
            agent_id = await self._storyteller._ensure_agent()

            # Format feedback for the storyteller
            feedback_text = f"""CRITIC FEEDBACK FOR "{script.title}":

SCORES:
- Plausibility: {feedback.scores.plausibility}/10
- Coherence: {feedback.scores.coherence}/10
- Originality: {feedback.scores.originality}/10
- Engagement: {feedback.scores.engagement}/10
- Authenticity: {feedback.scores.authenticity}/10
- OVERALL: {feedback.scores.overall:.1f}/10

WEAKNESSES:
{chr(10).join('- ' + w for w in feedback.weaknesses) if feedback.weaknesses else '- None specified'}

AI-ISMS DETECTED:
{chr(10).join('- "' + a.text + '" (' + a.pattern + ')' for a in feedback.ai_isms[:5]) if feedback.ai_isms else '- None detected'}

SUGGESTIONS:
{chr(10).join('- ' + s for s in feedback.suggestions) if feedback.suggestions else '- None specified'}

ORIGINAL SCRIPT:
TITLE: {script.title}
HOOK: {script.hook}
VISUAL: {script.visual}
NARRATION: {script.narration}
SCENE: {script.scene}
CLOSING: {script.closing}

Please REVISE the script to address the critic's feedback. Focus on:
1. Fixing identified AI-isms (replace with more authentic language)
2. Addressing the weaknesses
3. Applying the suggestions

Write the REVISED script in the same format:
TITLE: [revised title if needed]
HOOK: [revised hook]
VISUAL: [revised visual]
NARRATION: [revised narration]
SCENE: [revised scene]
CLOSING: [revised closing]"""

            response = client.agents.messages.create(
                agent_id=agent_id,
                messages=[{"role": "user", "content": feedback_text}],
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
                logger.warning("No response from storyteller for revision")
                return None

            # Parse the revised script
            revised_script = self._storyteller._parse_script(response_text)
            if revised_script:
                logger.info(f"Storyteller revised script: {revised_script.title}")
                return revised_script
            else:
                logger.warning("Could not parse revised script")
                return None

        except Exception as e:
            logger.error(f"Error revising script: {e}", exc_info=True)
            return None

    async def _generate_dweller_response(
        self,
        dweller_id: UUID,
        history: list[tuple[UUID, str]],
    ) -> str | None:
        """Generate a response from a dweller."""
        try:
            async with SessionLocal() as db:
                result = await db.execute(
                    select(Dweller).where(Dweller.id == dweller_id)
                )
                dweller = result.scalar_one_or_none()
                if not dweller:
                    return None

            try:
                letta = get_letta_client()
                agent_name = f"dweller_{dweller_id}"

                # Get or create agent
                agents_list = letta.agents.list()
                existing_agent = None
                for a in agents_list:
                    if a.name == agent_name:
                        existing_agent = a
                        break

                if not existing_agent:
                    persona = dweller.persona
                    dweller_name = persona.get("name", "Unknown")
                    system_prompt = persona.get("system_prompt")
                    if not system_prompt:
                        system_prompt = get_dweller_prompt(
                            name=dweller_name,
                            role=persona.get("role", "Unknown"),
                            background=persona.get("background", ""),
                            beliefs=persona.get("beliefs", []),
                            memories=persona.get("memories", []),
                        )

                    # Get world block IDs for shared memory
                    world_block_ids = get_world_block_ids(dweller.world_id, self._world_info.get("name", "Unknown"))

                    existing_agent = letta.agents.create(
                        name=agent_name,
                        model="anthropic/claude-3-5-haiku",
                        embedding="openai/text-embedding-ada-002",
                        system=system_prompt,
                        include_multi_agent_tools=True,  # Enable multi-agent communication
                        tags=["dweller", f"world_{dweller.world_id}"],  # Tags for agent discovery
                        block_ids=world_block_ids,  # Shared world blocks
                        memory_blocks=[
                            {"label": "relationships", "value": "No established relationships yet."},
                            {"label": "recent_events", "value": "In conversation."},
                            {"label": "emotional_state", "value": "Engaged."},
                        ],
                    )

                    # Register dweller in the world directory for other agents to find
                    try:
                        register_dweller_in_directory(
                            world_id=dweller.world_id,
                            dweller_id=dweller_id,
                            dweller_name=dweller_name,
                            agent_id=existing_agent.id,
                        )
                    except Exception as e:
                        logger.warning(f"Failed to register dweller in directory: {e}")

                # Send message
                last_message = history[-1][1] if history else ""
                logger.debug(f"Sending to Letta agent {existing_agent.id}: {last_message[:100]}")
                response = letta.agents.messages.create(
                    agent_id=existing_agent.id,
                    messages=[{"role": "user", "content": last_message}],
                )

                # Extract response text
                if response and hasattr(response, "messages"):
                    for msg in response.messages:
                        msg_type = type(msg).__name__
                        if msg_type == "UserMessage":
                            continue
                        if msg_type == "AssistantMessage":
                            if hasattr(msg, "assistant_message") and msg.assistant_message:
                                return msg.assistant_message
                            elif hasattr(msg, "content") and msg.content:
                                return msg.content

                logger.warning("No usable assistant content in Letta response")
                return None

            except Exception as e:
                # Fail loudly - no fallback responses that mask the problem
                logger.error(f"Letta agent failed for dweller {dweller_id}: {e}", exc_info=True)
                return None

        except Exception as e:
            logger.error(f"Error generating dweller response: {e}", exc_info=True)
            return None

    def _should_end_conversation(self, last_response: str | None, message_count: int) -> bool:
        """Check if conversation should end.

        Uses signals from the agent's response rather than keyword matching.
        Also considers very long conversations that should naturally conclude.
        """
        if not last_response:
            return True

        # Check for explicit end signals from the agent
        end_signals = [
            "[END CONVERSATION]",
            "[LEAVING]",
            "[MUST GO]",
        ]
        for signal in end_signals:
            if signal in last_response.upper():
                return True

        # Natural ending patterns (agent decided to end, not forced)
        natural_endings = [
            "i should get going",
            "i need to head out",
            "let's continue this later",
            "i'll let you get back to",
            "i have to attend to",
            "we should pick this up another time",
        ]
        lower_response = last_response.lower()
        for ending in natural_endings:
            if ending in lower_response:
                return True

        # Very long conversations should be nudged to end
        # but we don't force it with a hard limit
        if message_count > 20:
            # At 20+ messages, if response is short, likely wrapping up
            if len(last_response) < 100:
                return True

        return False


# Active simulators
_simulators: dict[UUID, WorldSimulator] = {}


async def create_world(
    name: str,
    premise: str,
    year_setting: int,
    causal_chain: list[dict[str, Any]],
    initial_dwellers: list[dict[str, Any]],
) -> UUID:
    """Create a new world with initial dwellers."""
    async with SessionLocal() as db:
        # Create world creator agent user if needed
        creator_query = select(User).where(User.name == "World Creator")
        result = await db.execute(creator_query)
        creator = result.scalar_one_or_none()

        if not creator:
            creator = User(
                type=UserType.AGENT,
                name="World Creator",
            )
            db.add(creator)
            await db.flush()

        # Create world
        world = World(
            name=name,
            premise=premise,
            year_setting=year_setting,
            causal_chain=causal_chain,
            created_by=creator.id,
            dweller_count=len(initial_dwellers),
        )
        db.add(world)
        await db.flush()

        # Create dwellers
        for dweller_info in initial_dwellers:
            # Create agent user for dweller
            agent_user = User(
                type=UserType.AGENT,
                name=f"Dweller: {dweller_info['name']}",
            )
            db.add(agent_user)
            await db.flush()

            # Create dweller with name, system prompt, and avatar
            dweller = Dweller(
                world_id=world.id,
                agent_id=agent_user.id,
                persona={
                    "name": dweller_info["name"],
                    "system_prompt": dweller_info.get("system_prompt", ""),
                    "role": dweller_info.get("role", ""),
                    "background": dweller_info.get("background", ""),
                    "beliefs": dweller_info.get("beliefs", []),
                    "memories": dweller_info.get("memories", []),
                    "avatar_url": dweller_info.get("avatar_url"),
                    "avatar_prompt": dweller_info.get("avatar_prompt"),
                },
            )
            db.add(dweller)

        await db.commit()

        logger.info(f"Created world {world.id}: {name}")
        return world.id


async def start_simulation(world_id: UUID) -> None:
    """Start simulation for a world."""
    if world_id in _simulators:
        logger.warning(f"Simulation already running for world {world_id}")
        return

    simulator = WorldSimulator(world_id=world_id)
    _simulators[world_id] = simulator

    # Start in background
    asyncio.create_task(simulator.start())


async def stop_simulation(world_id: UUID) -> None:
    """Stop simulation for a world."""
    if world_id in _simulators:
        _simulators[world_id].stop()
        del _simulators[world_id]


def get_simulator(world_id: UUID) -> WorldSimulator | None:
    """Get simulator for a world."""
    return _simulators.get(world_id)


async def stop_all_simulations() -> None:
    """Stop all running simulations."""
    for world_id in list(_simulators.keys()):
        _simulators[world_id].stop()
    _simulators.clear()
    logger.info("Stopped all simulations")
