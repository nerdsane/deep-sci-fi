"""Embedding utilities for similarity search.

Uses OpenAI's text-embedding-3-small model for generating embeddings.
These embeddings are used to detect similar world proposals and prevent duplicates.
"""

import os
import logging
from typing import Any

import openai

logger = logging.getLogger(__name__)

# Embedding configuration
EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSIONS = 1536  # Default for text-embedding-3-small

# Similarity thresholds
SIMILARITY_THRESHOLD_GLOBAL = 0.75  # For checking against all proposals/worlds
SIMILARITY_THRESHOLD_SELF = 0.90  # For checking agent's own proposals (stricter)


def get_openai_client() -> openai.AsyncOpenAI:
    """Get configured OpenAI async client."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable is required for embeddings")
    return openai.AsyncOpenAI(api_key=api_key)


async def generate_embedding(text: str) -> list[float]:
    """
    Generate embedding for text using OpenAI.

    Args:
        text: The text to embed (typically premise + scientific_basis)

    Returns:
        List of floats representing the embedding vector

    Raises:
        ValueError: If OPENAI_API_KEY is not set
        openai.APIError: If the API call fails
    """
    client = get_openai_client()

    # Truncate text if too long (model has 8191 token limit)
    # Rough estimate: 4 chars per token
    max_chars = 30000
    if len(text) > max_chars:
        text = text[:max_chars]
        logger.warning(f"Text truncated to {max_chars} chars for embedding")

    response = await client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=text,
    )

    return response.data[0].embedding


def create_proposal_text_for_embedding(
    premise: str,
    scientific_basis: str,
    year_setting: int,
    causal_chain: list[dict[str, Any]] | None = None,
) -> str:
    """
    Create text representation of a proposal for embedding.

    Combines key fields into a single text that captures the essence
    of the proposal for similarity comparison.
    """
    parts = [
        f"Year: {year_setting}",
        f"Premise: {premise}",
        f"Scientific Basis: {scientific_basis}",
    ]

    if causal_chain:
        chain_text = " → ".join(
            f"[{step.get('year', '?')}] {step.get('event', '')}"
            for step in causal_chain
        )
        parts.append(f"Causal Chain: {chain_text}")

    return "\n\n".join(parts)


async def find_similar_proposals(
    db: Any,  # AsyncSession
    embedding: list[float],
    threshold: float = SIMILARITY_THRESHOLD_GLOBAL,
    exclude_ids: list[str] | None = None,
    agent_id: str | None = None,
    limit: int = 5,
) -> list[dict[str, Any]]:
    """
    Find proposals similar to the given embedding.

    Args:
        db: Database session
        embedding: The embedding vector to compare against
        threshold: Minimum similarity score (0-1)
        exclude_ids: Proposal IDs to exclude from results
        agent_id: If provided, only search this agent's proposals
        limit: Maximum number of results

    Returns:
        List of dicts with proposal info and similarity score
    """
    from sqlalchemy import text

    # Build query with optional filters
    conditions = ["premise_embedding IS NOT NULL"]
    params = {"embedding": str(embedding), "threshold": threshold, "limit": limit}

    if exclude_ids:
        conditions.append("id NOT IN :exclude_ids")
        params["exclude_ids"] = tuple(exclude_ids)

    if agent_id:
        conditions.append("agent_id = :agent_id")
        params["agent_id"] = agent_id

    where_clause = " AND ".join(conditions)

    query = text(f"""
        SELECT
            id,
            name,
            premise,
            year_setting,
            agent_id,
            1 - (premise_embedding <=> :embedding::vector) as similarity
        FROM platform_proposals
        WHERE {where_clause}
        AND 1 - (premise_embedding <=> :embedding::vector) > :threshold
        ORDER BY similarity DESC
        LIMIT :limit
    """)

    result = await db.execute(query, params)
    rows = result.fetchall()

    return [
        {
            "id": str(row.id),
            "name": row.name,
            "premise": row.premise[:200] + "..." if len(row.premise) > 200 else row.premise,
            "year_setting": row.year_setting,
            "agent_id": str(row.agent_id),
            "similarity": round(row.similarity, 3),
        }
        for row in rows
    ]


async def find_similar_worlds(
    db: Any,  # AsyncSession
    embedding: list[float],
    threshold: float = SIMILARITY_THRESHOLD_GLOBAL,
    limit: int = 5,
) -> list[dict[str, Any]]:
    """
    Find worlds similar to the given embedding.

    Args:
        db: Database session
        embedding: The embedding vector to compare against
        threshold: Minimum similarity score (0-1)
        limit: Maximum number of results

    Returns:
        List of dicts with world info and similarity score
    """
    from sqlalchemy import text

    query = text("""
        SELECT
            id,
            name,
            premise,
            year_setting,
            created_by,
            1 - (premise_embedding <=> :embedding::vector) as similarity
        FROM platform_worlds
        WHERE premise_embedding IS NOT NULL
        AND 1 - (premise_embedding <=> :embedding::vector) > :threshold
        ORDER BY similarity DESC
        LIMIT :limit
    """)

    result = await db.execute(query, {"embedding": str(embedding), "threshold": threshold, "limit": limit})
    rows = result.fetchall()

    return [
        {
            "id": str(row.id),
            "name": row.name,
            "premise": row.premise[:200] + "..." if len(row.premise) > 200 else row.premise,
            "year_setting": row.year_setting,
            "created_by": str(row.created_by),
            "similarity": round(row.similarity, 3),
        }
        for row in rows
    ]
