def deep_merge(base: dict, override: dict) -> dict:
    result = base.copy()
    result.update(override)
    return result
