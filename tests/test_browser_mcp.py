"""Tests for Browser MCP integration."""

import asyncio
from datetime import datetime
from typing import Any, Dict, List, Tuple

import pytest

pytest.importorskip('pytest_asyncio')

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
    BrowserTransport,
    ScreenshotResult,
)
from SuperClaude.Modes.behavioral_manager import BehavioralMode


class MockTransport(BrowserTransport):
    """Deterministic transport used for unit testing."""

    def __init__(self) -> None:
        self.initialized = False
        self.closed = False
        self.calls: List[Tuple[str, Dict[str, Any]]] = []

    async def initialize(self, config: Dict[str, Any], browser_config: BrowserConfig) -> None:
        self.initialized = True

    async def invoke(self, tool: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        self.calls.append((tool, payload))

        if tool == 'browser.navigate':
            url = payload['url']
            return {
                'status': 'success',
                'url': url,
                'title': f"Mock page for {url}",
                'loaded': True,
            }
        if tool == 'browser.click':
            return {'status': 'success', 'selector': payload['selector'], 'clicked': True}
        if tool == 'browser.type':
            return {'status': 'success', 'selector': payload['selector'], 'entered': payload['text']}
        if tool == 'browser.snapshot':
            url = payload.get('url', 'about:blank')
            return {
                'snapshot': {
                    'url': url,
                    'title': 'Mock Snapshot',
                    'accessibility_tree': {'role': 'document', 'children': []},
                    'console_logs': ['[mock] DOM ready'],
                    'timestamp': datetime.now().isoformat(),
                }
            }
        if tool == 'browser.screenshot':
            return {
                'screenshot': {
                    'path': payload['path'],
                    'format': 'png',
                    'width': payload['config']['viewport']['width'],
                    'height': payload['config']['viewport']['height'],
                    'size_bytes': 2048,
                    'timestamp': datetime.now().isoformat(),
                }
            }
        if tool == 'browser.console_logs':
            return {'logs': ['[mock] log 1', '[mock] log 2']}
        if tool == 'browser.select':
            return {'status': 'success', 'selector': payload['selector'], 'values': payload['values']}
        if tool == 'browser.press_key':
            return {'status': 'success', 'key': payload['key']}
        if tool == 'browser.back':
            return {'status': 'success', 'action': 'back'}
        if tool == 'browser.forward':
            return {'status': 'success', 'action': 'forward'}
        if tool == 'browser.hover':
            return {'status': 'success', 'selector': payload['selector']}

        return {'status': 'success'}

    async def close(self) -> None:
        self.closed = True


@pytest.mark.asyncio
async def test_browser_integration_initializes_transport():
    transport = MockTransport()
    browser = BrowserIntegration(config={'enabled': True}, transport=transport)

    assert browser.enabled is True
    assert transport.initialized is False

    await browser.initialize()

    assert transport.initialized is True
    assert browser.session_active is True


@pytest.mark.asyncio
async def test_browser_navigation_invokes_transport():
    transport = MockTransport()
    browser = BrowserIntegration(config={'enabled': True}, transport=transport)

    await browser.initialize()
    result = await browser.navigate('https://example.com')

    assert result['url'] == 'https://example.com'
    assert transport.calls[0][0] == 'browser.navigate'


@pytest.mark.asyncio
async def test_browser_snapshot_returns_dataclass():
    transport = MockTransport()
    browser = BrowserIntegration(config={'enabled': True}, transport=transport)

    await browser.initialize()
    await browser.navigate('https://example.com')
    snapshot = await browser.snapshot()

    assert isinstance(snapshot, BrowserSnapshot)
    assert snapshot.url == 'https://example.com'
    assert isinstance(snapshot.accessibility_tree, dict)


@pytest.mark.asyncio
async def test_browser_screenshot_returns_metadata():
    transport = MockTransport()
    browser_config = BrowserConfig(mode=BrowserMode.headless, viewport_width=800, viewport_height=600)
    browser = BrowserIntegration(config={'enabled': True}, browser_config=browser_config, transport=transport)

    await browser.initialize()
    result = await browser.screenshot(full_page=True)

    assert isinstance(result, ScreenshotResult)
    assert result.width == 800
    assert result.height == 600
    assert transport.calls[-1][0] == 'browser.screenshot'


@pytest.mark.asyncio
async def test_browser_console_logs():
    transport = MockTransport()
    browser = BrowserIntegration(config={'enabled': True}, transport=transport)

    await browser.initialize()
    await browser.navigate('https://example.com')
    logs = await browser.get_console_logs()

    assert len(logs) == 2
    assert '[mock] log 1' in logs[0]


@pytest.mark.asyncio
async def test_browser_cleanup_closes_transport():
    transport = MockTransport()
    browser = BrowserIntegration(config={'enabled': True}, transport=transport)

    await browser.initialize()
    await browser.cleanup()

    assert transport.closed is True
    assert browser.session_active is False


@pytest.mark.asyncio
async def test_browser_disabled_raises_runtime_error():
    browser = BrowserIntegration(config={'enabled': False}, transport=MockTransport())

    with pytest.raises(RuntimeError):
        await browser.navigate('https://example.com')


@pytest.mark.asyncio
async def test_execute_browser_tests_helper(monkeypatch):
    registry = CommandRegistry()
    parser = CommandParser(registry=registry)
    executor = CommandExecutor(registry, parser)

    metadata = registry.get_command('test')
    assert metadata is not None

    transport = MockTransport()
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
