import os
import subprocess
import sys
import threading

from caneca.watchdog import pid_alive, watch_parent


def test_pid_alive_for_self_and_dead_process():
    assert pid_alive(os.getpid())
    proc = subprocess.Popen([sys.executable, "-c", "pass"])
    proc.wait()
    assert not pid_alive(proc.pid)
    assert not pid_alive(0)


def test_watch_parent_fires_when_process_exits():
    proc = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(0.3)"])
    fired = threading.Event()
    watch_parent(proc.pid, fired.set, interval=0.05)
    proc.wait()
    assert fired.wait(3), "watchdog should notice the parent is gone"
