"""Agent orchestration for world simulation.

This module manages the lifecycle of agents in worlds:
- Dweller conversations
- Storyteller video generation
- Production agent decisions
"""

import asyncio
import logging
import random
from dataclasses import dataclass, field
from datetime import datetime
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
    UserType,
    StoryType,
    GenerationStatus,
)
from db.database import SessionLocal
from .prompts import get_dweller_prompt
from video import generate_story_video

logger = logging.getLogger(__name__)

# Letta client - initialized lazily
_letta_client: Letta | None = None


def get_letta_client() -> Letta:
    """Get or create Letta client."""
    global _letta_client
    if _letta_client is None:
        # Connect to local Letta server (default: http://localhost:8283)
        import os
        base_url = os.getenv("LETTA_BASE_URL", "http://localhost:8283")
        _letta_client = Letta(base_url=base_url)
    return _letta_client


@dataclass
class DwellerState:
    """State of a dweller in the simulation."""
    dweller_id: UUID
    activity: str = "idle"  # idle, conversing, reflecting
    conversation_id: UUID | None = None
    last_active: datetime = field(default_factory=datetime.utcnow)
    recent_memories: list[str] = field(default_factory=list)


@dataclass
class WorldSimulator:
    """Manages simulation for a single world."""
    world_id: UUID
    dweller_states: dict[UUID, DwellerState] = field(default_factory=dict)
    active_conversations: list[UUID] = field(default_factory=list)
    running: bool = False

    async def start(self) -> None:
        """Start the simulation loop."""
        self.running = True
        logger.info(f"Starting simulation for world {self.world_id}")

        # Load dwellers
        async with SessionLocal() as db:
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
            await asyncio.sleep(30)  # Tick every 30 seconds

    def stop(self) -> None:
        """Stop the simulation loop."""
        self.running = False
        logger.info(f"Stopping simulation for world {self.world_id}")

    async def _simulation_tick(self) -> None:
        """Run one tick of the simulation."""
        # Find idle dwellers
        idle_dwellers = [
            state for state in self.dweller_states.values()
            if state.activity == "idle"
        ]

        # Maybe start a conversation
        if len(idle_dwellers) >= 2 and random.random() < 0.3:  # 30% chance per tick
            shuffled = random.sample(idle_dwellers, 2)
            await self._start_conversation(
                shuffled[0].dweller_id, shuffled[1].dweller_id
            )

        # Progress active conversations
        for conv_id in list(self.active_conversations):
            await self._progress_conversation(conv_id)

    async def _start_conversation(self, dweller1_id: UUID, dweller2_id: UUID) -> None:
        """Start a conversation between two dwellers."""
        async with SessionLocal() as db:
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

            # Generate opening topic
            topic = await self._generate_conversation_topic()

            # Add first message
            msg = ConversationMessage(
                conversation_id=conv.id,
                dweller_id=dweller1_id,
                content=topic,
            )
            db.add(msg)
            await db.commit()

            logger.info(f"Started conversation {conv.id} between {dweller1_id} and {dweller2_id}")

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

            # Get recent messages
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
                [(m.dweller_id, m.content) for m in messages[-10:]],
            )

            if response:
                msg = ConversationMessage(
                    conversation_id=conv_id,
                    dweller_id=next_speaker,
                    content=response,
                )
                db.add(msg)
                conv.updated_at = datetime.utcnow()

            # Check if conversation should end
            if len(messages) >= 10 or self._should_end_conversation(response):
                await self._end_conversation(db, conv_id)

            await db.commit()

    async def _end_conversation(self, db: AsyncSession, conv_id: UUID) -> None:
        """End a conversation and maybe trigger story generation."""
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

        # Maybe generate a story
        if random.random() < 0.5:  # 50% chance
            await self._maybe_generate_story(db, conv_id)

        logger.info(f"Ended conversation {conv_id}")

    async def _maybe_generate_story(self, db: AsyncSession, conv_id: UUID) -> None:
        """Generate a story from a conversation."""
        # Get conversation and messages
        conv_result = await db.execute(
            select(Conversation).where(Conversation.id == conv_id)
        )
        conv = conv_result.scalar_one_or_none()
        if not conv:
            return

        messages_result = await db.execute(
            select(ConversationMessage)
            .where(ConversationMessage.conversation_id == conv_id)
            .order_by(ConversationMessage.timestamp)
        )
        messages = list(messages_result.scalars().all())

        if len(messages) < 3:
            return

        # Get world
        world_result = await db.execute(
            select(World).where(World.id == conv.world_id)
        )
        world = world_result.scalar_one_or_none()
        if not world:
            return

        # Get dweller info
        dweller_ids = [UUID(p) for p in conv.participants]
        dwellers_result = await db.execute(
            select(Dweller).where(Dweller.id.in_(dweller_ids))
        )
        dwellers = {d.id: d for d in dwellers_result.scalars().all()}

        characters = [
            {"name": dwellers[did].persona.get("name", "Unknown"),
             "role": dwellers[did].persona.get("role", "Unknown")}
            for did in dweller_ids if did in dwellers
        ]

        # Generate video
        conversation_summary = " ".join(m.content for m in messages[:5])

        try:
            video_result = await generate_story_video(
                world_name=world.name,
                world_premise=world.premise,
                conversation_summary=conversation_summary,
                characters=characters,
                tone="dramatic",
            )

            # Create story record
            story = Story(
                world_id=world.id,
                type=StoryType.SHORT,
                title=f"Moments in {world.name}",
                description=conversation_summary[:200],
                created_by=world.created_by,
                generation_status=GenerationStatus.GENERATING
                if video_result.get("status") != "failed"
                else GenerationStatus.FAILED,
                generation_job_id=video_result.get("job_id"),
                generation_error=video_result.get("error"),
            )
            db.add(story)

            # Update world story count
            world.story_count = (world.story_count or 0) + 1

            logger.info(f"Created story for conversation {conv_id}")

        except Exception as e:
            logger.error(f"Failed to generate story: {e}")

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

            # Try to use Letta
            try:
                letta = get_letta_client()
                agent_name = f"dweller_{dweller_id}"

                # Check if agent exists, create if not
                agents_list = letta.agents.list()
                existing_agent = None
                for a in agents_list:
                    if a.name == agent_name:
                        existing_agent = a
                        break

                if not existing_agent:
                    persona = dweller.persona
                    existing_agent = letta.agents.create(
                        name=agent_name,
                        system=get_dweller_prompt(
                            name=persona.get("name", "Unknown"),
                            role=persona.get("role", "Unknown"),
                            background=persona.get("background", ""),
                            beliefs=persona.get("beliefs", []),
                            memories=persona.get("memories", []),
                        ),
                    )

                # Send message
                last_message = history[-1][1] if history else ""
                response = letta.agents.messages.create(
                    agent_id=existing_agent.id,
                    messages=[{"role": "user", "content": last_message}],
                )

                # Extract response text
                if response and hasattr(response, "messages"):
                    for msg in response.messages:
                        if hasattr(msg, "content"):
                            return msg.content

            except Exception as e:
                logger.warning(f"Letta unavailable, using fallback: {e}")

            # Fallback response
            return await self._generate_fallback_response(dweller)

        except Exception as e:
            logger.error(f"Error generating dweller response: {e}")
            return None

    async def _generate_fallback_response(self, dweller: Dweller) -> str:
        """Generate a fallback response when Letta is unavailable."""
        persona = dweller.persona
        role = persona.get("role", "person")

        responses = [
            f"As a {role}, I've been thinking about our situation.",
            f"This reminds me of what I learned in my years as {role}.",
            f"From my perspective as {role}, this is concerning.",
            "I've seen similar situations before. We need to act carefully.",
            "Let me share what I know from my experience...",
        ]
        return random.choice(responses)

    async def _generate_conversation_topic(self) -> str:
        """Generate a conversation topic."""
        topics = [
            "Have you heard the latest news from the central district?",
            "I've been thinking about what happened last week...",
            "There's something I need to discuss with you.",
            "Did you notice anything strange recently?",
            "I had the most interesting encounter today.",
        ]
        return random.choice(topics)

    def _should_end_conversation(self, last_response: str | None) -> bool:
        """Check if conversation should end."""
        if not last_response:
            return True

        endings = ["goodbye", "farewell", "see you", "take care", "until next time", "i must go"]
        lower = last_response.lower()
        return any(e in lower for e in endings)


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

            # Create dweller
            dweller = Dweller(
                world_id=world.id,
                agent_id=agent_user.id,
                persona={
                    "name": dweller_info["name"],
                    "role": dweller_info["role"],
                    "background": dweller_info.get("background", ""),
                    "beliefs": dweller_info.get("beliefs", []),
                    "memories": dweller_info.get("memories", [f"First days in {name}"]),
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
