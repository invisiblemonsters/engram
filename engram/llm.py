"""ENGRAM universal LLM client — OpenAI-compatible, Anthropic, Ollama, or none."""
import json
import time
import logging
from typing import Optional

import requests

logger = logging.getLogger("engram.llm")


class EngramLLM:
    """Universal LLM client. Supports OpenAI-compatible APIs, Anthropic, and Ollama."""

    def __init__(self, provider: str = "none",
                 model: str = "",
                 api_key: str = "",
                 base_url: str = "",
                 max_retries: int = 3,
                 timeout: int = 120):
        self.provider = provider
        self.model = model
        self.api_key = api_key
        self.base_url = base_url.rstrip("/") if base_url else ""
        self.max_retries = max_retries
        self.timeout = timeout
        self._last_call_ts = 0.0

        # Auto-configure base URLs for known providers
        if provider == "openai" and not base_url:
            self.base_url = "https://api.openai.com/v1"
            self.model = model or "gpt-4o-mini"
        elif provider == "anthropic" and not base_url:
            self.base_url = "https://api.anthropic.com/v1"
            self.model = model or "claude-haiku-4-20250414"
        elif provider == "ollama" and not base_url:
            self.base_url = "http://localhost:11434/v1"
            self.model = model or "llama3.2"

    def is_available(self) -> bool:
        if self.provider == "none" or not self.base_url:
            return False
        try:
            if self.provider == "anthropic":
                return bool(self.api_key)
            url = f"{self.base_url}/models"
            headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
            resp = requests.get(url, timeout=5, headers=headers)
            return resp.status_code < 500
        except Exception:
            return False

    def call(self, prompt: str,
             system: str = "You are a memory consolidation system. Output ONLY valid JSON.",
             temperature: float = 0.0,
             max_tokens: int = 4096,
             model: Optional[str] = None) -> Optional[dict]:
        """Send prompt, expect JSON response."""
        text = self.call_text(prompt, system=system, temperature=temperature,
                              max_tokens=max_tokens, model=model)
        if not text:
            return None
        # Strip code fences
        if text.startswith("```"):
            lines = text.split("\n")
            lines = [l for l in lines if not l.strip().startswith("```")]
            text = "\n".join(lines).strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # Try to find JSON in response
            start = text.find("{")
            if start == -1:
                start = text.find("[")
            end = max(text.rfind("}"), text.rfind("]"))
            if start >= 0 and end > start:
                try:
                    return json.loads(text[start:end + 1])
                except json.JSONDecodeError:
                    pass
            logger.warning(f"Failed to parse JSON from LLM response: {text[:200]}")
            return None

    def call_text(self, prompt: str, system: str = "",
                  temperature: float = 0.0,
                  max_tokens: int = 4096,
                  model: Optional[str] = None) -> Optional[str]:
        """Raw text call."""
        if self.provider == "none":
            return None

        for attempt in range(self.max_retries):
            try:
                if self.provider == "anthropic":
                    return self._call_anthropic(prompt, system, temperature, max_tokens, model)
                else:
                    return self._call_openai_compat(prompt, system, temperature, max_tokens, model)
            except Exception as e:
                logger.warning(f"LLM call failed (attempt {attempt + 1}): {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)
        return None

    def _call_openai_compat(self, prompt, system, temperature, max_tokens, model):
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": model or self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        url = f"{self.base_url}/chat/completions"
        resp = requests.post(url, json=payload, timeout=self.timeout, headers=headers)
        resp.raise_for_status()
        data = resp.json()
        content = data["choices"][0]["message"].get("content")
        if content is None:
            content = data["choices"][0]["message"].get("reasoning_content", "")
        return content.strip() if content else None

    def _call_anthropic(self, prompt, system, temperature, max_tokens, model):
        messages = [{"role": "user", "content": prompt}]
        payload = {
            "model": model or self.model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": messages,
        }
        if system:
            payload["system"] = system

        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        url = f"{self.base_url}/messages"
        resp = requests.post(url, json=payload, timeout=self.timeout, headers=headers)
        resp.raise_for_status()
        data = resp.json()
        return data["content"][0]["text"].strip()
