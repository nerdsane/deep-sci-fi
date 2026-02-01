"""Shared memory blocks for Letta multi-agent communication.

This module manages shared memory blocks that enable agents to communicate
and share state using Letta's native multi-agent architecture.

Block Types:
- Studio blocks: Global blocks for Curator, Architect, Editor coordination
- World blocks: Per-world blocks for Puppeteer, Storyteller, Dwellers
"""

import logging
import os
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from letta_client import Letta

logger = logging.getLogger(__name__)

# Cached block IDs
_studio_blocks: dict[str, str] = {}
_world_blocks: dict[UUID, dict[str, str]] = {}


def get_letta_client() -> Letta:
    """Get Letta client."""
    base_url = os.getenv("LETTA_BASE_URL", "http://localhost:8285")
    return Letta(base_url=base_url)


# =============================================================================
# STUDIO BLOCKS (Global - shared by Curator, Architect, Editor)
# =============================================================================

STUDIO_BLOCK_DEFINITIONS = {
    "studio_briefs": {
        "label": "studio_briefs",
        "value": "No active briefs. Curator will add briefs here for Architect to process.",
        "description": "Production briefs from Curator for Architect to build worlds from",
    },
    "studio_world_drafts": {
        "label": "studio_world_drafts",
        "value": "No world drafts in progress.",
        "description": "World drafts from Architect awaiting Editor review",
    },
    "studio_evaluation_queue": {
        "label": "studio_evaluation_queue",
        "value": "No evaluations pending.",
        "description": "Content awaiting Editor evaluation",
    },
    "studio_context": {
        "label": "studio_context",
        "value": "Studio pipeline idle. Agents: Curator (research/briefs), Architect (world building), Editor (quality review).",
        "description": "Current state of the studio pipeline",
    },
}


def ensure_studio_blocks() -> dict[str, str]:
    """Ensure all studio blocks exist and return their IDs.

    Returns:
        Dict mapping block label to block ID
    """
    global _studio_blocks

    if _studio_blocks:
        return _studio_blocks

    client = get_letta_client()

    # Get existing blocks
    existing_blocks = client.blocks.list()
    existing_by_label = {b.label: b for b in existing_blocks}

    for label, definition in STUDIO_BLOCK_DEFINITIONS.items():
        if label in existing_by_label:
            _studio_blocks[label] = existing_by_label[label].id
            logger.info(f"Found existing studio block: {label} ({_studio_blocks[label]})")
        else:
            # Create the block
            block = client.blocks.create(
                label=definition["label"],
                value=definition["value"],
            )
            _studio_blocks[label] = block.id
            logger.info(f"Created studio block: {label} ({block.id})")

    return _studio_blocks


def get_studio_block_ids() -> list[str]:
    """Get list of studio block IDs for attaching to agents."""
    blocks = ensure_studio_blocks()
    return list(blocks.values())


def update_studio_block(label: str, value: str) -> None:
    """Update a studio block's value.

    Args:
        label: Block label (e.g., 'studio_briefs')
        value: New value for the block
    """
    blocks = ensure_studio_blocks()
    if label not in blocks:
        raise ValueError(f"Unknown studio block: {label}")

    client = get_letta_client()
    client.blocks.update(
        block_id=blocks[label],
        value=value,
    )
    logger.debug(f"Updated studio block {label}")


def get_studio_block(label: str) -> str:
    """Get current value of a studio block.

    Args:
        label: Block label

    Returns:
        Current value of the block
    """
    blocks = ensure_studio_blocks()
    if label not in blocks:
        raise ValueError(f"Unknown studio block: {label}")

    client = get_letta_client()
    block = client.blocks.retrieve(block_id=blocks[label])
    return block.value


# =============================================================================
# WORLD BLOCKS (Per-world - shared by Puppeteer, Storyteller, Dwellers)
# =============================================================================

