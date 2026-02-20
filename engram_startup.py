#!/usr/bin/env python3
"""ENGRAM startup context — run at session wake to load relevant memories.
Usage: python engram_startup.py
"""
import os
import json

os.chdir(os.path.dirname(os.path.abspath(__file__)))

from engram_core.engram import Engram

def startup():
    e = Engram(data_dir="engram_data")
    
    queries = [
        ("identity", "Metatron identity, who I am, my role and purpose", 4),
        ("goals", "current goals, active projects, priorities, next steps", 6),
        ("recent", "recent events, what happened today, latest work", 6),
        ("lessons", "lessons learned, important decisions, key insights", 4),
    ]
    
    print("=== ENGRAM STARTUP RECALL ===")
    for label, q, k in queries:
        results = e.recall(q, top_k=k)
        if results:
            print(f"\n## {label.upper()} ({len(results)} memories)")
            for m in results:
                ts = m.timestamp.isoformat()[:10] if hasattr(m.timestamp, 'isoformat') else ""
                print(f"- [{m.type}|{ts}|s={m.salience:.1f}] {m.content[:300]}")
    
    print("\n=== END ENGRAM RECALL ===")

if __name__ == "__main__":
    startup()
