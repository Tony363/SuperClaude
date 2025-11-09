"""CodeRabbit MCP integration client for SuperClaude."""

from __future__ import annotations

import json
import logging
import os
import random
import time
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional

try:  # Optional dependency for config loading
    import yaml
except ModuleNotFoundError:  # pragma: no cover - depends on optional extras
    yaml = None  # type: ignore

try:  # Optional dependency for live HTTP calls
    import httpx  # type: ignore
except ImportError:  # pragma: no cover - httpx is optional
    httpx = None  # type: ignore

from ..Monitoring.paths import get_metrics_dir

logger = logging.getLogger(__name__)


DEFAULT_CONFIG_PATH = Path(__file__).resolve().parents[2] / "Config" / "coderabbit.yaml"

Transport = Callable[[Dict[str, Any]], Dict[str, Any]]
TimeFn = Callable[[], float]
SleepFn = Callable[[float], None]
RandomFn = Callable[[], float]


class CodeRabbitError(RuntimeError):
    """Base error raised for CodeRabbit integration issues."""

    retryable: bool = False

    def __init__(self, message: str, *, status: Optional[int] = None, payload: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.status = status
        self.payload = payload or {}


class NetworkError(CodeRabbitError):
    """Raised when the CodeRabbit API cannot be reached."""

    retryable = True


class AuthError(CodeRabbitError):
    """Raised when CodeRabbit authentication fails."""

    retryable = False


class RateLimitError(CodeRabbitError):
    """Raised when CodeRabbit signals that the caller is rate limited."""

    retryable = True


@dataclass
class CodeRabbitIssue:
    """Structured representation of a CodeRabbit issue/comment."""

    title: str
    body: str
    severity: str
    file_path: Optional[str] = None
    line: Optional[int] = None
    tag: Optional[str] = None

    @classmethod
    def from_payload(cls, payload: Dict[str, Any]) -> "CodeRabbitIssue":
        return cls(
            title=str(payload.get("title") or payload.get("summary") or "Issue"),
            body=str(payload.get("body") or payload.get("details") or ""),
            severity=str(payload.get("severity") or payload.get("level") or "info"),
            file_path=payload.get("file_path") or payload.get("file"),
            line=payload.get("line") or payload.get("line_number"),
            tag=payload.get("tag") or payload.get("category"),
        )


@dataclass
class CodeRabbitReview:
    """Container for CodeRabbit review results."""

    repo: str
    pr_number: int
    score: float
    status: str
    summary: str
    issues: List[CodeRabbitIssue]
    raw: Dict[str, Any]
    received_at: datetime
    degraded: bool = False
    degraded_reason: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "repo": self.repo,
            "pr_number": self.pr_number,
            "score": self.score,
            "status": self.status,
            "summary": self.summary,
            "issues": [issue.__dict__ for issue in self.issues],
            "raw": self.raw,
            "received_at": self.received_at.isoformat(),
            "degraded": self.degraded,
            "degraded_reason": self.degraded_reason,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CodeRabbitReview":
        issues = [CodeRabbitIssue.from_payload(issue) for issue in data.get("issues", [])]
        received_at = data.get("received_at")
        if isinstance(received_at, str):
            try:
                received_dt = datetime.fromisoformat(received_at)
            except ValueError:
                received_dt = datetime.now(timezone.utc)
        else:
            received_dt = datetime.now(timezone.utc)

        return cls(
            repo=data.get("repo", ""),
            pr_number=int(data.get("pr_number", 0)),
            score=float(data.get("score", 0.0)),
            status=str(data.get("status") or "unknown"),
            summary=str(data.get("summary") or ""),
            issues=issues,
            raw=data.get("raw", {}),
            received_at=received_dt,
            degraded=bool(data.get("degraded", False)),
            degraded_reason=data.get("degraded_reason"),
        )

    def degraded_copy(self, reason: str) -> "CodeRabbitReview":
        return replace(self, degraded=True, degraded_reason=reason)


def scrub_secrets(data: Any, *, redact_keys: Optional[Iterable[str]] = None) -> Any:
    """Return a copy of *data* with secret-looking values redacted."""

    key_fragments = {"token", "secret", "password", "api_key", "key", "auth", "authorization"}
    if redact_keys:
        key_fragments.update({str(item).lower() for item in redact_keys})

    def _scrub(value: Any, *, key: Optional[str] = None) -> Any:
        if isinstance(value, dict):
            return {k: _scrub(v, key=k) for k, v in value.items()}
        if isinstance(value, list):
            return [_scrub(item) for item in value]

        if key:
            lowered = key.lower()
            if any(fragment in lowered for fragment in key_fragments):
                return "<redacted>"

        return value

    return _scrub(data)


class CodeRabbitClient:
    """Client wrapper that talks to the CodeRabbit MCP endpoint."""

    def __init__(
        self,
        *,
        config: Optional[Dict[str, Any]] = None,
        config_path: Optional[Path] = None,
        transport: Optional[Transport] = None,
        time_fn: TimeFn = time.time,
        sleep_fn: SleepFn = time.sleep,
        random_fn: RandomFn = random.random,
    ) -> None:
        self._config = config or self._load_config(config_path)
        self.enabled = bool(self._config.get("enabled", True))
        self.endpoint = self._config.get("endpoint", "https://api.coderabbit.ai/v1/reviews")
        self.timeout_seconds = float(self._config.get("timeout_seconds", 30))
        self.requires_network = bool(self._config.get("requires_network", True))
        self.api_key_env = str(self._config.get("api_key_env", "CODERABBIT_API_KEY"))
        self.api_key = os.getenv(self.api_key_env) or self._config.get("api_key")
        self.cache_ttl = float(self._config.get("cache_ttl_seconds", 3600))
        retry_cfg = self._config.get("retry_policy", {})
        self.max_attempts = max(1, int(retry_cfg.get("max_attempts", 3)))
        self.backoff_seconds = max(0.1, float(retry_cfg.get("backoff_seconds", 1.0)))
        self.max_backoff_seconds = max(self.backoff_seconds, float(retry_cfg.get("max_backoff_seconds", 8.0)))
        self.jitter_seconds = max(0.0, float(retry_cfg.get("jitter_seconds", 0.3)))
        self._transport = transport or self._http_transport
        self._time_fn = time_fn
        self._sleep_fn = sleep_fn
        self._random_fn = random_fn

        metrics_dir = get_metrics_dir()
        telemetry_cfg = self._config.get("telemetry", {})
        telemetry_filename = telemetry_cfg.get("filename", "coderabbit_telemetry.jsonl")
        self.telemetry_path = metrics_dir / telemetry_filename
        self.telemetry_redact_keys = telemetry_cfg.get("redact_keys", [])
        cache_filename = self._config.get("cache_filename", "coderabbit_cache.json")
        self.cache_path = metrics_dir / cache_filename
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        self.telemetry_path.parent.mkdir(parents=True, exist_ok=True)

        self._cache: Optional[Dict[str, Any]] = None

    def _load_config(self, config_path: Optional[Path]) -> Dict[str, Any]:
        path = config_path or DEFAULT_CONFIG_PATH
        if not path.exists():
            logger.debug("CodeRabbit config not found at %s; using defaults", path)
            return {}

        if yaml is None:
            logger.debug("PyYAML not available; skipping CodeRabbit config load")
            return {}

        try:
            with open(path, "r", encoding="utf-8") as handle:
                data = yaml.safe_load(handle) or {}
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("Failed to read CodeRabbit config %s: %s", path, exc)
            return {}

        return data

    # Public API -----------------------------------------------------------------

    def review_pull_request(
        self,
        *,
        repo: str,
        pr_number: int,
        diff: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        force_refresh: bool = False,
    ) -> CodeRabbitReview:
        """Fetch CodeRabbit review data for the requested pull request."""

        if not self.enabled:
            raise RuntimeError("CodeRabbit integration is disabled via configuration.")

        cache_key = self._cache_key(repo, pr_number)
        now = self._time_fn()

        if not force_refresh:
            cached = self._load_from_cache(cache_key, now)
            if cached:
                return cached

        payload = {
            "repo": repo,
            "pr_number": pr_number,
            "diff": diff,
            "metadata": metadata or {},
        }

        try:
            raw = self._invoke_with_retries(payload)
            review = self._build_review(repo=repo, pr_number=pr_number, response=raw)
            self._store_in_cache(cache_key, review, now)
            self._write_telemetry("review.success", review, payload)
            return review
        except CodeRabbitError as exc:
            cached = self._load_from_cache(cache_key, now)
            if cached:
                degraded = cached.degraded_copy(str(exc))
                self._write_telemetry("review.degraded", degraded, payload)
                return degraded
            self._write_telemetry("review.failed", None, payload, error=str(exc))
            raise

    # Internal helpers -----------------------------------------------------------

    def _invoke_with_retries(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        attempt = 0
        last_error: Optional[CodeRabbitError] = None
        delay = self.backoff_seconds

        while attempt < self.max_attempts:
            attempt += 1
            try:
                return self._transport(payload)
            except CodeRabbitError as exc:
                last_error = exc
                if not exc.retryable or attempt >= self.max_attempts:
                    raise
                jitter = self.jitter_seconds * self._random_fn()
                sleep_for = min(delay, self.max_backoff_seconds) + jitter
                self._sleep_fn(sleep_for)
                delay = min(delay * 2, self.max_backoff_seconds)
                continue

        if last_error:
            raise last_error
        raise RuntimeError("CodeRabbit invocation failed without raising an error")

    def _http_transport(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        if not self.requires_network:
            raise NetworkError("CodeRabbit network access disabled", status=None)

        if httpx is None:  # pragma: no cover - only when httpx missing at runtime
            raise NetworkError("httpx is required for CodeRabbit live calls", status=None)

        if not self.api_key:
            raise AuthError(
                f"Environment variable {self.api_key_env} is not set for CodeRabbit.", status=None
            )

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        try:
            response = httpx.post(
                self.endpoint,
                json=payload,
                timeout=self.timeout_seconds,
                headers=headers,
            )
        except httpx.TimeoutException as exc:  # pragma: no cover - requires live call
            raise NetworkError("CodeRabbit request timed out") from exc
        except httpx.HTTPError as exc:  # pragma: no cover - requires live call
            raise NetworkError("CodeRabbit HTTP transport error") from exc

        if response.status_code == 401:
            raise AuthError("CodeRabbit rejected the credentials", status=401)
        if response.status_code == 429:
            raise RateLimitError("CodeRabbit rate limit hit", status=429)
        if response.status_code >= 400:
            raise CodeRabbitError(
                f"CodeRabbit responded with HTTP {response.status_code}",
                status=response.status_code,
                payload=self._safe_json(response),
            )

        data = self._safe_json(response)
        if not isinstance(data, dict):
            raise CodeRabbitError("CodeRabbit returned non-object JSON", payload={"body": data})
        return data

    @staticmethod
    def _safe_json(response: Any) -> Any:  # pragma: no cover - simple helper
        try:
            return response.json()
        except Exception:
            return {"raw": response.text}

    def _build_review(self, *, repo: str, pr_number: int, response: Dict[str, Any]) -> CodeRabbitReview:
        issues_payload = response.get("issues") or response.get("comments") or []
        issues = [CodeRabbitIssue.from_payload(item) for item in issues_payload]
        score = float(response.get("score") or response.get("quality", {}).get("score") or 0.0)
        status = str(response.get("status") or response.get("state") or "ok")
        summary = str(response.get("summary") or response.get("overview") or "")
        received_at = datetime.now(timezone.utc)

        return CodeRabbitReview(
            repo=repo,
            pr_number=pr_number,
            score=score,
            status=status,
            summary=summary,
            issues=issues,
            raw=response,
            received_at=received_at,
        )

    def _cache_key(self, repo: str, pr_number: int) -> str:
        return f"{repo}#{pr_number}"

    def _load_cache_map(self) -> Dict[str, Any]:
        if self._cache is not None:
            return self._cache

        if not self.cache_path.exists():
            self._cache = {}
            return self._cache

        try:
            with open(self.cache_path, "r", encoding="utf-8") as handle:
                self._cache = json.load(handle)
        except Exception:
            self._cache = {}

        return self._cache

    def _store_cache_map(self, cache: Dict[str, Any]) -> None:
        tmp_path = self.cache_path.with_suffix(".tmp")
        with open(tmp_path, "w", encoding="utf-8") as handle:
            json.dump(cache, handle, indent=2)
        tmp_path.replace(self.cache_path)

    def _load_from_cache(self, cache_key: str, now: float) -> Optional[CodeRabbitReview]:
        cache = self._load_cache_map()
        entry = cache.get(cache_key)
        if not entry:
            return None

        stored_at = float(entry.get("stored_at", 0.0))
        if stored_at and now - stored_at > self.cache_ttl:
            return None

        review_dict = entry.get("review")
        if not isinstance(review_dict, dict):
            return None
        return CodeRabbitReview.from_dict(review_dict)

    def _store_in_cache(self, cache_key: str, review: CodeRabbitReview, now: float) -> None:
        cache = self._load_cache_map()
        cache[cache_key] = {
            "stored_at": now,
            "review": review.to_dict(),
        }
        self._store_cache_map(cache)

    def _write_telemetry(
        self,
        event: str,
        review: Optional[CodeRabbitReview],
        request_payload: Dict[str, Any],
        *,
        error: Optional[str] = None,
    ) -> None:
        telemetry_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": event,
            "repo": request_payload.get("repo"),
            "pr_number": request_payload.get("pr_number"),
            "degraded": review.degraded if review else False,
            "degraded_reason": review.degraded_reason if review else None,
            "score": review.score if review else None,
            "status": review.status if review else None,
            "error": error,
            "request": scrub_secrets(request_payload, redact_keys=self.telemetry_redact_keys),
        }
        if review:
            telemetry_entry["issues"] = len(review.issues)
        sanitized_entry = scrub_secrets(telemetry_entry, redact_keys=self.telemetry_redact_keys)
        try:
            with open(self.telemetry_path, "a", encoding="utf-8") as handle:
                handle.write(json.dumps(sanitized_entry) + "\n")
        except Exception as exc:  # pragma: no cover - logging best effort
            logger.debug("Failed to write CodeRabbit telemetry: %s", exc)


__all__ = [
    "CodeRabbitClient",
    "CodeRabbitReview",
    "CodeRabbitIssue",
    "CodeRabbitError",
    "NetworkError",
    "AuthError",
    "RateLimitError",
    "scrub_secrets",
]
