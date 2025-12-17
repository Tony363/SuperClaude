"""
Lightweight HTTP helpers for the SuperClaude API clients.

Provides minimal async wrappers around the standard library so that
API-specific clients can issue JSON POST requests without depending on
third-party HTTP libraries. The helpers convert network failures into
structured exceptions that upstream callers can handle consistently.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any
from urllib import error as urllib_error
from urllib import parse as urllib_parse
from urllib import request as urllib_request


@dataclass
class HTTPClientError(RuntimeError):
    """Error raised when an HTTP request fails."""

    status: int | None
    message: str
    payload: dict[str, Any] | None = None

    def __str__(self) -> str:
        status_part = f"HTTP {self.status}" if self.status is not None else "HTTP error"
        if self.payload and "error" in self.payload:
            detail = self.payload["error"]
            if isinstance(detail, Mapping):
                detail_message = detail.get("message") or json.dumps(detail)
            else:
                detail_message = str(detail)
        else:
            detail_message = self.message
        return f"{status_part}: {detail_message}"


async def post_json(
    url: str,
    payload: dict[str, Any],
    *,
    headers: Mapping[str, str] | None = None,
    params: Mapping[str, Any] | None = None,
    timeout: int = 120,
) -> tuple[int, dict[str, Any], dict[str, str]]:
    """
    Execute an HTTP POST request that sends and expects JSON payloads.

    Args:
        url: Endpoint URL.
        payload: Request body to serialise as JSON.
        headers: Optional request headers.
        params: Optional query parameters.
        timeout: Socket timeout in seconds.

    Returns:
        Tuple of (status_code, decoded_json_payload, response_headers).

    Raises:
        HTTPClientError: When the request fails or the payload cannot be decoded.
    """

    request_headers = {"Content-Type": "application/json"}
    if headers:
        request_headers.update(headers)

    def _do_request() -> tuple[int, bytes, dict[str, str]]:
        encoded = json.dumps(payload).encode("utf-8")
        target_url = url
        if params:
            query = urllib_parse.urlencode(
                {key: value for key, value in params.items() if value is not None}
            )
            target_url = f"{url}?{query}"

        req = urllib_request.Request(
            target_url,
            data=encoded,
            headers=request_headers,
            method="POST",
        )

        with urllib_request.urlopen(req, timeout=timeout) as response:
            status_code = response.getcode()
            body = response.read()
            response_headers = dict(response.headers.items())
        return status_code, body, response_headers

    try:
        status_code, raw_body, response_headers = await asyncio.to_thread(_do_request)
    except urllib_error.HTTPError as err:
        error_body = err.read()
        decoded: dict[str, Any] | None = None
        if error_body:
            try:
                decoded = json.loads(error_body.decode("utf-8"))
            except json.JSONDecodeError:
                decoded = None
        raise HTTPClientError(err.code, err.reason, decoded) from err
    except urllib_error.URLError as exc:
        raise HTTPClientError(None, str(exc)) from exc

    try:
        decoded_body = json.loads(raw_body.decode("utf-8") or "{}")
    except json.JSONDecodeError as exc:
        raise HTTPClientError(status_code, f"Invalid JSON response: {exc}") from exc

    return status_code, decoded_body, response_headers
