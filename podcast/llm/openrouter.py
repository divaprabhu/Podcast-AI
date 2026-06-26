import logging
import os

import requests

from ._format import get_openai_response_format as _get_openai_response_format

logger = logging.getLogger(__name__)

DEFAULT_BASE_URL = "https://openrouter.ai"


def call(config, system_prompt, user_prompt, model, response_format):
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY missing from environment.")

    base_url = config.get("llm", {}).get("providers", {}).get("openrouter", {}).get("base_url", DEFAULT_BASE_URL).rstrip("/")
    api_url = f"{base_url}/api/v1/chat/completions"

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

    timeout = config.get("llm", {}).get("providers", {}).get("openrouter", {}).get("timeout", 300)
    response = requests.post(api_url, headers=headers, json=payload, timeout=timeout)
    response.raise_for_status()
    logger.debug(f"OpenRouter Raw Response: {response.text.strip()}")
    data = response.json()
    content = data["choices"][0]["message"]["content"]
    if not content:
        raise Exception("Null response received")
    return content, data.get("usage", {})
