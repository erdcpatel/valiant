"""
Dockerfile parsing and base image automation utilities.
"""
import re
from pathlib import Path
from typing import Optional, Union


class DockerHelper:
    """Helper methods for Dockerfile inspection and base image updates."""

    @staticmethod
    def get_base_image(dockerfile_path: Union[str, Path]) -> Optional[str]:
        """Extract the first base image name from FROM instruction in Dockerfile."""
        path = Path(dockerfile_path)
        if not path.exists():
            return None
        content = path.read_text(encoding="utf-8")
        match = re.search(r"^\s*FROM\s+([^\s]+)", content, re.MULTILINE | re.IGNORECASE)
        return match.group(1) if match else None

    @staticmethod
    def update_base_image(dockerfile_path: Union[str, Path], new_base_image: str) -> bool:
        """
        Update the base image in Dockerfile FROM instruction while preserving
        platform flags and AS build aliases.
        """
        path = Path(dockerfile_path)
        if not path.exists():
            return False

        content = path.read_text(encoding="utf-8")
        # Match FROM [--platform=...] <old_image> [AS <alias>]
        pattern = r"(^\s*FROM\s+(?:--platform=[^\s]+\s+)?)([^\s]+)(\s*(?:AS\s+[^\s]+)?)"

        def repl(match):
            prefix = match.group(1)
            alias = match.group(3) or ""
            return f"{prefix}{new_base_image.strip()}{alias}"

        updated, count = re.subn(pattern, repl, content, count=1, flags=re.MULTILINE | re.IGNORECASE)
        if count > 0:
            path.write_text(updated, encoding="utf-8")
            return True
        return False
