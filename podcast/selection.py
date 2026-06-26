import logging

from .cache import read_cache_json, write_cache_json
from .llm import call_llm_json
from .utils import format_prompt

logger = logging.getLogger(__name__)


def step_select_paper(config):
    # If a unified paper cache exists and contains a selected paper, load it
    data = read_cache_json(config)
    if isinstance(data, dict) and "selected" in data:
        logger.info("Loading selected paper from cache.")
        return data["selected"]

    prompts = config.get("prompts", {}).get("selection", {})
    if isinstance(data, dict) and "papers" in data:
        papers = data["papers"]
    else:
        raise KeyError(
            "No papers available in cache; run the 'fetch' step first."
        )
    system_prompt = prompts.get("system", "")

    papers_list_text = ""
    for idx, p in enumerate(papers):
        papers_list_text += (
            f"[{idx}] Title: {p['title']}\nSummary: {p['summary']}\n\n"
            )

    user_prompt = format_prompt(
        prompts.get("user", ""), {"papers_list": papers_list_text}
    )

    response_format = {
        "type": "object",
        "properties": {
            "index": {"type": "integer"},
            "reason": {"type": "string"},
        },
        "required": ["index", "reason"],
    }

    sel_provider = config.get("llm", {}).get("pipeline", {})
    sel_provider = sel_provider.get("selection", {}).get("provider")
    sel_model = config.get("llm", {}).get("pipeline", {})
    sel_model = sel_model.get("selection", {}).get("model")

    selection = call_llm_json(
        config, system_prompt, user_prompt,
        provider=sel_provider, model=sel_model,
        response_format=response_format,
    )

    if (
        not isinstance(selection, dict)
        or "index" not in selection
        or "reason" not in selection
    ):
        raise ValueError(
            f"LLM returned unexpected JSON format: {selection}. "
            "Expected {\"index\": <int>, \"reason\": \"<string>\"}."
        )
    idx = int(selection["index"])
    if idx < 0 or idx >= len(papers):
        raise ValueError(f"LLM returned out-of-bounds paper index: {idx}")
    selected_paper = papers[idx]
    selected_paper["selection_reason"] = selection["reason"]

    data["selected"] = selected_paper
    write_cache_json(data, config)
    logger.info(
        f"Selected Paper: {selection['index']}: {selected_paper['title']}"
    )
    return selected_paper
