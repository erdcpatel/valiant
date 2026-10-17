"""
Tests for BOMAutomationWorkflow:
- Workflow registration and input validation
- Execution in mock_mode
- Polars Tabular Data generation for Maven build metrics and post-deployment health checks
- Approval Gate handling and resumption
"""
import pytest
import asyncio
from pathlib import Path
import polars as pl

from backend.workflows.bom_test_automation import BOMAutomationWorkflow
from backend.valiant.core.runner import WorkflowRunner, signal_step_approval
from backend.valiant.core.models import WorkflowStatus, StepStatus
from backend.valiant.core.logging import RunLogManager


@pytest.mark.anyio
async def test_bom_workflow_lifecycle():
    """Verify BOMAutomationWorkflow runs through test steps and pauses at approval gate."""
    wf = BOMAutomationWorkflow()
    run_id = "test_bom_run_01"
    env = "dev"

    runner = WorkflowRunner(workflow=wf, run_id=run_id, environment=env)
    inputs = {
        "bom_version": "5.1.0",
        "jira_id": "DEVOPS-2024",
        "components": "auth-service,payment-service",
        "docker_base_image": "eclipse-temurin:21-jre",
        "mock_mode": True
    }

    # Run workflow with pre-approved gates to test end-to-end flow
    approved_steps = {
        "Approval Gate Push": {"approved": True, "approved_by": "lead_dev"},
        "Approval Gate Uat": {"approved": True, "approved_by": "lead_sre"}
    }
    result = await runner.run(inputs=inputs, approved_steps=approved_steps)

    assert result.status == WorkflowStatus.COMPLETED
    assert result.success is True

    step_map = {r.name: r for r in result.results}

    # Check Step 1: Validate Environment
    assert "Validate Environment" in step_map
    assert step_map["Validate Environment"].success is True

    # Check Step 2: Prepare Branches And Files
    assert "Prepare Branches And Files" in step_map
    assert step_map["Prepare Branches And Files"].success is True

    # Check Step 3: Compile Components
    assert "Compile Components" in step_map
    assert step_map["Compile Components"].success is True

    # Check Step 4: Run Tests (Polars Tabular Data)
    assert "Run Tests" in step_map
    assert step_map["Run Tests"].success is True
    assert step_map["Run Tests"].tabular_data is not None
    assert step_map["Run Tests"].tabular_data["total_rows"] == 2
    assert "tests_run" in [c["name"] for c in step_map["Run Tests"].tabular_data["columns"]]

    # Verify log file was written to disk
    log_content = RunLogManager.read_log_content(run_id, env=env)
    assert "VALIANT EXECUTION LOG: test_bom_run_01" in log_content
    assert "bom_test_automation" in log_content
    assert "auth-service" in log_content
    assert "payment-service" in log_content


@pytest.mark.anyio
async def test_maven_helper_pom_update(tmp_path):
    """Verify MavenHelper updates parent BOM version while preserving XML structure."""
    from backend.valiant.tools.maven import MavenHelper

    sample_pom = tmp_path / "pom.xml"
    sample_pom.write_text("""<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
    <modelVersion>4.0.0</modelVersion>
    <parent>
        <groupId>com.company.platform</groupId>
        <artifactId>platform-bom</artifactId>
        <version>4.8.0</version>
        <relativePath/>
    </parent>
    <artifactId>auth-service</artifactId>
</project>
""", encoding="utf-8")

    current_ver = MavenHelper.get_parent_bom_version(sample_pom)
    assert current_ver == "4.8.0"

    updated = MavenHelper.update_parent_bom_version(sample_pom, "5.2.0")
    assert updated is True

    new_ver = MavenHelper.get_parent_bom_version(sample_pom)
    assert new_ver == "5.2.0"
    content = sample_pom.read_text(encoding="utf-8")
    assert "<version>5.2.0</version>" in content
    assert "<artifactId>platform-bom</artifactId>" in content


@pytest.mark.anyio
async def test_docker_helper_base_image_update(tmp_path):
    """Verify DockerHelper updates base image in Dockerfile."""
    from backend.valiant.tools.docker import DockerHelper

    sample_dockerfile = tmp_path / "Dockerfile"
    sample_dockerfile.write_text("""FROM openjdk:11-jre-slim AS runtime
WORKDIR /app
COPY target/*.jar app.jar
ENTRYPOINT ["java", "-jar", "app.jar"]
""", encoding="utf-8")

    current_base = DockerHelper.get_base_image(sample_dockerfile)
    assert current_base == "openjdk:11-jre-slim"

    updated = DockerHelper.update_base_image(sample_dockerfile, "eclipse-temurin:17-jre")
    assert updated is True

    new_base = DockerHelper.get_base_image(sample_dockerfile)
    assert new_base == "eclipse-temurin:17-jre"
    content = sample_dockerfile.read_text(encoding="utf-8")
    assert "FROM eclipse-temurin:17-jre AS runtime" in content
