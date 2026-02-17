"""ENGRAM identity — Ed25519 signing, chain verification, wakeup attestation."""
import base64
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


class Identity:
    """Agent identity via Ed25519 keypair.
    
    - Signs every MemoryUnit for tamper evidence
    - Generates wakeup attestations for session continuity
    - Verifies chain integrity on boot
    """

    def __init__(self, identity_dir: str = "identity"):
        self.identity_dir = Path(identity_dir)
        self.identity_dir.mkdir(parents=True, exist_ok=True)
        self.keypair_path = self.identity_dir / "keypair.json"
        self.attestation_path = self.identity_dir / "attestations.jsonl"
        self._signing_key = None
        self._verify_key = None
        self._init_keys()

    def _init_keys(self):
        """Load or generate Ed25519 keypair."""
        try:
            from nacl.signing import SigningKey, VerifyKey
            
            if self.keypair_path.exists():
                with open(self.keypair_path, "r") as f:
                    data = json.load(f)
                seed = base64.b64decode(data["seed"])
                self._signing_key = SigningKey(seed)
                self._verify_key = self._signing_key.verify_key
                print(f"[ENGRAM] Identity loaded: {self.public_key_b64()}")
            else:
                self._signing_key = SigningKey.generate()
                self._verify_key = self._signing_key.verify_key
                with open(self.keypair_path, "w") as f:
                    json.dump({
                        "seed": base64.b64encode(bytes(self._signing_key)).decode(),
                        "public_key": self.public_key_b64(),
                        "created": datetime.now(timezone.utc).isoformat(),
                    }, f, indent=2)
                print(f"[ENGRAM] New identity created: {self.public_key_b64()}")
        except ImportError:
            print("[ENGRAM] PyNaCl not installed — identity signing disabled")
            print("[ENGRAM] Install: pip install pynacl")

    def public_key_b64(self) -> str:
        if self._verify_key:
            return base64.b64encode(bytes(self._verify_key)).decode()
        return ""

    def sign(self, data: str) -> str:
        """Sign data, return base64 signature."""
        if not self._signing_key:
            return ""
        signed = self._signing_key.sign(data.encode())
        return base64.b64encode(signed.signature).decode()

    def verify(self, data: str, signature_b64: str, public_key_b64: Optional[str] = None) -> bool:
        """Verify a signature. Uses own key if no public_key provided."""
        try:
            from nacl.signing import VerifyKey
            from nacl.exceptions import BadSignatureError
            
            if public_key_b64:
                vk = VerifyKey(base64.b64decode(public_key_b64))
            elif self._verify_key:
                vk = self._verify_key
            else:
                return False

            sig = base64.b64decode(signature_b64)
            vk.verify(data.encode(), sig)
            return True
        except (BadSignatureError, Exception):
            return False

    def sign_memory(self, unit) -> str:
        """Sign a MemoryUnit's content hash."""
        content_hash = unit.content_hash()
        return self.sign(content_hash)

    def verify_memory(self, unit, public_key_b64: Optional[str] = None) -> bool:
        """Verify a MemoryUnit's signature."""
        if not unit.signature:
            return False
        content_hash = unit.content_hash()
        return self.verify(content_hash, unit.signature, public_key_b64)

    def wakeup_attestation(self, root_hash: str, last_consolidation: Optional[str] = None) -> dict:
        """Generate signed wakeup attestation for session continuity."""
        now = datetime.now(timezone.utc).isoformat()
        attestation = {
            "type": "wakeup",
            "agent_id": self.public_key_b64(),
            "timestamp": now,
            "root_hash": root_hash,
            "last_consolidation": last_consolidation,
        }
        payload = json.dumps(attestation, sort_keys=True)
        attestation["signature"] = self.sign(payload)

        # Append to attestation log
        with open(self.attestation_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(attestation) + "\n")

        return attestation

    def verify_chain(self, memories: list) -> tuple[bool, Optional[str]]:
        """Verify the hash chain of a list of memories.
        
        Returns (valid, broken_at_id).
        """
        prev_hash = ""
        for m in sorted(memories, key=lambda x: x.timestamp):
            if m.prev_hash != prev_hash and prev_hash != "":
                return False, m.id
            if m.signature and not self.verify_memory(m):
                return False, m.id
            prev_hash = m.content_hash()
        return True, None

    def compute_root_hash(self, memories: list) -> str:
        """Compute Merkle root hash of all memories."""
        if not memories:
            return hashlib.sha256(b"empty").hexdigest()
        
        hashes = [m.content_hash() for m in sorted(memories, key=lambda x: x.timestamp)]
        
        # Build Merkle tree
        while len(hashes) > 1:
            if len(hashes) % 2 == 1:
                hashes.append(hashes[-1])
            next_level = []
            for i in range(0, len(hashes), 2):
                combined = hashlib.sha256((hashes[i] + hashes[i+1]).encode()).hexdigest()
                next_level.append(combined)
            hashes = next_level

        return hashes[0]
