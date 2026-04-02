"""
Valiant v3 — entry point.

Usage:
    python main.py run demo --set name=Alice
    python main.py list
    python main.py history
    python main.py serve
    python main.py serve --api-only
    python main.py serve --ui-only
"""
import sys
from pathlib import Path

# Ensure src/ is on the path when running directly (without pip install)
sys.path.insert(0, str(Path(__file__).parent / "src"))

from valiant.cli.app import app

if __name__ == "__main__":
    app()
