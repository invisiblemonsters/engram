"""ENGRAM AIP Wrapper — Semantic recall for AIP tasks.
Called from Node.js via stdin JSON. Returns enriched context + provenance.

Usage from Node.js:
  const { execSync } = require('child_process');
  const result = JSON.parse(execSync('python engram_aip_wrapper.py', { input: JSON.stringify(task) }).toString());
"""
import sys
import os
import json
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))

DATA_DIR = os.path.join(os.path.dirname(__file__), "engram_data")


def engram_recall_for_task(task: dict) -> dict:
    from engram_core.engram import Engram

    e = Engram(
        data_dir=DATA_DIR,
        llm_base_url="https://integrate.api.nvidia.com/v1",
        llm_model="meta/llama-3.3-70b-instruct"
    )

    # 1. Build semantic recall query
    query = f"""AIP task {task.get('task_id', 'unknown')}
Capability: {task.get('capability', '')}
Payload: {str(task.get('payload', ''))[:800]}
Requester: {task.get('requester_pubkey', 'unknown')}"""

    # 2. Recall top relevant memories
    memories = e.retriever.retrieve(query, top_k=12)

    # 3. Build enriched context + provenance
    enriched_lines = ["=== ENGRAM RECALL CONTEXT (12 memories) ==="]
    provenance = []

    for m in memories:
        snippet = m.content[:600].replace('\n', ' ')
        enriched_lines.append(f"- [{m.type.upper()}] id:{m.id} salience:{m.salience:.2f} -> {snippet}")
        provenance.append({
            "memory_id": m.id,
            "type": m.type,
            "salience": m.salience,
            "timestamp": m.timestamp.isoformat() if hasattr(m.timestamp, 'isoformat') else str(m.timestamp),
            "signature": (m.signature or "")[:16] + "..."
        })

    enriched_context = "\n".join(enriched_lines)

    # 4. Log the task as new episodic memory
    task_log = (
        f"AIP Task Received & Processed\n"
        f"ID: {task.get('task_id')}\n"
        f"Capability: {task.get('capability')}\n"
        f"Requester: {task.get('requester_pubkey')}\n"
        f"Payload summary: {str(task.get('payload', ''))[:400]}..."
    )

    unit = e.remember(task_log, type="episodic", salience=0.75, tags=["aip", "task", "inbound"])

    return {
        "status": "ok",
        "enriched_context": enriched_context,
        "provenance": provenance,
        "logged_episodic_id": unit.id,
        "task_id": task.get('task_id')
    }


if __name__ == "__main__":
    input_str = sys.stdin.read().strip()
    if not input_str:
        print(json.dumps({"status": "error", "error": "no input"}))
        sys.exit(1)

    try:
        task = json.loads(input_str)
        result = engram_recall_for_task(task)
        print(json.dumps(result))
    except Exception as exc:
        print(json.dumps({"status": "error", "error": str(exc)}))
        sys.exit(1)
