import pytest
import sys
from pathlib import Path


root_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(root_dir))


@pytest.fixture
def raw_players():
    ids_and_usernames = [
        (3, "Chuck"),
        (2, "Bob"),
        (5, "Eve"),
        (1, "Alice"),
        (4, "Daniel")
    ]
    return ids_and_usernames
