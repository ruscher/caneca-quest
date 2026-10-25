"""Shuts the server down when the process that launched it disappears.

The desktop shell starts the backend as a sidecar and passes its own PID in
``CANECA_PARENT_PID``. If the shell is killed (crash, SIGKILL, task manager), it can't
stop the sidecar itself, so the sidecar notices and exits instead of lingering.
"""

from __future__ import annotations

import logging
import os
import sys
import threading
from collections.abc import Callable

log = logging.getLogger(__name__)


def pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    if sys.platform.startswith("win"):
        import ctypes

        synchronize, query_limited, wait_timeout = 0x00100000, 0x1000, 0x102
        kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
        handle = kernel32.OpenProcess(synchronize | query_limited, False, pid)
        if not handle:
            return False
        try:
            return bool(kernel32.WaitForSingleObject(handle, 0) == wait_timeout)
        finally:
            kernel32.CloseHandle(handle)
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def watch_parent(pid: int, on_exit: Callable[[], None], interval: float = 1.5) -> threading.Thread:
    stop = threading.Event()

    def loop() -> None:
        while not stop.wait(interval):
            if not pid_alive(pid):
                log.info("processo %s encerrado; desligando o servidor", pid)
                on_exit()
                return

    thread = threading.Thread(target=loop, name="parent-watchdog", daemon=True)
    thread.start()
    return thread
