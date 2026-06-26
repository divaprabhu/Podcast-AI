"""Podcast script generation.

Produces a turn-by-turn podcast script by calling the LLM with the paper
summary and wrapping the result in deterministic intro / CTA / outro turns.
"""

import logging
from typing import Any

from .cache import read_cache_json, write_cache_json
from .llm import call_llm_json
from .utils import format_prompt

logger = logging.getLogger(__name__)


def _normalize_host_fields(
    script_data: list[dict[str, str]],
    host_male: str,
    host_female: str,
) -> list[dict[str, str]]:
    """Normalise host field values to ``'Male'`` or ``'Female'``.

    Accepts the configured host names (e.g. ``'Alex'``, ``'Maya'``),
    case-insensitive variants, or the literal strings ``'Male'`` /
    ``'Female'``.  Logs a warning for any value that cannot be mapped and
    leaves it unchanged so callers can detect the problem.

    Args:
        script_data: List of turn dicts with a ``host`` key.
        host_male: Configured name of the male host.
        host_female: Configured name of the female host.

    Returns:
        The same list with canonicalised ``host`` values.
    """
    male_aliases = {"male", host_male.lower()}
    female_aliases = {"female", host_female.lower()}
    for i, turn in enumerate(script_data):
        raw = turn.get("host", "")
        key = raw.strip().lower()
        if key in male_aliases:
            turn["host"] = "Male"
        elif key in female_aliases:
            turn["host"] = "Female"
        else:
            logger.warning(
                "Unexpected host value %r in turn %d — leaving unchanged. "
                "Expected one of: %r",
                raw, i, sorted(male_aliases | female_aliases),
            )
    return script_data


def _build_intro(config: dict[str, Any]) -> list[dict[str, str]]:
    """Return fixed intro turns: Male introduces the show, Female confirms.

    Args:
        config: Runtime configuration dictionary.

    Returns:
        A list of two introductory turns.
    """
    show_name = config["podcast"]["show_name"]
    host_male = config["podcast"]["hosts"]["male"]
    host_female = config["podcast"]["hosts"]["female"]
    return [
        {"host": "Male", "text": f"Welcome to {show_name}! I'm {host_male}."},
        {"host": "Female", "text": f"And I'm {host_female}."},
    ]


def _build_cta(config: dict[str, Any]) -> dict[str, str]:
    """Return a fixed mid-episode CTA turn.

    Args:
        config: Runtime configuration dictionary.

    Returns:
        A single turn dict with ``host`` and ``text`` keys.
    """
    show_name = config["podcast"]["show_name"]
    return {
        "host": "Female",
        "text": (
            f"If you are enjoying this, follow or subscribe to {show_name} "
            "wherever you listen - it really helps, and we have a new episode "
            "every day."
        ),
    }


def _build_outro(config: dict[str, Any], authors_str: str) -> dict[str, str]:
    """Return a fixed outro/credits turn.

    Args:
        config: Runtime configuration dictionary.
        authors_str: Comma-separated author names to credit.

    Returns:
        A single turn dict with ``host`` and ``text`` keys.
    """
    show_name = config["podcast"]["show_name"]
    return {
        "host": "Male",
        "text": f"Paper by {authors_str}, produced by {show_name}.",
    }


def step_generate_script(config: dict[str, Any]) -> list[dict[str, str]]:
    """Run the script-generation pipeline step.

    Reads the selected paper and its final summary from the cache, calls
    the LLM for a JSON array of turns, normalises host fields, and wraps
    the result with intro / CTA / outro turns.

    Args:
        config: Runtime configuration dictionary.

    Returns:
        A list of turn dicts, each with ``host`` and ``text`` keys,
        representing the full podcast script.

    Raises:
        KeyError: If no selected paper is found in the cache.
        ValueError: If no content summary is available.
    """
    data = read_cache_json(config)
    if not isinstance(data, dict) or "selected" not in data:
        raise KeyError("No selected paper found in cache")
    paper = data["selected"]

    if paper.get("script"):
        logger.info("Loading script from cache.")
        return paper["script"]

    script_prompts = config.get("prompts", {}).get("script", {})
    authors = paper.get("authors", [])
    authors_str = ", ".join(authors) if authors else "the paper authors"
    system_prompt = format_prompt(script_prompts.get("system", ""), {
        "show_name": config["podcast"]["show_name"],
        "host_male": config["podcast"]["hosts"]["male"],
        "host_female": config["podcast"]["hosts"]["female"],
        "num_words": config["podcast"]["script"]["num_words"],
    })

    content_summary = paper.get("content_summary")
    if not content_summary or content_summary.strip() == '':
        raise ValueError(
            "No content summary. Rerun 'final_summary' again"
        )

    content_summary_section = f"\n\nPaper Content Summary: {content_summary}"

    user_prompt = format_prompt(script_prompts.get("user", ""), {
        "title": paper.get("title", ""),
        "summary": paper.get("summary", ""),
        "content_summary_section": content_summary_section,
    })

    response_format = {
        "type": "array",
        "items": {
            "type": "object",
            "properties": {
                "host": {"type": "string", "enum": ["Male", "Female"]},
                "text": {"type": "string"},
            },
            "required": ["host", "text"],
        },
    }

    pipeline = config.get("llm", {}).get("pipeline", {})
    script_provider = pipeline.get("script", {}).get("provider")
    script_model = pipeline.get("script", {}).get("model")

    script_data = call_llm_json(
        config, system_prompt, user_prompt,
        provider=script_provider, model=script_model,
        response_format=response_format,
    )
    logger.info("Script generation complete (length %d)", len(script_data))
    logger.debug("Clean JSON: %s", script_data)

    if not isinstance(script_data, list):
        raise ValueError(
            f"LLM returned unexpected JSON format: {script_data}. "
            "Expected a JSON array of {host, text} objects."
        )

    # Normalize host field values to canonical "Male" / "Female" strings.
    script_data = _normalize_host_fields(
        script_data,
        host_male=config["podcast"]["hosts"]["male"],
        host_female=config["podcast"]["hosts"]["female"],
    )

    # Wrap the LLM body with deterministic structural turns.
    intro = _build_intro(config)
    cta = _build_cta(config)
    outro = _build_outro(config, authors_str)
    script_data = intro + script_data + [cta, outro]

    paper["script"] = script_data
    data["selected"] = paper
    write_cache_json(data, config)
    return script_data
