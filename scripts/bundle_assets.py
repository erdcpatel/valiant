#!/usr/bin/env python3
"""
Bundle frontend assets into the backend package for distribution.
Copies `frontend/dist/` into `backend/valiant/web/` so that `valiant serve`
works out-of-the-box when installed as a Python package from PyPI (`valiantflow`).
"""
import os
import shutil
import subprocess
import sys
from pathlib import Path


def bundle_assets():
    repo_root = Path(__file__).resolve().parent.parent
    frontend_dir = repo_root / "frontend"
    frontend_dist = frontend_dir / "dist"
    target_web_dir = repo_root / "backend" / "valiant" / "web"

    # Build frontend if dist does not exist
    if not (frontend_dist / "index.html").exists():
        print("Frontend dist not found. Building frontend assets...")
        npm_bin = shutil.which("npm")
        if not npm_bin:
            print("ERROR: npm not found in PATH. Please build frontend manually.", file=sys.stderr)
            sys.exit(1)
        subprocess.run([npm_bin, "run", "build"], cwd=frontend_dir, check=True)

    # Clean existing target directory
    if target_web_dir.exists():
        shutil.rmtree(target_web_dir)
    target_web_dir.mkdir(parents=True, exist_ok=True)

    # Copy frontend dist to backend/valiant/web
    print(f"Bundling assets from {frontend_dist} -> {target_web_dir}...")
    for item in frontend_dist.iterdir():
        dest = target_web_dir / item.name
        if item.is_dir():
            shutil.copytree(item, dest)
        else:
            shutil.copy2(item, dest)

    # Create a .gitkeep or __init__.py if desired, but index.html is the indicator
    if (target_web_dir / "index.html").exists():
        print(f"Successfully bundled frontend assets ({sum(1 for _ in target_web_dir.rglob('*'))} files).")
    else:
        print("ERROR: Failed to bundle frontend assets: index.html missing.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    bundle_assets()
