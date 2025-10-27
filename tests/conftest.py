"""Pytest fixtures and environment shims."""

import sys
import types


class _PsutilProcessStub:
    def cpu_percent(self) -> float:
        return 0.0

    def memory_info(self):
        return types.SimpleNamespace(rss=0)

    def memory_percent(self) -> float:
        return 0.0

    def io_counters(self):
        return types.SimpleNamespace(read_bytes=0, write_bytes=0)

    def num_threads(self) -> int:
        return 1


class _PsutilStub:
    def __init__(self) -> None:
        self.Process = lambda: _PsutilProcessStub()

    def net_io_counters(self):
        return types.SimpleNamespace(bytes_sent=0, bytes_recv=0)


sys.modules.setdefault('psutil', _PsutilStub())
