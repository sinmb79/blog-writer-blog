"""
Blog-only writing engine selection and loading.
"""
from __future__ import annotations

import json
import logging
import os
import subprocess
import time
from abc import ABC, abstractmethod
from pathlib import Path

from bots.blog_config import CONFIG_DIR, LOG_DIR, load_settings


# ─── Writer 예외 계층 ───────────────────────────────────

class WriterError(Exception):
    """글쓰기 엔진 공통 예외."""


class WriterCLINotFoundError(WriterError):
    """CLI 실행 파일을 찾을 수 없을 때."""


class WriterTimeoutError(WriterError):
    """글쓰기 엔진이 제한시간을 초과했을 때."""


class WriterEmptyResponseError(WriterError):
    """글쓰기 엔진이 빈 응답을 반환했을 때."""


class WriterAPIError(WriterError):
    """API 호출이 실패했을 때."""


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

    def write_with_retry(
        self,
        prompt: str,
        system: str = "",
        max_retries: int = 1,
        backoff: float = 5.0,
    ) -> str:
        """
        write()를 호출하되, 재시도 가능한 에러 시 backoff 후 재시도.
        WriterCLINotFoundError는 재시도 불가 → 즉시 raise.
        """
        last_err: WriterError | None = None
        for attempt in range(1 + max_retries):
            try:
                return self.write(prompt, system)
            except WriterCLINotFoundError:
                raise
            except (WriterTimeoutError, WriterEmptyResponseError) as exc:
                last_err = exc
                if attempt < max_retries:
                    logger.warning(
                        "재시도 %d/%d (%s), %s초 후 재시도",
                        attempt + 1, max_retries, type(exc).__name__, backoff,
                    )
                    time.sleep(backoff)
            except WriterError:
                raise
        raise last_err  # type: ignore[misc]


class OpenClawWriter(BaseWriter):
    _CLI = "openclaw.cmd" if os.name == "nt" else "openclaw"

    def __init__(self, cfg: dict):
        self.agent_name = cfg.get("agent_name", "blog-writer")
        self.timeout = cfg.get("timeout", 300)

    def write(self, prompt: str, system: str = "") -> str:
        # system을 [SYSTEM INSTRUCTION] 블록으로 명시적 분리
        if system:
            message = (
                "[SYSTEM INSTRUCTION — 반드시 따라라]\n"
                f"{system}\n"
                "[END SYSTEM INSTRUCTION]\n\n"
                "[USER REQUEST — 아래 요청에 대해 위 지시대로 즉시 출력하라]\n"
                f"{prompt}"
            )
        else:
            message = prompt
        try:
            cmd = [
                self._CLI, "agent",
                "--agent", self.agent_name,
                "--message", message,
                "--json",
            ]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=self.timeout,
            )
        except FileNotFoundError:
            raise WriterCLINotFoundError("openclaw CLI를 찾을 수 없음")
        except subprocess.TimeoutExpired:
            raise WriterTimeoutError(f"openclaw가 {self.timeout}초 제한시간 초과")

        if result.returncode != 0:
            raise WriterAPIError(
                f"openclaw 종료코드 {result.returncode}: {result.stderr.strip()[:300]}"
            )

        stdout = result.stdout.strip()
        if not stdout:
            raise WriterEmptyResponseError("openclaw 응답이 비어 있음")

        return self._parse_response(stdout)

    @staticmethod
    def _parse_response(stdout: str) -> str:
        """OpenClaw stdout에서 본문 텍스트를 추출한다. 여러 JSON 구조에 대응."""
        try:
            data = json.loads(stdout)
        except json.JSONDecodeError:
            logger.info("OpenClaw 응답이 JSON이 아님, 원문 그대로 사용 (len=%d)", len(stdout))
            return stdout

        # 경로 1: result.payloads[0].text (기본 형식)
        payloads = data.get("result", {}).get("payloads", [])
        if payloads:
            text = payloads[0].get("text", "")
            if text:
                return text

        # 경로 2: result.text (단일 텍스트 응답)
        result_text = data.get("result", {}).get("text", "")
        if result_text:
            logger.info("OpenClaw fallback: result.text 사용")
            return result_text

        # 경로 3: output 키 (간이 형식)
        output_text = data.get("output", "")
        if output_text:
            logger.info("OpenClaw fallback: output 키 사용")
            return output_text

        logger.warning("OpenClaw JSON에서 텍스트를 찾지 못함: keys=%s", list(data.keys()))
        return stdout


class ClaudeWriter(BaseWriter):
    def __init__(self, cfg: dict):
        self.api_key = os.getenv(cfg.get("api_key_env", "ANTHROPIC_API_KEY"), "")
        self.model = cfg.get("model", "claude-3-5-sonnet-latest")
        self.max_tokens = cfg.get("max_tokens", 4096)

    def write(self, prompt: str, system: str = "") -> str:
        if not self.api_key:
            raise WriterAPIError("ANTHROPIC_API_KEY가 설정되지 않음")
        try:
            import anthropic

            client = anthropic.Anthropic(api_key=self.api_key)
            message = client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                system=system or None,
                messages=[{"role": "user", "content": prompt}],
            )
            text = message.content[0].text if message.content else ""
            if not text:
                raise WriterEmptyResponseError("Claude 응답이 비어 있음")
            return text
        except WriterError:
            raise
        except Exception as exc:
            raise WriterAPIError(f"Claude API 실패: {exc}") from exc


class GeminiWriter(BaseWriter):
    def __init__(self, cfg: dict):
        self.api_key = os.getenv(cfg.get("api_key_env", "GEMINI_API_KEY"), "")
        self.model = cfg.get("model", "gemini-2.5-flash")
        self.max_tokens = cfg.get("max_tokens", 4096)
        self.temperature = cfg.get("temperature", 0.7)

    def write(self, prompt: str, system: str = "") -> str:
        if not self.api_key:
            raise WriterAPIError("GEMINI_API_KEY가 설정되지 않음")
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
            text = getattr(response, "text", "") or ""
            if not text:
                raise WriterEmptyResponseError("Gemini 응답이 비어 있음")
            return text
        except WriterError:
            raise
        except Exception as exc:
            raise WriterAPIError(f"Gemini API 실패: {exc}") from exc


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
