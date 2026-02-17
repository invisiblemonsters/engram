"""ENGRAM Heartbeat — Check prospective memory triggers.
Run every 15 min via Task Scheduler or OpenClaw cron.
"""
import os
import sys
import json
import time
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))

DATA_DIR = os.path.join(os.path.dirname(__file__), "engram_data")
ACTIONS_FILE = os.path.join(os.path.dirname(__file__), "engram_data", "ACTIONS.md")

def heartbeat_check():
    from engram_core.engram import Engram
    
    # Build context from recent session activity
    context_parts = []
    context_parts.append(f"Current time: {datetime.now().isoformat()}")
    
    # Read HEARTBEAT.md if it exists (OpenClaw workspace)
    heartbeat_path = os.path.join(os.path.dirname(__file__), "..", "HEARTBEAT.md")
    if os.path.exists(heartbeat_path):
        with open(heartbeat_path, "r", encoding="utf-8") as f:
            context_parts.append(f.read()[:2000])
    
    # Read recent daily notes for context
    daily_dir = os.path.join(os.path.dirname(__file__), "..", "memory", "daily")
    today = datetime.now().strftime("%Y-%m-%d")
    daily_path = os.path.join(daily_dir, f"{today}.md")
    if os.path.exists(daily_path):
        with open(daily_path, "r", encoding="utf-8") as f:
            context_parts.append(f.read()[-2000:])
    
    context = "\n---\n".join(context_parts)
    
    print(f"[HEARTBEAT] Initializing ENGRAM...")
    e = Engram(
        data_dir=DATA_DIR,
        llm_base_url="https://integrate.api.nvidia.com/v1",
        llm_model="meta/llama-3.3-70b-instruct"
    )
    
    # Check prospective memories
    matches = e.prospective.check_triggers(context)
    
    if matches:
        print(f"[HEARTBEAT] {len(matches)} prospective triggers matched!")
        # Fire each and write actions to ACTIONS.md
        with open(ACTIONS_FILE, "a", encoding="utf-8") as f:
            for unit, score in matches:
                action = e.prospective.fire(unit)
                f.write(f"\n## {datetime.now().isoformat()} (score={score:.2f})\n")
                f.write(f"Trigger: {unit.trigger_condition}\n")
                f.write(f"Action: {json.dumps(action)}\n")
        print(f"[HEARTBEAT] Actions written to {ACTIONS_FILE}")
    else:
        print(f"[HEARTBEAT] No triggers matched")

if __name__ == "__main__":
    heartbeat_check()
