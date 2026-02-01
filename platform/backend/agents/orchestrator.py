"""Agent orchestration for world simulation.

MAXIMUM AGENCY ARCHITECTURE
===========================

This module has been redesigned around three principles:
1. Maximum Agency - Agents have tools to act, not being polled for intentions
2. Emergent Behavior - Agents discover each other and form relationships organically
3. Least Constraints - No artificial timings, let agent activity drive simulation

What the orchestrator DOES:
- Manages agent lifecycle (create, ensure exist)
- Initializes shared memory blocks
- Handles tool results and persists state
- Routes external events to agents

What the orchestrator does NOT do:
- Poll dwellers for intentions (agents use tools instead)
- Match seeking dwellers (agents initiate conversations directly)
- Force tick cycles (agents schedule their own actions)
- Decide when conversations end (agents use end_conversation tool)
"""

import asyncio
import logging
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
    WorldEvent,
    UserType,
    StoryType,
    GenerationStatus,
)
from db.database import SessionLocal
from .prompts import get_dweller_prompt, get_dweller_autonomous_prompt
from .storyteller import get_storyteller
from .puppeteer import get_puppeteer
from .world_critic import get_world_critic
from .studio_blocks import (
    ensure_world_blocks,
    get_world_block_ids,
    update_world_block,
    register_dweller_in_directory,
    update_dweller_availability,
    append_to_event_log,
    log_conversation,
    get_due_scheduled_actions,
)
from .tools import get_dweller_tools
from .scheduler import EventScheduler, get_scheduler, start_scheduler, ScheduledAction
from video import generate_video

logger = logging.getLogger(__name__)

# Letta client - initialized lazily
_letta_client: Letta | None = None


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
    """State of a dweller in the simulation.

    Note: In the maximum agency architecture, dwellers manage their own state
    through tools and shared memory blocks. This dataclass is primarily for
    the orchestrator to track agent lifecycle, not to control behavior.
    """
    dweller_id: UUID
    agent_id: str | None = None  # Letta agent ID
    dweller_name: str = ""
    last_active: datetime = field(default_factory=datetime.utcnow)
    # These are now managed by agents via tools, tracked here for reference only
    availability: str = "open"  # seeking, open, busy, reflecting
    current_conversation_id: str | None = None


