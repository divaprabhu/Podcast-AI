def get_openai_response_format(format_val):
    if not format_val:
        return None
    if isinstance(format_val, dict):
        return {
            "type": "json_schema",
            "json_schema": {
                "name": "response",
                "strict": True,
                "schema": format_val,
            },
        }
    if format_val == "json":
        return {"type": "json_object"}
    return None
