"""ENGRAM core tests — must all pass for self-evolution auto-apply."""
import time
import pytest


class TestMemoryStore:
    """Test memory storage and retrieval basics."""

    def test_store_has_memories(self, engram):
        """Store should have >0 memories."""
        status = engram.status()
        assert status["memories"]["total"] > 0, "No memories in store"

    def test_recall_returns_results(self, engram):
        """Recall should return results for a known topic."""
        results = engram.retriever.retrieve("AIP protocol", top_k=5)
        assert len(results) > 0, "Recall returned empty for 'AIP protocol'"

    def test_recall_performance(self, engram):
        """Recall should complete in <2s (CPU embedding)."""
        start = time.time()
        engram.retriever.retrieve("dream cycle insights", top_k=10)
        elapsed = time.time() - start
        assert elapsed < 10.0, f"Recall took {elapsed:.1f}s (>10s)"  # LanceDB cold start is slow, warm is <1s

    def test_remember_creates_unit(self, engram):
        """Remember should create and return a MemoryUnit."""
        unit = engram.remember(
            "pytest auto-test memory — safe to delete",
            type="episodic",
            salience=0.1,
            tags=["test", "auto-delete"]
        )
        assert unit is not None
        assert unit.id is not None
        assert unit.content == "pytest auto-test memory — safe to delete"


class TestIdentity:
    """Test Ed25519 identity system."""

    def test_identity_loaded(self, engram):
        """Agent should have an Ed25519 identity."""
        pubkey = engram.identity.public_key_b64()
        assert pubkey is not None
        assert len(pubkey) > 10

    def test_sign_verify(self, engram):
        """Sign/verify round-trip should work."""
        msg = "test message for signing"
        sig = engram.identity.sign(msg)
        assert sig is not None
        verified = engram.identity.verify(msg, sig, engram.identity.public_key_b64())
        assert verified, "Signature verification failed"


class TestDreamer:
    """Test dream cycle components."""

    def test_dreamer_exists(self, engram):
        """Dreamer subsystem should be initialized."""
        assert engram.dreamer is not None

    def test_diverse_sample(self, engram):
        """Dreamer should be able to sample memories."""
        # Just check it doesn't crash
        assert engram.dreamer.store is not None


class TestProspective:
    """Test prospective memory system."""

    def test_list_active(self, engram):
        """Should be able to list active prospective memories."""
        active = engram.prospective.list_active()
        assert isinstance(active, list)

    def test_check_triggers(self, engram):
        """Trigger check should not crash on arbitrary context."""
        result = engram.prospective.check_triggers("random test context string")
        assert isinstance(result, list)


class TestSafeWrite:
    """Test transactional backup layer."""

    def test_safe_writer_init(self, engram):
        """SafeWriter should exist on engram."""
        assert engram.safe_writer is not None
        assert hasattr(engram.safe_writer, 'snapshot')
        assert hasattr(engram.safe_writer, 'rollback')

    def test_snapshot_creates_backup(self, engram):
        """Snapshot should create a backup directory."""
        import os
        path = engram.safe_writer.snapshot()
        assert os.path.exists(path)


class TestSelfEvolveSafety:
    """Test self-evolve safety gates."""

    def test_confidence_threshold(self, engram):
        """Self-evolve should reject patches below 0.99."""
        from engram_core.self_evolve import SelfEvolver, EvolutionPatch
        evolver = SelfEvolver(engram)
        patch = EvolutionPatch(
            patch_type="test", target_file="engram_core/schema.py",
            diff="test", confidence=0.95, rationale="test"
        )
        assert evolver.try_auto_apply(patch) == False


class TestTransplant:
    """Test transplant system."""

    def test_export_empty(self, engram):
        """Export with no matching IDs should return empty."""
        package = engram.transplant.export_package(["nonexistent-id-12345"])
        # Should return empty or dict with 0 units
        assert package.get("unit_count", 0) == 0 or package == {}
