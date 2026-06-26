import logging

import requests

logger = logging.getLogger(__name__)

DEFAULT_BASE_URL = "http://localhost:11434"


def call(config, system_prompt, user_prompt, model, response_format):
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
