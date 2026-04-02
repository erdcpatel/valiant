"""
WorkflowRegistry — discovers and manages registered workflow classes.

Workflows are auto-registered via @workflow decorator on import.
The registry also supports loading workflows from configured directories.
"""
from __future__ import annotations

import importlib
import importlib.util
import sys
from pathlib import Path
from typing import Any

import structlog

from valiant.core.exceptions import WorkflowNotFoundError
from valiant.core.models import InputField, WorkflowMeta
from valiant.core.workflow import Workflow, get_registered_workflows

log = structlog.get_logger(__name__)

# Built-in workflow module paths — always loaded
_BUILTIN_MODULES = [
    "valiant.workflows.demo",
    "valiant.workflows.user_management",
]


class WorkflowRegistry:
    """
    Central registry for all available workflows.

    Usage::

        registry = WorkflowRegistry()
        registry.load_builtins()

        meta = registry.get_meta("demo")
        cls  = registry.get_class("demo")
    """

    def __init__(self) -> None:
        self._loaded = False

    def load_builtins(self) -> None:
        """Import built-in workflow modules so @workflow decorators fire."""
        for module_path in _BUILTIN_MODULES:
            try:
                importlib.import_module(module_path)
                log.debug("registry.loaded_module", module=module_path)
            except ImportError as exc:
                log.warning("registry.skip_module", module=module_path, error=str(exc))
        self._loaded = True

    def load_directory(self, directory: str | Path) -> int:
        """
        Scan a directory for Python files and import them.
        Returns the count of newly imported modules.
        """
        path = Path(directory)
        if not path.is_dir():
            log.warning("registry.dir_not_found", directory=str(directory))
            return 0

        count = 0
        for py_file in sorted(path.glob("*.py")):
            if py_file.name.startswith("_"):
                continue
            module_name = f"_valiant_user_{py_file.stem}"
            spec = importlib.util.spec_from_file_location(module_name, py_file)
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                sys.modules[module_name] = module
                try:
                    spec.loader.exec_module(module)  # type: ignore[union-attr]
                    count += 1
                    log.debug("registry.loaded_file", file=str(py_file))
                except Exception as exc:
                    log.error("registry.load_error", file=str(py_file), error=str(exc))
        return count

    # ── Accessors ──────────────────────────────────────────────────────────────

    def all_classes(self) -> dict[str, type[Workflow]]:
        return get_registered_workflows()

    def get_class(self, name: str) -> type[Workflow]:
        workflows = get_registered_workflows()
        if name not in workflows:
            raise WorkflowNotFoundError(name)
        return workflows[name]

    def get_meta(self, name: str) -> WorkflowMeta:
        cls = self.get_class(name)
        instance = cls()
        return WorkflowMeta(
            name=name,
            description=getattr(cls, "_workflow_description", ""),
            tags=getattr(cls, "_workflow_tags", []),
            version=getattr(cls, "_workflow_version", "1.0.0"),
            input_fields=instance.get_input_fields(),
        )

    def list_meta(self) -> list[WorkflowMeta]:
        return [self.get_meta(name) for name in sorted(self.all_classes().keys())]

    def names(self) -> list[str]:
        return sorted(self.all_classes().keys())

    def __len__(self) -> int:
        return len(self.all_classes())

    def __contains__(self, name: str) -> bool:
        return name in self.all_classes()


# Module-level singleton
registry = WorkflowRegistry()
