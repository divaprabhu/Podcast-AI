"""OpenAI-compatible response-format marshalling.

Converts a high-level format specification (``None``, ``"json"``, or a JSON
schema dict) into the OpenAI ``response_format`` structure used by the API
endpoint.
"""

from typing import Any


def get_openai_response_format(
    format_val: str | dict[str, Any] | None,
) -> dict[str, Any] | None:
    """Convert a high-level format value to an OpenAI ``response_format`` dict.

    Args:
        format_val: ``None`` (no constraint), ``"json"`` for free-form JSON
            mode, or a dict representing a JSON Schema for structured output.

    Returns:
        An OpenAI ``response_format`` dict, or ``None`` if *format_val* is
        falsy.
    """
    if not format_val:
        return None
    if isinstance(format_val, dict):
        return {
            "type": "json_schema",
            "json_schema": {
                "name": "response",
                "strict": True,
                "schema": format_val,
            },
        }
    if format_val == "json":
        return {"type": "json_object"}
    return None
