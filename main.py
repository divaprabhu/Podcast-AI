"""Entrypoint for the Podcast-AI CLI.

Parses command-line arguments, loads runtime configuration, and orchestrates
the full podcast-production pipeline or a single isolated pipeline step.
"""

import argparse
import logging
import os
import sys
from datetime import datetime, timezone
from typing import Any

from dotenv import load_dotenv

from podcast.cache import step_clear_cache
from podcast.config import load_config
from podcast.log import setup_logging

from podcast import (
    arxiv,
    audio,
    chunk_summary,
    final_summary,
    pdf,
    release,
    rss,
    script,
    selection,
    video,
    youtube,
)

load_dotenv()

logger = logging.getLogger(__name__)


STEP_HANDLERS = {
    "fetch":         ("Fetch",         arxiv.step_fetch_arxiv),
    "select":        ("Select",        selection.step_select_paper),
    "pdf":           ("PDF",           pdf.step_pdf),
    "chunk_summary": ("Chunk Summary", chunk_summary.step_chunk_summary),
    "final_summary": ("Final Summary", final_summary.step_final_summary),
    "script":        ("Script",        script.step_generate_script),
    "audio":         ("Audio",         audio.step_generate_audio),
    "video":         ("Video",         video.step_generate_video),
    "release":       ("Release",       release.step_prepare_release),
    "rss":           ("RSS",           rss.step_generate_rss),
    "upload":        ("Upload",        youtube.step_upload_youtube),
    "clear":         ("Clear Cache",   step_clear_cache),
}

STEPS = list(STEP_HANDLERS)


def parse_args() -> argparse.Namespace:
    """Parse and return CLI arguments.

    Returns:
        Parsed argument namespace with an optional ``step`` attribute.
    """
    parser = argparse.ArgumentParser(
        description="Automated AI Paper Podcast Studio"
    )
    parser.add_argument(
        "--step",
        choices=STEP_HANDLERS,
        help="Run an isolated segment pipeline block.",
    )
    args = parser.parse_args()
    return args


def run_all(config: dict[str, Any]) -> None:
    """Execute every pipeline step in sequence.

    Runs the core content-production steps unconditionally, then conditionally
    executes release, RSS, and YouTube upload when running inside GitHub
    Actions (``config["is_github_run"]`` is ``True``).

    Args:
        config: Runtime configuration dictionary loaded from ``config.json``
            and augmented with ``run_number`` and ``is_github_run``.
    """
    logger.info("Executing complete pipeline sequentially...")
    arxiv.step_fetch_arxiv(config)
    selection.step_select_paper(config)
    pdf.step_pdf(config)
    chunk_summary.step_chunk_summary(config)
    final_summary.step_final_summary(config)
    script.step_generate_script(config)
    audio.step_generate_audio(config)
    video.step_generate_video(config)

    if config["is_github_run"]:
        release.step_prepare_release(config)
        rss.step_generate_rss(config)
        youtube.step_upload_youtube(config)


def main() -> None:
    """CLI entry point for Podcast-AI.

    Loads configuration, resolves the requested pipeline step (or runs the
    full pipeline if no step is specified), and exits with a non-zero status
    code on failure.
    """
    args = parse_args()

    config = load_config()
    config["run_number"] = datetime.now(timezone.utc).strftime("%Y%m%d")
    config["is_github_run"] = os.getenv("GITHUB_ACTIONS") == "true"
    setup_logging(config)

    try:
        if args.step is None:
            run_all(config)
        else:
            label, handler = STEP_HANDLERS[args.step]
            logger.info("Running isolated step: %s", label)
            handler(config)

    except Exception as e:
        logger.exception("Execution failed: %s", str(e))
        sys.exit(1)


if __name__ == "__main__":
    main()
