"""
Automated Pytest for Human-in-the-Loop Breakpoints and Manual Approvals.
Verifies execution suspension, operator approval resumption, and rejection halting.
"""
import pytest
import asyncio
from fastapi.testclient import TestClient

from backend.valiant.api.app import app
from backend.valiant.core.runner import WorkflowRunner, get_active_runner, signal_step_approval
from backend.valiant.core.models import StepStatus, WorkflowStatus
from backend.workflows.infrastructure_deployment import InfrastructureDeploymentWorkflow
from backend.valiant.db.database import get_run_by_id, init_db


def test_step_suspension_and_approval_resumption():
    async def _async_test():
        init_db("dev")
        wf = InfrastructureDeploymentWorkflow()
        runner = WorkflowRunner(workflow=wf, environment="dev")

        run_task = asyncio.create_task(runner.run(inputs={"target_cloud": "aws-us-east-1"}))
        await asyncio.sleep(0.4)

        assert "Provision Live Cloud Infrastructure" in runner.initial_steps[2]["name"]
        assert get_active_runner(runner.run_id) is not None

        signaled = signal_step_approval(
            run_id=runner.run_id,
            step_name="Provision Live Cloud Infrastructure",
            approved=True,
            approver="senior_sre@valiant.internal",
            notes="Validated AWS VPC CIDR and security groups"
        )
        assert signaled is True

        result = await asyncio.wait_for(run_task, timeout=5.0)
        assert result.status == WorkflowStatus.COMPLETED
        assert result.success is True

        step_3 = next(s for s in result.results if s.name == "Provision Live Cloud Infrastructure")
        assert step_3.status == StepStatus.SUCCESS
        assert step_3.requires_approval is True
        assert step_3.approved_by == "senior_sre@valiant.internal"
        assert "Validated AWS VPC" in (step_3.approval_notes or "")

        step_4 = next(s for s in result.results if s.name == "Deploy Application Services")
        assert step_4.status == StepStatus.SUCCESS

    asyncio.run(_async_test())


def test_step_rejection_halts_workflow():
    async def _async_test():
        init_db("dev")
        wf = InfrastructureDeploymentWorkflow()
        runner = WorkflowRunner(workflow=wf, environment="dev")

        run_task = asyncio.create_task(runner.run(inputs={"target_cloud": "gcp-us-central1"}))
        await asyncio.sleep(0.4)

        signaled = signal_step_approval(
            run_id=runner.run_id,
            step_name="Provision Live Cloud Infrastructure",
            approved=False,
            approver="security_audit@valiant.internal",
            notes="Security group port 22 open to 0.0.0.0/0 forbidden"
        )
        assert signaled is True

        result = await asyncio.wait_for(run_task, timeout=5.0)
        assert result.success is False
        step_3 = next(s for s in result.results if s.name == "Provision Live Cloud Infrastructure")
        assert step_3.status == StepStatus.REJECTED
        assert "Security group port 22 open" in step_3.message

        step_4_executed = any(s.name == "Deploy Application Services" and s.executed for s in result.results)
        assert step_4_executed is False

    asyncio.run(_async_test())


def test_api_approval_endpoints():
    async def _async_test():
        init_db("dev")
        wf = InfrastructureDeploymentWorkflow()
        runner = WorkflowRunner(workflow=wf, environment="dev")

        run_task = asyncio.create_task(runner.run(inputs={"target_cloud": "azure-eastus"}))
        await asyncio.sleep(0.4)

        with TestClient(app) as client:
            # 1. Inspect run detail via API
            get_res = client.get(f"/api/runs/{runner.run_id}", headers={"X-Valiant-Env": "dev"})
            assert get_res.status_code == 200
            data = get_res.json()["data"]
            assert data["status"] == "waiting_approval"

            # 2. Call approve API endpoint
            appr_res = client.post(
                f"/api/runs/{runner.run_id}/steps/Provision Live Cloud Infrastructure/approve",
                json={"notes": "Approved for Azure rollout", "approver": "sre_lead"},
                headers={"X-Valiant-Env": "dev"}
            )
            assert appr_res.status_code == 200
            assert appr_res.json()["success"] is True
            assert appr_res.json()["status"] == "approved"

        result = await asyncio.wait_for(run_task, timeout=5.0)
        assert result.status == WorkflowStatus.COMPLETED
        assert result.success is True

    asyncio.run(_async_test())

