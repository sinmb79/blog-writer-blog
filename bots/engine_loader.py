"""
Blog-only writing engine selection and loading.
"""
from __future__ import annotations

import json
import logging
import os
import subprocess
from abc import ABC, abstractmethod
from pathlib import Path

from bots.blog_config import CONFIG_DIR, LOG_DIR, load_settings


load_settings()

CONFIG_PATH = CONFIG_DIR / "engine.json"
logger = logging.getLogger(__name__)
if not logger.handlers:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    handler = logging.FileHandler(LOG_DIR / "engine_loader.log", encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    logger.addHandler(handler)
    logger.addHandler(logging.StreamHandler())
    logger.setLevel(logging.INFO)


class BaseWriter(ABC):
    @abstractmethod
    def write(self, prompt: str, system: str = "") -> str:
        raise NotImplementedError


class OpenClawWriter(BaseWriter):
    _CLI = "openclaw.cmd" if os.name == "nt" else "openclaw"

    def __init__(self, cfg: dict):
        self.agent_name = cfg.get("agent_name", "blog-writer")
        self.timeout = cfg.get("timeout", 300)

    def write(self, prompt: str, system: str = "") -> str:
        message = f"{system}\n\n{prompt}".strip() if system else prompt
        try:
            result = subprocess.run(
                [self._CLI, "agent", "--agent", self.agent_name, "--message", message, "--json"],
                capture_output=True,
                text=True,
                timeout=self.timeout,
            )
        except FileNotFoundError:
            logger.warning("openclaw CLI was not found")
            return ""
        except subprocess.TimeoutExpired:
            logger.error("openclaw timed out after %s seconds", self.timeout)
            return ""
        except Exception as exc:
            logger.error("openclaw failed: %s", exc)
            return ""

        if result.returncode != 0:
            logger.error("openclaw returned %s: %s", result.returncode, result.stderr.strip()[:300])
            return ""

        stdout = result.stdout.strip()
        if not stdout:
            return ""

        try:
            data = json.loads(stdout)
            payloads = data.get("result", {}).get("payloads", [])
            if payloads:
                return payloads[0].get("text", "")
        except json.JSONDecodeError:
            pass

        return stdout


class ClaudeWriter(BaseWriter):
    def __init__(self, cfg: dict):
        self.api_key = os.getenv(cfg.get("api_key_env", "ANTHROPIC_API_KEY"), "")
        self.model = cfg.get("model", "claude-3-5-sonnet-latest")
        self.max_tokens = cfg.get("max_tokens", 4096)

    def write(self, prompt: str, system: str = "") -> str:
        if not self.api_key:
            logger.warning("ANTHROPIC_API_KEY is not configured")
            return ""
        try:
            import anthropic

            client = anthropic.Anthropic(api_key=self.api_key)
            message = client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                system=system or None,
                messages=[{"role": "user", "content": prompt}],
            )
            return message.content[0].text if message.content else ""
        except Exception as exc:
            logger.error("Claude writer failed: %s", exc)
            return ""


class GeminiWriter(BaseWriter):
    def __init__(self, cfg: dict):
        self.api_key = os.getenv(cfg.get("api_key_env", "GEMINI_API_KEY"), "")
        self.model = cfg.get("model", "gemini-2.5-flash")
        self.max_tokens = cfg.get("max_tokens", 4096)
        self.temperature = cfg.get("temperature", 0.7)

    def write(self, prompt: str, system: str = "") -> str:
        if not self.api_key:
            logger.warning("GEMINI_API_KEY is not configured")
            return ""
        try:
            import google.generativeai as genai

            genai.configure(api_key=self.api_key)
            model = genai.GenerativeModel(
                model_name=self.model,
                generation_config={
                    "max_output_tokens": self.max_tokens,
                    "temperature": self.temperature,
                },
                system_instruction=system or None,
            )
            response = model.generate_content(prompt)
            return getattr(response, "text", "") or ""
        except Exception as exc:
            logger.error("Gemini writer failed: %s", exc)
            return ""


class EngineLoader:
    _DEFAULT_CONFIG = {
        "writing": {
            "provider": "openclaw",
            "options": {
                "openclaw": {"agent_name": "blog-writer", "timeout": 300},
                "claude": {"api_key_env": "ANTHROPIC_API_KEY", "model": "claude-3-5-sonnet-latest"},
                "gemini": {"api_key_env": "GEMINI_API_KEY", "model": "gemini-2.5-flash"},
            },
        }
    }

    def __init__(self, config_path: Path | None = None):
        self._config_path = config_path or CONFIG_PATH
        self._config = self._load_config()

    def _load_config(self) -> dict:
        if not self._config_path.exists():
            return dict(self._DEFAULT_CONFIG)
        try:
            data = json.loads(self._config_path.read_text(encoding="utf-8"))
            return data or dict(self._DEFAULT_CONFIG)
        except json.JSONDecodeError:
            logger.warning("engine.json is invalid; using defaults")
            return dict(self._DEFAULT_CONFIG)

    def get_config(self, *keys):
        value = self._config
        for key in keys:
            if not isinstance(value, dict):
                return None
            value = value.get(key)
        return value

    def get_writer(self) -> BaseWriter:
        writing_cfg = self._config.get("writing", {})
        provider = writing_cfg.get("provider", "openclaw")
        options = writing_cfg.get("options", {}).get(provider, {})
        writers = {
            "openclaw": OpenClawWriter,
            "claude": ClaudeWriter,
            "gemini": GeminiWriter,
        }
        writer_cls = writers.get(provider, OpenClawWriter)
        return writer_cls(options)
