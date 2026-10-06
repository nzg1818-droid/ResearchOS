"""Keep test data inside the checkout, with inherited Windows workspace ACLs."""
from pathlib import Path
from uuid import uuid4
import pytest

@pytest.fixture
def tmp_path():
    path = Path(__file__).resolve().parents[2] / 'acceptance-data' / 'pytest' / uuid4().hex
    path.mkdir(parents=True)
    return path