def get_world_block_definitions(world_id: UUID, world_name: str) -> dict[str, dict]:
    """Get block definitions for a specific world.

    Block types for autonomous agent coordination:
    - world_state: Current world conditions (puppeteer writes, all read)
    - world_knowledge: Accumulated facts about the world
    - world_dweller_directory: Who exists and their availability status
    - world_event_log: Recent events (append-only)
    - world_conversation_log: Active and recent conversations
    - world_scheduled_actions: Agent-scheduled future actions
    """
    return {
        f"world_state_{world_id}": {
            "label": f"world_state_{world_id}",
            "value": f"World '{world_name}' just starting. No events yet.",
            "description": "Current world state: events, conditions, time of day",
        },
        f"world_knowledge_{world_id}": {
            "label": f"world_knowledge_{world_id}",
            "value": f"World '{world_name}' knowledge base. Facts will accumulate here.",
            "description": "Established facts about the world that all agents know",
        },
        f"world_dweller_directory_{world_id}": {
            "label": f"world_dweller_directory_{world_id}",
            "value": "DWELLER DIRECTORY\n================\nNo dwellers registered yet.\n\nFormat: name | status | reason | agent_id",
            "description": "Directory of dweller agents with their availability status",
        },
        f"world_event_log_{world_id}": {
            "label": f"world_event_log_{world_id}",
            "value": "EVENT LOG\n=========\nNo events yet.",
            "description": "Recent world events (newest first, max 20)",
        },
        f"world_conversation_log_{world_id}": {
            "label": f"world_conversation_log_{world_id}",
            "value": "CONVERSATION LOG\n================\nNo conversations yet.",
            "description": "Active and recent conversations between dwellers",
        },
        f"world_scheduled_actions_{world_id}": {
            "label": f"world_scheduled_actions_{world_id}",
            "value": "SCHEDULED ACTIONS\n=================\nNo scheduled actions.",
            "description": "Agent-scheduled future actions pending execution",
        },
    }


def ensure_world_blocks(world_id: UUID, world_name: str) -> dict[str, str]:
    """Ensure all blocks for a world exist and return their IDs.

    Args:
        world_id: The world's UUID
        world_name: The world's name (for initial values)

    Returns:
        Dict mapping block label to block ID
    """
    global _world_blocks

    if world_id in _world_blocks:
        return _world_blocks[world_id]

    client = get_letta_client()
    definitions = get_world_block_definitions(world_id, world_name)

    # Get existing blocks
    existing_blocks = client.blocks.list()
    existing_by_label = {b.label: b for b in existing_blocks}

    _world_blocks[world_id] = {}

    for label, definition in definitions.items():
        if label in existing_by_label:
            _world_blocks[world_id][label] = existing_by_label[label].id
            logger.info(f"Found existing world block: {label}")
        else:
            # Create the block
            block = client.blocks.create(
                label=definition["label"],
                value=definition["value"],
            )
            _world_blocks[world_id][label] = block.id
            logger.info(f"Created world block: {label} ({block.id})")

    return _world_blocks[world_id]


def get_world_block_ids(world_id: UUID, world_name: str) -> list[str]:
    """Get list of world block IDs for attaching to agents.

    Args:
        world_id: The world's UUID
        world_name: The world's name

    Returns:
        List of block IDs
    """
    blocks = ensure_world_blocks(world_id, world_name)
    return list(blocks.values())


def update_world_block(world_id: UUID, label_suffix: str, value: str) -> None:
    """Update a world block's value.

    Args:
        world_id: The world's UUID
        label_suffix: Block label suffix (e.g., 'state', 'knowledge', 'dweller_directory')
        value: New value for the block
    """
    full_label = f"world_{label_suffix}_{world_id}"

    if world_id not in _world_blocks:
        raise ValueError(f"World blocks not initialized for {world_id}")

    if full_label not in _world_blocks[world_id]:
        raise ValueError(f"Unknown world block: {full_label}")

    client = get_letta_client()
    client.blocks.update(
        block_id=_world_blocks[world_id][full_label],
        value=value,
    )
    logger.debug(f"Updated world block {full_label}")


def get_world_block(world_id: UUID, label_suffix: str) -> str:
    """Get current value of a world block.

    Args:
        world_id: The world's UUID
        label_suffix: Block label suffix

    Returns:
        Current value of the block
    """
    full_label = f"world_{label_suffix}_{world_id}"

    if world_id not in _world_blocks:
        raise ValueError(f"World blocks not initialized for {world_id}")

    if full_label not in _world_blocks[world_id]:
        raise ValueError(f"Unknown world block: {full_label}")

    client = get_letta_client()
    block = client.blocks.retrieve(block_id=_world_blocks[world_id][full_label])
    return block.value


