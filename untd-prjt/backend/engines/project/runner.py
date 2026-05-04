"""
Project Runner — Orchestrates detection, installation, and execution of full-stack projects.
Ties together the detector, process_manager, and loader modules.
"""

import os
import subprocess
import sys
import time
import http.server
import threading
from pathlib import Path

from engines.project.detector import detect_project_type
from engines.project.process_manager import find_available_port, spawn_process, check_health


def run_project(project_root: str, timeout: int = 120) -> dict:
    """
    Detect, install dependencies, and run a project.
    Returns a status dict with port, logs, and health check result.
    """
    # 1. Detect project type
    detection = detect_project_type(project_root)
    project_type = detection.get("type", "unknown")

    if project_type == "unknown":
        return {
            "success": False,
            "project_type": detection,
            "error": "Could not determine project type. Ensure your project has a recognizable entry point (index.html, package.json, app.py, manage.py, index.php).",
        }

    # 2. Get actual root (where entry point was found)
    actual_root = detection.get("actual_root", project_root)

    # 3. Allocate port
    try:
        port = find_available_port()
    except RuntimeError as e:
        return {"success": False, "project_type": detection, "error": str(e)}

    # 4. Install dependencies (if needed)
    install_log = ""
    install_cmd = detection.get("install_cmd")
    if install_cmd and _needs_install(actual_root, project_type):
        install_result = _run_install(install_cmd, actual_root)
        install_log = install_result.get("log", "")
        if not install_result.get("success"):
            print(f"Warning: Dependency installation failed for {project_type}. Attempting to run anyway...")
            install_log += f"\n\n!!! WARNING: INSTALLATION FAILED !!!\nTrying to execute project with existing environment...\n"

    # 5. Execute project
    print(f"Executing {project_type} project on port {port}...")
    if project_type == "static":
        result = _serve_static(actual_root, port, detection, timeout)
    elif project_type == "nodejs":
        result = _run_node(actual_root, port, detection, timeout)
    elif project_type in ("python_flask", "python_django"):
        result = _run_python(actual_root, port, detection, timeout)
    elif project_type == "php":
        result = _run_php(actual_root, port, detection, timeout)
    else:
        result = {"success": False, "error": f"Execution not implemented for type: {project_type}"}

    if not result.get("success"):
        print(f"Execution error: {result.get('error')}")
    else:
        print(f"Project started successfully on port {port}")

    result["project_type"] = detection
    result["install_log"] = install_log
    return result


def _needs_install(project_root: str, project_type: str) -> bool:
    """Check if dependency installation is needed."""
    if project_type == "nodejs":
        return not os.path.isdir(os.path.join(project_root, "node_modules"))
    if project_type in ("python_flask", "python_django"):
        return os.path.isfile(os.path.join(project_root, "requirements.txt"))
    return False


def _run_install(cmd: str, cwd: str) -> dict:
    """Run an install command synchronously."""
    try:
        result = subprocess.run(
            cmd.split(),
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=120,
            env={**os.environ, "NODE_ENV": "development"},
        )
        return {
            "success": result.returncode == 0,
            "log": (result.stdout + "\n" + result.stderr)[:5000],
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "log": "Installation timed out after 120 seconds."}
    except FileNotFoundError:
        return {"success": False, "log": f"Command not found: {cmd.split()[0]}"}
    except Exception as e:
        return {"success": False, "log": str(e)}


def _serve_static(project_root: str, port: int, detection: dict, timeout: int) -> dict:
    """Serve a static HTML project using Python's built-in HTTP server as a subprocess."""
    entry = detection.get("entry_file", "index.html")
    serve_dir = project_root

    # If entry_file is in a subdir, serve from that subdir
    if "/" in entry:
        serve_dir = os.path.join(project_root, os.path.dirname(entry))

    # Command to run the static server as a process
    # Use sys.executable to ensure we use the same python environment
    cmd = [sys.executable, "-m", "http.server", str(port), "--directory", serve_dir, "--bind", "127.0.0.1"]
    
    result = spawn_process(cmd, serve_dir, port, timeout=timeout, label="Static Web")

    if result.get("success"):
        healthy = check_health(port, retries=10, delay=1.0)
        result["health"] = healthy
        result["url"] = f"http://localhost:{port}"
        result["mode"] = "real"
        if not healthy:
            result["warning"] = "Static server started but health check failed."

    return result


def _run_node(project_root: str, port: int, detection: dict, timeout: int) -> dict:
    """Run a Node.js project."""
    run_cmd = detection.get("run_cmd", "npm start")
    cmd = run_cmd.split()
    if os.name == "nt":
        cmd = ["cmd", "/c"] + cmd

    result = spawn_process(cmd, project_root, port, timeout=timeout, label=detection.get("framework", "Node.js"))

    if result.get("success"):
        healthy = check_health(port, retries=15, delay=2.0)
        result["health"] = healthy
        result["url"] = f"http://localhost:{port}"
        result["mode"] = "real"
        if not healthy:
            result["warning"] = "Server started but health check failed. It may still be booting."

    return result


def _run_python(project_root: str, port: int, detection: dict, timeout: int) -> dict:
    """Run a Python Flask/Django/Generic project."""
    project_type = detection.get("type")
    entry_file = detection.get("entry_file", "app.py")

    if project_type == "python_django":
        cmd = [sys.executable, entry_file, "runserver", f"0.0.0.0:{port}"]
    else:
        cmd = [sys.executable, entry_file]

    env = {"FLASK_RUN_PORT": str(port), "FLASK_ENV": "development"}

    result = spawn_process(cmd, project_root, port, env=env, timeout=timeout,
                           label=detection.get("label", "Python"))

    if result.get("success"):
        healthy = check_health(port, retries=10, delay=2.0)
        result["health"] = healthy
        result["url"] = f"http://localhost:{port}"
        result["mode"] = "real"

    return result


def _run_php(project_root: str, port: int, detection: dict, timeout: int) -> dict:
    """Run a PHP built-in server."""
    cmd = ["php", "-S", f"0.0.0.0:{port}"]

    result = spawn_process(cmd, project_root, port, timeout=timeout, label="PHP")

    if result.get("success"):
        healthy = check_health(port, retries=8, delay=1.5)
        result["health"] = healthy
        result["url"] = f"http://localhost:{port}"
        result["mode"] = "real"

    return result
