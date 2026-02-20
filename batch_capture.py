#!/usr/bin/env python3
"""Batch capture daily logs into ENGRAM as episodic memories.
Splits each file into ~1500 char chunks at section boundaries.
Usage: python batch_capture.py memory/daily/2026-02-18.md memory/daily/2026-02-19.md ...
"""
import sys
import os
import re

os.chdir(os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from engram_core.engram import Engram

CHUNK_SIZE = 1500

def split_sections(text):
    """Split markdown into sections at ## headers, then chunk if needed."""
    sections = re.split(r'\n(?=## )', text)
    chunks = []
    for section in sections:
        if len(section) <= CHUNK_SIZE:
            if section.strip():
                chunks.append(section.strip())
        else:
            # Split at ### headers within section
            subsections = re.split(r'\n(?=### )', section)
            current = ""
            for sub in subsections:
                if len(current) + len(sub) > CHUNK_SIZE and current:
                    chunks.append(current.strip())
                    current = sub
                else:
                    current += "\n" + sub
            if current.strip():
                chunks.append(current.strip())
    return chunks

def main():
    files = sys.argv[1:]
    if not files:
        print("Usage: python batch_capture.py <file1.md> <file2.md> ...")
        return

    e = Engram(data_dir="engram_data")
    total = 0

    for fpath in files:
        abspath = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", fpath)
        if not os.path.exists(abspath):
            print(f"[SKIP] {fpath} not found")
            continue

        with open(abspath, 'r', encoding='utf-8') as f:
            text = f.read()

        date = os.path.basename(fpath).replace('.md', '')
        chunks = split_sections(text)
        print(f"[{date}] {len(chunks)} chunks from {len(text)} chars")

        for i, chunk in enumerate(chunks):
            e.remember(
                content=f"Daily log {date} (part {i+1}/{len(chunks)}):\n{chunk}",
                type="episodic",
                tags=["daily-log", date, "metatron"],
                salience=0.8
            )
            total += 1

    print(f"\nDone! Captured {total} memories total.")

if __name__ == "__main__":
    main()
