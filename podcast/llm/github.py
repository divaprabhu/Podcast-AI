"""GitHub Models LLM provider.

Wraps the GitHub Models inference API (OpenAI-compatible chat completions
endpoint).
"""

import logging
import os
from typing import Any

import requests

from ._format import get_openai_response_format as _get_openai_response_format

logger = logging.getLogger(__name__)

DEFAULT_BASE_URL: str = "https://models.github.ai"


def call(
    config: dict[str, Any],
    system_prompt: str,
    user_prompt: str,
    model: str,
    response_format: dict[str, Any] | str | None,
) -> tuple[str, dict[str, Any]]:
    """Send a chat completion request to GitHub Models.

    Args:
        config: Runtime configuration dictionary.
        system_prompt: System message content.
        user_prompt: User message content.
        model: Model identifier string.
        response_format: Optional response-format constraint (JSON schema
            dict or ``"json"`` string).

    Returns:
        A tuple ``(content, usage)`` where *content* is the response text
        and *usage* is a dict of token-usage statistics.

    Raises:
        ValueError: If ``GH_API_KEY`` is not set in the environment.
        requests.RequestException: On API error.
    """
    api_key = os.getenv("GH_API_KEY")
    if not api_key:
        raise ValueError("GH_API_KEY missing from environment.")

    base_url = config.get("llm", {}).get("providers", {}).get("github", {}).get("base_url", DEFAULT_BASE_URL).rstrip("/")
    api_url = f"{base_url}/inference/chat/completions"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    }
    resp_format = _get_openai_response_format(response_format)
    if resp_format:
        payload["response_format"] = resp_format

    timeout = config.get("llm", {}).get("providers", {}).get("github", {}).get("timeout", 300)
    response = requests.post(api_url, headers=headers, json=payload, timeout=timeout)
    response.raise_for_status()
    logger.debug(f"GitHub Models Raw Response: {response.text}")
    data = response.json()
    content = data["choices"][0]["message"]["content"]
    if not content:
        raise Exception("Null response received")
    return content, data.get("usage", {})
