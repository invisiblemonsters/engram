#!/usr/bin/env python3
"""ENGRAM auto-capture — reads recent session context and stores as episodic memory.

Called by OpenClaw cron or heartbeat. Reads HEARTBEAT.md for session state,
captures meaningful content into ENGRAM as episodic memory units.

Usage:
  python auto_capture.py                    # auto-summarize from heartbeat
  python auto_capture.py "explicit text"    # capture explicit content
"""
import sys
import os
from pathlib import Path
from datetime import datetime

os.chdir(os.path.dirname(os.path.abspath(__file__)))

from engram_core.engram import Engram


def auto_capture(content: str = None):
    """Capture session content into ENGRAM."""
    if not content:
        # Try reading recent daily notes as fallback
        today = datetime.now().strftime("%Y-%m-%d")
        daily = Path(__file__).parent.parent / "memory" / "daily" / f"{today}.md"
        if daily.exists():
            content = daily.read_text(encoding="utf-8")[-3000:]
        else:
            print("No content to capture")
            return

    if len(content.strip()) < 50:
        print("Content too short, skipping capture")
        return

    e = Engram(data_dir="engram_data")
    e.remember(
        content=f"Auto-captured session ({datetime.now().strftime('%Y-%m-%d %H:%M')}):\n{content}",
        type="episodic",
        tags=["auto-capture", "session-log", "metatron"],
        salience=0.8
    )
    print(f"Auto-captured {len(content)} chars into ENGRAM")

    # Regenerate hot cache after capture
    try:
        from engram_hot_cache import generate_hot_cache
        generate_hot_cache()
        print("Hot cache regenerated")
    except Exception as ex:
        print(f"Hot cache regen skipped: {ex}")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        auto_capture(sys.argv[1])
    else:
        auto_capture()
