#!/usr/bin/env python3
"""ENGRAM capture — save session summary as episodic memory.
Usage: python engram_capture.py "Session summary text here"
"""
import sys
import os

os.chdir(os.path.dirname(os.path.abspath(__file__)))

from engram_core.engram import Engram

def capture(content: str):
    e = Engram(data_dir="engram_data")
    e.remember(
        content=f"Session log:\n{content}",
        type="episodic",
        tags=["session-log", "metatron"],
        salience=0.85
    )
    print(f"Captured session memory ({len(content)} chars)")

if __name__ == "__main__":
    content = sys.argv[1] if len(sys.argv) > 1 else sys.stdin.read()
    capture(content)
