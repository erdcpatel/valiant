"""
Workflow Registry with automatic file discovery.
"""
import os
import sys
import importlib
import inspect
import re
from pathlib import Path
from typing import Dict, Any, Optional, List, Type
from .workflow import Workflow, get_global_registry
from .models import InputField


PACKAGE_TEMPLATES_DIR = (Path(__file__).resolve().parent.parent.parent / "workflows").resolve()


def _derive_workflow_id(cls_or_obj: Any, file_stem: str) -> str:
    """
    Safely derive a unique workflow identifier:
    1. If workflow_id is explicitly specified and not default base 'workflow', use it.
    2. Else if name is specified and not 'Base Workflow', convert name to snake_case.
    3. Else fallback to clean class name or file stem.
    """
    raw_id = getattr(cls_or_obj, "workflow_id", None)
    if raw_id and raw_id != "workflow":
        return str(raw_id)

    raw_name = getattr(cls_or_obj, "name", None)
    if raw_name and raw_name != "Base Workflow":
        clean_name = re.sub(r"[^a-zA-Z0-9_]+", "_", str(raw_name).strip()).lower().strip("_")
        if clean_name and clean_name != "workflow":
            return clean_name

    cls_name = cls_or_obj.__name__ if isinstance(cls_or_obj, type) else cls_or_obj.__class__.__name__
    if cls_name and cls_name not in ("Workflow", "FunctionalWorkflow"):
        clean_cls = re.sub(r"(?<!^)(?=[A-Z])", "_", cls_name).lower()
        clean_cls = re.sub(r"_workflow$", "", clean_cls).strip("_")
        if clean_cls:
            return clean_cls

    return file_stem.lower()


def is_package_template(file_path: Path) -> bool:
    """Determine whether a file is an internal template shipped with the package."""
    try:
        res = file_path.resolve()
        if not res.is_relative_to(PACKAGE_TEMPLATES_DIR):
            return False
        cwd_res = Path.cwd().resolve()
        if not res.is_relative_to(cwd_res):
            return True
        # In repo development mode, only files located directly inside PACKAGE_TEMPLATES_DIR are default templates
        return res.parent.resolve() == PACKAGE_TEMPLATES_DIR
    except Exception:
        return False


class WorkflowRegistry:
    """Central registry and discovery engine for Valiant workflows."""

    def __init__(self):
        self._workflows: Dict[str, Type[Workflow]] = {}
        self._default_workflow_ids: set = set()

    def register(self, name: str, workflow_cls: Type[Workflow], is_default: bool = False) -> None:
        self._workflows[name] = workflow_cls
        if is_default:
            self._default_workflow_ids.add(name)

    def get(self, name: str) -> Optional[Type[Workflow]]:
        # Sync with global decorator registry
        for k, v in get_global_registry().items():
            if k not in self._workflows:
                self._workflows[k] = v
        return self._workflows.get(name)

    def list_workflows(self, include_defaults: bool = True) -> Dict[str, Dict[str, Any]]:
        """Return metadata for all registered workflows."""
        for k, v in get_global_registry().items():
            if k not in self._workflows:
                self._workflows[k] = v

        result = {}
        for name, cls in self._workflows.items():
            instance = cls() if isinstance(cls, type) else cls

            # Check explicit declaration on class or instance
            explicit_default = getattr(cls, "is_default", None)
            if explicit_default is None:
                explicit_default = getattr(instance, "is_default", None)

            if explicit_default is not None:
                is_default = bool(explicit_default)
            else:
                is_default = (name in self._default_workflow_ids)

            if not include_defaults and is_default:
                continue

            steps = instance.get_steps()
            inputs = instance.inputs()
            result[name] = {
                "id": name,
                "name": getattr(cls, "name", name),
                "description": getattr(cls, "description", ""),
                "version": getattr(cls, "version", "1.0.0"),
                "author": getattr(cls, "author", None),
                "tags": getattr(cls, "tags", []),
                "is_default": is_default,
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
            candidate_dirs = []

            # 1. Environment variable: VALIANT_WORKFLOWS_DIR (supports colon, semicolon, or comma separated paths)
            env_dir = os.environ.get("VALIANT_WORKFLOWS_DIR")
            if env_dir:
                for d in re.split(r"[,;:]", env_dir):
                    d = d.strip()
                    if d:
                        candidate_dirs.append(d)

            # 2. Standard user project directories (relative to current working directory)
            cwd = Path.cwd().resolve()
            standard_dirs = [
                cwd / "workflows",
                cwd / "src" / "workflows",
                cwd / "app" / "workflows",
                cwd / "flows",
                cwd / "pipelines",
                cwd / "workflow",
                cwd / "backend" / "workflows",
            ]
            for sd in standard_dirs:
                if sd.is_dir():
                    candidate_dirs.append(str(sd))

            # 3. Built-in platform package templates (only if not explicitly hidden via VALIANT_HIDE_DEFAULTS)
            hide_defaults_env = os.environ.get("VALIANT_HIDE_DEFAULTS", "0").lower() in ("1", "true", "yes")
            if not hide_defaults_env and PACKAGE_TEMPLATES_DIR.is_dir():
                candidate_dirs.append(str(PACKAGE_TEMPLATES_DIR))

            search_dirs = []
            for cd in candidate_dirs:
                p = Path(cd)
                if cd not in search_dirs and (p.is_dir() or (p.is_file() and p.suffix == ".py")):
                    search_dirs.append(cd)

        for d in search_dirs:
            p = Path(d)
            if not p.exists():
                continue

            # Support single Python files or recursive directory scanning
            files_to_load = []
            if p.is_file() and p.suffix == ".py":
                files_to_load = [p]
            elif p.is_dir():
                for py_path in p.rglob("*.py"):
                    parts = set(py_path.parts)
                    # Ignore virtualenvs, caches, node_modules, git, and hidden directories
                    if any(ign in parts for ign in (".venv", "venv", "node_modules", "__pycache__", ".git", ".pytest_cache")):
                        continue
                    if py_path.name.startswith((".", "_")):
                        continue
                    files_to_load.append(py_path)

            if not files_to_load:
                continue

            dir_for_sys_path = p.parent if p.is_file() else p
            if str(dir_for_sys_path) not in sys.path:
                sys.path.insert(0, str(dir_for_sys_path))

            for file_path in files_to_load:
                if file_path.name.startswith("__"):
                    continue

                is_default_file = is_package_template(file_path)
                module_name = file_path.stem
                try:
                    spec = importlib.util.spec_from_file_location(module_name, str(file_path))
                    if spec and spec.loader:
                        mod = importlib.util.module_from_spec(spec)
                        sys.modules[module_name] = mod
                        spec.loader.exec_module(mod)

                        for _, obj in inspect.getmembers(mod, inspect.isclass):
                            if issubclass(obj, Workflow) and obj is not Workflow:
                                wf_id = _derive_workflow_id(obj, file_path.stem)
                                self._workflows[wf_id] = obj
                                if is_default_file:
                                    self._default_workflow_ids.add(wf_id)

                        # Also discover top-level functional Workflow instances
                        for _, obj in inspect.getmembers(mod):
                            if isinstance(obj, Workflow) and not isinstance(obj, type):
                                wf_id = _derive_workflow_id(obj, file_path.stem)
                                if wf_id:
                                    self._workflows[wf_id] = obj
                                    if is_default_file:
                                        self._default_workflow_ids.add(wf_id)
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
