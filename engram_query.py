#!/usr/bin/env python3
"""ENGRAM CLI query — semantic recall for Metatron's sessions.
Usage: python engram_query.py "what do I know about AIP?"
       python engram_query.py "recent goals" --top_k 15
"""
import sys
import json
import os

os.chdir(os.path.dirname(os.path.abspath(__file__)))

from engram import Engram

def query(q: str, top_k: int = 8):
    e = Engram(data_dir="engram_data")
    results = e.recall(q, top_k=top_k)
    out = []
    for m in results:
        out.append({
            "id": m.id[:12],
            "type": m.type,
            "salience": round(m.salience, 2),
            "ts": m.timestamp.isoformat() if hasattr(m.timestamp, 'isoformat') else str(m.timestamp),
            "content": m.content[:1200]
        })
    import sys as _sys
    _sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    print(json.dumps(out, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    q = sys.argv[1] if len(sys.argv) > 1 else "current goals and recent events"
    k = int(sys.argv[2]) if len(sys.argv) > 2 else 8
    query(q, k)
