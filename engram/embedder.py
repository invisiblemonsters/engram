"""ENGRAM universal embedder — supports sentence-transformers, OpenAI, Ollama, HuggingFace, hash fallback."""
import hashlib
import struct
import logging
from typing import Optional

logger = logging.getLogger("engram.embedder")


class Embedder:
    """Universal embedding backend. Auto-detects best available provider."""

    def __init__(self, provider: str = "sentence-transformers",
                 model: str = "BAAI/bge-small-en-v1.5",
                 api_key: Optional[str] = None,
                 base_url: Optional[str] = None,
                 dim: int = 384):
        self.dim = dim
        self._model = None
        self._backend = "hash"
        self._api_key = api_key
        self._base_url = base_url
        self._model_name = model

        if provider == "sentence-transformers":
            self._init_sentence_transformers(model)
        elif provider == "openai":
            self._init_openai(model, api_key, base_url)
        elif provider == "ollama":
            self._init_ollama(model, base_url)
        elif provider == "huggingface":
            self._init_sentence_transformers(model)  # same underlying lib
        else:
            logger.info("Embedding: deterministic hash fallback")

    def _init_sentence_transformers(self, model: str):
        try:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(model)
            self.dim = self._model.get_sentence_embedding_dimension()
            self._backend = "sentence_transformers"
            logger.info(f"Embedding: sentence-transformers ({model}, dim={self.dim})")
        except ImportError:
            logger.warning("sentence-transformers not installed, using hash fallback")

    def _init_openai(self, model: str, api_key: Optional[str], base_url: Optional[str]):
        try:
            import openai
            kwargs = {}
            if api_key:
                kwargs["api_key"] = api_key
            if base_url:
                kwargs["base_url"] = base_url
            self._model = openai.OpenAI(**kwargs)
            self._backend = "openai"
            self._model_name = model or "text-embedding-3-small"
            # OpenAI defaults
            if "3-small" in self._model_name:
                self.dim = 1536
            elif "3-large" in self._model_name:
                self.dim = 3072
            else:
                self.dim = 1536
            logger.info(f"Embedding: OpenAI ({self._model_name})")
        except ImportError:
            logger.warning("openai package not installed, using hash fallback")

    def _init_ollama(self, model: str, base_url: Optional[str]):
        import requests
        self._base_url = (base_url or "http://localhost:11434").rstrip("/")
        self._model_name = model or "nomic-embed-text"
        # Quick check
        try:
            resp = requests.get(f"{self._base_url}/api/tags", timeout=3)
            if resp.status_code < 500:
                self._backend = "ollama"
                self.dim = 768  # typical, will auto-detect on first embed
                logger.info(f"Embedding: Ollama ({self._model_name})")
                return
        except Exception:
            pass
        logger.warning("Ollama not available, using hash fallback")

    def embed(self, text: str) -> list[float]:
        if self._backend == "sentence_transformers":
            return self._model.encode(text).tolist()
        elif self._backend == "openai":
            resp = self._model.embeddings.create(input=text, model=self._model_name)
            vec = resp.data[0].embedding
            self.dim = len(vec)
            return vec
        elif self._backend == "ollama":
            import requests
            resp = requests.post(f"{self._base_url}/api/embed",
                                 json={"model": self._model_name, "input": text}, timeout=30)
            resp.raise_for_status()
            vec = resp.json()["embeddings"][0]
            self.dim = len(vec)
            return vec
        else:
            return self._hash_embed(text)

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        if self._backend == "sentence_transformers":
            return self._model.encode(texts).tolist()
        elif self._backend == "openai":
            resp = self._model.embeddings.create(input=texts, model=self._model_name)
            return [d.embedding for d in resp.data]
        return [self.embed(t) for t in texts]

    def _hash_embed(self, text: str) -> list[float]:
        import math
        result = []
        for i in range(0, self.dim, 8):
            h = hashlib.sha256(f"{text}|{i}".encode()).digest()
            vals = struct.unpack("8f" if len(h) >= 32 else f"{len(h)//4}f", h[:32])
            # Replace NaN/Inf with 0
            result.extend(0.0 if (math.isnan(v) or math.isinf(v)) else v
                          for v in vals[:min(8, self.dim - len(result))])
        norm = sum(v * v for v in result) ** 0.5
        if norm > 0:
            result = [v / norm for v in result]
        return result[:self.dim]

    @property
    def backend(self) -> str:
        return self._backend
