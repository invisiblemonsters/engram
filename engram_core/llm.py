"""
ENGRAM LLM Backend — Uses copilot-proxy (OpenAI-compatible) for structured JSON calls.
Designed for autonomous operation (cron, dream cycles) without human interaction.
"""

import json
import os
import time
import logging
import requests
from typing import Optional

logger = logging.getLogger("engram.llm")

# Backend priority: copilot-proxy > Anthropic (via auth-profiles) > NVIDIA > OpenAI
AUTH_PROFILES_PATH = os.path.expanduser("~/.openclaw/agents/main/agent/auth-profiles.json")

def _load_anthropic_key():
    """Load Anthropic API key from OpenClaw auth profiles."""
    try:
        with open(AUTH_PROFILES_PATH) as f:
            profiles = json.load(f)
        for name, prof in profiles.get("profiles", {}).items():
            if prof.get("provider") == "anthropic" and prof.get("token"):
                return prof["token"]
    except Exception:
        pass
    return os.environ.get("ANTHROPIC_API_KEY")

def _load_nvidia_key():
    """Load NVIDIA API key from OpenClaw config."""
    try:
        config_path = os.path.expanduser("~/.openclaw/openclaw.json")
        with open(config_path) as f:
            config = json.load(f)
        nvidia = config.get("models", {}).get("providers", {}).get("nvidia", {})
        key = nvidia.get("apiKey")
        if key and key != "__OPENCLAW_REDACTED__":
            return key
    except Exception:
        pass
    return os.environ.get("NVIDIA_API_KEY")

BACKENDS = [
    {"name": "minimax-proxy", "url": "http://localhost:11435/v1", "model": "minimax-m2.5:cloud", "key": "dummy"},
    {"name": "copilot-proxy", "url": "http://localhost:3000/v1", "model": "claude-haiku-4.5", "key": "dummy"},
    {"name": "nvidia-llama", "url": "https://integrate.api.nvidia.com/v1", "model": "meta/llama-3.3-70b-instruct", "key_fn": _load_nvidia_key},
    {"name": "nvidia-qwen", "url": "https://integrate.api.nvidia.com/v1", "model": "qwen/qwen3-coder-480b-a35b-instruct", "key_fn": _load_nvidia_key},
    {"name": "nvidia-kimi", "url": "https://integrate.api.nvidia.com/v1", "model": "moonshotai/kimi-k2.5", "key_fn": _load_nvidia_key},
    {"name": "nvidia-nemotron", "url": "https://integrate.api.nvidia.com/v1", "model": "nvidia/nemotron-3-nano-30b-a3b", "key_fn": _load_nvidia_key},
    {"name": "nvidia-glm", "url": "https://integrate.api.nvidia.com/v1", "model": "z-ai/glm5", "key_fn": _load_nvidia_key},
]


