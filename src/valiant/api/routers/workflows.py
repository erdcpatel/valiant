from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from valiant.api.auth import require_api_key
from valiant.api.schemas import InputFieldResponse, WorkflowDetailResponse, WorkflowSummaryResponse
from valiant.core.exceptions import WorkflowNotFoundError
from valiant.core.registry import registry
from valiant.core.workflow import Workflow

router = APIRouter(prefix="/workflows", tags=["workflows"])


def _step_count(cls: type[Workflow]) -> int:
    return len(cls.discover_steps())


def _to_summary(name: str) -> WorkflowSummaryResponse:
    meta = registry.get_meta(name)
    cls = registry.get_class(name)
    return WorkflowSummaryResponse(
        name=meta.name,
        description=meta.description,
        tags=meta.tags,
        version=meta.version,
        step_count=_step_count(cls),
    )


def _to_detail(name: str) -> WorkflowDetailResponse:
    meta = registry.get_meta(name)
    cls = registry.get_class(name)
    fields = [
        InputFieldResponse(
            name=f.name,
            label=f.display_label(),
            type=f.type.value,
            required=f.required,
            default=f.default,
            description=f.description,
            options=f.options,
            sensitive=f.sensitive,
        )
        for f in meta.input_fields
    ]
    return WorkflowDetailResponse(
        name=meta.name,
        description=meta.description,
        tags=meta.tags,
        version=meta.version,
        step_count=_step_count(cls),
        input_fields=fields,
    )


@router.get("", response_model=list[WorkflowSummaryResponse])
def list_workflows(_key: str = Depends(require_api_key)) -> list[WorkflowSummaryResponse]:
    return [_to_summary(name) for name in registry.names()]


@router.get("/{name}", response_model=WorkflowDetailResponse)
def get_workflow(name: str, _key: str = Depends(require_api_key)) -> WorkflowDetailResponse:
    try:
        return _to_detail(name)
    except WorkflowNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
