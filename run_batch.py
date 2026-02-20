#!/usr/bin/env python3
"""Run batch capture with suppressed stderr and flushed stdout."""
import sys, os, io

os.chdir(os.path.dirname(os.path.abspath(__file__)))
sys.stderr = open(os.devnull, 'w')
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace', line_buffering=True)

print("Loading ENGRAM...")
from engram_core.engram import Engram
import re

CHUNK_SIZE = 1500

def split_sections(text):
    sections = re.split(r'\n(?=## )', text)
    chunks = []
    for section in sections:
        if len(section) <= CHUNK_SIZE:
            if section.strip():
                chunks.append(section.strip())
        else:
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

e = Engram(data_dir="engram_data")
print("ENGRAM ready.")

files = ["memory/daily/2026-02-18.md", "memory/daily/2026-02-19.md", "memory/daily/2026-02-20.md"]
total = 0

for fpath in files:
    abspath = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", fpath)
    if not os.path.exists(abspath):
        print(f"SKIP: {fpath}")
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
        if (total % 5) == 0:
            print(f"  ...captured {total} memories so far")

print(f"DONE: Captured {total} new memories.")
