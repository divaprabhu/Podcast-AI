"""Google AI Studio (Gemini) LLM provider.

Wraps the Google Generative Language API (Gemini) for chat completions.
"""

import logging
import os
from typing import Any

import requests

from ._format import get_openai_response_format as _get_openai_response_format

logger = logging.getLogger(__name__)

DEFAULT_BASE_URL: str = "https://generativelanguage.googleapis.com/v1beta"


def call(
    config: dict[str, Any],
    system_prompt: str,
    user_prompt: str,
    model: str,
    response_format: dict[str, Any] | str | None,
) -> tuple[str, dict[str, Any]]:
    """Send a chat completion request to Google AI Studio (Gemini API).

    Args:
        config: Runtime configuration dictionary.
        system_prompt: System message content.
        user_prompt: User message content.
        model: Model identifier string (e.g., "gemini-1.5-pro", "gemini-1.5-flash").
        response_format: Optional response-format constraint (JSON schema
            dict or "json" string).

    Returns:
        A tuple (content, usage) where content is the response text
        and usage is a dict of token-usage statistics.

    Raises:
        ValueError: If GOOGLE_API_KEY is not set in the environment.
        requests.RequestException: On API error.
    """
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY missing from environment.")

    base_url = config.get("llm", {}).get("providers", {}).get("google", {}).get("base_url", DEFAULT_BASE_URL).rstrip("/")
    api_url = f"{base_url}/models/{model}:generateContent"

    # Google AI Studio uses the API key as a query parameter
    params = {"key": api_key}

    headers = {
        "Content-Type": "application/json",
    }

    # Build the request payload in Gemini format
    # Gemini API expects contents as a list of parts with role and parts
    contents = []

    # Add system prompt as a user message with a special role if provided
    # Note: Gemini doesn't have a dedicated system role, so we prepend it to the first user message
    if system_prompt:
        contents.append({
            "role": "user",
            "parts": [{"text": system_prompt}]
        })
        contents.append({
            "role": "model",
            "parts": [{"text": "Understood. I'll follow these instructions."}]
        })

    contents.append({
        "role": "user",
        "parts": [{"text": user_prompt}]
    })

    payload = {
        "contents": contents,
    }

    # Add generation config for response format if specified
    resp_format = _get_openai_response_format(response_format)
    if resp_format:
        if resp_format.get("type") == "json_object":
            payload["generationConfig"] = {
                "responseMimeType": "application/json",
            }
        elif resp_format.get("type") == "json_schema":
            schema = resp_format.get("json_schema", {}).get("schema", {})
            payload["generationConfig"] = {
                "responseMimeType": "application/json",
                "responseSchema": schema,
            }

    timeout = config.get("llm", {}).get("providers", {}).get("google", {}).get("timeout", 300)
    response = requests.post(api_url, headers=headers, params=params, json=payload, timeout=timeout)
    response.raise_for_status()
    logger.debug(f"Google AI Studio Raw Response: {response.text.strip()}")
    data = response.json()

    # Extract content from Gemini response format
    try:
        content = data["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError) as e:
        logger.error(f"Unexpected response format: {data}")
        raise Exception(f"Failed to extract content from response: {e}")

    if not content:
        raise Exception("Null response received")

    # Extract usage information if available
    usage = {}
    if "usageMetadata" in data:
        usage = {
            "prompt_tokens": data["usageMetadata"].get("promptTokenCount", 0),
            "completion_tokens": data["usageMetadata"].get("candidatesTokenCount", 0),
            "total_tokens": data["usageMetadata"].get("totalTokenCount", 0),
        }

    return content, usage