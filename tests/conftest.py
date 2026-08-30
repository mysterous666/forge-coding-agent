from pathlib import Path
from uuid import uuid4

import pytest


@pytest.fixture
def tmp_path() -> Path:
    """Use a workspace-local temp directory (the managed Windows temp ACL is restricted)."""
    path = Path.cwd() / ".test_tmp" / uuid4().hex
    path.mkdir(parents=True)
    return path

