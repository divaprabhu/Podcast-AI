"""Configuration loading.

Provides a single function to load the JSON-based runtime configuration
and raise clear errors when the file is missing or malformed.
"""

import json
import logging
import os
from typing import Any


DEFAULT_CONFIG_PATH = "config.json"

logger = logging.getLogger(__name__)


def load_config(path: str = DEFAULT_CONFIG_PATH) -> dict[str, Any]:
    """Load and return the JSON configuration file.

    Args:
        path: Filesystem path to the configuration file.

    Returns:
        Parsed configuration dictionary.

    Raises:
        FileNotFoundError: If the configuration file does not exist.
        json.JSONDecodeError: If the file contains invalid JSON.
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"Missing required configuration file '{path}'.")
    try:
        with open(path, "r") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        logger.error("Invalid JSON in '%s': %s", path, e)
        raise
