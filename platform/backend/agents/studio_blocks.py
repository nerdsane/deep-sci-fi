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
    """Get block definitions for a specific world."""
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
            "value": "No dwellers registered yet.",
            "description": "Directory of dweller agents for multi-agent messaging",
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
) -> None:
    """Register a dweller in the world's directory for multi-agent messaging.

    Args:
        world_id: The world's UUID
        dweller_id: The dweller's UUID
        dweller_name: The dweller's name
        agent_id: The Letta agent ID
    """
    if world_id not in _world_blocks:
        raise ValueError(f"World blocks not initialized for {world_id}")

    # Get current directory
    current = get_world_block(world_id, f"dweller_directory_{world_id}")

    # Add new dweller entry
    entry = f"\n- {dweller_name} (dweller_{dweller_id}): agent_id={agent_id}"

    if "No dwellers registered" in current:
        new_value = f"Registered dwellers:{entry}"
    else:
        new_value = current + entry

    update_world_block(world_id, f"dweller_directory_{world_id}", new_value)
    logger.info(f"Registered dweller {dweller_name} in world {world_id} directory")


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
