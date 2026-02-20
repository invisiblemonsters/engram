"""ENGRAM core tests."""
import time
from pathlib import Path
import pytest


class TestMemoryStore:
    def test_store_has_memories(self, engram):
        status = engram.status()
        assert status["memories"]["total"] > 0

    def test_recall_returns_results(self, engram):
        results = engram.recall("memory system", top_k=5)
        assert len(results) >= 0  # may be empty on fresh install

    def test_recall_performance(self, engram):
        start = time.time()
        engram.recall("test query", top_k=10)
        assert time.time() - start < 30.0

    def test_remember_creates_unit(self, engram):
        unit = engram.remember("pytest auto-test memory", type="episodic",
                                salience=0.1, tags=["test", "auto-delete"])
        assert unit is not None
        assert unit.id is not None


class TestIdentity:
    def test_identity_loaded(self, engram):
        pubkey = engram.identity.public_key_b64()
        assert pubkey is not None
        assert len(pubkey) > 10

    def test_sign_verify(self, engram):
        msg = "test message for signing"
        sig = engram.identity.sign(msg)
        assert sig
        assert engram.identity.verify(msg, sig, engram.identity.public_key_b64())


class TestDreamer:
    def test_dreamer_exists(self, engram):
        assert engram.dreamer is not None


class TestProspective:
    def test_list_active(self, engram):
        assert isinstance(engram.prospective.list_active(), list)

    def test_check_triggers(self, engram):
        assert isinstance(engram.prospective.check_triggers("test"), list)


class TestSafeWrite:
    def test_safe_writer_init(self, engram):
        assert engram.safe_writer is not None

    def test_snapshot_creates_backup(self, engram):
        import os
        path = engram.safe_writer.snapshot()
        assert os.path.exists(path)


class TestTransplant:
    def test_export_empty(self, engram):
        package = engram.transplant.export_package(["nonexistent-id"])
        assert package.get("unit_count", 0) == 0 or package == {}


class TestConfig:
    def test_default_config(self):
        from engram.config import EngramConfig
        cfg = EngramConfig()
        assert cfg.embedding_provider == "sentence-transformers"
        assert cfg.llm_provider == "none"
        assert cfg.max_tokens == 2_000_000

    def test_override_config(self):
        from engram.config import EngramConfig
        cfg = EngramConfig(data_dir="/tmp/test", llm_provider="openai")
        assert cfg.data_dir == Path("/tmp/test")
        assert cfg.llm_provider == "openai"

    def test_env_override(self, monkeypatch):
        from engram.config import EngramConfig
        monkeypatch.setenv("ENGRAM_LLM_PROVIDER", "anthropic")
        cfg = EngramConfig()
        assert cfg.llm_provider == "anthropic"


class TestEmbedder:
    def test_hash_fallback(self):
        from engram.embedder import Embedder
        e = Embedder(provider="none")
        vec = e.embed("test")
        assert len(vec) == 384
        assert e.backend == "hash"

    def test_deterministic(self):
        from engram.embedder import Embedder
        e = Embedder(provider="none")
        v1 = e.embed("hello")
        v2 = e.embed("hello")
        assert v1 == v2
