import json
import logging
import time

from . import openrouter
from . import github
from . import ollama
from . import lm_studio
from . import ollama_cloud

logger = logging.getLogger(__name__)


def _get_sleep(config):
    return config.get("llm", {}).get("default", {}).get("sleep", 10)


_PROVIDERS = {
    "openrouter": openrouter,
    "github": github,
    "ollama": ollama,
    "lm_studio": lm_studio,
    "ollama_cloud": ollama_cloud
}


def call_llm(config, system_prompt, user_prompt, provider=None, model=None, response_format=None):
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


def safe_json_load(text):
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


def call_llm_json(config, system_prompt, user_prompt, provider=None, model=None, response_format=None):
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
