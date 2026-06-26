"""LM Studio LLM provider.

Wraps the local LM Studio inference server (OpenAI-compatible chat
completions endpoint).
"""

import logging
from typing import Any

import requests

from ._format import get_openai_response_format as _get_openai_response_format

logger = logging.getLogger(__name__)

DEFAULT_BASE_URL: str = "http://localhost:1234"


def call(
    config: dict[str, Any],
    system_prompt: str,
    user_prompt: str,
    model: str,
    response_format: dict[str, Any] | str | None,
) -> tuple[str, dict[str, Any]]:
    """Send a chat completion request to a local LM Studio instance.

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
        requests.RequestException: On API error.
    """
    base_url = config.get("llm", {}).get("providers", {}).get("lm_studio", {}).get("base_url", DEFAULT_BASE_URL).rstrip("/")
    api_url = f"{base_url}/v1/chat/completions"

    headers = {
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "stream": False,
        "max_tokens": config.get("llm", {}).get("providers", {}).get("lm_studio", {}).get("num_ctx", 32768),
    }
    resp_format = _get_openai_response_format(response_format)
    if resp_format:
        payload["response_format"] = resp_format

    timeout = config.get("llm", {}).get("providers", {}).get("lm_studio", {}).get("timeout", 3600)
    response = requests.post(api_url, headers=headers, json=payload, timeout=timeout)
    response.raise_for_status()
    logger.debug(f"LM Studio Raw Response: {response.text.strip()}")
    data = response.json()
    content = data["choices"][0]["message"]["content"]
    if not content:
        raise Exception("Null response received")
    return content, data.get("usage", {})
