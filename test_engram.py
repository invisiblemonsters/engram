"""Quick smoke test for ENGRAM core."""
import sys
import os
import shutil

# Add parent to path
sys.path.insert(0, os.path.dirname(__file__))

from engram_core.engram import Engram

TEST_DIR = os.path.join(os.path.dirname(__file__), "test_data")

def test_basic():
    """Test basic remember/recall cycle."""
    # Clean test dir
    if os.path.exists(TEST_DIR):
        shutil.rmtree(TEST_DIR)

    engram = Engram(data_dir=TEST_DIR)
    
    # Wakeup
    report = engram.wakeup()
    print(f"Wakeup report: {report['metabolism']}")

    # Remember some things
    m1 = engram.remember("AIP v0.1 was deployed on February 16, 2026", 
                         tags=["aip", "milestone"], salience=0.9)
    print(f"Stored: {m1.id[:8]}... type={m1.type} salience={m1.salience}")

    m2 = engram.remember("Coinos API uses bearer tokens for authentication",
                         tags=["coinos", "api"], salience=0.7)
    print(f"Stored: {m2.id[:8]}... type={m2.type}")

    m3 = engram.remember("snowflake-arctic-embed-m runs at 40-90ms on CPU",
                         tags=["embedding", "performance"], salience=0.6)
    print(f"Stored: {m3.id[:8]}... type={m3.type}")

    # Create a prospective memory
    p1 = engram.intend(
        trigger="Someone mentions huntr.com or bug bounty",
        action={"type": "remind", "message": "Check if any new MFV targets appeared"},
        content="Check huntr for new targets when bounties come up"
    )
    print(f"Prospective: {p1.id[:8]}... trigger={p1.trigger_condition[:40]}")

    # Recall
    results = engram.recall("What do I know about AIP?")
    print(f"\nRecall 'AIP': {len(results)} results")
    for r in results[:3]:
        print(f"  - [{r.type}] {r.content[:80]}...")

    results2 = engram.recall("How does authentication work?")
    print(f"\nRecall 'authentication': {len(results2)} results")
    for r in results2[:3]:
        print(f"  - [{r.type}] {r.content[:80]}...")

    # Status
    status = engram.status()
    print(f"\nStatus: {status['memories']}")
    print(f"Embedder: {status['embedder']}")
    print(f"Identity: {status['identity'][:20]}...")
    print(f"Metabolism: {status['metabolism']}")

    # Sleep
    sleep_report = engram.sleep()
    print(f"\nSleep: {sleep_report}")

    # Cleanup
    shutil.rmtree(TEST_DIR)
    print("\nAll tests passed!")


if __name__ == "__main__":
    test_basic()
