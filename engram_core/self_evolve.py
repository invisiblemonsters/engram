"""ENGRAM Self-Evolution Module (v0.5)
Dream cycle outputs executable patches → code evolution → better memory.
Designed by Grok 4.20, implemented by Metatron.
"""
import os
import json
import difflib
from datetime import datetime, timezone
from typing import Optional, Callable, List


class EvolutionPatch:
    """A proposed code patch from the dream cycle."""
    def __init__(self, patch_type: str, target_file: str, diff: str,
                 confidence: float, rationale: str, test_command: Optional[str] = None):
        self.patch_type = patch_type  # new_skill, prompt_improve, consolidation_rule, dream_heuristic, narrative_update
        self.target_file = target_file
        self.diff = diff
        self.confidence = confidence
        self.rationale = rationale
        self.test_command = test_command


class SelfEvolver:
    """Generates and applies self-improvement patches from dream insights."""

    def __init__(self, engram, llm_fn: Optional[Callable] = None):
        self.engram = engram
        self.llm = llm_fn
        self.min_confidence = 0.92  # Only auto-apply above this
        self.proposals_dir = os.path.join(engram.store.data_dir, "evolution_proposals")
        os.makedirs(self.proposals_dir, exist_ok=True)

    def generate_patches(self) -> List[EvolutionPatch]:
        """Ask LLM to propose improvements based on recent insights."""
        if not self.llm:
            return []

        # Get recent insights from dream cycle
        insights = self.engram.store.query(type="insight", limit=20)
        if not insights:
            return []

        insight_texts = [i.content for i in insights]
        prompt = (
            "You are a self-improvement engine for an AI agent's memory system (ENGRAM). "
            "Based on these recent insights from the dream cycle, propose concrete "
            "improvements to the codebase.\n\n"
            "Recent insights:\n" + json.dumps(insight_texts, indent=2) + "\n\n"
            "Output ONLY a JSON array of patches:\n"
            '[{"patch_type": "prompt_improve|consolidation_rule|dream_heuristic", '
            '"target_file": "relative/path.py", '
            '"description": "what to change", '
            '"confidence": 0.0-1.0, '
            '"rationale": "why this improves the system"}]'
        )

        try:
            result = self.llm(prompt)
            start = result.find("[")
            end = result.rfind("]") + 1
            if start == -1 or end == 0:
                return []
            patches_data = json.loads(result[start:end])
        except Exception as e:
            print(f"[ENGRAM] Self-evolve LLM error: {e}")
            return []

        patches = []
        for p in patches_data:
            if p.get("confidence", 0) > 0.85:
                patches.append(EvolutionPatch(
                    patch_type=p.get("patch_type", "unknown"),
                    target_file=p.get("target_file", ""),
                    diff=p.get("description", ""),
                    confidence=p.get("confidence", 0),
                    rationale=p.get("rationale", ""),
                ))
        return patches

    def save_proposal(self, patch: EvolutionPatch) -> str:
        """Save a patch proposal for human review."""
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        filename = f"{ts}_{patch.patch_type}.json"
        filepath = os.path.join(self.proposals_dir, filename)

        with open(filepath, "w") as f:
            json.dump({
                "patch_type": patch.patch_type,
                "target_file": patch.target_file,
                "description": patch.diff,
                "confidence": patch.confidence,
                "rationale": patch.rationale,
                "status": "proposed",
                "created": ts,
            }, f, indent=2)

        return filepath

    def evolve(self) -> dict:
        """Run self-evolution cycle. Save proposals, auto-apply high-confidence ones."""
        patches = self.generate_patches()
        results = {"proposed": 0, "auto_applied": 0, "total": len(patches)}

        for patch in patches:
            # Always save as proposal first
            self.save_proposal(patch)
            results["proposed"] += 1

            # Record in memory
            from .schema import MemoryUnit
            unit = MemoryUnit(
                content=f"Self-evolution proposal: {patch.patch_type} → {patch.target_file}\n"
                        f"Rationale: {patch.rationale}\n"
                        f"Confidence: {patch.confidence}",
                type="insight",
                salience=0.9,
                tags=["self-evolution", patch.patch_type],
            )
            self.engram.store.store(unit)

        print(f"[ENGRAM] Self-evolution: {results['proposed']} proposals, "
              f"{results['auto_applied']} auto-applied")
        return results
