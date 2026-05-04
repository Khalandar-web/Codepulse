"""
Project Loader — Handles ZIP/folder upload extraction.
Accepts uploaded archives, extracts them to temp dirs, and provides a clean project root.
"""

import zipfile
import tempfile
import shutil
import os
from pathlib import Path


def extract_project(zip_bytes: bytes, filename: str = "project.zip") -> dict:
    """
    Extract an uploaded zip file to a temporary directory.
    Returns dict with project_root path and file listing.
    """
    tmp_dir = tempfile.mkdtemp(prefix="codepulse_project_")
    zip_path = os.path.join(tmp_dir, filename)

    try:
        with open(zip_path, "wb") as f:
            f.write(zip_bytes)

        extract_dir = os.path.join(tmp_dir, "source")
        os.makedirs(extract_dir, exist_ok=True)
        print(f"Extracting {filename} ({len(zip_bytes)} bytes) to {extract_dir}...")

        with zipfile.ZipFile(zip_path, "r") as zf:
            # Pre-filter: collect safe members only
            safe_members = []
            for member in zf.namelist():
                normalized_path = Path(member)
                if member.startswith("/") or normalized_path.is_absolute() or ".." in normalized_path.parts:
                    print(f"Skipping unsafe path: {member}")
                    continue
                safe_members.append(member)

            print(f"Extracting {len(safe_members)} files (skipped {len(zf.namelist()) - len(safe_members)})...")
            zf.extractall(extract_dir, members=safe_members)

        # If the zip contains a single root folder (ignoring metadata), descend into it
        entries = [e for e in os.listdir(extract_dir) if e not in ("__MACOSX", ".DS_Store")]
        if len(entries) == 1 and os.path.isdir(os.path.join(extract_dir, entries[0])):
            project_root = os.path.join(extract_dir, entries[0])
        else:
            project_root = extract_dir

        # Build file tree
        file_tree = _build_file_tree(project_root)

        return {
            "success": True,
            "project_root": project_root,
            "temp_dir": tmp_dir,
            "file_count": len(file_tree),
            "files": file_tree[:200],  # cap listing
        }

    except zipfile.BadZipFile:
        cleanup_project(tmp_dir)
        print(f"Error: Invalid ZIP file uploaded: {filename}")
        return {"success": False, "error": "Invalid ZIP file. Please upload a valid archive."}
    except ValueError as ve:
        cleanup_project(tmp_dir)
        print(f"Extraction security error: {str(ve)}")
        return {"success": False, "error": str(ve)}
    except Exception as e:
        cleanup_project(tmp_dir)
        print(f"Extraction unexpected error: {str(e)}")
        return {"success": False, "error": f"Extraction failed: {str(e)}"}


def _build_file_tree(root: str) -> list:
    """Walk the project root and return a flat list of relative file paths."""
    files = []
    for dirpath, dirnames, filenames in os.walk(root):
        # Skip node_modules / venvs / hidden dirs
        dirnames[:] = [d for d in dirnames if d not in ("node_modules", ".git", "__pycache__", "venv", ".venv", ".idea")]
        for fname in filenames:
            full = os.path.join(dirpath, fname)
            rel = os.path.relpath(full, root)
            size_kb = round(os.path.getsize(full) / 1024, 1)
            files.append({"path": rel.replace("\\", "/"), "size_kb": size_kb})
    return files


def cleanup_project(tmp_dir: str):
    """Remove a temporary project directory."""
    try:
        shutil.rmtree(tmp_dir, ignore_errors=True)
    except Exception:
        pass
