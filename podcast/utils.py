import re


def format_prompt(prompt_template, replacements):
    if not prompt_template:
        return ""
    def replacer(m):
        return str(replacements.get(m.group(1), m.group(0)))
    return re.sub(r"\{\{(\w+)\}\}", replacer, prompt_template)
