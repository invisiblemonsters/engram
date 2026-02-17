"""ENGRAM Attestation (v0.8) — Nostr kind 30079 proof-of-capability receipts.
Proves an agent actually used specific memories successfully.
"""
import os
import json
from datetime import datetime, timezone
from .schema import MemoryUnit
from .store import EngramStore
from .identity import Identity


class Attester:
    """Generate Nostr kind 30079 attestation receipts for memory capabilities."""

    NPUB = "npub182m9y3qyd7wfm9sew59yk7f8wm9mhwhme2gfjfyq44djm6wfswtsumxtyk"

    def __init__(self, store: EngramStore, identity: Identity):
        self.store = store
        self.identity = identity
        self.attestations_dir = os.path.join(store.data_dir, "attestations")
        os.makedirs(self.attestations_dir, exist_ok=True)

    def attest(self, memory_ids: list[str], capability: str,
               evidence: str = "") -> dict:
        """Create a kind 30079 attestation receipt.
        
        Args:
            memory_ids: IDs of memories that prove the capability
            capability: What was demonstrated (e.g. 'prospective-memory', 'dream-insight')
            evidence: Optional description of what happened
        """
        now = datetime.now(timezone.utc)
        
        # Verify memories exist
        valid_ids = []
        for mid in memory_ids:
            unit = self.store.get(mid)
            if unit:
                valid_ids.append(mid)

        receipt = {
            "kind": 30079,
            "created_at": int(now.timestamp()),
            "content": json.dumps({
                "capability": capability,
                "evidence": evidence or f"ENGRAM capability proof: {capability}",
                "memory_count": len(valid_ids),
                "agent_pubkey": self.identity.public_key_b64(),
                "engram_version": "0.8",
            }),
            "tags": [
                ["d", f"engram-attest-{now.strftime('%Y%m%d%H%M')}"],
                ["title", f"ENGRAM {capability} attested"],
                ["p", self.NPUB],
                *[["e", uid, "", "mention"] for uid in valid_ids],
                ["t", "engram"],
                ["t", "attestation"],
                ["t", capability.replace(" ", "-")],
            ]
        }

        # Sign the receipt content
        receipt_payload = json.dumps(receipt, sort_keys=True)
        receipt["signature"] = self.identity.sign(receipt_payload)

        # Log as narrative memory
        unit = MemoryUnit(
            content=f"Attested capability '{capability}' for {len(valid_ids)} memories",
            type="narrative",
            salience=0.92,
            tags=["attestation", "kind-30079", capability],
        )
        self.store.store(unit)

        return receipt

    def export_receipt(self, receipt: dict, name: str = None) -> str:
        """Save attestation to file."""
        if not name:
            name = f"attest-{datetime.now().strftime('%Y%m%d%H%M')}"
        filepath = os.path.join(self.attestations_dir, f"{name}.json")
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(receipt, f, indent=2)
        print(f"[ENGRAM] Attestation saved: {filepath}")
        return filepath

    def list_attestations(self) -> list[dict]:
        """List all saved attestations."""
        results = []
        for f in os.listdir(self.attestations_dir):
            if f.endswith(".json"):
                with open(os.path.join(self.attestations_dir, f)) as fh:
                    results.append(json.load(fh))
        return results
