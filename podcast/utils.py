"""Template-string formatting utility.

Provides a simple ``{{placeholder}}``-style substitution function used by
pipeline prompt builders.
"""

import re


def format_prompt(prompt_template: str, replacements: dict[str, str]) -> str:
    """Replace ``{{key}}`` placeholders in *prompt_template* with values.

    The template uses double-curly-brace placeholders (e.g. ``{{title}}``).
    Keys that do not appear in *replacements* are left unchanged.

    Args:
        prompt_template: Template string with ``{{key}}`` placeholders.
        replacements: Mapping of placeholder keys to their string values.

    Returns:
        The template with all recognised placeholders substituted.
    """
    if not prompt_template:
        return ""

    def replacer(m):
        return str(replacements.get(m.group(1), m.group(0)))
    return re.sub(r"\{\{(\w+)\}\}", replacer, prompt_template)
