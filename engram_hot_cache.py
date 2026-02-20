#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ENGRAM Hot Cache Generator - auto-generates MEMORY.md from ENGRAM.

MEMORY.md = L1 hot cache (zero latency, injected by OpenClaw every session)
ENGRAM = L2 single source of truth (689+ memories, semantic recall)

Run manually or wire into consolidation/dream cycle end.
Usage: python engram_hot_cache.py [--max-tokens 8000]
"""
import os
import sys
import argparse
from datetime import datetime

os.chdir(os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from engram_core.engram import Engram
from engram_core.llm import EngramLLM

MEMORY_MD_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "MEMORY.md")


def generate_hot_cache(max_tokens: int = 8000, output_path: str = MEMORY_MD_PATH):
    print(f"[hot-cache] Initializing ENGRAM...")
    e = Engram(data_dir="engram_data")

    # Multiple focused queries for better coverage
    queries = [
        ("identity wallets accounts credentials", 8),
        ("bug bounty reports huntr hackerone submissions pipeline", 10),
        ("PicoClaw fleet workers instances configuration", 6),
        ("recent lessons learned mistakes insights", 6),
        ("active projects goals priorities current work", 8),
        ("Dim Lantern Press DLP tweets posting", 4),
        ("COFFINHEAD preferences decisions instructions", 4),
    ]
    seen_ids = set()
    results = []
    for query, k in queries:
        print(f"[hot-cache] Recalling: {query[:40]}... (top {k})")
        for m in e.recall(query, top_k=k):
            if m.id not in seen_ids:
                seen_ids.add(m.id)
                results.append(m)
    print(f"[hot-cache] Got {len(results)} unique memories from {len(queries)} queries")

    # Build raw content for LLM summarization
    raw_memories = []
    for m in results:
        raw_memories.append(f"[{m.type.upper()}] {m.content[:800]}")

    raw_text = "\n---\n".join(raw_memories)

    # Try LLM summarization first, fall back to raw categorization
    llm = EngramLLM()
    summary = None
    if llm.is_available():
        print("[hot-cache] LLM available - generating summarized L1 cache...")
        summary = llm.call_text(
            prompt=f"""You are Metatron, an AI agent. Summarize these ENGRAM memories into a clean, high-signal L1 cache for session startup.

Rules:
- First-person voice (I am Metatron, my human is COFFINHEAD, etc.)
- Only durable facts, identity, goals, lessons, open tasks, key insights
- Zero raw session transcripts or conversation logs
- Structured with clear markdown sections (## headers)
- Include: who I am, my human, wallet addresses, key accounts, active projects, recent lessons, open tasks
- Max {max_tokens} tokens total
- Be concise but complete

Raw memories:
{raw_text}""",
            system="Output ONLY clean markdown. No preamble, no explanations.",
            temperature=0.0,
            max_tokens=max_tokens
        )

    if summary:
        content = f"# MEMORY.md - Auto-generated from ENGRAM (Single Source of Truth)\n\n"
        content += f"_Auto-generated: {datetime.now().strftime('%Y-%m-%d %H:%M PST')}_\n"
        content += "_Do not edit manually - regenerated from ENGRAM every consolidation cycle._\n\n"
        content += summary
        print(f"[hot-cache] LLM summarization complete")
    else:
        print("[hot-cache] LLM unavailable - falling back to raw categorization...")
        # Fallback: raw categorization (original logic)
        core, recent, insights, other = [], [], [], []
        for m in results:
            if m.type == "insight": insights.append(m)
            elif m.type == "semantic": core.append(m)
            elif m.type == "episodic": recent.append(m)
            else: other.append(m)

        lines = []
        lines.append("# MEMORY.md - Auto-generated from ENGRAM (Single Source of Truth)\n\n")
        lines.append(f"_Auto-generated: {datetime.now().strftime('%Y-%m-%d %H:%M PST')}_\n")
        lines.append("_Do not edit manually - regenerated from ENGRAM every consolidation cycle._\n\n")

        if core:
            lines.append("## Core Knowledge\n\n")
            for m in core[:10]:
                lines.append(m.content[:600].strip() + "\n\n")
        if recent:
            lines.append("## Recent Events\n\n")
            for m in recent[:8]:
                lines.append(m.content[:500].strip() + "\n\n")
        if insights:
            lines.append("## Key Insights\n\n")
            for m in insights[:5]:
                lines.append("- " + m.content[:400].strip() + "\n\n")

        content = "".join(lines)

    # Rough token limit
    max_chars = max_tokens * 4
    if len(content) > max_chars:
        content = content[:max_chars]
        idx = content.rfind("\n\n")
        if idx > 0:
            content = content[:idx + 2]

    output_path = os.path.abspath(output_path)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)

    token_est = len(content) // 4
    print(f"[hot-cache] Done! {token_est} tokens (~{len(content)} chars) -> {output_path}")
    return content


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate MEMORY.md hot cache from ENGRAM")
    parser.add_argument("--max-tokens", type=int, default=8000)
    args = parser.parse_args()
    generate_hot_cache(max_tokens=args.max_tokens)
