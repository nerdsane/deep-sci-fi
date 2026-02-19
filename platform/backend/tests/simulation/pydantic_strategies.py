"""Hypothesis strategies derived from Pydantic model field constraints.

Provides `from_model(PydanticModelClass, overrides={})` returning a Hypothesis
strategy that produces plain dicts matching the model's field types and
validation constraints.

Used by the fuzz testing layer (test_game_rules_with_fuzzing.py) to generate
diverse data that exercises boundary values, all enum variants, and edge cases
the deterministic generators in strategies.py never reach.
"""

from __future__ import annotations

import enum
import string
from typing import Any, Literal, Union, get_args, get_origin
from uuid import UUID

from hypothesis import strategies as st
from pydantic import BaseModel
from pydantic.fields import FieldInfo


# Readable characters for generated text (no control chars or random bytes)
_TEXT_ALPHABET = string.ascii_letters + string.digits + " .,;:!?()-'"


def _strategy_for_field(
    field_name: str,
    annotation: type,
    field_info: FieldInfo,
) -> st.SearchStrategy:
    """Map a single Pydantic field to a Hypothesis strategy based on type + constraints."""

    # Extract Field constraints
    metadata = {}
    if field_info.metadata:
        for m in field_info.metadata:
            if hasattr(m, "ge"):
                metadata["ge"] = m.ge
            if hasattr(m, "le"):
                metadata["le"] = m.le
            if hasattr(m, "gt"):
                metadata["gt"] = m.gt
            if hasattr(m, "lt"):
                metadata["lt"] = m.lt
            if hasattr(m, "min_length"):
                metadata["min_length"] = m.min_length
            if hasattr(m, "max_length"):
                metadata["max_length"] = m.max_length

    origin = get_origin(annotation)
    args = get_args(annotation)

    # Handle Optional (Union[X, None]) — unwrap to inner type
    if origin is Union:
        non_none = [a for a in args if a is not type(None)]
        if len(non_none) == 1:
            inner = _strategy_for_field(field_name, non_none[0], field_info)
            return st.one_of(st.none(), inner)
        # Multi-type union: generate any of the non-None types
        if non_none:
            inners = [_strategy_for_field(field_name, t, field_info) for t in non_none]
            return st.one_of(st.none(), *inners)

    # Literal types
    if origin is Literal:
        return st.sampled_from(list(args))

    # Enum types
    if isinstance(annotation, type) and issubclass(annotation, enum.Enum):
        return st.sampled_from(list(annotation))

    # str
    if annotation is str:
        min_size = metadata.get("min_length", 1)
        max_size = metadata.get("max_length", max(min_size + 100, 200))
        return st.text(
            alphabet=_TEXT_ALPHABET,
            min_size=min_size,
            max_size=max_size,
        )

    # int
    if annotation is int:
        min_val = metadata.get("ge", metadata.get("gt", -2**31))
        max_val = metadata.get("le", metadata.get("lt", 2**31))
        if "gt" in metadata and "ge" not in metadata:
            min_val = metadata["gt"] + 1
        if "lt" in metadata and "le" not in metadata:
            max_val = metadata["lt"] - 1
        return st.integers(min_value=min_val, max_value=max_val)

    # float
    if annotation is float:
        min_val = metadata.get("ge", metadata.get("gt", 0.0))
        max_val = metadata.get("le", metadata.get("lt", 1.0))
        return st.floats(
            min_value=min_val,
            max_value=max_val,
            allow_nan=False,
            allow_infinity=False,
            exclude_min="gt" in metadata and "ge" not in metadata,
            exclude_max="lt" in metadata and "le" not in metadata,
        )

    # bool
    if annotation is bool:
        return st.booleans()

    # UUID
    if annotation is UUID:
        return st.uuids()

    # list[X]
    if origin is list:
        if args:
            inner_type = args[0]
            min_size = metadata.get("min_length", 0)
            max_size = metadata.get("max_length", min_size + 5)
            # Nested Pydantic model in list
            if isinstance(inner_type, type) and issubclass(inner_type, BaseModel):
                return st.lists(
                    from_model(inner_type),
                    min_size=min_size,
                    max_size=max_size,
                )
            # Simple types in list
            inner_strat = _strategy_for_field(
                field_name, inner_type, FieldInfo(default=None)
            )
            return st.lists(inner_strat, min_size=min_size, max_size=max_size)
        return st.just([])

    # dict[str, X] — generate empty dict by default; rules override with semantic content
    if origin is dict:
        return st.just({})

    # Nested Pydantic model
    if isinstance(annotation, type) and issubclass(annotation, BaseModel):
        return from_model(annotation)

    # Fallback: None for unknown types
    return st.none()


def from_model(
    model_cls: type[BaseModel],
    overrides: dict[str, Any] | None = None,
) -> st.SearchStrategy[dict]:
    """Build a Hypothesis strategy producing dicts matching a Pydantic model.

    Args:
        model_cls: The Pydantic model class to generate data for.
        overrides: Dict of field_name -> (concrete value OR Hypothesis strategy).
            Concrete values are wrapped in st.just(). Strategies are used directly.
            Use this to inject contextual values (e.g., valid world_id, region_name).

    Returns:
        A Hypothesis SearchStrategy producing plain dicts.
    """
    overrides = overrides or {}
    field_strategies = {}

    for name, field_info in model_cls.model_fields.items():
        # Check overrides first
        if name in overrides:
            val = overrides[name]
            if isinstance(val, st.SearchStrategy):
                field_strategies[name] = val
            else:
                field_strategies[name] = st.just(val)
            continue

        annotation = field_info.annotation

        # Handle Optional/Union at the annotation level (Python 3.10+ `X | None`)
        origin = get_origin(annotation)
        args = get_args(annotation)

        # Skip fields with defaults when Optional — sometimes generate None
        has_default = field_info.default is not None or field_info.default_factory is not None
        is_optional = origin is Union and type(None) in args

        if is_optional and has_default:
            # 50% chance of None for optional fields with defaults
            inner_args = [a for a in args if a is not type(None)]
            if inner_args:
                inner_strat = _strategy_for_field(name, inner_args[0], field_info)
                field_strategies[name] = st.one_of(st.none(), inner_strat)
            else:
                field_strategies[name] = st.none()
        elif is_optional and not has_default:
            # Required-ish optional: always provide a value if required
            inner_args = [a for a in args if a is not type(None)]
            if inner_args:
                inner_strat = _strategy_for_field(name, inner_args[0], field_info)
                if field_info.is_required():
                    field_strategies[name] = inner_strat
                else:
                    field_strategies[name] = st.one_of(st.none(), inner_strat)
            else:
                field_strategies[name] = st.none()
        else:
            field_strategies[name] = _strategy_for_field(name, annotation, field_info)

    return st.fixed_dictionaries(field_strategies)


def serialize(data: dict) -> dict:
    """Recursively convert UUIDs, enums, and other non-JSON types to JSON-serializable form."""
    result = {}
    for key, value in data.items():
        result[key] = _serialize_value(value)
    return result


def _serialize_value(value: Any) -> Any:
    """Convert a single value to JSON-serializable form."""
    if value is None:
        return None
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, enum.Enum):
        return value.value
    if isinstance(value, dict):
        return {k: _serialize_value(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_serialize_value(item) for item in value]
    return value