class EngramLLM:
    """Production LLM client with retries, structured JSON output, fallbacks."""

    def __init__(
        self,
        base_url: str = None,
        model: str = None,
        api_key: str = None,
        max_retries: int = 3,
        timeout: int = 120,
    ):
        self._is_anthropic = False
        # Auto-detect best available backend
        if base_url:
            self.url = f"{base_url.rstrip('/')}/chat/completions"
            self.model = model or "claude-haiku-4.5"
            # Auto-detect key for known providers
            if api_key:
                self.api_key = api_key
            elif "nvidia" in base_url:
                self.api_key = _load_nvidia_key()
            else:
                self.api_key = None
        else:
            self.url, self.model, self.api_key = self._detect_backend()

        self.max_retries = max_retries
        self.timeout = timeout
        self._last_call_ts = 0.0
        self._rate_limit_sec = 8  # Free tier NVIDIA cooldown
        self._fallback_backends = self._build_fallback_chain()

    def _build_fallback_chain(self):
        """Build list of (url, model, key) tuples for fallback on failure."""
        chain = []
        for b in BACKENDS:
            key = b.get("key") or (b["key_fn"]() if b.get("key_fn") else None)
            if not key:
                continue
            is_anthropic = b.get("is_anthropic", False)
            url = f"{b['url'].rstrip('/')}/{'messages' if is_anthropic else 'chat/completions'}"
            chain.append({"url": url, "model": b["model"], "key": key, "name": b["name"], "is_anthropic": is_anthropic})
        return chain

    def _detect_backend(self):
        """Try backends in priority order, return first available."""
        for b in BACKENDS:
            key = None
            if b.get("key"):
                key = b["key"]
            elif b.get("key_fn"):
                key = b["key_fn"]()
                if not key:
                    continue

            is_anthropic = b.get("is_anthropic", False)

            if is_anthropic:
                url = f"{b['url'].rstrip('/')}/messages"
            else:
                url = f"{b['url'].rstrip('/')}/chat/completions"

            # Quick connectivity check
            try:
                if is_anthropic:
                    # Anthropic doesn't have /models, just check the key exists
                    if key:
                        logger.info(f"Using backend: {b['name']} ({b['model']})")
                        self._is_anthropic = True
                        return url, b["model"], key
                else:
                    test_url = f"{b['url'].rstrip('/')}/models"
                    headers = {"Authorization": f"Bearer {key}"} if key and key != "dummy" else {}
                    resp = requests.get(test_url, timeout=3, headers=headers)
                    if resp.status_code < 500:
                        logger.info(f"Using backend: {b['name']} ({b['model']})")
                        self._is_anthropic = False
                        return url, b["model"], key
            except Exception:
                continue

        self._is_anthropic = False
        logger.warning("No LLM backend available")
        return None, None, None

    def _call_anthropic(self, messages, model, temperature, max_tokens):
        """Call Anthropic Messages API directly."""
        system_msg = ""
        user_msgs = []
        for m in messages:
            if m["role"] == "system":
                system_msg = m["content"]
            else:
                user_msgs.append(m)

        payload = {
            "model": model or self.model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": user_msgs,
        }
        if system_msg:
            payload["system"] = system_msg

        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        resp = requests.post(self.url, json=payload, timeout=self.timeout, headers=headers)
        resp.raise_for_status()
        data = resp.json()
        return data["content"][0]["text"].strip()

    def call(
        self,
        prompt: str,
        system: str = "You are ENGRAM, a memory consolidation system. Output ONLY valid JSON. No markdown, no explanations, no code fences.",
        temperature: float = 0.0,
        max_tokens: int = 4096,
        model: Optional[str] = None,
    ) -> Optional[dict]:
        """
        Send prompt, expect JSON response. Returns parsed dict or None on failure.
        """
        # Rate limit guard (NVIDIA free tier)
        elapsed = time.time() - self._last_call_ts
        if elapsed < self._rate_limit_sec:
            time.sleep(self._rate_limit_sec - elapsed)
        self._last_call_ts = time.time()

        for attempt in range(self.max_retries):
            try:
                messages = [
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt},
                ]

                if getattr(self, '_is_anthropic', False):
                    content = self._call_anthropic(messages, model, temperature, max_tokens)
                else:
                    payload = {
                        "model": model or self.model,
                        "messages": messages,
                        "temperature": temperature,
                        "max_tokens": max_tokens,
                    }
                    headers = {}
                    if self.api_key and self.api_key != "dummy":
                        headers["Authorization"] = f"Bearer {self.api_key}"
                    resp = requests.post(self.url, json=payload, timeout=self.timeout, headers=headers)
                    resp.raise_for_status()
                    data = resp.json()
                    content = data["choices"][0]["message"].get("content")
                    if content is None:
                        content = data["choices"][0]["message"].get("reasoning_content", "")
                    if not content:
                        logger.warning(f"JSON call returned empty content (attempt {attempt+1})")
                        if attempt < self.max_retries - 1:
                            time.sleep(2 ** attempt)
                        continue
                    content = content.strip()

                # Strip markdown code fences if present
                if content.startswith("```"):
                    lines = content.split("\n")
                    # Remove first and last lines (``` markers)
                    lines = [l for l in lines if not l.strip().startswith("```")]
                    content = "\n".join(lines).strip()

                parsed = json.loads(content)
                return parsed

            except requests.ConnectionError:
                logger.warning(f"LLM connection failed (attempt {attempt+1}). Is copilot-proxy running?")
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)
            except requests.Timeout:
                logger.warning(f"LLM timeout (attempt {attempt+1})")
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)
            except json.JSONDecodeError as e:
                logger.warning(f"LLM returned non-JSON (attempt {attempt+1}): {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(1)
            except Exception as e:
                logger.error(f"LLM unexpected error: {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)

        # Try fallback backends
        for fb in self._fallback_backends:
            if fb["url"] == self.url and fb["model"] == self.model:
                continue  # skip the one we already tried
            logger.info(f"Trying fallback: {fb['name']} ({fb['model']})")
            try:
                messages = [
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt},
                ]
                payload = {
                    "model": fb["model"],
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                }
                headers = {"Authorization": f"Bearer {fb['key']}"} if fb["key"] != "dummy" else {}
                resp = requests.post(fb["url"], json=payload, timeout=self.timeout, headers=headers)
                resp.raise_for_status()
                data = resp.json()
                content = data["choices"][0]["message"].get("content", "").strip()
                if content.startswith("```"):
                    lines = content.split("\n")
                    lines = [l for l in lines if not l.strip().startswith("```")]
                    content = "\n".join(lines).strip()
                parsed = json.loads(content)
                logger.info(f"Fallback {fb['name']} succeeded")
                return parsed
            except Exception as e:
                logger.warning(f"Fallback {fb['name']} failed: {e}")
                continue

        logger.error(f"All {self.max_retries} LLM attempts + all fallbacks failed")
        return None

    def call_text(
        self,
        prompt: str,
        system: str = "",
        temperature: float = 0.0,
        max_tokens: int = 4096,
        model: Optional[str] = None,
    ) -> Optional[str]:
        """Raw text call (for narrative generation)."""
        for attempt in range(self.max_retries):
            try:
                messages = [
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt},
                ]
                if getattr(self, '_is_anthropic', False):
                    return self._call_anthropic(messages, model, temperature, max_tokens)
                else:
                    payload = {
                        "model": model or self.model,
                        "messages": messages,
                        "temperature": temperature,
                        "max_tokens": max_tokens,
                    }
                    headers = {}
                    if self.api_key and self.api_key != "dummy":
                        headers["Authorization"] = f"Bearer {self.api_key}"
                    resp = requests.post(self.url, json=payload, timeout=self.timeout, headers=headers)
                    resp.raise_for_status()
                    data = resp.json()
                    content = data["choices"][0]["message"].get("content")
                    if content is None:
                        # Some models return content=null with reasoning_content or refusal
                        content = data["choices"][0]["message"].get("reasoning_content", "")
                    if not content:
                        logger.warning(f"Text call returned empty content (attempt {attempt+1}): {json.dumps(data['choices'][0]['message'])[:200]}")
                        if attempt < self.max_retries - 1:
                            time.sleep(2 ** attempt)
                        continue
                    return content.strip()
            except Exception as e:
                logger.warning(f"Text call failed (attempt {attempt+1}): {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)

        # Try fallback backends
        for fb in self._fallback_backends:
            if fb["url"] == self.url and fb["model"] == self.model:
                continue
            logger.info(f"Text fallback: {fb['name']} ({fb['model']})")
            try:
                messages = [
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt},
                ]
                payload = {
                    "model": fb["model"],
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                }
                headers = {"Authorization": f"Bearer {fb['key']}"} if fb["key"] != "dummy" else {}
                resp = requests.post(fb["url"], json=payload, timeout=self.timeout, headers=headers)
                resp.raise_for_status()
                data = resp.json()
                content = data["choices"][0]["message"].get("content")
                if content is None:
                    content = data["choices"][0]["message"].get("reasoning_content", "")
                if content:
                    logger.info(f"Text fallback {fb['name']} succeeded")
                    return content.strip()
            except Exception as e:
                logger.warning(f"Text fallback {fb['name']} failed: {e}")
                continue

        return None

    def is_available(self) -> bool:
        """Check if the LLM backend is reachable."""
        if not self.url:
            return False
        try:
            headers = {}
            if self.api_key and self.api_key != "dummy":
                headers["Authorization"] = f"Bearer {self.api_key}"
            resp = requests.get(
                self.url.replace("/chat/completions", "/models"),
                timeout=5, headers=headers
            )
            return resp.status_code < 500
        except Exception:
            return False
