"""ENGRAM Configuration — yaml file + environment variables, env vars take precedence."""
import os
from pathlib import Path
from typing import Optional

try:
    import yaml
except ImportError:
    yaml = None


_DEFAULTS = {
    "data_dir": "./engram_data",
    "embedding_provider": "sentence-transformers",
    "embedding_model": "BAAI/bge-small-en-v1.5",
    "llm_provider": "none",
    "llm_model": "",
    "llm_api_key": "",
    "llm_base_url": "",
    "agent_name": "Agent",
    "max_tokens": 2_000_000,
    "hot_cache_path": "",
}

_ENV_MAP = {
    "ENGRAM_DATA_DIR": "data_dir",
    "ENGRAM_EMBEDDING_PROVIDER": "embedding_provider",
    "ENGRAM_EMBEDDING_MODEL": "embedding_model",
    "ENGRAM_LLM_PROVIDER": "llm_provider",
    "ENGRAM_LLM_MODEL": "llm_model",
    "ENGRAM_LLM_API_KEY": "llm_api_key",
    "ENGRAM_LLM_BASE_URL": "llm_base_url",
    "ENGRAM_AGENT_NAME": "agent_name",
    "ENGRAM_MAX_TOKENS": "max_tokens",
    "ENGRAM_HOT_CACHE_PATH": "hot_cache_path",
}


class EngramConfig:
    """Loads config from engram.yaml (if present) then env vars (override)."""

    def __init__(self, config_path: Optional[str] = None, **overrides):
        self._cfg = dict(_DEFAULTS)

        # 1. Load yaml if available
        if config_path is None:
            # Search: ./engram.yaml, then data_dir/engram.yaml
            for candidate in ["engram.yaml", "engram.yml"]:
                if Path(candidate).exists():
                    config_path = candidate
                    break

        if config_path and Path(config_path).exists() and yaml:
            with open(config_path, "r", encoding="utf-8") as f:
                file_cfg = yaml.safe_load(f) or {}
            for k, v in file_cfg.items():
                if k in self._cfg:
                    self._cfg[k] = v

        # 2. Env vars override
        for env_key, cfg_key in _ENV_MAP.items():
            val = os.environ.get(env_key)
            if val is not None:
                if cfg_key == "max_tokens":
                    self._cfg[cfg_key] = int(val)
                else:
                    self._cfg[cfg_key] = val

        # 3. Explicit overrides (from constructor kwargs)
        for k, v in overrides.items():
            if v is not None and k in self._cfg:
                self._cfg[k] = v

    @property
    def data_dir(self) -> Path:
        return Path(self._cfg["data_dir"])

    @property
    def embedding_provider(self) -> str:
        return self._cfg["embedding_provider"]

    @property
    def embedding_model(self) -> str:
        return self._cfg["embedding_model"]

    @property
    def llm_provider(self) -> str:
        return self._cfg["llm_provider"]

    @property
    def llm_model(self) -> str:
        return self._cfg["llm_model"]

    @property
    def llm_api_key(self) -> str:
        return self._cfg["llm_api_key"]

    @property
    def llm_base_url(self) -> str:
        return self._cfg["llm_base_url"]

    @property
    def agent_name(self) -> str:
        return self._cfg["agent_name"]

    @property
    def max_tokens(self) -> int:
        return int(self._cfg["max_tokens"])

    @property
    def hot_cache_path(self) -> str:
        return self._cfg["hot_cache_path"]

    def to_dict(self) -> dict:
        return dict(self._cfg)