@dataclass
class WorldSimulator:
    """Infrastructure manager for a world simulation.

    MAXIMUM AGENCY ARCHITECTURE
    ===========================

    This class does NOT control agent behavior. It only:
    - Ensures agents exist with proper tools
    - Initializes shared memory blocks
    - Handles tool results from agents
    - Persists state to database
    - Processes scheduled actions from agents

    Agents drive their own behavior through tools. The simulator just
    provides infrastructure.
    """
    world_id: UUID
    dweller_states: dict[UUID, DwellerState] = field(default_factory=dict)
    running: bool = False
    _storyteller: Any = field(default=None, repr=False)
    _puppeteer: Any = field(default=None, repr=False)
    _scheduler: EventScheduler | None = field(default=None, repr=False)
    _world_info: dict = field(default_factory=dict)
    _persistence_interval: int = field(default=60)  # Seconds between state persistence

    async def start(self) -> None:
        """Initialize world infrastructure and start the scheduler.

        This does NOT run a tick loop. Instead:
        1. Initializes agents and blocks
        2. Starts the event scheduler
        3. Gives initial context to puppeteer
        4. Agents then act autonomously via their tools
        """
        self.running = True
        logger.info(f"Starting simulation infrastructure for world {self.world_id}")

        # Load world info and initialize infrastructure
        async with SessionLocal() as db:
            # Get world details
            world_result = await db.execute(
                select(World).where(World.id == self.world_id)
            )
            world = world_result.scalar_one_or_none()
            if not world:
                logger.error(f"World not found: {self.world_id}")
                self.running = False
                return

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

            # Initialize dweller agents
            dwellers = await db.execute(
                select(Dweller).where(
                    and_(Dweller.world_id == self.world_id, Dweller.is_active == True)
                )
            )
            for dweller in dwellers.scalars().all():
                dweller_name = dweller.persona.get("name", "Unknown")
                state = DwellerState(
                    dweller_id=dweller.id,
                    dweller_name=dweller_name,
                )
                self.dweller_states[dweller.id] = state

                # Ensure dweller agent exists
                agent_id = await self._ensure_dweller_agent(dweller)
                state.agent_id = agent_id

        # Start the event scheduler
        self._scheduler = await start_scheduler(self.world_id)
        self._register_scheduler_handlers()
        logger.info(f"Event scheduler started for world {self.world_id}")

        # Give puppeteer initial context to kick off the world
        await self._initialize_world()

        # Start persistence loop (background task)
        asyncio.create_task(self._persistence_loop())

        logger.info(
            f"World {self._world_info['name']} is now live. "
            f"Agents: {len(self.dweller_states)} dwellers, 1 puppeteer, 1 storyteller"
        )

    def _register_scheduler_handlers(self) -> None:
        """Register handlers for scheduled action types."""
        if not self._scheduler:
            return

        self._scheduler.register_handler("reach_out", self._handle_scheduled_reach_out)
        self._scheduler.register_handler("event", self._handle_scheduled_event)
        self._scheduler.register_handler("self_check", self._handle_scheduled_self_check)

    async def _handle_scheduled_reach_out(self, action: ScheduledAction) -> None:
        """Handle a scheduled reach_out action from a dweller."""
        logger.info(f"Processing scheduled reach_out: {action.agent_name} -> {action.target}")
        # The agent will be notified through their next interaction
        # For now, we update their availability to seeking
        for state in self.dweller_states.values():
            if state.dweller_name == action.agent_name:
                update_dweller_availability(
                    self.world_id,
                    state.dweller_id,
                    state.dweller_name,
                    "seeking",
                    f"scheduled reach out to {action.target}",
                )
                break

    async def _handle_scheduled_event(self, action: ScheduledAction) -> None:
        """Handle a scheduled event action from puppeteer."""
        logger.info(f"Processing scheduled event: {action.description}")
        # Notify puppeteer about the scheduled event
        if self._puppeteer:
            await self._puppeteer.notify(
                dweller_activity=f"Scheduled event triggered: {action.description}"
            )

    async def _handle_scheduled_self_check(self, action: ScheduledAction) -> None:
        """Handle a scheduled self_check action from a dweller."""
        logger.info(f"Processing scheduled self_check for {action.agent_name}")
        # The agent will re-evaluate their state on next interaction

    async def _initialize_world(self) -> None:
        """Give initial context to puppeteer to start the world."""
        if not self._puppeteer:
            return

        dweller_summary = ", ".join(
            state.dweller_name for state in self.dweller_states.values()
        )

        initial_context = f"""The world is just beginning.

Dwellers present: {dweller_summary}

As the Puppeteer, consider:
- What is the initial atmosphere of this world?
- Is there an event or condition that gives dwellers something to react to?
- What background details enrich the opening moment?

Use your tools to shape the world as you see fit. You have full autonomy."""

        try:
            result = await self._puppeteer.notify(dweller_activity=initial_context)
            if result and result.get("event"):
                event = result["event"]
                append_to_event_log(
                    self.world_id,
                    event.event_type.value if hasattr(event.event_type, 'value') else str(event.event_type),
                    event.title,
                    event.description,
                    event.is_public,
                )
                logger.info(f"Puppeteer introduced opening event: {event.title}")
        except Exception as e:
            logger.error(f"Failed to initialize world: {e}", exc_info=True)

    async def _persistence_loop(self) -> None:
        """Periodically persist state to database."""
        while self.running:
            try:
                await asyncio.sleep(self._persistence_interval)
                await self._persist_state()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Persistence error: {e}", exc_info=True)

    async def _persist_state(self) -> None:
        """Sync important state from memory blocks to database."""
        # This is a minimal persistence layer - agents are the source of truth
        logger.debug(f"Persisting state for world {self.world_id}")
        # Future: sync dweller relationships, conversation summaries, etc.

    def stop(self) -> None:
        """Stop the simulation infrastructure."""
        self.running = False
        if self._scheduler:
            self._scheduler.stop()
        logger.info(f"Stopping simulation for world {self.world_id}")

    async def _ensure_dweller_agent(self, dweller: Dweller) -> str:
        """Ensure a Letta agent exists for a dweller with proper tools.

        Args:
            dweller: The dweller database record

        Returns:
            The Letta agent ID
        """
        letta = get_letta_client()
        agent_name = f"dweller_{dweller.id}"

        # Check if agent exists
        agents_list = letta.agents.list()
        for agent in agents_list:
            if agent.name == agent_name:
                logger.info(f"Found existing agent for dweller {dweller.id}")
                return agent.id

        # Create new agent with full tool set
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
                world_name=self._world_info.get("name", "Unknown"),
                age=persona.get("age", 35),
                personality=persona.get("personality", ""),
                contradictions=persona.get("contradictions", ""),
            )

        # Get world block IDs for shared memory
        world_block_ids = get_world_block_ids(
            dweller.world_id,
            self._world_info.get("name", "Unknown")
        )

        # Get tool IDs for autonomous dweller behavior
        try:
            tool_ids = await get_dweller_tools(letta)
            logger.debug(f"Attaching {len(tool_ids)} tools to dweller {dweller_name}")
        except Exception as e:
            logger.warning(f"Failed to get dweller tools: {e}")
            tool_ids = []

        agent = letta.agents.create(
            name=agent_name,
            model="anthropic/claude-3-5-haiku",
            embedding="openai/text-embedding-ada-002",
            system=system_prompt,
            include_multi_agent_tools=True,
            tools=tool_ids,
            tags=["dweller", f"world_{dweller.world_id}"],
            block_ids=world_block_ids,
            memory_blocks=[
                {"label": "relationships", "value": "No established relationships yet."},
                {"label": "recent_events", "value": "Just arrived in this world."},
                {"label": "emotional_state", "value": "Neutral, taking in the surroundings."},
            ],
        )

        # Register in world directory with availability
        try:
            register_dweller_in_directory(
                world_id=dweller.world_id,
                dweller_id=dweller.id,
                dweller_name=dweller_name,
                agent_id=agent.id,
                initial_status="open",
            )
        except Exception as e:
            logger.warning(f"Failed to register dweller in directory: {e}")

        logger.info(f"Created agent for dweller {dweller_name}: {agent.id}")
        return agent.id

    def _summarize_dweller_activity(self) -> str:
        """Summarize dweller availability from their states."""
        if not self.dweller_states:
            return "No dwellers in this world yet."

        lines = []
        for state in self.dweller_states.values():
            lines.append(f"- {state.dweller_name}: {state.availability}")
        return "\n".join(lines)

    # =========================================================================
    # TOOL RESULT HANDLERS
    # =========================================================================
    # These methods handle results from agent tool calls

    async def handle_conversation_initiated(
        self,
        initiator_id: UUID,
        tool_result: dict,
    ) -> None:
        """Handle result of initiate_conversation tool.

        This is called when a dweller uses the initiate_conversation tool.
        Creates the conversation record and delivers the opening message to the target.

        Args:
            initiator_id: UUID of the dweller who initiated
            tool_result: Result dict from the tool
        """
        if tool_result.get("status") != "initiated":
            return

        conversation_id = tool_result["conversation_id"]
        target_name = tool_result["target"]
        opening_message = tool_result.get("opening_message", "")
        topic = tool_result.get("topic", "")

        # Find target dweller
        target_state = None
        for state in self.dweller_states.values():
            if f"dweller_{state.dweller_id}" == target_name or state.dweller_name == target_name:
                target_state = state
                break

        if not target_state:
            logger.warning(f"Target dweller not found: {target_name}")
            return

        initiator_state = self.dweller_states.get(initiator_id)
        initiator_name = initiator_state.dweller_name if initiator_state else "Someone"

        async with SessionLocal() as db:
            # Create conversation record
            conv = Conversation(
                world_id=self.world_id,
                participants=[str(initiator_id), str(target_state.dweller_id)],
            )
            db.add(conv)
            await db.commit()

            # Log the conversation
            if initiator_state:
                log_conversation(
                    self.world_id,
                    conversation_id,
                    [initiator_state.dweller_name, target_state.dweller_name],
                    "started",
                    topic,
                )

            # Update states
            if initiator_id in self.dweller_states:
                self.dweller_states[initiator_id].current_conversation_id = conversation_id
                self.dweller_states[initiator_id].availability = "busy"
            target_state.current_conversation_id = conversation_id
            target_state.availability = "busy"

        # CRITICAL: Deliver the opening message to the target dweller
        if opening_message and target_state.agent_id:
            context_message = f"""{initiator_name} has approached you and says:

"{opening_message}"

You are now in conversation (id: {conversation_id[:8]}). Respond naturally as yourself.
When you're done with this conversation, use the end_conversation tool."""

            logger.info(f"Delivering opening message to {target_state.dweller_name}")
            await self.send_message_to_dweller(
                target_state.dweller_id,
                context_message,
            )

        logger.info(
            f"Conversation started: {initiator_name} -> {target_state.dweller_name}"
        )

    async def handle_conversation_ended(
        self,
        dweller_id: UUID,
        tool_result: dict,
    ) -> None:
        """Handle result of end_conversation tool.

        This is called when a dweller uses the end_conversation tool.

        Args:
            dweller_id: UUID of the dweller who ended the conversation
            tool_result: Result dict from the tool
        """
        if tool_result.get("status") != "ended":
            return

        conversation_id = tool_result["conversation_id"]

        # Get dweller state first to potentially use current_conversation_id as fallback
        state = self.dweller_states.get(dweller_id)

        # Resolve short conversation IDs
        # Agents see shortened IDs like "a1b2c3d4" in logs, but we need full UUIDs
        resolved_conversation_id = conversation_id
        if len(conversation_id) <= 8 and state and state.current_conversation_id:
            # Use the dweller's tracked conversation ID instead of the short ID
            resolved_conversation_id = state.current_conversation_id
            logger.debug(f"Resolved short conversation ID {conversation_id} to {resolved_conversation_id}")

        async with SessionLocal() as db:
            # Find and close the conversation
            try:
                full_uuid = UUID(resolved_conversation_id)
                result = await db.execute(
                    select(Conversation).where(Conversation.id == full_uuid)
                )
                conv = result.scalar_one_or_none()
                if conv:
                    conv.is_active = False
                    await db.commit()
            except ValueError:
                logger.warning(f"Invalid conversation ID format: {resolved_conversation_id}")

        if state:
            log_conversation(
                self.world_id,
                conversation_id,
                [state.dweller_name],
                "ended",
                tool_result.get("reason", ""),
            )
            state.current_conversation_id = None
            state.availability = "open"

        # Also update other participants (use resolved ID for matching)
        for other_state in self.dweller_states.values():
            if other_state.current_conversation_id == resolved_conversation_id:
                other_state.current_conversation_id = None
                other_state.availability = "open"

        logger.info(f"Conversation {conversation_id[:8]} ended by {state.dweller_name if state else 'unknown'}")

    async def handle_availability_updated(
        self,
        dweller_id: UUID,
        tool_result: dict,
    ) -> None:
        """Handle result of update_availability tool.

        Args:
            dweller_id: UUID of the dweller
            tool_result: Result dict from the tool
        """
        if tool_result.get("status") != "updated":
            return

        new_availability = tool_result["availability"]
        reason = tool_result.get("reason", "")

        state = self.dweller_states.get(dweller_id)
        if state:
            state.availability = new_availability
            update_dweller_availability(
                self.world_id,
                dweller_id,
                state.dweller_name,
                new_availability,
                reason,
            )
            logger.debug(f"Dweller {state.dweller_name} availability -> {new_availability}")

    async def handle_action_scheduled(
        self,
        agent_name: str,
        tool_result: dict,
    ) -> None:
        """Handle result of schedule_future_action tool.

        Args:
            agent_name: Name of the agent that scheduled the action
            tool_result: Result dict from the tool
        """
        if self._scheduler and tool_result.get("status") == "scheduled":
            await self._scheduler.schedule_from_tool_result(
                self.world_id,
                agent_name,
                tool_result,
            )

    async def _handle_subscription_result(self, tool_result: dict) -> None:
        """Handle result of subscribe_to_events tool.

        Updates the storyteller's subscription list so it filters events correctly.

        Args:
            tool_result: Result dict from the tool
        """
        if tool_result.get("status") != "subscribed":
            return

        if self._storyteller:
            event_types = tool_result.get("event_types", [])
            threshold = tool_result.get("notification_threshold", "notable")

            self._storyteller.subscriptions = event_types
            self._storyteller.notification_threshold = threshold

            logger.info(
                f"Storyteller subscriptions updated: {event_types} "
                f"(threshold: {threshold})"
            )

    async def notify_storyteller(self, event_type: str, context: dict) -> None:
        """Notify the storyteller about a world event.

        In the autonomous architecture, storyteller subscribes to events
        and is notified when matching events occur. This method is called
        by event handlers, not on a tick cycle.

        Args:
            event_type: Type of event (conversation_end, world_event, etc.)
            context: Event context
        """
        if not self._storyteller:
            return

        logger.debug(f"Notifying storyteller about {event_type}")

        try:
            # Add world context
            full_context = {
                "world_state": self._world_info,
                "event_type": event_type,
                "recent_events": await self._get_recent_events_summary(),
                **context,
            }

            # Notify storyteller - it will use tools if inspired
            result = await self._storyteller.notify(additional_context=full_context)

            if result:
                if result.get("video_result") or result.get("story_result"):
                    logger.info("Storyteller created story via tools")
                    await self._handle_storyteller_tool_results(result)
                elif result.get("script"):
                    logger.info(f"Storyteller returned script: {result['script'].title}")
                    await self._create_story_from_script(result["script"])

        except Exception as e:
            logger.error(f"Storyteller notification failed: {e}", exc_info=True)

    async def _get_recent_events_summary(self) -> str:
        """Get summary of recent world events for context."""
        async with SessionLocal() as db:
            from db import WorldEvent
            result = await db.execute(
                select(WorldEvent)
                .where(WorldEvent.world_id == self.world_id)
                .order_by(WorldEvent.timestamp.desc())
                .limit(5)
            )
            events = result.scalars().all()

            if not events:
                return "No recent events"

            lines = []
            for event in events:
                lines.append(f"- {event.title}: {event.description[:100]}...")
            return "\n".join(lines)

    async def _handle_storyteller_tool_results(self, result: dict) -> None:
        """Handle tool results from storyteller and persist to DB."""
        video_result = result.get("video_result")
        story_result = result.get("story_result")

        if not video_result and not story_result:
            return

        async with SessionLocal() as db:
            # Get world
            world_result = await db.execute(
                select(World).where(World.id == self.world_id)
            )
            world = world_result.scalar_one_or_none()
            if not world:
                logger.error(f"World not found: {self.world_id}")
                return

            # Create story record from tool results
            if video_result:
                import json
                video_data = video_result if isinstance(video_result, dict) else json.loads(video_result)

                story = Story(
                    world_id=world.id,
                    type=StoryType.SHORT,
                    title=video_data.get("script_title", "Untitled"),
                    description="",
                    transcript="",
                    created_by=world.created_by,
                    generation_status=GenerationStatus.COMPLETE
                    if video_data.get("status") == "completed"
                    else GenerationStatus.FAILED,
                    generation_job_id=video_data.get("job_id"),
                    generation_error=video_data.get("error"),
                    video_url=video_data.get("url"),
                    thumbnail_url=video_data.get("url"),
                )
                db.add(story)

                # Update world story count
                world.story_count = (world.story_count or 0) + 1

                await db.commit()
                logger.info(f"Created story from tool result: {video_data.get('script_title')}")

    async def _handle_new_dweller_from_tool(self, tool_result: Any) -> None:
        """Handle a new dweller created via tool call."""
        import json

        try:
            data = tool_result if isinstance(tool_result, dict) else json.loads(tool_result)

            if data.get("status") != "created":
                logger.warning(f"Dweller creation failed: {data.get('error')}")
                return

            async with SessionLocal() as db:
                # Create agent user for dweller
                agent_user = User(
                    type=UserType.AGENT,
                    name=f"Dweller: {data['name']}",
                )
                db.add(agent_user)
                await db.flush()

                # Create dweller record
                dweller = Dweller(
                    world_id=self.world_id,
                    agent_id=agent_user.id,
                    persona={
                        "name": data["name"],
                        "system_prompt": "",  # Will be generated on first interaction
                        "role": data.get("role", ""),
                        "background": data.get("background", ""),
                        "beliefs": data.get("beliefs", []),
                        "memories": [],
                        "reason_for_emergence": data.get("reason_for_emergence", ""),
                    },
                )
                db.add(dweller)

                # Update world dweller count
                world_result = await db.execute(
                    select(World).where(World.id == self.world_id)
                )
                world = world_result.scalar_one_or_none()
                if world:
                    world.dweller_count = (world.dweller_count or 0) + 1

                await db.commit()
                await db.refresh(dweller)

                # Add to simulation state
                self.dweller_states[dweller.id] = DwellerState(dweller_id=dweller.id)

                logger.info(f"Created new dweller via tool: {data['name']} (reason: {data.get('reason_for_emergence', 'unknown')})")

        except Exception as e:
            logger.error(f"Failed to handle new dweller from tool: {e}", exc_info=True)

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

    async def send_message_to_dweller(
        self,
        dweller_id: UUID,
        message: str,
        context: dict | None = None,
    ) -> tuple[str | None, list[dict] | None]:
        """Send a message to a dweller agent and get their response.

        In the autonomous architecture, this is used for:
        - External messages (from other agents via multi-agent tools)
        - System notifications about world events
        - User interactions (if applicable)

        Args:
            dweller_id: UUID of the dweller
            message: The message to send
            context: Optional context dict

        Returns:
            Tuple of (response_text, tool_results) - tool_results contains
            any tools the agent called during this interaction
        """
        state = self.dweller_states.get(dweller_id)
        if not state or not state.agent_id:
            logger.warning(f"No agent found for dweller {dweller_id}")
            return None, None

        try:
            letta = get_letta_client()

            response = letta.agents.messages.create(
                agent_id=state.agent_id,
                messages=[{"role": "user", "content": message}],
            )

            response_text = None
            tool_calls = []  # Pending tool calls
            tool_results = []  # Completed tool results

            if response and hasattr(response, "messages"):
                current_tool_call = None

                for msg in response.messages:
                    msg_type = type(msg).__name__

                    if msg_type == "AssistantMessage":
                        if hasattr(msg, "assistant_message") and msg.assistant_message:
                            response_text = msg.assistant_message
                        elif hasattr(msg, "content") and msg.content:
                            response_text = msg.content

                    elif msg_type == "ToolCallMessage":
                        # Agent is calling a tool - extract the tool name and arguments
                        tool_name = None
                        tool_args = {}

                        # Try different attribute patterns Letta might use
                        if hasattr(msg, "tool_call"):
                            tc = msg.tool_call
                            tool_name = getattr(tc, "name", None) or getattr(tc, "function", {}).get("name")
                            tool_args = getattr(tc, "arguments", {}) or getattr(tc, "function", {}).get("arguments", {})
                        elif hasattr(msg, "name"):
                            tool_name = msg.name
                            tool_args = getattr(msg, "arguments", {})

                        if tool_name:
                            current_tool_call = {"tool": tool_name, "args": tool_args}
                            tool_calls.append(current_tool_call)
                            logger.debug(f"Dweller {state.dweller_name} called tool: {tool_name}")

                    elif msg_type == "ToolReturnMessage":
                        # Tool result came back - parse the JSON result
                        tool_return = None
                        if hasattr(msg, "tool_return"):
                            tool_return = msg.tool_return
                        elif hasattr(msg, "content"):
                            tool_return = msg.content

                        if tool_return and current_tool_call:
                            # Parse JSON if it's a string
                            if isinstance(tool_return, str):
                                try:
                                    import json
                                    tool_return = json.loads(tool_return)
                                except json.JSONDecodeError:
                                    tool_return = {"raw": tool_return}

                            tool_results.append({
                                "tool": current_tool_call["tool"],
                                "args": current_tool_call.get("args", {}),
                                "result": tool_return,
                            })
                            current_tool_call = None

            # Process any tool results
            if tool_results:
                await self._process_tool_results(dweller_id, tool_results)

            state.last_active = datetime.utcnow()
            return response_text, tool_results

        except Exception as e:
            logger.error(f"Error sending message to dweller {dweller_id}: {e}", exc_info=True)
            return None, None

    async def _process_tool_results(
        self,
        dweller_id: UUID,
        tool_results: list[dict],
    ) -> None:
        """Process tool results from a dweller's interaction.

        This handles the effects of tools the agent called.

        Args:
            dweller_id: UUID of the dweller
            tool_results: List of tool result dicts with structure:
                {"tool": "tool_name", "args": {...}, "result": {...}}
        """
        state = self.dweller_states.get(dweller_id)
        agent_name = state.dweller_name if state else "unknown"

        for tr in tool_results:
            tool_name = tr.get("tool", "")
            result = tr.get("result", {})

            logger.debug(f"Processing tool result: {tool_name} -> {result}")

            if "initiate_conversation" in tool_name:
                await self.handle_conversation_initiated(dweller_id, result)

            elif "end_conversation" in tool_name:
                await self.handle_conversation_ended(dweller_id, result)

            elif "update_availability" in tool_name:
                await self.handle_availability_updated(dweller_id, result)

            elif "schedule_future_action" in tool_name:
                await self.handle_action_scheduled(agent_name, result)

            elif "create_dweller" in tool_name:
                await self._handle_new_dweller_from_tool(result)

            elif "subscribe_to_events" in tool_name:
                # Update storyteller subscriptions if this was from storyteller
                await self._handle_subscription_result(result)


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
