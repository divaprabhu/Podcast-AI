"""Logging configuration.

Provides a single function to initialise the root logger based on the
application configuration.
"""

import logging
import sys
from typing import Any


def setup_logging(config: dict[str, Any]) -> None:
    """Configure the root logger with the level from *config*.

    Args:
        config: Runtime configuration dictionary.  Uses
            ``config["logging"]["level"]`` (default ``"INFO"``).
    """
    level_name = config.get("logging", {}).get("level", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)

    logging.basicConfig(
        level=level,
        format="[%(levelname)s] %(asctime)s - %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
        stream=sys.stdout,
        force=True,
    )
