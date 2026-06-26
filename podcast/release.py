"""Release preparation.

Copies the generated audio and cache data to timestamped release files,
updates the episode history, and prepares assets for publishing.
"""

import logging
import os
import shutil
from datetime import datetime, timezone
from typing import Any

from .cache import get_cache_path, read_cache_json
from .episodes import load_episodes, save_episodes

logger = logging.getLogger(__name__)


def step_prepare_release(config: dict[str, Any]) -> str:
    """Prepare the podcast release: copy assets and update episode history.

    Creates timestamped copies of the audio file and selected-paper cache,
    appends an entry to ``episodes.json``, and returns the unique audio
    filename.

    Args:
        config: Runtime configuration dictionary.

    Returns:
        The unique audio filename (e.g. ``"podcast_202503311430.mp3"``).

    Raises:
        FileNotFoundError: If the generated audio or cache file is missing.
        KeyError: If no selected paper is found in the cache.
    """
    if not config.get("is_github_run"):
        logger.warning("Release step should only be run in CI.")
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M")
    run_number = config["run_number"]
    unique_audio = f"podcast_{timestamp}.mp3"
    unique_selected_json = f"paper_{timestamp}.json"

    src = get_cache_path(config, "audio")
    if os.path.exists(src):
        shutil.copy2(src, unique_audio)
        logger.info(f"Copied {src} to {unique_audio} for release.")
    else:
        logger.error("Audio not found, cannot rename for release.")
        raise FileNotFoundError("No audio found for release")

    data = read_cache_json(config)
    if not isinstance(data, dict) or "selected" not in data:
        raise KeyError("No selected paper found in cache; run the 'select' step first.")
    paper = data["selected"]

    size = os.path.getsize(unique_audio)

    episodes = load_episodes()
    episode_entry = {
        "title": paper["title"],
        "description": paper.get("selection_reason", "AI Research Paper"),
        "pubDate": datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S +0000"),
        "filename": unique_audio,
        "selected_json": unique_selected_json,
        "tag": f"podcast-{run_number}",
        "guid": paper["id"],
        "size": size
    }
    episodes.append(episode_entry)

    selected_cache = get_cache_path(config)
    if os.path.exists(selected_cache):
        shutil.copy2(selected_cache, unique_selected_json)
        logger.info(
            f"Copied {selected_cache} to {unique_selected_json} for release."
        )
    else:
        logger.error("Cache file not found, cannot rename for release.")
        raise FileNotFoundError("No cache file found for release")

    if config.get("is_github_run"):
        save_episodes(episodes)
        logger.info(
            f"Episode history updated in episodes.json. Total episodes: {len(episodes)}"
        )
    else:
        logger.info(
            "Skipping episodes.json update (not a CI run)"
        )

    return unique_audio
