"""Final condensation of chunk summaries.

Combines all per-chunk summaries into a single, coherent overview of the
paper by calling the LLM once more with the aggregated text.
"""

import logging
from typing import Any

from .cache import read_cache_json, write_cache_json
from .llm import call_llm
from .utils import format_prompt

logger = logging.getLogger(__name__)


def step_final_summary(config: dict[str, Any]) -> dict[str, Any]:
    """Run the final-summary pipeline step.

    Combines all chunk summaries from the cache into a single prompt and
    calls the LLM to produce a condensed overview.  The result is stored
    as ``content_summary`` on the selected paper.

    Args:
        config: Runtime configuration dictionary.

    Returns:
        The paper dict enriched with the ``content_summary`` key.

    Raises:
        KeyError: If no selected paper or chunk summaries are found in the
            cache.
        ValueError: If the combined summaries are empty.
    """
    data = read_cache_json(config)
    if isinstance(data, dict) and "selected" in data:
        paper = data.get("selected")
    else:
        raise KeyError("No selected paper found in cache")

    if paper.get("content_summary"):
        logger.info("Loading final summary from cache.")
        return paper

    chunk_summaries = paper.get("chunk_summaries", [])
    if not chunk_summaries:
        raise KeyError(
            "No chunk summaries found in cache."
            "Run 'chunk_summary' step first."
        )

    combined_summaries = "\n\n".join(s for s in chunk_summaries if s)

    if combined_summaries.strip() == "":
        raise ValueError(
            "No combined summary. Rerun 'chunk_summary' again"
        )

    final_prompts = config.get("prompts", {}).get("final_summary", {})
    final_context_limit = config.get("paper", {}).get("processing", {})
    final_context_limit = final_context_limit.get("final_context_limit", 25000)
    final_system = format_prompt(final_prompts.get("system", ""), {
        "max_chars": final_context_limit,
    })
    final_user = format_prompt(final_prompts.get("user", ""), {
        "combined_summaries": combined_summaries,
    })

    pipeline = config.get("llm", {}).get("pipeline", {})
    final_provider = pipeline.get("final_summary", {}).get("provider")
    final_model = pipeline.get("final_summary", {}).get("model")

    try:
        final_condensed = call_llm(
            config, final_system, final_user,
            provider=final_provider, model=final_model
        )
        logger.info(
            f"Final condensation complete. (length {len(final_condensed)})"
        )
    except Exception as e:
        logger.exception("Final condensation LLM call failed: %s", e)
        raise

    paper["content_summary"] = final_condensed
    data["selected"] = paper
    write_cache_json(data, config)
    logger.info("Final summary written to paper.json")
    return paper
