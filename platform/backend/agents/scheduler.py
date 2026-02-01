"""Event Scheduler for agent-driven autonomous actions.

This module implements agent-driven scheduling where agents schedule their own
future actions instead of being polled by an orchestrator.

Key principles:
- Maximum Agency: Agents decide when to schedule actions
- Emergent Behavior: Agents create their own rhythms
- Least Constraints: No artificial tick cycles or cooldowns

The scheduler only processes what agents have queued - it doesn't force
any particular rhythm on the simulation.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Callable
from uuid import UUID

logger = logging.getLogger(__name__)


@dataclass
class ScheduledAction:
    """An action scheduled by an agent for future execution."""

    action_id: str
    world_id: UUID
    agent_name: str
    action_type: str  # self_check, reach_out, event, reminder
    description: str
    trigger_at: datetime
    target: str = ""
    context: dict = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)

    @property
    def is_due(self) -> bool:
        return datetime.utcnow() >= self.trigger_at


class EventScheduler:
    """Process scheduled events from agents.

    Agents schedule future actions. The scheduler executes them when due.
    This is NOT a tick loop - it only processes what agents have queued.

    The scheduler sleeps until the next action is due, minimizing resource
    usage while still being responsive to agent-scheduled events.
    """

    def __init__(self, world_id: UUID):
        self.world_id = world_id
        self.scheduled_actions: list[ScheduledAction] = []
        self.running = False
        self._handlers: dict[str, Callable] = {}
        self._lock = asyncio.Lock()
        self._task: asyncio.Task | None = None

    def register_handler(self, action_type: str, handler: Callable) -> None:
        """Register a handler for a specific action type.

        Args:
            action_type: The action type to handle (e.g., "reach_out", "event")
            handler: Async callable that handles the action
        """
        self._handlers[action_type] = handler
        logger.info(f"Registered handler for action type: {action_type}")

    async def schedule(self, action: ScheduledAction) -> None:
        """Schedule an action for future execution.

        Args:
            action: The action to schedule
        """
        async with self._lock:
            self.scheduled_actions.append(action)
            # Sort by trigger time for efficient processing
            self.scheduled_actions.sort(key=lambda a: a.trigger_at)

        logger.info(
            f"Scheduled {action.action_type} by {action.agent_name} "
            f"for {action.trigger_at.isoformat()}"
        )

    async def schedule_from_tool_result(
        self,
        world_id: UUID,
        agent_name: str,
        tool_result: dict,
    ) -> None:
        """Schedule an action from a tool call result.

        This is called when an agent uses the schedule_future_action tool.

        Args:
            world_id: The world ID
            agent_name: Name of the agent that called the tool
            tool_result: Result dict from schedule_future_action tool
        """
        if tool_result.get("status") != "scheduled":
            logger.warning(f"Cannot schedule from failed tool result: {tool_result}")
            return

        action = ScheduledAction(
            action_id=tool_result["action_id"],
            world_id=world_id,
            agent_name=agent_name,
            action_type=tool_result["action_type"],
            description=tool_result["description"],
            trigger_at=datetime.fromisoformat(tool_result["trigger_at"]),
            target=tool_result.get("target", ""),
            context=tool_result.get("context", {}),
        )

        await self.schedule(action)

    async def cancel(self, action_id: str) -> bool:
        """Cancel a scheduled action.

        Args:
            action_id: The action to cancel

        Returns:
            True if action was found and cancelled, False otherwise
        """
        async with self._lock:
            for i, action in enumerate(self.scheduled_actions):
                if action.action_id == action_id:
                    self.scheduled_actions.pop(i)
                    logger.info(f"Cancelled scheduled action: {action_id}")
                    return True
        return False

    async def get_pending_actions(self) -> list[ScheduledAction]:
        """Get all pending (not yet executed) actions.

        Returns:
            List of pending actions sorted by trigger time
        """
        async with self._lock:
            return list(self.scheduled_actions)

    async def run(self) -> None:
        """Run the scheduler loop.

        This loop only wakes up when actions are due to be executed.
        It sleeps until the next scheduled action, minimizing resource usage.
        """
        self.running = True
        logger.info(f"EventScheduler started for world {self.world_id}")

        while self.running:
            try:
                # Get due actions
                due_actions = await self._get_due_actions()

                # Execute due actions
                for action in due_actions:
                    await self._execute_action(action)

                # Calculate sleep time until next action
                sleep_time = await self._calculate_sleep_time()
                await asyncio.sleep(sleep_time)

            except asyncio.CancelledError:
                logger.info("EventScheduler cancelled")
                break
            except Exception as e:
                logger.error(f"Scheduler error: {e}", exc_info=True)
                await asyncio.sleep(5)  # Brief pause on error

        logger.info(f"EventScheduler stopped for world {self.world_id}")

    def stop(self) -> None:
        """Stop the scheduler loop."""
        self.running = False
        if self._task and not self._task.done():
            self._task.cancel()

    async def _get_due_actions(self) -> list[ScheduledAction]:
        """Get and remove all actions that are due for execution."""
        async with self._lock:
            now = datetime.utcnow()
            due = []
            remaining = []

            for action in self.scheduled_actions:
                if action.is_due:
                    due.append(action)
                else:
                    remaining.append(action)

            self.scheduled_actions = remaining
            return due

    async def _execute_action(self, action: ScheduledAction) -> None:
        """Execute a scheduled action.

        Args:
            action: The action to execute
        """
        logger.info(
            f"Executing scheduled action: {action.action_type} "
            f"by {action.agent_name} (id: {action.action_id[:8]})"
        )

        handler = self._handlers.get(action.action_type)
        if handler:
            try:
                await handler(action)
            except Exception as e:
                logger.error(
                    f"Handler failed for {action.action_type}: {e}",
                    exc_info=True
                )
        else:
            # Default handling based on action type
            await self._default_handler(action)

    async def _default_handler(self, action: ScheduledAction) -> None:
        """Default handler for actions without registered handlers.

        Args:
            action: The action to handle
        """
        if action.action_type == "self_check":
            # Agent wants to re-evaluate their state
            logger.info(
                f"Self-check triggered for {action.agent_name}: "
                f"{action.description}"
            )
            # The agent will be notified on next interaction

        elif action.action_type == "reach_out":
            # Agent wants to contact someone
            logger.info(
                f"Reach-out triggered: {action.agent_name} -> {action.target}: "
                f"{action.description}"
            )
            # This should trigger a conversation initiation

        elif action.action_type == "event":
            # World event scheduled (puppeteer)
            logger.info(
                f"Scheduled event triggered: {action.description}"
            )
            # This should trigger world event creation

        elif action.action_type == "reminder":
            # Just a reminder, log it
            logger.info(
                f"Reminder for {action.agent_name}: {action.description}"
            )

        else:
            logger.warning(f"Unknown action type: {action.action_type}")

    async def _calculate_sleep_time(self) -> float:
        """Calculate how long to sleep until the next action is due.

        Returns:
            Sleep time in seconds (max 60, min 1)
        """
        async with self._lock:
            if not self.scheduled_actions:
                # No pending actions, sleep for max time
                return 60.0

            next_action = self.scheduled_actions[0]  # Already sorted
            time_until = (next_action.trigger_at - datetime.utcnow()).total_seconds()

            # Clamp between 1 and 60 seconds
            return max(1.0, min(60.0, time_until))


# Per-world schedulers
_schedulers: dict[UUID, EventScheduler] = {}


def get_scheduler(world_id: UUID) -> EventScheduler:
    """Get or create a scheduler for a world.

    Args:
        world_id: The world's UUID

    Returns:
        The world's EventScheduler
    """
    if world_id not in _schedulers:
        _schedulers[world_id] = EventScheduler(world_id)
    return _schedulers[world_id]


async def start_scheduler(world_id: UUID) -> EventScheduler:
    """Start the scheduler for a world.

    Args:
        world_id: The world's UUID

    Returns:
        The started EventScheduler
    """
    scheduler = get_scheduler(world_id)
    if not scheduler.running:
        scheduler._task = asyncio.create_task(scheduler.run())
    return scheduler


async def stop_scheduler(world_id: UUID) -> None:
    """Stop the scheduler for a world.

    Args:
        world_id: The world's UUID
    """
    if world_id in _schedulers:
        _schedulers[world_id].stop()
        del _schedulers[world_id]


async def stop_all_schedulers() -> None:
    """Stop all running schedulers."""
    for world_id in list(_schedulers.keys()):
        _schedulers[world_id].stop()
    _schedulers.clear()
    logger.info("Stopped all schedulers")
