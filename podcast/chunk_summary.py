"""Chunk-based paper summarisation.

Splits the full PDF text into manageable chunks, sends each chunk to an LLM
for summarisation, and monitors the failure rate against a configurable
threshold.
"""

import logging
from typing import Any

from .cache import read_cache_json, write_cache_json
from .llm import call_llm
from .utils import format_prompt

logger = logging.getLogger(__name__)


def _find_split_point(text: str, max_chars: int) -> int:
    """Find the best index to split *text* at or before *max_chars*.

    Priority order: sentence boundary, paragraph break, line break,
    word boundary, hard cut.

    Args:
        text: The text to split.
        max_chars: Maximum length of the first chunk.

    Returns:
        The end index of the first chunk (exclusive).
    """
    if max_chars >= len(text):
        return len(text)

    candidate = text[:max_chars]
    min_chars = max_chars // 3

    # 1. Sentence boundary (punctuation + space)
    for sep in ('. ', '! ', '? '):
        idx = candidate.rfind(sep)
        if idx != -1 and idx >= min_chars:
            return idx + len(sep)

    # 2. Paragraph break
    idx = candidate.rfind('\n\n')
    if idx != -1 and idx >= min_chars:
        return idx + 2

    # 3. Single newline
    idx = candidate.rfind('\n')
    if idx != -1 and idx >= min_chars:
        return idx + 1

    # 4. Word boundary
    idx = candidate.rfind(' ')
    if idx != -1:
        return idx + 1

    # 5. Hard cut
    return max_chars


def _build_chunks(pages_text: list[str], chunk_size: int) -> list[str]:
    """Split *pages_text* into chunks of at most *chunk_size* characters.

    Pages are joined into a buffer and flushed whenever adding another page
    would exceed the limit.  Large pages are split further using
    :func:`_find_split_point`.

    Args:
        pages_text: List of per-page text strings.
        chunk_size: Maximum number of characters per chunk.

    Returns:
        List of text chunks.
    """
    chunks = []
    buffer = ""
    for page_text in pages_text:
        if not page_text:
            continue
        remaining = page_text
        while remaining and len(remaining) > chunk_size:
            if buffer:
                chunks.append(buffer)
                buffer = ""
            split_at = _find_split_point(remaining, chunk_size)
            chunks.append(remaining[:split_at])
            remaining = remaining[split_at:]
        if not remaining:
            continue
        if buffer:
            if len(buffer) + len(remaining) > chunk_size:
                chunks.append(buffer)
                buffer = remaining
            else:
                buffer += "\n\n" + remaining
        else:
            buffer = remaining
    if buffer:
        chunks.append(buffer)
    return chunks


def _summarize_chunks(
    config: dict[str, Any],
    chunks: list[str],
    chunk_prompts: dict[str, Any],
    max_context: int,
) -> tuple[list[str], int]:
    """Call the LLM for each chunk and return summaries and failure count.

    Args:
        config: Runtime configuration dictionary.
        chunks: List of text chunks to summarise.
        chunk_prompts: Dict with ``system`` and ``user`` prompt templates.
        max_context: Maximum context length used to compute per-chunk limit.

    Returns:
        A tuple ``(summaries, failed_count)`` where *summaries* contains a
        string for each chunk (empty string on failure) and *failed_count* is
        the number of chunks that could not be summarised.
    """
    pipeline = config.get("llm", {}).get("pipeline", {})
    summary_provider = pipeline.get("summary", {}).get("provider")
    summary_model = pipeline.get("summary", {}).get("model")

    chunk_summaries = []
    failed_chunks = 0
    for idx, chunk in enumerate(chunks):
        logger.info("Summarizing chunk: %d/%d", idx + 1, len(chunks))
        system_prompt = format_prompt(chunk_prompts.get("system", ""), {
            "max_chars": int(max_context / len(chunks)),
        })
        user_prompt = format_prompt(chunk_prompts.get("user", ""), {
            "chunk_id": f"{idx+1}/{len(chunks)}",
            "chunk_text": chunk,
        })
        try:
            summary = call_llm(
                config, system_prompt, user_prompt,
                provider=summary_provider, model=summary_model,
            )
            logger.info(
                "Chunk %d summarized (length %d)", idx + 1, len(summary)
            )
        except Exception as e:
            logger.warning(
                "LLM failed to summarize chunk %d: %s", idx + 1, e
            )
            summary = ""
            failed_chunks += 1
        chunk_summaries.append(summary)
    return chunk_summaries, failed_chunks


