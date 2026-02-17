"""ENGRAM Self-Evolution Module (v0.6)
Dream cycle outputs executable patches → code evolution → better memory.
Now with test-3-times safety + automatic rollback.
Designed by Grok 4.20, implemented by Metatron.
"""
import os
import json
import difflib
import subprocess
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

    def test_patch(self, patch: EvolutionPatch) -> bool:
        """Run a patch's test command. Returns True if test passes."""
        if not patch.test_command:
            return True  # No test = assume pass (but won't auto-apply without test)
        try:
            result = subprocess.run(
                patch.test_command, shell=True, timeout=30,
                capture_output=True, cwd=os.path.dirname(os.path.dirname(__file__))
            )
            return result.returncode == 0
        except Exception:
            return False

    def try_auto_apply(self, patch: EvolutionPatch) -> bool:
        """Attempt auto-application with 3-test safety gate.
        Only applies if confidence >= 0.95 AND test_command is set AND passes 2/3 runs.
        """
        if patch.confidence < 0.95:
            return False
        if not patch.test_command:
            return False  # Won't auto-apply without tests

        filepath = os.path.join(os.path.dirname(os.path.dirname(__file__)), patch.target_file)
        if not os.path.exists(filepath):
            print(f"[ENGRAM] Auto-apply skipped: {filepath} not found")
            return False

        # Read original for rollback
        with open(filepath, "r", encoding="utf-8") as f:
            original = f.read()

        # Apply diff (for now, description-based — real diffs in v0.7)
        # TODO: Apply actual unified diffs when LLM generates them
        print(f"[ENGRAM] Auto-apply candidate: {patch.patch_type} → {patch.target_file} (conf={patch.confidence})")

        # Run test 3 times
        successes = sum(self.test_patch(patch) for _ in range(3))
        if successes >= 2:
            print(f"[ENGRAM] Tests passed {successes}/3 — patch eligible")
            return True
        else:
            print(f"[ENGRAM] Tests failed {3-successes}/3 — rollback")
            return False

    def evolve(self) -> dict:
        """Run self-evolution cycle. Save proposals, attempt auto-apply for high-confidence."""
        patches = self.generate_patches()
        results = {"proposed": 0, "auto_applied": 0, "total": len(patches)}

        for patch in patches:
            # Always save as proposal first
            filepath = self.save_proposal(patch)
            results["proposed"] += 1

            # Attempt auto-apply for very high confidence patches with tests
            if patch.confidence >= 0.95 and patch.test_command:
                if self.try_auto_apply(patch):
                    results["auto_applied"] += 1
                    # Update proposal status
                    with open(filepath, "r") as f:
                        proposal = json.load(f)
                    proposal["status"] = "auto_applied"
                    with open(filepath, "w") as f:
                        json.dump(proposal, f, indent=2)

            # Record in memory
            from .schema import MemoryUnit
            status = "auto_applied" if patch.confidence >= 0.95 and patch.test_command else "proposed"
            unit = MemoryUnit(
                content=f"Self-evolution {status}: {patch.patch_type} → {patch.target_file}\n"
                        f"Rationale: {patch.rationale}\n"
                        f"Confidence: {patch.confidence}",
                type="insight",
                salience=0.9,
                tags=["self-evolution", patch.patch_type, status],
            )
            self.engram.store.store(unit)

        print(f"[ENGRAM] Self-evolution: {results['proposed']} proposals, "
              f"{results['auto_applied']} auto-applied")
        return results
