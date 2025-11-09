"""Tests for Browser MCP integration."""

from datetime import datetime
from typing import Any, Dict, List, Tuple

import pytest

from SuperClaude.Commands import (
    CommandExecutor,
    CommandParser,
    CommandRegistry,
)
from SuperClaude.Commands.executor import CommandContext
from SuperClaude.MCP import (
    BrowserConfig,
    BrowserIntegration,
    BrowserMode,
    BrowserSnapshot,
    ScreenshotResult,
)
from SuperClaude.Modes.behavioral_manager import BehavioralMode

pytestmark = pytest.mark.asyncio


class InMemoryBrowserTransport:
    """Deterministic transport that maintains lightweight browser state."""

    def __init__(self) -> None:
        self.initialized = False
        self.closed = False
        self.calls: List[Tuple[str, Dict[str, Any]]] = []
        self.current_url: str = "about:blank"
        self.console_history: List[str] = []
        self.viewport = (1280, 720)

    async def initialize(self, config: Dict[str, Any], browser_config: BrowserConfig) -> None:
        self.initialized = True
        self.viewport = (browser_config.viewport_width, browser_config.viewport_height)
        self.console_history.append("[transport] session initialised")

    async def invoke(self, tool: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        self.calls.append((tool, payload))

        if tool == 'browser.navigate':
            url = payload['url']
            self.current_url = url
            self.console_history.append(f"[transport] navigated to {url}")
            return {
                'status': 'success',
                'url': url,
                'title': f"In-memory page for {url}",
                'loaded': True,
            }
        if tool == 'browser.click':
            selector = payload['selector']
            self.console_history.append(f"[transport] clicked {selector}")
            return {'status': 'success', 'selector': selector, 'clicked': True}
        if tool == 'browser.type':
            selector = payload['selector']
            text = payload['text']
            self.console_history.append(f"[transport] typed '{text}' into {selector}")
            return {'status': 'success', 'selector': selector, 'entered': text}
        if tool == 'browser.snapshot':
            url = payload.get('url', self.current_url)
            return {
                'snapshot': {
                    'url': url,
                    'title': f"Snapshot for {url}",
                    'accessibility_tree': {'role': 'document', 'children': []},
                    'console_logs': list(self.console_history[-5:]),
                    'timestamp': datetime.now().isoformat(),
                }
            }
        if tool == 'browser.screenshot':
            width = payload['config']['viewport']['width']
            height = payload['config']['viewport']['height']
            size_bytes = max(1, width * height // 6)
            return {
                'screenshot': {
                    'path': payload['path'],
                    'format': 'png',
                    'width': width,
                    'height': height,
                    'size_bytes': size_bytes,
                    'timestamp': datetime.now().isoformat(),
                }
            }
        if tool == 'browser.console_logs':
            return {'logs': list(self.console_history)}
        if tool == 'browser.select':
            selector = payload['selector']
            values = payload['values']
            self.console_history.append(f"[transport] selected {values} in {selector}")
            return {'status': 'success', 'selector': selector, 'values': values}
        if tool == 'browser.press_key':
            key = payload['key']
            self.console_history.append(f"[transport] pressed {key}")
            return {'status': 'success', 'key': key}
        if tool == 'browser.back':
            self.console_history.append("[transport] navigated back")
            return {'status': 'success', 'action': 'back'}
        if tool == 'browser.forward':
            self.console_history.append("[transport] navigated forward")
            return {'status': 'success', 'action': 'forward'}
        if tool == 'browser.hover':
            selector = payload['selector']
            self.console_history.append(f"[transport] hovered {selector}")
            return {'status': 'success', 'selector': selector}

        return {'status': 'success'}

    async def close(self) -> None:
        self.closed = True
        self.console_history.append("[transport] session closed")


class FailingTransport(InMemoryBrowserTransport):
    def __init__(self, fail_init: bool = False, fail_tool: str | None = None, fail_close: bool = False):
        super().__init__()
        self.fail_init = fail_init
        self.fail_tool = fail_tool
        self.fail_close = fail_close

    async def initialize(self, config: Dict[str, Any], browser_config: BrowserConfig) -> None:
        if self.fail_init:
            raise RuntimeError("transport init failed")
        await super().initialize(config, browser_config)

    async def invoke(self, tool: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        if self.fail_tool == tool:
            raise RuntimeError(f"transport failed on {tool}")
        return await super().invoke(tool, payload)

    async def close(self) -> None:
        if self.fail_close:
            raise RuntimeError("close failed")
        await super().close()


async def test_browser_integration_initializes_transport():
    transport = InMemoryBrowserTransport()
    browser = BrowserIntegration(config={'enabled': True}, transport=transport)

    assert browser.enabled is True
    assert transport.initialized is False

    await browser.initialize()

    assert transport.initialized is True
    assert browser.session_active is True


async def test_browser_navigation_invokes_transport():
    transport = InMemoryBrowserTransport()
    browser = BrowserIntegration(config={'enabled': True}, transport=transport)

    await browser.initialize()
    result = await browser.navigate('https://example.com')

    assert result['url'] == 'https://example.com'
    assert transport.calls[0][0] == 'browser.navigate'


async def test_browser_snapshot_returns_dataclass():
    transport = InMemoryBrowserTransport()
    browser = BrowserIntegration(config={'enabled': True}, transport=transport)

    await browser.initialize()
    await browser.navigate('https://example.com')
    snapshot = await browser.snapshot()

    assert isinstance(snapshot, BrowserSnapshot)
    assert snapshot.url == 'https://example.com'
    assert isinstance(snapshot.accessibility_tree, dict)


async def test_browser_screenshot_returns_metadata():
    transport = InMemoryBrowserTransport()
    browser_config = BrowserConfig(mode=BrowserMode.headless, viewport_width=800, viewport_height=600)
    browser = BrowserIntegration(config={'enabled': True}, browser_config=browser_config, transport=transport)

    await browser.initialize()
    result = await browser.screenshot(full_page=True)

    assert isinstance(result, ScreenshotResult)
    assert result.width == 800
    assert result.height == 600
    assert transport.calls[-1][0] == 'browser.screenshot'


async def test_browser_console_logs():
    transport = InMemoryBrowserTransport()
    browser = BrowserIntegration(config={'enabled': True}, transport=transport)

    await browser.initialize()
    await browser.navigate('https://example.com')
    logs = await browser.get_console_logs()

    assert len(logs) >= 2
    assert any('[transport]' in entry for entry in logs)


async def test_browser_cleanup_closes_transport():
    transport = InMemoryBrowserTransport()
    browser = BrowserIntegration(config={'enabled': True}, transport=transport)

    await browser.initialize()
    await browser.cleanup()

    assert transport.closed is True
    assert browser.session_active is False


async def test_browser_disabled_raises_runtime_error():
    browser = BrowserIntegration(config={'enabled': False}, transport=InMemoryBrowserTransport())

    with pytest.raises(RuntimeError):
        await browser.navigate('https://example.com')


async def test_execute_browser_tests_helper(monkeypatch):
    registry = CommandRegistry()
    parser = CommandParser(registry=registry)
    executor = CommandExecutor(registry, parser)

    metadata = registry.get_command('test')
    assert metadata is not None

    transport = InMemoryBrowserTransport()
    browser = BrowserIntegration(config={'enabled': True}, transport=transport)

    parsed = parser.parse('/sc:test https://example.com --browser --type visual')
    context = CommandContext(
        command=parsed,
        metadata=metadata,
        session_id='session-test',
        behavior_mode=BehavioralMode.NORMAL.value,
    )
    context.mcp_servers.append('browser')

    executor.active_mcp_servers['browser'] = {
        'status': 'active',
        'activated_at': datetime.now(),
        'instance': browser,
        'config': {'enabled': True},
    }

    result = await executor._execute_browser_tests(context, scenario_hint='visual')

    assert result['status'] == 'browser_completed'
    assert result['url'] == 'https://example.com'
    assert any(call[0] == 'browser.navigate' for call in transport.calls)
    assert any(call[0] == 'browser.screenshot' for call in transport.calls)


async def test_browser_navigate_propagates_initialize_failure():
    transport = FailingTransport(fail_init=True)
    browser = BrowserIntegration(config={'enabled': True}, transport=transport)

    with pytest.raises(RuntimeError, match="transport init failed"):
        await browser.navigate('https://example.com')


async def test_browser_screenshot_propagates_tool_error():
    transport = FailingTransport(fail_tool='browser.screenshot')
    browser = BrowserIntegration(config={'enabled': True}, transport=transport)

    await browser.initialize()
    with pytest.raises(RuntimeError, match="screenshot"):
        await browser.screenshot(full_page=True)


async def test_browser_cleanup_surfaces_close_error():
    transport = FailingTransport(fail_close=True)
    browser = BrowserIntegration(config={'enabled': True}, transport=transport)

    await browser.initialize()
    with pytest.raises(RuntimeError, match="close failed"):
        await browser.cleanup()
    assert browser.session_active is True
