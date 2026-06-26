"""Unified cache management utilities.

Provides functions to read, write, and clear a JSON-based pipeline cache.
All I/O uses atomic writes via :func:`tempfile.mkstemp` + :func:`os.replace`
to avoid data corruption.
"""

import json
import logging
import os
import shutil
import tempfile
from typing import Any

logger = logging.getLogger(__name__)


def get_cache_dir(config: dict[str, Any]) -> str:
    """Return the filesystem path for the cache directory.

    Args:
        config: Runtime configuration dictionary. Uses
            ``config["cache"]["directory"]`` or defaults to
            ``".podcast_cache"``.

    Returns:
        Absolute or relative path to the cache directory.
    """
    cache_cfg = (config or {}).get("cache", {})
    directory = cache_cfg.get("directory", ".podcast_cache")
    return directory


def get_cache_path(config: dict[str, Any], key: str = "file") -> str:
    """Return the full path to a cached resource based on config.

    Args:
        config: Configuration dict.
        key: Config key for the filename. One of ``'file'``, ``'audio'``,
            ``'video'``.

    Returns:
        Full path to the cached resource.

    Raises:
        ValueError: If the filename is not configured for *key*.
    """
    cache_cfg = (config or {}).get("cache", {})
    directory = cache_cfg.get("directory", ".podcast_cache")
    filename = cache_cfg.get(key)
    if not filename:
        raise ValueError(
            f"Missing cache filename for key {key!r} in config cache section"
        )
    return os.path.join(directory, filename)


def step_clear_cache(config: dict[str, Any]) -> None:
    """Remove the entire cache directory.

    Args:
        config: Runtime configuration dictionary.
    """
    cache_dir = get_cache_dir(config)
    if os.path.exists(cache_dir):
        shutil.rmtree(cache_dir)
        logger.info("Cleared cache directory: %s", cache_dir)
    else:
        logger.info("Cache directory does not exist: %s", cache_dir)


def read_cache_json(config: dict[str, Any]) -> dict[str, Any]:
    """Read and return the cache file as a dict.

    If the file or directory does not exist, or the JSON top-level is not an
    object, an empty dict is returned.  Callers are responsible for
    interpreting keys such as ``'papers'`` or ``'selected'``.

    Args:
        config: Runtime configuration dictionary.

    Returns:
        The cached data, or an empty dict if the cache file is absent or
        corrupt.
    """
    path = get_cache_path(config)
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return data
        logger.warning(
            "Cache file %s contains non-dict JSON; resetting to {}.",
            path
        )
        return {}
    except json.JSONDecodeError as exc:
        logger.exception(
            "Cache file %s is corrupt (JSONDecodeError: %s); resetting to {}.",
            path, exc
        )
        return {}
    except OSError as exc:
        logger.warning(
            "Could not read cache file %s: %s. resetting to {}.",
            path, exc
        )
        return {}


def write_cache_json(data: dict[str, Any], config: dict[str, Any]) -> None:
    """Persist the given dict to the configured cache file (atomic write).

    Creates the cache directory if it does not exist.  Uses a temporary file
    followed by :func:`os.replace` to ensure atomicity.

    Args:
        data: Data to write.  If ``None`` or falsy, an empty dict is stored.
        config: Runtime configuration dictionary.
    """
    path = get_cache_path(config)
    dirpath = os.path.dirname(path) or "."
    os.makedirs(dirpath, exist_ok=True)

    fd, tmp_path = tempfile.mkstemp(dir=dirpath)
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(data or {}, f, indent=2)
        os.replace(tmp_path, path)
    finally:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError as exc:
                logger.warning(
                    "Could not remove temporary cache file %s: %s",
                    tmp_path, exc
                )