def register_dweller_in_directory(
    world_id: UUID,
    dweller_id: UUID,
    dweller_name: str,
    agent_id: str,
    initial_status: str = "open",
) -> None:
    """Register a dweller in the world's directory with availability status.

    Args:
        world_id: The world's UUID
        dweller_id: The dweller's UUID
        dweller_name: The dweller's name
        agent_id: The Letta agent ID
        initial_status: Initial availability status (open, seeking, busy, reflecting)
    """
    if world_id not in _world_blocks:
        raise ValueError(f"World blocks not initialized for {world_id}")

    # Get current directory (suffix is just "dweller_directory", not including world_id)
    current = get_world_block(world_id, "dweller_directory")

    # Add new dweller entry with availability
    entry = f"\n{dweller_name} | {initial_status} | just arrived | agent_id={agent_id} | dweller_{dweller_id}"

    if "No dwellers registered" in current:
        new_value = f"DWELLER DIRECTORY\n================\n{entry}"
    else:
        new_value = current + entry

    update_world_block(world_id, "dweller_directory", new_value)
    logger.info(f"Registered dweller {dweller_name} in world {world_id} directory")


def update_dweller_availability(
    world_id: UUID,
    dweller_id: UUID,
    dweller_name: str,
    status: str,
    reason: str = "",
) -> None:
    """Update a dweller's availability status in the directory.

    Args:
        world_id: The world's UUID
        dweller_id: The dweller's UUID
        dweller_name: The dweller's name
        status: New status (seeking, open, busy, reflecting)
        reason: Why they're in this state
    """
    if world_id not in _world_blocks:
        raise ValueError(f"World blocks not initialized for {world_id}")

    current = get_world_block(world_id, "dweller_directory")

    # Find and update the dweller's entry
    lines = current.split("\n")
    updated_lines = []
    for line in lines:
        if f"dweller_{dweller_id}" in line:
            # Parse existing entry to preserve agent_id
            parts = line.split("|")
            if len(parts) >= 4:
                agent_info = parts[-1].strip()
                updated_line = f"{dweller_name} | {status} | {reason or 'no reason given'} | {agent_info}"
                updated_lines.append(updated_line)
            else:
                updated_lines.append(line)
        else:
            updated_lines.append(line)

    update_world_block(world_id, "dweller_directory", "\n".join(updated_lines))
    logger.debug(f"Updated dweller {dweller_name} availability to {status}")


def append_to_event_log(
    world_id: UUID,
    event_type: str,
    title: str,
    description: str,
    is_public: bool = True,
) -> None:
    """Append an event to the world's event log.

    Args:
        world_id: The world's UUID
        event_type: Type of event (environmental, societal, technological, background)
        title: Brief event title
        description: Event description
        is_public: Whether dwellers know about this
    """
    from datetime import datetime

    if world_id not in _world_blocks:
        raise ValueError(f"World blocks not initialized for {world_id}")

    current = get_world_block(world_id, "event_log")

    timestamp = datetime.utcnow().strftime("%H:%M")
    visibility = "PUBLIC" if is_public else "HIDDEN"
    entry = f"\n[{timestamp}] [{event_type.upper()}] [{visibility}] {title}: {description}"

    if "No events yet" in current:
        new_value = f"EVENT LOG\n=========\n{entry}"
    else:
        # Keep max 20 events
        lines = current.split("\n")
        header = lines[:2]
        events = lines[2:]
        events.insert(0, entry)
        events = events[:20]  # Keep newest 20
        new_value = "\n".join(header + events)

    update_world_block(world_id, "event_log", new_value)
    logger.debug(f"Added event to log: {title}")


def log_conversation(
    world_id: UUID,
    conversation_id: str,
    participants: list[str],
    status: str,
    topic: str = "",
) -> None:
    """Log a conversation in the world's conversation log.

    Args:
        world_id: The world's UUID
        conversation_id: The conversation ID
        participants: Names of participants
        status: Conversation status (started, ongoing, ended)
        topic: Optional conversation topic
    """
    from datetime import datetime

    if world_id not in _world_blocks:
        raise ValueError(f"World blocks not initialized for {world_id}")

    current = get_world_block(world_id, "conversation_log")

    timestamp = datetime.utcnow().strftime("%H:%M")
    participant_str = " & ".join(participants)
    topic_str = f" - {topic}" if topic else ""
    entry = f"\n[{timestamp}] [{status.upper()}] {participant_str}{topic_str} (id:{conversation_id[:8]})"

    if "No conversations yet" in current:
        new_value = f"CONVERSATION LOG\n================\n{entry}"
    else:
        # Keep max 15 conversations
        lines = current.split("\n")
        header = lines[:2]
        convos = lines[2:]
        convos.insert(0, entry)
        convos = convos[:15]
        new_value = "\n".join(header + convos)

    update_world_block(world_id, "conversation_log", new_value)
    logger.debug(f"Logged conversation: {participant_str} - {status}")


def schedule_action(
    world_id: UUID,
    action_id: str,
    agent_name: str,
    action_type: str,
    description: str,
    trigger_at: str,
    target: str = "",
) -> None:
    """Schedule a future action in the world.

    Args:
        world_id: The world's UUID
        action_id: Unique action ID
        agent_name: Agent that scheduled this
        action_type: Type of action (self_check, reach_out, event, reminder)
        description: What should happen
        trigger_at: ISO timestamp when to trigger
        target: Optional target of the action
    """
    if world_id not in _world_blocks:
        raise ValueError(f"World blocks not initialized for {world_id}")

    current = get_world_block(world_id, "scheduled_actions")

    target_str = f" -> {target}" if target else ""
    entry = f"\n[{trigger_at}] [{action_type.upper()}] {agent_name}{target_str}: {description} (id:{action_id[:8]})"

    if "No scheduled actions" in current:
        new_value = f"SCHEDULED ACTIONS\n=================\n{entry}"
    else:
        new_value = current + entry

    update_world_block(world_id, "scheduled_actions", new_value)
    logger.debug(f"Scheduled action: {action_type} by {agent_name}")


def get_due_scheduled_actions(world_id: UUID) -> list[dict]:
    """Get scheduled actions that are due for execution.

    Args:
        world_id: The world's UUID

    Returns:
        List of action dicts that are due
    """
    from datetime import datetime

    if world_id not in _world_blocks:
        return []

    current = get_world_block(world_id, "scheduled_actions")
    if "No scheduled actions" in current:
        return []

    now = datetime.utcnow()
    due_actions = []
    remaining_lines = []

    lines = current.split("\n")
    header = lines[:2]

    for line in lines[2:]:
        if not line.strip():
            continue
        # Parse: [timestamp] [TYPE] agent -> target: description (id:xxx)
        try:
            # Extract timestamp
            if line.startswith("["):
                timestamp_end = line.index("]")
                timestamp_str = line[1:timestamp_end]
                trigger_time = datetime.fromisoformat(timestamp_str)

                if trigger_time <= now:
                    # Parse rest of the line
                    rest = line[timestamp_end + 1:].strip()
                    type_start = rest.index("[") + 1
                    type_end = rest.index("]")
                    action_type = rest[type_start:type_end].lower()

                    due_actions.append({
                        "line": line,
                        "action_type": action_type,
                        "trigger_time": timestamp_str,
                    })
                else:
                    remaining_lines.append(line)
            else:
                remaining_lines.append(line)
        except (ValueError, IndexError):
            remaining_lines.append(line)

    # Update block to remove executed actions
    if due_actions:
        if remaining_lines:
            new_value = "\n".join(header + remaining_lines)
        else:
            new_value = "SCHEDULED ACTIONS\n=================\nNo scheduled actions."
        update_world_block(world_id, "scheduled_actions", new_value)

    return due_actions


# =============================================================================
# CLEANUP
# =============================================================================

def cleanup_world_blocks(world_id: UUID) -> None:
    """Clean up blocks for a world when simulation ends.

    Note: We don't delete blocks by default to preserve history.
    This just clears the cache.
    """
    global _world_blocks
    if world_id in _world_blocks:
        del _world_blocks[world_id]
        logger.info(f"Cleared world block cache for {world_id}")
