"""
Context management for workflow execution with secret masking and lineage telemetry.
"""
from typing import Any, Dict, Set, Optional, Iterator, List
from copy import deepcopy


class ScopedStepContext:
    """
    A step-scoped view of WorkflowContext that isolates read/write/delete telemetry
    per step, ensuring accurate data lineage even during concurrent parallel execution.
    """

    def __init__(self, parent: "WorkflowContext", step_name: str):
        self._parent = parent
        self.step_name = step_name
        self.reads: Set[str] = set()
        self.writes: Set[str] = set()
        self.deletes: Set[str] = set()

    def get_telemetry(self) -> Dict[str, List[str]]:
        return {
            "reads": sorted(list(self.reads)),
            "writes": sorted(list(self.writes)),
            "deletes": sorted(list(self.deletes)),
        }

    def mark_sensitive(self, key: str) -> None:
        self._parent.mark_sensitive(key)

    def get(self, key: str, default: Any = None) -> Any:
        self.reads.add(key)
        return self._parent.get(key, default)

    def set(self, key: str, value: Any, sensitive: bool = False) -> None:
        self.writes.add(key)
        self._parent.set(key, value, sensitive=sensitive)

    def __getitem__(self, key: str) -> Any:
        self.reads.add(key)
        return self._parent[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self.writes.add(key)
        self._parent[key] = value

    def __delitem__(self, key: str) -> None:
        self.deletes.add(key)
        del self._parent[key]

    def pop(self, key: str, *args: Any) -> Any:
        self.deletes.add(key)
        return self._parent.pop(key, *args)

    def __contains__(self, key: str) -> bool:
        self.reads.add(key)
        return key in self._parent

    def __iter__(self) -> Iterator[str]:
        return iter(self._parent)

    def __len__(self) -> int:
        return len(self._parent)

    def keys(self):
        return self._parent.keys()

    def values(self):
        return self._parent.values()

    def items(self):
        return self._parent.items()

    def update(self, other: Dict[str, Any]) -> None:
        if other:
            self.writes.update(other.keys())
        self._parent.update(other)

    def to_dict(self, mask_secrets: bool = True) -> Dict[str, Any]:
        return self._parent.to_dict(mask_secrets=mask_secrets)


class WorkflowContext:
    """
    Isolated execution context passed between workflow steps.
    Provides dictionary-like access, automatic sensitive data redacting,
    and step-scoped telemetry for live data lineage.
    """

    def __init__(self, initial_data: Optional[Dict[str, Any]] = None, sensitive_keys: Optional[Set[str]] = None):
        self._data: Dict[str, Any] = dict(initial_data or {})
        self._sensitive_keys: Set[str] = set(sensitive_keys or set())

    def scoped(self, step_name: str) -> ScopedStepContext:
        """Create a step-isolated context view for per-step access tracking."""
        return ScopedStepContext(self, step_name)

    def mark_sensitive(self, key: str) -> None:
        """Mark a context key as sensitive (will be redacted in dumps)."""
        self._sensitive_keys.add(key)

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def set(self, key: str, value: Any, sensitive: bool = False) -> None:
        self._data[key] = value
        if sensitive:
            self._sensitive_keys.add(key)

    def __getitem__(self, key: str) -> Any:
        return self._data[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self._data[key] = value

    def __delitem__(self, key: str) -> None:
        del self._data[key]

    def pop(self, key: str, *args: Any) -> Any:
        return self._data.pop(key, *args)

    def __contains__(self, key: str) -> bool:
        return key in self._data

    def __iter__(self) -> Iterator[str]:
        return iter(self._data)

    def __len__(self) -> int:
        return len(self._data)

    def keys(self):
        return self._data.keys()

    def values(self):
        return self._data.values()

    def items(self):
        return self._data.items()

    def update(self, other: Dict[str, Any]) -> None:
        self._data.update(other)

    def to_dict(self, mask_secrets: bool = True) -> Dict[str, Any]:
        """Convert to standard dict, optionally redacting sensitive values."""
        result = {}
        for k, v in self._data.items():
            is_secret = (
                k in self._sensitive_keys or
                any(secret_word in k.lower() for secret_word in ["password", "secret", "token", "api_key", "auth_token"])
            )
            if mask_secrets and is_secret and v:
                result[k] = "********"
            else:
                try:
                    from .tabular import is_polars_dataframe, to_tabular_payload
                    if is_polars_dataframe(v):
                        result[k] = to_tabular_payload(v, dataset_name=k)
                    else:
                        result[k] = deepcopy(v)
                except Exception:
                    result[k] = str(v)
        return result
