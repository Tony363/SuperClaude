"""Tests for Browser MCP integration."""

import asyncio
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


def test_browser_integration_initializes_transport():
    transport = InMemoryBrowserTransport()
    browser = BrowserIntegration(config={'enabled': True}, transport=transport)

    assert browser.enabled is True
    assert transport.initialized is False

    asyncio.run(browser.initialize())

    assert transport.initialized is True
    assert browser.session_active is True


def test_browser_navigation_invokes_transport():
    transport = InMemoryBrowserTransport()
    browser = BrowserIntegration(config={'enabled': True}, transport=transport)

    asyncio.run(browser.initialize())
    result = asyncio.run(browser.navigate('https://example.com'))

    assert result['url'] == 'https://example.com'
    assert transport.calls[0][0] == 'browser.navigate'


def test_browser_snapshot_returns_dataclass():
    transport = InMemoryBrowserTransport()
    browser = BrowserIntegration(config={'enabled': True}, transport=transport)

    asyncio.run(browser.initialize())
    asyncio.run(browser.navigate('https://example.com'))
    snapshot = asyncio.run(browser.snapshot())

    assert isinstance(snapshot, BrowserSnapshot)
    assert snapshot.url == 'https://example.com'
    assert isinstance(snapshot.accessibility_tree, dict)


def test_browser_screenshot_returns_metadata():
    transport = InMemoryBrowserTransport()
    browser_config = BrowserConfig(mode=BrowserMode.headless, viewport_width=800, viewport_height=600)
    browser = BrowserIntegration(config={'enabled': True}, browser_config=browser_config, transport=transport)

    asyncio.run(browser.initialize())
    result = asyncio.run(browser.screenshot(full_page=True))

    assert isinstance(result, ScreenshotResult)
    assert result.width == 800
    assert result.height == 600
    assert transport.calls[-1][0] == 'browser.screenshot'


def test_browser_console_logs():
    transport = InMemoryBrowserTransport()
    browser = BrowserIntegration(config={'enabled': True}, transport=transport)

    asyncio.run(browser.initialize())
    asyncio.run(browser.navigate('https://example.com'))
    logs = asyncio.run(browser.get_console_logs())

    assert len(logs) >= 2
    assert any('[transport]' in entry for entry in logs)


def test_browser_cleanup_closes_transport():
    transport = InMemoryBrowserTransport()
    browser = BrowserIntegration(config={'enabled': True}, transport=transport)

    asyncio.run(browser.initialize())
    asyncio.run(browser.cleanup())

    assert transport.closed is True
    assert browser.session_active is False


def test_browser_disabled_raises_runtime_error():
    browser = BrowserIntegration(config={'enabled': False}, transport=InMemoryBrowserTransport())

    with pytest.raises(RuntimeError):
        asyncio.run(browser.navigate('https://example.com'))


def test_execute_browser_tests_helper(monkeypatch):
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

    result = asyncio.run(executor._execute_browser_tests(context, scenario_hint='visual'))

    assert result['status'] == 'browser_completed'
    assert result['url'] == 'https://example.com'
    assert any(call[0] == 'browser.navigate' for call in transport.calls)
    assert any(call[0] == 'browser.screenshot' for call in transport.calls)
