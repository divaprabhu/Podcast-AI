"""Local Ollama LLM provider.

Wraps the local Ollama inference API (``/api/chat`` endpoint).
"""

import logging
from typing import Any

import requests

logger = logging.getLogger(__name__)

DEFAULT_BASE_URL: str = "http://localhost:11434"


def call(
    config: dict[str, Any],
    system_prompt: str,
    user_prompt: str,
    model: str,
    response_format: dict[str, Any] | None,
) -> tuple[str, dict[str, Any]]:
    """Send a chat completion request to a local Ollama instance.

    Args:
        config: Runtime configuration dictionary.
        system_prompt: System message content.
        user_prompt: User message content.
        model: Model identifier string.
        response_format: Optional JSON schema dict for structured output
            (passed as ``format`` to the Ollama API).

    Returns:
        A tuple ``(content, usage)`` where *content* is the response text
        and *usage* is a dict of token-usage statistics.

    Raises:
        requests.RequestException: On API error.
    """
    base_url = config.get("llm", {}).get("providers", {}).get("ollama", {}).get("base_url", DEFAULT_BASE_URL).rstrip("/")
    api_url = f"{base_url}/api/chat"

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "stream": False,
        "options": {
            "num_ctx": config.get("llm", {}).get("providers", {}).get("ollama", {}).get("num_ctx", 32768),
        },
    }
    if response_format:
        payload["format"] = response_format

    timeout = config.get("llm", {}).get("providers", {}).get("ollama", {}).get("timeout", 3600)
    response = requests.post(api_url, json=payload, timeout=timeout)
    response.raise_for_status()
    logger.debug(f"Ollama Raw Response: {response.text}")
    data = response.json()
    content = data["message"]["content"]
    if not content:
        raise Exception("Null response received")
    return content, data.get("usage", {})
