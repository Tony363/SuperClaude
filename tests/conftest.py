"""Minimal asyncio support for pytest without external plugins."""

import asyncio
import inspect

import pytest


@pytest.hookimpl()
def pytest_pyfunc_call(pyfuncitem):
    """Execute coroutine tests using an event loop when pytest-asyncio is unavailable."""
    test_function = pyfuncitem.obj

    if not inspect.iscoroutinefunction(test_function):
        return None

    signature = inspect.signature(test_function)
    accepts_kwargs = any(param.kind == inspect.Parameter.VAR_KEYWORD for param in signature.parameters.values())
    funcargs = dict(pyfuncitem.funcargs)
    if not accepts_kwargs:
        allowed = set(signature.parameters.keys())
        funcargs = {name: value for name, value in funcargs.items() if name in allowed}

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(test_function(**funcargs))
    finally:
        try:
            loop.run_until_complete(loop.shutdown_asyncgens())
        except (RuntimeError, AttributeError):
            pass
        loop.close()
        asyncio.set_event_loop(None)

    return True
