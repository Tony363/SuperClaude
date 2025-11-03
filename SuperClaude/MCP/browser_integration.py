"""Browser MCP integration for SuperClaude slash commands.

This module provides an asynchronous bridge between the SuperClaude framework
and the local Browser MCP server. Runtime invocations delegate browser
operations to the Browser MCP via the Claude CLI (``claude mcp call ...``).
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class BrowserMode(Enum):
    """Browser execution modes."""

    headless = "headless"
    headed = "headed"
    debug = "debug"


class WaitStrategy(Enum):
    """Wait strategies for DOM stabilisation."""

    none = "none"
    idle = "idle"
    load = "load"
    networkidle = "networkidle"


@dataclass
class BrowserConfig:
    """Configuration passed to Browser MCP operations."""

    mode: BrowserMode = BrowserMode.headless
    viewport_width: int = 1280
    viewport_height: int = 720
    timeout: int = 30000  # milliseconds
    wait_strategy: WaitStrategy = WaitStrategy.load
    chromium_path: Optional[str] = None
    temp_dir: Optional[str] = None


@dataclass
class BrowserSnapshot:
    """Structured result of a Browser MCP snapshot call."""

    url: str
    title: str
    accessibility_tree: Dict[str, Any] = field(default_factory=dict)
    console_logs: List[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class ScreenshotResult:
    """Metadata describing a captured screenshot."""

    path: str
    format: str = "png"
    width: int = 0
    height: int = 0
    size_bytes: int = 0
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class CLIBrowserTransport:
    """Transport that talks to Browser MCP via the Claude CLI."""

    def __init__(self, cli_path: Optional[str] = None, server_name: str = "browser", timeout: int = 120):
        self.cli_path = cli_path or os.environ.get("CLAUDE_CLI_PATH", "claude")
        self.server_name = server_name
        self.timeout = timeout

    async def initialize(self, config: Dict[str, Any], browser_config: BrowserConfig) -> None:
        await asyncio.to_thread(self._ensure_server_registered)

    def _ensure_server_registered(self) -> None:
        try:
            result = subprocess.run(
                [self.cli_path, "mcp", "list"],
                capture_output=True,
                text=True,
                timeout=self.timeout,
            )
        except FileNotFoundError as exc:  # pragma: no cover - depends on local CLI installation
            raise RuntimeError("Claude CLI not found. Install the claude CLI to use Browser MCP.") from exc

        if result.returncode != 0:
            stderr = result.stderr.strip() or "Unknown error"
            raise RuntimeError(f"Failed to list MCP servers: {stderr}")

        if self.server_name not in result.stdout.lower():
            raise RuntimeError(
                f"MCP server '{self.server_name}' is not registered with Claude CLI. "
                "Run 'claude mcp add -s user -- browser npx -y @browsermcp/mcp@latest'."
            )

    async def invoke(self, tool: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        command = [self.cli_path, "mcp", "call", self.server_name, tool]
        body = json.dumps(payload)

        def _run() -> Dict[str, Any]:
            result = subprocess.run(
                command,
                input=body.encode("utf-8"),
                capture_output=True,
                timeout=self.timeout,
            )
            if result.returncode != 0:
                stderr = result.stderr.strip() or "Unknown MCP error"
                raise RuntimeError(f"Browser MCP invocation failed ({tool}): {stderr}")

            raw = result.stdout.strip() or "{}"
            try:
                return json.loads(raw)
            except json.JSONDecodeError:
                return {"status": "success", "raw": raw}

        return await asyncio.to_thread(_run)

    async def close(self) -> None:  # pragma: no cover - nothing to close for CLI invocations
        return


class BrowserIntegration:
    """High-level interface for interacting with Browser MCP."""

    TOOL_MAP = {
        "navigate": "browser.navigate",
        "click": "browser.click",
        "type": "browser.type",
        "snapshot": "browser.snapshot",
        "screenshot": "browser.screenshot",
        "console": "browser.console_logs",
        "select": "browser.select",
        "press": "browser.press_key",
        "back": "browser.back",
        "forward": "browser.forward",
        "hover": "browser.hover",
    }

    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        browser_config: Optional[BrowserConfig] = None,
        transport: Optional[Any] = None,
        test_mode: bool = False,
    ) -> None:
        self.config = config or {}
        self.browser_config = browser_config or BrowserConfig()
        self.enabled = bool(self.config.get("enabled", False))
        self.transport = transport or CLIBrowserTransport()
        self.transport_initialized = False
        self.session_active = False
        self.current_url: Optional[str] = None
        self.test_mode = test_mode

        self._setup_environment()

    def _setup_environment(self) -> None:
        if self.browser_config.chromium_path:
            os.environ["BROWSER_MCP_CHROMIUM_PATH"] = self.browser_config.chromium_path

        if self.browser_config.temp_dir:
            os.environ["BROWSER_MCP_TEMP_DIR"] = self.browser_config.temp_dir

        if os.environ.get("CI") or self.browser_config.mode == BrowserMode.headless:
            os.environ["BROWSER_MCP_HEADLESS"] = "true"

    def _serialize_config(self) -> Dict[str, Any]:
        return {
            "mode": self.browser_config.mode.value,
            "viewport": {
                "width": self.browser_config.viewport_width,
                "height": self.browser_config.viewport_height,
            },
            "timeout": self.browser_config.timeout,
            "wait_strategy": self.browser_config.wait_strategy.value,
        }

    async def initialize(self) -> bool:
        if not self.enabled:
            logger.info("Browser MCP integration disabled; skipping initialization")
            return False

        if not self.transport_initialized:
            await self.transport.initialize(self.config, self.browser_config)
            self.transport_initialized = True

        self.session_active = True
        logger.info("Browser MCP session initialized (mode=%s)", self.browser_config.mode.value)
        return True

    async def _ensure_session(self) -> None:
        if not self.session_active:
            await self.initialize()
        if not self.session_active:
            raise RuntimeError("Browser MCP session is not active")

    async def _call_tool(self, tool_key: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        if not self.enabled:
            raise RuntimeError("Browser MCP integration is disabled")

        await self._ensure_session()

        tool_name = self.TOOL_MAP.get(tool_key, tool_key)
        request_payload = {
            "config": self._serialize_config(),
            **payload,
        }
        logger.debug("Invoking Browser MCP tool %s with payload %s", tool_name, request_payload)
        return await self.transport.invoke(tool_name, request_payload)

    async def navigate(self, url: str) -> Dict[str, Any]:
        result = await self._call_tool("navigate", {"url": url})
        self.current_url = result.get("url", url)
        return result

    async def click(self, selector: str, description: str = "") -> Dict[str, Any]:
        return await self._call_tool(
            "click",
            {
                "selector": selector,
                "description": description,
            },
        )

    async def type_text(
        self,
        selector: str,
        text: str,
        submit: bool = False,
        description: str = "",
    ) -> Dict[str, Any]:
        return await self._call_tool(
            "type",
            {
                "selector": selector,
                "text": text,
                "submit": submit,
                "description": description,
            },
        )

    async def snapshot(self) -> BrowserSnapshot:
        result = await self._call_tool("snapshot", {"url": self.current_url})
        snapshot_data = result.get("snapshot", result)
        return BrowserSnapshot(
            url=snapshot_data.get("url", self.current_url or "about:blank"),
            title=snapshot_data.get("title", ""),
            accessibility_tree=snapshot_data.get("accessibility_tree", {}),
            console_logs=snapshot_data.get("console_logs", []),
            timestamp=snapshot_data.get("timestamp", datetime.now().isoformat()),
        )

    async def screenshot(self, path: Optional[str] = None, full_page: bool = False) -> ScreenshotResult:
        destination = path or self._default_screenshot_path()
        os.makedirs(os.path.dirname(destination), exist_ok=True)

        result = await self._call_tool(
            "screenshot",
            {
                "path": destination,
                "full_page": full_page,
            },
        )
        data = result.get("screenshot", result)
        return ScreenshotResult(
            path=data.get("path", destination),
            format=data.get("format", "png"),
            width=int(data.get("width", self.browser_config.viewport_width)),
            height=int(data.get("height", self.browser_config.viewport_height)),
            size_bytes=int(data.get("size_bytes", 0)),
            timestamp=data.get("timestamp", datetime.now().isoformat()),
        )

    async def get_console_logs(self) -> List[str]:
        result = await self._call_tool("console", {"url": self.current_url})
        logs = result.get("logs")
        if isinstance(logs, list):
            return [str(entry) for entry in logs]
        return []

    async def select_option(self, selector: str, values: List[str], description: str = "") -> Dict[str, Any]:
        return await self._call_tool(
            "select",
            {
                "selector": selector,
                "values": values,
                "description": description,
            },
        )

    async def press_key(self, key: str) -> Dict[str, Any]:
        return await self._call_tool("press", {"key": key})

    async def go_back(self) -> Dict[str, Any]:
        return await self._call_tool("back", {})

    async def go_forward(self) -> Dict[str, Any]:
        return await self._call_tool("forward", {})

    async def hover(self, selector: str, description: str = "") -> Dict[str, Any]:
        return await self._call_tool(
            "hover",
            {
                "selector": selector,
                "description": description,
            },
        )

    async def wait(self, seconds: float) -> None:
        await asyncio.sleep(seconds)

    async def cleanup(self) -> None:
        if self.session_active:
            await self.transport.close()
            self.session_active = False
            self.current_url = None

    def _default_screenshot_path(self) -> str:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f".superclaude_metrics/screenshots/browser_{timestamp}.png"

    def __repr__(self) -> str:
        return (
            "BrowserIntegration(enabled={enabled}, session_active={active}, mode={mode})"
        ).format(
            enabled=self.enabled,
            active=self.session_active,
            mode=self.browser_config.mode.value,
        )
