"""ENGRAM test fixtures."""
import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "engram_data")


@pytest.fixture(scope="session")
def engram():
    from engram import Engram
    return Engram(data_dir=DATA_DIR)
