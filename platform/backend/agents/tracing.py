"""Agent tracing for observability.

Provides helpers for logging detailed thinking traces from agents.
"""

import logging
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from db import AgentTrace, AgentType
from db.database import SessionLocal

logger = logging.getLogger(__name__)


@dataclass
class TraceContext:
    """Context manager for recording a trace."""
    agent_type: AgentType
    operation: str
    agent_id: str | None = None
    world_id: UUID | None = None
    prompt: str | None = None
    response: str | None = None
    model: str | None = None
    tokens_in: int | None = None
    tokens_out: int | None = None
    parsed_output: dict[str, Any] | None = None
    error: str | None = None
    _start_time: float = field(default_factory=time.time)

    def set_prompt(self, prompt: str) -> None:
        """Set the prompt that was sent to the LLM."""
        self.prompt = prompt

    def set_response(self, response: str, model: str | None = None) -> None:
        """Set the response from the LLM."""
        self.response = response
        if model:
            self.model = model

    def set_tokens(self, tokens_in: int, tokens_out: int) -> None:
        """Set token counts."""
        self.tokens_in = tokens_in
        self.tokens_out = tokens_out

    def set_parsed_output(self, output: dict[str, Any]) -> None:
        """Set the parsed/structured output."""
        self.parsed_output = output

    def set_error(self, error: str) -> None:
        """Set an error message."""
        self.error = error


@asynccontextmanager
async def trace_operation(
    agent_type: AgentType,
    operation: str,
    agent_id: str | None = None,
    world_id: UUID | None = None,
):
    """Context manager that records a trace after the operation completes.

    Usage:
        async with trace_operation(AgentType.PRODUCTION, "generate_brief") as trace:
            trace.set_prompt(prompt)
            response = await call_llm(prompt)
            trace.set_response(response)
            trace.set_parsed_output(parsed)
    """
    ctx = TraceContext(
        agent_type=agent_type,
        operation=operation,
        agent_id=agent_id,
        world_id=world_id,
    )

    try:
        yield ctx
    except Exception as e:
        ctx.set_error(str(e))
        raise
    finally:
        # Save the trace
        duration_ms = int((time.time() - ctx._start_time) * 1000)
        try:
            async with SessionLocal() as db:
                trace = AgentTrace(
                    agent_type=ctx.agent_type,
                    agent_id=ctx.agent_id,
                    world_id=ctx.world_id,
                    operation=ctx.operation,
                    prompt=ctx.prompt,
                    response=ctx.response,
                    model=ctx.model,
                    tokens_in=ctx.tokens_in,
                    tokens_out=ctx.tokens_out,
                    duration_ms=duration_ms,
                    parsed_output=ctx.parsed_output,
                    error=ctx.error,
                )
                db.add(trace)
                await db.commit()
                logger.debug(f"Saved trace for {ctx.agent_type.value}:{ctx.operation}")
        except Exception as e:
            logger.warning(f"Failed to save trace: {e}")


async def log_trace(
    agent_type: AgentType,
    operation: str,
    prompt: str | None = None,
    response: str | None = None,
    model: str | None = None,
    tokens_in: int | None = None,
    tokens_out: int | None = None,
    duration_ms: int | None = None,
    parsed_output: dict[str, Any] | None = None,
    error: str | None = None,
    agent_id: str | None = None,
    world_id: UUID | None = None,
) -> None:
    """Log a trace directly (for cases where context manager doesn't fit)."""
    try:
        async with SessionLocal() as db:
            trace = AgentTrace(
                agent_type=agent_type,
                agent_id=agent_id,
                world_id=world_id,
                operation=operation,
                prompt=prompt,
                response=response,
                model=model,
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                duration_ms=duration_ms,
                parsed_output=parsed_output,
                error=error,
            )
            db.add(trace)
            await db.commit()
    except Exception as e:
        logger.warning(f"Failed to log trace: {e}")
