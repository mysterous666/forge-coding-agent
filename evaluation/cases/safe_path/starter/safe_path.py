from pathlib import Path


def safe_join(root: Path, user_path: str) -> Path:
    return (root / user_path).resolve()