def _check_failure_threshold(
    failed_chunks: int,
    chunks: list[Any],
    failure_threshold: float,
) -> None:
    """Raise if the failure rate exceeds *failure_threshold*; else warn.

    Args:
        failed_chunks: Number of chunks that failed summarisation.
        chunks: Full list of chunks (used to compute the failure rate).
        failure_threshold: Maximum allowable failure rate (0.0 – 1.0).

    Raises:
        RuntimeError: If the failure rate exceeds the threshold.
    """
    if failed_chunks == 0:
        return
    failure_rate = failed_chunks / len(chunks)
    if failure_rate > failure_threshold:
        raise RuntimeError(
            f"Too many chunk summarization failures: "
            f"{failed_chunks}/{len(chunks)} "
            f"({failure_rate:.0%}) exceeded threshold of "
            f"{failure_threshold:.0%}. "
            "The resulting summary would be too incomplete to use."
        )
    logger.warning(
        "Some chunks failed summarization: %d/%d. "
        "Proceeding (below %.0f%% threshold).",
        failed_chunks, len(chunks), failure_threshold * 100,
    )


def step_chunk_summary(config: dict[str, Any]) -> dict[str, Any]:
    """Run the chunk-summary pipeline step.

    Reads the selected paper from the cache, splits its PDF text into chunks,
    sends each chunk to an LLM for summarisation, and persists the results
    back to the cache.

    Args:
        config: Runtime configuration dictionary.

    Returns:
        The paper dict enriched with ``chunks`` and ``chunk_summaries`` lists.

    Raises:
        KeyError: If no selected paper is found in the cache.
        ValueError: If no extracted pages are available or chunks are empty.
        RuntimeError: If the chunk failure rate exceeds the configured
            threshold.
    """
    data = read_cache_json(config)
    if isinstance(data, dict) and "selected" in data:
        paper = data["selected"]
    else:
        raise KeyError("No selected paper found in cache")

    if paper.get("chunk_summaries"):
        logger.info("Loading chunk summaries from cache.")
        return paper

    pages_text = paper.get("pages_text", [])
    if not pages_text:
        raise ValueError(
            "No extracted pages found in cache. Run the 'pdf' step first."
        )

    processing = config.get("paper", {}).get("processing", {})
    chunk_size = processing.get("pdf_chunk_size", 10000)
    chunks = _build_chunks(pages_text, chunk_size)

    if not chunks:
        raise ValueError(
            "No text chunks could be extracted from pages. "
            "The PDF may be empty or all pages yielded no extractable text."
        )

    logger.debug("Built %d text chunks for summarization", len(chunks))

    chunk_prompts = config.get("prompts", {}).get("chunk_summary", {})
    max_context = processing.get("chunk_context_limit", 25000)
    failure_threshold = processing.get("chunk_failure_threshold", 0.3)

    chunk_summaries, failed_chunks = _summarize_chunks(
        config, chunks, chunk_prompts, max_context
    )
    _check_failure_threshold(failed_chunks, chunks, failure_threshold)

    paper["chunks"] = chunks
    paper["chunk_summaries"] = chunk_summaries
    data["selected"] = paper
    write_cache_json(data, config)
    logger.info("Chunk summaries persisted to paper.json")
    return paper
