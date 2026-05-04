"""
Process Manager — Handles spawning, tracking, and terminating project server processes.
Manages port allocation and process lifecycle with timeouts.
"""

import subprocess
import os
import signal
import time
import socket
import threading
from typing import Optional


# Port range for project servers
PORT_RANGE_START = 9100
PORT_RANGE_END = 9199

_active_processes: dict = {}  # port -> process info
_project_history: dict = {}   # port -> last known cwd
_lock = threading.Lock()


def find_available_port() -> int:
    """Find an available port in the configured range."""
    for port in range(PORT_RANGE_START, PORT_RANGE_END + 1):
        with _lock:
            if port in _active_processes:
                continue
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(("127.0.0.1", port))
                return port
        except OSError:
            continue
    raise RuntimeError("No available ports in range {}-{}".format(PORT_RANGE_START, PORT_RANGE_END))


def spawn_process(cmd: list, cwd: str, port: int, env: Optional[dict] = None,
                   timeout: int = 60, label: str = "project") -> dict:
    """
    Spawn a background process to run a project server.
    Returns status dict with port, pid, and log capture.
    """
    merged_env = {**os.environ, **(env or {})}
    merged_env["PORT"] = str(port)

    try:
        proc = subprocess.Popen(
            cmd,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=merged_env,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0,
        )

        with _lock:
            _active_processes[port] = {
                "process": proc,
                "pid": proc.pid,
                "port": port,
                "label": label,
                "cwd": cwd,
                "started_at": time.time(),
                "timeout": timeout,
            }
            _project_history[port] = cwd

        # Schedule auto-kill after timeout
        timer = threading.Timer(timeout, lambda: terminate_process(port))
        timer.daemon = True
        timer.start()

        return {
            "success": True,
            "pid": proc.pid,
            "port": port,
            "label": label,
            "message": f"Process started on port {port} (PID: {proc.pid}). Auto-terminate in {timeout}s.",
        }

    except FileNotFoundError as e:
        return {"success": False, "error": f"Command not found: {cmd[0]}. Ensure it is installed.", "detail": str(e)}
    except Exception as e:
        return {"success": False, "error": f"Failed to spawn process: {str(e)}"}


def check_health(port: int, retries: int = 10, delay: float = 1.0) -> bool:
    """
    Poll a port to see if a server is accepting connections.
    Returns True if the server responds within the retry window.
    """
    for _ in range(retries):
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=2):
                return True
        except (ConnectionRefusedError, OSError, socket.timeout):
            time.sleep(delay)
    return False


def get_process_logs(port: int, max_bytes: int = 8192) -> dict:
    """Read accumulated stdout/stderr from a running process."""
    with _lock:
        info = _active_processes.get(port)
    if not info:
        return {"stdout": "", "stderr": "", "error": "No process on this port."}

    proc = info["process"]
    stdout = ""
    stderr = ""

    try:
        if proc.stdout and proc.stdout.readable():
            stdout = proc.stdout.read(max_bytes).decode("utf-8", errors="replace") if proc.stdout.readable() else ""
    except Exception:
        pass
    try:
        if proc.stderr and proc.stderr.readable():
            stderr = proc.stderr.read(max_bytes).decode("utf-8", errors="replace") if proc.stderr.readable() else ""
    except Exception:
        pass

    return {"stdout": stdout, "stderr": stderr, "pid": proc.pid, "running": proc.poll() is None}


def terminate_process(port: int) -> dict:
    """Terminate a project server process by port."""
    with _lock:
        info = _active_processes.pop(port, None)
    if not info:
        return {"success": False, "message": f"No active process on port {port}."}

    proc = info["process"]
    try:
        if os.name == "nt":
            proc.send_signal(signal.CTRL_BREAK_EVENT)
        else:
            proc.terminate()
        proc.wait(timeout=5)
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass

    return {"success": True, "message": f"Process on port {port} (PID: {info['pid']}) terminated."}


def terminate_all():
    """Kill all active project processes."""
    with _lock:
        ports = list(_active_processes.keys())
    for port in ports:
        terminate_process(port)


def list_active() -> list:
    """List all active project processes."""
    with _lock:
        return [
            {"port": p, "pid": info["pid"], "label": info["label"],
             "uptime_s": round(time.time() - info["started_at"], 1)}
            for p, info in _active_processes.items()
        ]
