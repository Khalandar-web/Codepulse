"""
Project Detector — Identifies the project type/stack from its file structure.
Supports: Static (HTML/CSS/JS), Node.js/React, Python (Flask/Django), PHP.
"""

import os
import json
from pathlib import Path


# Detection priority (first match wins)
DETECTION_RULES = [
    {
        "type": "nodejs",
        "label": "Node.js Application",
        "indicators": ["package.json", "index.js", "server.js", "app.js"],
        "run_cmd": "node index.js", # Overridden below if package.json exists
        "install_cmd": "npm install",
    },
    {
        "type": "python_flask",
        "label": "Python Flask/Generic Application",
        "indicators": ["app.py", "wsgi.py", "main.py"],
        "secondary": ["requirements.txt", "Pipfile"],
        "run_cmd": "python app.py", # Overridden dynamically
        "install_cmd": "pip install --prefer-binary -r requirements.txt",
    },
    {
        "type": "python_django",
        "label": "Python Django Application",
        "indicators": ["manage.py"],
        "secondary": ["requirements.txt"],
        "run_cmd": "python manage.py runserver 0.0.0.0:{port}",
        "install_cmd": "pip install --prefer-binary -r requirements.txt",
    },
    {
        "type": "php",
        "label": "PHP Application",
        "indicators": ["index.php"],
        "run_cmd": "php -S 0.0.0.0:{port}",
        "install_cmd": None,
    },
    {
        "type": "static",
        "label": "Static Web Application (HTML/CSS/JS)",
        "indicators": ["index.html"],
        "run_cmd": None,  # served by built-in static server
        "install_cmd": None,
    },
]


def detect_project_type(project_root: str) -> dict:
    """
    Analyze the project root directory and return the detected project type
    with execution instructions.
    """
    if not os.path.isdir(project_root):
        return {"type": "unknown", "label": "Unknown", "error": "Project root not found."}

    root_files = set(os.listdir(project_root))

    for rule in DETECTION_RULES:
        indicators = rule.get("indicators", [])
        matched_ind = next((ind for ind in indicators if ind in root_files), None)
        if matched_ind:
            result = {
                "type": rule["type"],
                "label": rule["label"],
                "run_cmd": rule.get("run_cmd"),
                "install_cmd": rule.get("install_cmd"),
                "entry_file": matched_ind,
                "actual_root": project_root,
            }

            # Enhance detection for Node.js (check if React/Next/Vite)
            if rule["type"] == "nodejs":
                result["framework"] = _detect_node_framework(project_root)
                if matched_ind != "package.json":
                    result["run_cmd"] = f"node {matched_ind}"
                else:
                    result["run_cmd"] = "npm start"

            return result

    # Fallback: check for any HTML, PY, or JS files deeper in the tree
    for dirpath, dirnames, filenames in os.walk(project_root):
        # Skip common non-source directories
        dirnames[:] = [d for d in dirnames if d not in ("node_modules", ".git", "__pycache__", "venv", ".venv", "dist", "build", ".next")]
        
        rel_dir = os.path.relpath(dirpath, project_root)
        if rel_dir == ".": rel_dir = ""

        # Check standard web
        for f in filenames:
            if f.lower() == "index.html":
                return {
                    "type": "static",
                    "label": "Static Web Application (HTML)",
                    "run_cmd": None,
                    "install_cmd": None,
                    "entry_file": f,
                    "actual_root": dirpath,
                }
                
        # Check python
        for f in filenames:
            if f in ("app.py", "main.py", "wsgi.py", "manage.py"):
                is_django = f == "manage.py"
                return {
                    "type": "python_django" if is_django else "python_flask",
                    "label": "Python Application",
                    "run_cmd": f"python {f}" if not is_django else "python manage.py runserver 0.0.0.0:{port}",
                    "install_cmd": "pip install -r requirements.txt" if "requirements.txt" in filenames else None,
                    "entry_file": f,
                    "actual_root": dirpath,
                }

        # Check JS/Node
        for f in filenames:
            if f in ("package.json", "server.js", "app.js", "index.js"):
                return {
                    "type": "nodejs",
                    "label": "Node.js Application",
                    "run_cmd": "npm start" if f == "package.json" else f"node {f}",
                    "install_cmd": "npm install" if f == "package.json" else None,
                    "entry_file": f,
                    "actual_root": dirpath,
                }
    

    return {"type": "unknown", "label": "Unrecognized project structure"}


def _detect_node_framework(project_root: str) -> str:
    """Check package.json for known frameworks."""
    pkg_path = os.path.join(project_root, "package.json")
    try:
        with open(pkg_path, "r", encoding="utf-8") as f:
            pkg = json.load(f)
        deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
        if "next" in deps:
            return "Next.js"
        if "react-scripts" in deps:
            return "Create React App"
        if "vite" in deps:
            return "Vite"
        if "vue" in deps:
            return "Vue.js"
        if "express" in deps:
            return "Express.js"
        return "Node.js"
    except Exception:
        return "Node.js"
