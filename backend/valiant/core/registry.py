"""
Workflow Registry with automatic file discovery.
"""
import os
import sys
import importlib
import inspect
from pathlib import Path
from typing import Dict, Any, Optional, List, Type
from .workflow import Workflow, get_global_registry
from .models import InputField


class WorkflowRegistry:
    """Central registry and discovery engine for Valiant workflows."""

    def __init__(self):
        self._workflows: Dict[str, Type[Workflow]] = {}

    def register(self, name: str, workflow_cls: Type[Workflow]) -> None:
        self._workflows[name] = workflow_cls

    def get(self, name: str) -> Optional[Type[Workflow]]:
        # Sync with global decorator registry
        for k, v in get_global_registry().items():
            if k not in self._workflows:
                self._workflows[k] = v
        return self._workflows.get(name)

    def list_workflows(self) -> Dict[str, Dict[str, Any]]:
        """Return metadata for all registered workflows."""
        for k, v in get_global_registry().items():
            if k not in self._workflows:
                self._workflows[k] = v

        result = {}
        for name, cls in self._workflows.items():
            instance = cls() if isinstance(cls, type) else cls
            steps = instance.get_steps()
            inputs = instance.inputs()
            result[name] = {
                "id": name,
                "name": getattr(cls, "name", name),
                "description": getattr(cls, "description", ""),
                "version": getattr(cls, "version", "1.0.0"),
                "author": getattr(cls, "author", None),
                "tags": getattr(cls, "tags", []),
                "step_count": len(steps),
                "steps": [
                    {
                        "name": cfg.name,
                        "order": cfg.order,
                        "description": cfg.description,
                        "requires": cfg.requires,
                        "tags": cfg.tags,
                        "parallel_group": cfg.parallel_group,
                        "condition": cfg.condition,
                        "requires_approval": getattr(cfg, "requires_approval", False),
                        "approval_prompt": getattr(cfg, "approval_prompt", None),
                        "approval_roles": getattr(cfg, "approval_roles", []),
                    }
                    for cfg, _ in steps
                ],
                "inputs": [f.model_dump() for f in inputs],
                "profiles": instance.get_profiles()
            }
        return result

    def discover(self, search_dirs: Optional[List[str]] = None) -> None:
        """Scan directories and import Python modules to find workflows."""
        if search_dirs is None:
            # Default directories: backend/workflows, local cwd workflows, or VALIANT_WORKFLOWS_DIR
            project_root = Path(__file__).resolve().parent.parent.parent.parent
            candidate_dirs = [
                str(project_root / "backend" / "workflows"),
                str(project_root / "workflows"),
                str(Path.cwd() / "backend" / "workflows"),
                str(Path.cwd() / "workflows"),
            ]
            env_dir = os.environ.get("VALIANT_WORKFLOWS_DIR")
            if env_dir:
                candidate_dirs.append(env_dir)

            search_dirs = []
            for cd in candidate_dirs:
                if cd not in search_dirs and Path(cd).is_dir():
                    search_dirs.append(cd)

        for d in search_dirs:
            p = Path(d)
            if not p.exists() or not p.is_dir():
                continue

            if str(p.parent) not in sys.path:
                sys.path.insert(0, str(p.parent))

            for file_path in p.glob("*.py"):
                if file_path.name.startswith("__"):
                    continue

                module_name = file_path.stem
                try:
                    spec = importlib.util.spec_from_file_location(module_name, str(file_path))
                    if spec and spec.loader:
                        mod = importlib.util.module_from_spec(spec)
                        sys.modules[module_name] = mod
                        spec.loader.exec_module(mod)

                        for _, obj in inspect.getmembers(mod, inspect.isclass):
                            if issubclass(obj, Workflow) and obj is not Workflow:
                                wf_id = getattr(obj, "workflow_id", obj.__name__)
                                self._workflows[wf_id] = obj

                        # Also discover top-level functional Workflow instances
                        for _, obj in inspect.getmembers(mod):
                            if isinstance(obj, Workflow) and not isinstance(obj, type):
                                wf_id = getattr(obj, "workflow_id", getattr(obj, "name", None))
                                if wf_id:
                                    self._workflows[wf_id] = obj
                except Exception as e:
                    print(f"[Registry Discovery Error] {file_path.name}: {e}")

        # Also pull from global registry
        for k, v in get_global_registry().items():
            if k not in self._workflows:
                self._workflows[k] = v

    def get_instance(self, name: str) -> Optional[Workflow]:
        """Retrieve a ready-to-run instance of a workflow by name."""
        wf = self.get(name)
        if wf is None:
            return None
        if isinstance(wf, type):
            return wf()
        return wf


# Singleton instance
registry = WorkflowRegistry()
