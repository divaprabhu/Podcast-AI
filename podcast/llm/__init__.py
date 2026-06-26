"""LLM provider dispatch.

Routes calls to the configured provider module, handles retry logic, and
provides JSON-safe output parsing.
"""

import json
import logging
import time
from collections.abc import Callable
from typing import Any

from . import openrouter
from . import github
from . import ollama
from . import lm_studio
from . import ollama_cloud

logger = logging.getLogger(__name__)


def _get_sleep(config: dict[str, Any]) -> int:
    """Return the sleep interval (in seconds) between retry attempts.

    Args:
        config: Runtime configuration dictionary.

    Returns:
        Sleep duration in seconds (default 10).
    """
    return config.get("llm", {}).get("default", {}).get("sleep", 10)


_PROVIDERS: dict[str, Any] = {
    "openrouter": openrouter,
    "github": github,
    "ollama": ollama,
    "lm_studio": lm_studio,
    "ollama_cloud": ollama_cloud,
}


def call_llm(
    config: dict[str, Any],
    system_prompt: str,
    user_prompt: str,
    provider: str | None = None,
    model: str | None = None,
    response_format: dict[str, Any] | None = None,
) -> str:
    """Call an LLM provider with retry logic and return the response text.

    Resolves the provider and model from the config or supplied arguments,
    delegates to the corresponding provider module, and retries once on
    failure after a configurable sleep.

    Args:
        config: Runtime configuration dictionary.
        system_prompt: System message content.
        user_prompt: User message content.
        provider: Provider name override (e.g. ``"openrouter"``).  If unset,
            the default provider from config is used.
        model: Model name override.  If unset, the default model from config
            is used.
        response_format: Optional JSON schema or ``"json"`` string to
            constrain the response format.

    Returns:
        The LLM response text.

    Raises:
        ValueError: If provider or model cannot be resolved.
    """
    global_provider = config.get("llm", {}).get("default", {}).get("provider")
    if global_provider:
        resolved_provider = global_provider.lower()
        resolved_model = config.get("llm", {}).get("default", {}).get("model", "") or ""
    else:
        resolved_provider = (provider or "").lower()
        resolved_model = model or ""

    if not resolved_provider and not resolved_model:
        raise ValueError(
            "LLM call requires both provider and model. "
            "Please set the step-specific provider/model in config."
        )
    if not resolved_model:
        raise ValueError(
            f"LLM provider '{resolved_provider}' is set but no model is configured. "
            "Set the model in config under llm.default.model or the step-specific pipeline config."
        )

    logger.info(f"Calling LLM Provider: {resolved_provider} ({resolved_model})")
    logger.debug(f"System Prompt:\n{system_prompt}\nUser Prompt:\n{user_prompt}")

    provider_module = _PROVIDERS.get(resolved_provider)
    if not provider_module:
        raise ValueError(f"Unsupported LLM provider: {resolved_provider}")

    for attempt in range(2):
        try:
            content, usage = provider_module.call(
                config, system_prompt, user_prompt, resolved_model, response_format
            )
            prompt_tokens = usage.get("prompt_tokens", 0)
            completion_tokens = usage.get("completion_tokens", 0)
            total_tokens = usage.get("total_tokens", 0)
            logger.info(
                "LLM Response | Input tokens: %s | Output tokens: %s | Total: %s",
                prompt_tokens, completion_tokens, total_tokens,
            )
            return content
        except Exception as e:
            if attempt == 0:
                logger.warning(f"LLM call failed (attempt 1/2): {e}. Retrying...")
                time.sleep(_get_sleep(config))
                continue
            raise


def safe_json_load(text: str) -> Any:
    """Parse JSON from an LLM response, stripping markdown fences if present.

    Args:
        text: Raw LLM response that may contain JSON embedded in markdown
            code blocks.

    Returns:
        Decoded JSON data.

    Raises:
        json.JSONDecodeError: If the text cannot be parsed as JSON.
    """
    text = text.strip()
    start = text.find("```")
    if start != -1:
        end = text.find("```", start + 3)
        if end != -1:
            text = text[start:end + 3]
        else:
            text = text[start:]
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[-1] if "\n" in text else text[3:]
    if text.endswith("```"):
        text = text[:-3]
    return json.loads(text.strip())


def call_llm_json(
    config: dict[str, Any],
    system_prompt: str,
    user_prompt: str,
    provider: str | None = None,
    model: str | None = None,
    response_format: dict[str, Any] | None = None,
) -> Any:
    """Call the LLM and parse the response as JSON, retrying on parse errors.

    Attempts the LLM call via :func:`call_llm` and parses the output with
    :func:`safe_json_load`.  If JSON parsing fails, retries once after a
    configurable sleep.

    Args:
        config: Runtime configuration dictionary.
        system_prompt: System message content.
        user_prompt: User message content.
        provider: Provider name override.
        model: Model name override.
        response_format: Optional JSON schema or ``"json"`` string.

    Returns:
        Decoded JSON data.

    Raises:
        json.JSONDecodeError: If parsing fails on the second attempt.
    """
    for attempt in range(2):
        try:
            raw_output = call_llm(
                config, system_prompt, user_prompt,
                provider=provider, model=model, response_format=response_format,
            )
            return safe_json_load(raw_output)
        except json.JSONDecodeError as e:
            if attempt == 0:
                logger.warning(f"JSON parsing failed (attempt 1/2): {e}. Retrying...")
                time.sleep(_get_sleep(config))
                continue
            raise
