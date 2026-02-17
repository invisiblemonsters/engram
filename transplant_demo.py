"""ENGRAM Transplant Demo — Export signed memory package from Metatron.
Usage: python transplant_demo.py export [--topic QUERY] [--limit N]
       python transplant_demo.py import FILE
"""
import sys
import os
import json
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))

DATA_DIR = os.path.join(os.path.dirname(__file__), "engram_data")
PACKAGES_DIR = os.path.join(DATA_DIR, "memory_packages")
os.makedirs(PACKAGES_DIR, exist_ok=True)


def do_export(topic="AIP OR dream OR self-evolution OR insight", limit=30):
    from engram_core.engram import Engram

    e = Engram(
        data_dir=DATA_DIR,
        llm_base_url="https://integrate.api.nvidia.com/v1",
        llm_model="meta/llama-3.3-70b-instruct"
    )

    # Recall top memories matching topic
    memories = e.retriever.retrieve(topic, top_k=limit)
    if not memories:
        print("No memories found for topic:", topic)
        return

    unit_ids = [m.id for m in memories]
    package = e.transplant.export_package(
        unit_ids,
        metadata={
            "topic": topic,
            "source_agent": "Metatron",
            "source_npub": "npub182m9y3qyd7wfm9sew59yk7f8wm9mhwhme2gfjfyq44djm6wfswtsumxtyk",
            "engram_version": "0.6",
        }
    )

    ts = datetime.now().strftime("%Y%m%d%H%M")
    filename = f"metatron-to-picoclaw-{ts}.json"
    filepath = os.path.join(PACKAGES_DIR, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(package, f, indent=2, default=str)

    print(f"Exported {len(memories)} signed memories -> {filepath}")
    print(f"Package signed by: {package.get('agent_id', 'unknown')[:24]}...")
    print(f"Share this file with PicoClaw or post on Nostr/Gist")
    return filepath


def do_import(filepath):
    from engram_core.engram import Engram

    e = Engram(
        data_dir=DATA_DIR,
        llm_base_url="https://integrate.api.nvidia.com/v1",
        llm_model="meta/llama-3.3-70b-instruct"
    )

    with open(filepath, encoding="utf-8") as f:
        package = json.load(f)

    print(f"Package from: {package.get('agent_id', 'unknown')[:24]}...")
    print(f"Contains: {package.get('unit_count', 0)} memories")

    imported = e.transplant.import_package(package, auto_accept=False)
    print(f"Imported {len(imported)} memories as proposals (inactive)")
    print("Run 'python transplant_demo.py list' to see proposals")
    print("Run 'python transplant_demo.py approve <id>' to accept")


def do_list():
    from engram_core.engram import Engram

    e = Engram(
        data_dir=DATA_DIR,
        llm_base_url="https://integrate.api.nvidia.com/v1",
        llm_model="meta/llama-3.3-70b-instruct"
    )

    proposals = e.transplant.list_proposals()
    if not proposals:
        print("No pending proposals")
        return

    for p in proposals:
        print(f"  [{p.type}] {p.id[:12]}... | {p.content[:80]}...")


def do_approve(unit_id):
    from engram_core.engram import Engram

    e = Engram(
        data_dir=DATA_DIR,
        llm_base_url="https://integrate.api.nvidia.com/v1",
        llm_model="meta/llama-3.3-70b-instruct"
    )

    e.transplant.accept_proposal(unit_id)
    print(f"Approved: {unit_id}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python transplant_demo.py export|import|list|approve [args]")
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "export":
        topic = sys.argv[2] if len(sys.argv) > 2 else "AIP OR dream OR self-evolution OR insight"
        limit = int(sys.argv[3]) if len(sys.argv) > 3 else 30
        do_export(topic, limit)
    elif cmd == "import":
        do_import(sys.argv[2])
    elif cmd == "list":
        do_list()
    elif cmd == "approve":
        do_approve(sys.argv[2])
    else:
        print(f"Unknown command: {cmd}")
