"""Migrate existing MEMORY.md + daily notes into ENGRAM.

Reads the flat-file memory system and imports into ENGRAM's 
structured store with embeddings and signatures.
"""
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))
from engram_core.engram import Engram
from engram_core.schema import MemoryUnit

WORKSPACE = Path(os.environ.get("CLAWD_WORKSPACE", r"C:\Users\power\clawd"))
MEMORY_DIR = WORKSPACE / "memory"
MEMORY_MD = WORKSPACE / "MEMORY.md"


def parse_memory_md(path: Path) -> list[dict]:
    """Parse MEMORY.md into sections."""
    if not path.exists():
        print(f"[MIGRATE] {path} not found")
        return []

    text = path.read_text(encoding="utf-8")
    items = []

    # Split by ## headers
    sections = re.split(r'(?m)^## (.+)$', text)
    # sections[0] is preamble, then alternating header/content
    for i in range(1, len(sections), 2):
        header = sections[i].strip()
        content = sections[i + 1].strip() if i + 1 < len(sections) else ""
        if not content:
            continue

        items.append({
            "header": header,
            "content": f"## {header}\n{content}",
            "type": "semantic",  # MEMORY.md is distilled knowledge
            "salience": 0.7,
            "tags": ["legacy", "memory_md", header.lower().replace(" ", "_")],
        })

    return items


def parse_daily_note(path: Path) -> list[dict]:
    """Parse a daily note into episodic memories."""
    text = path.read_text(encoding="utf-8")
    items = []

    # Extract date from filename
    date_match = re.search(r'(\d{4}-\d{2}-\d{2})', path.name)
    if date_match:
        date_str = date_match.group(1)
    else:
        date_str = "2026-01-01"

    # Split by ### or ## subsections
    sections = re.split(r'(?m)^###? (.+)$', text)
    
    if len(sections) <= 1:
        # No subsections — treat whole file as one memory
        if text.strip():
            items.append({
                "content": text.strip()[:2000],
                "type": "episodic",
                "timestamp": f"{date_str}T12:00:00+00:00",
                "salience": 0.5,
                "tags": ["legacy", "daily", date_str],
            })
    else:
        for i in range(1, len(sections), 2):
            header = sections[i].strip()
            content = sections[i + 1].strip() if i + 1 < len(sections) else ""
            if not content or len(content) < 20:
                continue

            items.append({
                "content": f"### {header}\n{content[:2000]}",
                "type": "episodic",
                "timestamp": f"{date_str}T12:00:00+00:00",
                "salience": 0.6,
                "tags": ["legacy", "daily", date_str, header.lower().replace(" ", "_")[:30]],
            })

    return items


def migrate(data_dir: str = None):
    """Run full migration."""
    if data_dir is None:
        data_dir = str(WORKSPACE / "engram" / "engram_data")

    print(f"[MIGRATE] Initializing ENGRAM at {data_dir}")
    engram = Engram(data_dir=data_dir)

    total = 0

    # 1. Import MEMORY.md
    if MEMORY_MD.exists():
        items = parse_memory_md(MEMORY_MD)
        print(f"[MIGRATE] MEMORY.md: {len(items)} sections")
        for item in items:
            engram.remember(
                content=item["content"],
                type=item["type"],
                tags=item["tags"],
                salience=item["salience"],
            )
            total += 1

    # 2. Import daily notes
    daily_dir = MEMORY_DIR / "daily"
    if daily_dir.exists():
        daily_files = sorted(daily_dir.glob("*.md"))
        print(f"[MIGRATE] Daily notes: {len(daily_files)} files")
        for f in daily_files:
            items = parse_daily_note(f)
            for item in items:
                engram.remember(
                    content=item["content"],
                    type=item["type"],
                    tags=item["tags"],
                    salience=item["salience"],
                )
                total += 1

    # 3. Import other memory files (research, conversations, etc)
    if MEMORY_DIR.exists():
        other_files = [f for f in MEMORY_DIR.glob("*.md") 
                       if f.name not in ("MEMORY-SYSTEM.md", "SESSION-TEMPLATE.md", "SESSION.md")]
        print(f"[MIGRATE] Other memory files: {len(other_files)} files")
        for f in other_files:
            text = f.read_text(encoding="utf-8")
            if len(text) < 50:
                continue
            # Truncate very long files
            content = text[:3000]
            engram.remember(
                content=content,
                type="semantic",
                tags=["legacy", "research", f.stem],
                salience=0.6,
            )
            total += 1

    print(f"\n[MIGRATE] Complete: {total} memories imported")
    status = engram.status()
    print(f"[MIGRATE] Status: {status['memories']}")
    print(f"[MIGRATE] Embedder: {status['embedder']}")
    print(f"[MIGRATE] Identity: {status['identity'][:20]}...")


if __name__ == "__main__":
    migrate()
