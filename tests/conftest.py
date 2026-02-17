"""ENGRAM test fixtures — shared across all test modules."""
import os
import sys
import pytest

# Ensure engram root is on path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "engram_data")


@pytest.fixture(scope="session")
def engram():
    """Shared ENGRAM instance for all tests (session-scoped to avoid reload)."""
    from engram_core.engram import Engram
    return Engram(
        data_dir=DATA_DIR,
        llm_base_url="https://integrate.api.nvidia.com/v1",
        llm_model="meta/llama-3.3-70b-instruct"
    )
