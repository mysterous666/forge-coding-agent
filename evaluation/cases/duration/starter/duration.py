import re


SECONDS = {"d": 86400, "h": 3600, "m": 60, "s": 1}


def parse_duration(text: str) -> int:
    parts = re.findall(r"(\d+)\s*([dhms])", text)
    if not parts:
        raise ValueError("invalid duration")
    return sum(int(value) * SECONDS[unit] for value, unit in parts)
