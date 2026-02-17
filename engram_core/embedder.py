"""ENGRAM local CPU embedding via llama-cpp-python or fallback TF-IDF."""
import hashlib
import json
import os
from pathlib import Path
from typing import Optional


class Embedder:
    """Local CPU embedding. Tries llama.cpp GGUF first, falls back to TF-IDF hash."""

    def __init__(self, model_path: Optional[str] = None, dim: int = 768):
        self.dim = dim
        self.model = None
        self._backend = "hash"  # fallback

        if model_path and os.path.exists(model_path):
            try:
                from llama_cpp import Llama
                self.model = Llama(
                    model_path=model_path,
                    n_gpu_layers=0,
                    embedding=True,
                    verbose=False
                )
                self._backend = "llama"
                print(f"[ENGRAM] Embedding: llama.cpp ({model_path})")
            except Exception as e:
                print(f"[ENGRAM] llama.cpp failed: {e}, using hash fallback")
        else:
            # Try sentence-transformers as middle ground
            try:
                from sentence_transformers import SentenceTransformer
                self.model = SentenceTransformer("all-MiniLM-L6-v2")
                self.dim = 384
                self._backend = "sentence_transformers"
                print("[ENGRAM] Embedding: sentence-transformers (all-MiniLM-L6-v2)")
            except ImportError:
                print("[ENGRAM] Embedding: deterministic hash fallback (install sentence-transformers for better quality)")

    def embed(self, text: str) -> list[float]:
        """Embed a single text string. Returns float vector."""
        if self._backend == "llama":
            return self.model.embed(text)
        elif self._backend == "sentence_transformers":
            return self.model.encode(text).tolist()
        else:
            return self._hash_embed(text)

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed multiple texts."""
        if self._backend == "sentence_transformers":
            return self.model.encode(texts).tolist()
        return [self.embed(t) for t in texts]

    def _hash_embed(self, text: str) -> list[float]:
        """Deterministic hash-based embedding. Not semantic but consistent.
        Uses rolling SHA-256 to fill the vector. Good enough for exact-match
        and basic clustering, not for semantic similarity."""
        import struct
        result = []
        for i in range(0, self.dim, 8):
            h = hashlib.sha256(f"{text}|{i}".encode()).digest()
            vals = struct.unpack("8f" if len(h) >= 32 else f"{len(h)//4}f", h[:32])
            result.extend(vals[:min(8, self.dim - len(result))])
        # Normalize
        norm = sum(v*v for v in result) ** 0.5
        if norm > 0:
            result = [v / norm for v in result]
        return result[:self.dim]

    @property
    def backend(self) -> str:
        return self._backend
