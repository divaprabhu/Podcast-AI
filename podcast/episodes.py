"""Episode history management.

Loads and saves a JSON list of published podcast episodes.  All writes are
atomic (temp file + replace) to prevent corruption on concurrent or
interrupted runs.
"""

import json
import logging
import os
import tempfile
from typing import Any

logger = logging.getLogger(__name__)

EPISODES_PATH = "episodes.json"


def load_episodes() -> list[dict[str, Any]]:
    """Load the published episode history from disk.

    Returns:
        A list of episode dicts, or an empty list if the file does not
        exist or cannot be parsed.
    """
    if not os.path.exists(EPISODES_PATH):
        return []
    try:
        with open(EPISODES_PATH, "r") as f:
            data = json.load(f)
        if isinstance(data, list):
            return data
        logger.warning("episodes.json is not a list, resetting to empty.")
        return []
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("Failed to load episodes.json: %s. Starting fresh.", e)
        return []


def save_episodes(episodes: list[dict[str, Any]]) -> None:
    """Atomically persist the episode list to disk.

    Args:
        episodes: List of episode dicts to save.
    """
    dirpath = os.path.dirname(EPISODES_PATH) or "."
    os.makedirs(dirpath, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=dirpath)
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(episodes, f, indent=2)
        os.replace(tmp_path, EPISODES_PATH)
    finally:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass
