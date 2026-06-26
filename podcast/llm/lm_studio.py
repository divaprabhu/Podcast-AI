import logging

import requests

from ._format import get_openai_response_format as _get_openai_response_format

logger = logging.getLogger(__name__)

DEFAULT_BASE_URL = "http://localhost:1234"


def call(config, system_prompt, user_prompt, model, response_format):
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
