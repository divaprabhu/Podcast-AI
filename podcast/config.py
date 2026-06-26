import json
import logging
import os


DEFAULT_CONFIG_PATH = "config.json"

logger = logging.getLogger(__name__)


def load_config(path=DEFAULT_CONFIG_PATH):
    if not os.path.exists(path):
        raise FileNotFoundError(f"Missing required configuration file '{path}'.")
    try:
        with open(path, "r") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        logger.error("Invalid JSON in '%s': %s", path, e)
        raise
