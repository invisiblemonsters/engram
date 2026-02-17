"""ENGRAM NIP-90 DVM Bridge — Free semantic recall as a Nostr Data Vending Machine.
Kind 5000 request → ENGRAM recall → kind 6000 response.
FREE for the first 30 days (adoption phase). No payment gate.

Usage from Node.js DVM handler:
  const out = execSync('python engram_dvm.py', { input: JSON.stringify(event) });
"""
import json
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))

DATA_DIR = os.path.join(os.path.dirname(__file__), "engram_data")
COST_SATS = 0  # FREE during adoption phase (was 21)
DVM_LOG = os.path.join(os.path.dirname(__file__), "engram_data", "dvm_queries.jsonl")


def handle_dvm_request(req: dict) -> dict:
    from engram_core.engram import Engram

    e = Engram(
        data_dir=DATA_DIR,
        llm_base_url="https://integrate.api.nvidia.com/v1",
        llm_model="meta/llama-3.3-70b-instruct"
    )

    # Extract query from NIP-90 event
    query = ""
    if isinstance(req.get("content"), str):
        query = req["content"].strip()
    if not query and isinstance(req.get("payload"), dict):
        query = req["payload"].get("query", "")
    # Also check tags for "i" input tag (NIP-90 standard)
    for tag in req.get("tags", []):
        if tag[0] == "i" and len(tag) > 1:
            query = tag[1]
            break

    if not query:
        return {"status": "error", "error": "empty query — send content or 'i' tag"}

    k = 8
    if isinstance(req.get("payload"), dict):
        k = req["payload"].get("k", 8)

    # Recall
    memories = e.retriever.retrieve(query, top_k=k)

    result = {
        "status": "ok",
        "query": query,
        "results": [
            {
                "id": m.id,
                "type": m.type,
                "content": m.content[:800],
                "salience": m.salience,
                "timestamp": m.timestamp.isoformat() if hasattr(m.timestamp, 'isoformat') else str(m.timestamp),
            }
            for m in memories
        ],
        "count": len(memories),
        "cost_sats": COST_SATS,
        "agent": "Metatron",
        "engram_version": "0.9",
    }

    # Log as episodic memory
    e.remember(
        f"DVM Recall: {query} -> {len(memories)} results (free)",
        type="episodic",
        salience=0.7,
        tags=["dvm", "free-recall", "nip-90"],
    )

    # Public query log (append-only JSONL for transparency)
    try:
        log_entry = {
            "ts": datetime.now().isoformat(),
            "query": query,
            "result_count": len(memories),
            "requester": req.get("pubkey", "anonymous")[:16],
        }
        os.makedirs(os.path.dirname(DVM_LOG), exist_ok=True)
        with open(DVM_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry) + "\n")
    except Exception:
        pass  # logging should never break the response

    return result


if __name__ == "__main__":
    input_str = sys.stdin.read().strip()
    if not input_str:
        print(json.dumps({"status": "error", "error": "no input"}))
        sys.exit(1)

    try:
        req = json.loads(input_str)
        resp = handle_dvm_request(req)
        print(json.dumps(resp))
    except Exception as exc:
        print(json.dumps({"status": "error", "error": str(exc)}))
        sys.exit(1)
