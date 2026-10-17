"""
Cross-platform Git automation utilities for local desktop workflows.
"""
import os
import subprocess
import shutil
from pathlib import Path
from typing import Tuple, Optional, Union, List


class GitHelper:
    """Helper methods for local Git operations using system git executable."""

    @staticmethod
    def _git_cmd() -> str:
        git_bin = shutil.which("git")
        if not git_bin:
            raise FileNotFoundError("Git executable not found in PATH")
        return git_bin

    @classmethod
    def run_git(cls, args: List[str], cwd: Union[str, Path]) -> subprocess.CompletedProcess:
        """Run a git command synchronously returning CompletedProcess."""
        git_bin = cls._git_cmd()
        cmd = [git_bin] + args
        return subprocess.run(
            cmd,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace"
        )

    @classmethod
    def is_git_repo(cls, path: Union[str, Path]) -> bool:
        """Check if target path is a valid Git repository root or worktree."""
        target = Path(path)
        if not target.exists():
            return False
        res = cls.run_git(["rev-parse", "--is-inside-work-tree"], cwd=target)
        return res.returncode == 0 and "true" in res.stdout.lower()

    @classmethod
    def is_clean(cls, path: Union[str, Path]) -> Tuple[bool, str]:
        """Check if working tree has no uncommitted changes."""
        res = cls.run_git(["status", "--porcelain"], cwd=path)
        if res.returncode != 0:
            return False, f"Git error: {res.stderr.strip()}"
        output = res.stdout.strip()
        return (len(output) == 0), output

    @classmethod
    def get_head_commit(cls, path: Union[str, Path], short: bool = True) -> str:
        """Retrieve current HEAD commit hash."""
        args = ["rev-parse", "--short", "HEAD"] if short else ["rev-parse", "HEAD"]
        res = cls.run_git(args, cwd=path)
        if res.returncode != 0:
            raise RuntimeError(f"Failed to get HEAD commit: {res.stderr.strip()}")
        return res.stdout.strip()

    @classmethod
    def get_current_branch(cls, path: Union[str, Path]) -> str:
        """Retrieve active branch name."""
        res = cls.run_git(["rev-parse", "--abbrev-ref", "HEAD"], cwd=path)
        if res.returncode != 0:
            raise RuntimeError(f"Failed to get branch: {res.stderr.strip()}")
        return res.stdout.strip()

    @classmethod
    def create_and_checkout_branch(
        cls,
        path: Union[str, Path],
        branch_name: str,
        base_branch: str = "main"
    ) -> Tuple[bool, str]:
        """Checkout base branch, pull latest, and create/checkout new feature branch."""
        # 1. Checkout base branch
        c1 = cls.run_git(["checkout", base_branch], cwd=path)
        if c1.returncode != 0:
            return False, f"Failed to checkout {base_branch}: {c1.stderr.strip()}"

        # 2. Pull latest
        cls.run_git(["pull", "--rebase"], cwd=path)

        # 3. Create and checkout new branch
        c3 = cls.run_git(["checkout", "-B", branch_name], cwd=path)
        if c3.returncode != 0:
            return False, f"Failed to create branch {branch_name}: {c3.stderr.strip()}"

        return True, f"Successfully checked out branch {branch_name}"

    @classmethod
    def commit_and_push(
        cls,
        path: Union[str, Path],
        commit_msg: str,
        branch_name: Optional[str] = None,
        remote: str = "origin"
    ) -> Tuple[bool, str]:
        """Stage all changes, commit with message, and push to remote."""
        # 1. Stage all
        s1 = cls.run_git(["add", "-A"], cwd=path)
        if s1.returncode != 0:
            return False, f"Failed to stage changes: {s1.stderr.strip()}"

        # 2. Commit
        s2 = cls.run_git(["commit", "-m", commit_msg], cwd=path)
        if s2.returncode != 0 and "nothing to commit" not in s2.stdout.lower():
            return False, f"Failed to commit: {s2.stderr.strip()}"

        # 3. Push
        target_branch = branch_name or cls.get_current_branch(path)
        s3 = cls.run_git(["push", "-u", remote, target_branch], cwd=path)
        if s3.returncode != 0:
            return False, f"Failed to push to {remote}/{target_branch}: {s3.stderr.strip()}"

        commit_hash = cls.get_head_commit(path, short=False)
        return True, commit_hash
