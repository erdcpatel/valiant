"""
Infrastructure Deployment Workflow with Manual Operator Approval Breakpoint.
Demonstrates Human-in-the-Loop approval gate before critical cloud provisioning.
"""
from typing import Dict, Any, List
import time

from backend.valiant import (
    Workflow,
    step,
    workflow,
    InputField,
    InputType,
    WorkflowContext,
    StepResult,
)


@workflow(
    name="infrastructure_deployment",
    description="Multi-tier cloud deployment pipeline with Human-in-the-Loop approval before live provisioning",
    tags=["infra", "cloud", "security", "approval"]
)
class InfrastructureDeploymentWorkflow(Workflow):
    workflow_id = "infrastructure_deployment"
    name = "Cloud Infrastructure Provisioning"
    description = "Multi-tier cloud deployment pipeline with Human-in-the-Loop approval before live provisioning"
    version = "1.0.0"
    author = "DevOps Platform Team"
    tags = ["infra", "cloud", "security", "approval"]

    def inputs(self) -> List[InputField]:
        return [
            InputField(
                name="target_cloud",
                type=InputType.SELECT,
                label="Target Cloud Provider",
                default="aws-us-east-1",
                options=["aws-us-east-1", "aws-eu-west-1", "gcp-us-central1", "azure-eastus"],
                help_text="Target public cloud region for infrastructure deployment"
            ),
            InputField(
                name="cluster_size",
                type=InputType.SELECT,
                label="Cluster Topology Size",
                default="production-ha-3node",
                options=["sandbox-single-node", "staging-2node", "production-ha-3node", "enterprise-multi-region"],
                help_text="Node capacity and auto-scaling boundary profile"
            ),
            InputField(
                name="auto_rollback",
                type=InputType.CHECKBOX,
                label="Auto Rollback on Smoke Test Failure",
                default=True,
                help_text="Trigger immediate infrastructure rollback if health checks fail"
            ),
            InputField(
                name="notification_channel",
                type=InputType.TEXT,
                label="Alerts Channel",
                default="#platform-infra-deployments",
                help_text="Slack or Teams channel for real-time deployment notifications"
            )
        ]

    def get_profiles(self) -> Dict[str, Dict[str, Any]]:
        return {
            "dev": {
                "target_cloud": "aws-us-east-1",
                "cluster_size": "sandbox-single-node",
                "auto_rollback": True,
                "notification_channel": "#dev-infra-sandbox"
            },
            "uat": {
                "target_cloud": "aws-eu-west-1",
                "cluster_size": "staging-2node",
                "auto_rollback": True,
                "notification_channel": "#staging-deployments"
            },
            "prod": {
                "target_cloud": "aws-us-east-1",
                "cluster_size": "production-ha-3node",
                "auto_rollback": True,
                "notification_channel": "#prod-critical-alerts"
            }
        }

    @step(
        name="Validate Infrastructure Spec",
        order=1,
        tags=["preflight", "validation"]
    )
    def validate_spec(self, context: WorkflowContext) -> StepResult:
        cloud = context.get("target_cloud", "aws-us-east-1")
        size = context.get("cluster_size", "production-ha-3node")

        context.set("spec_validated", True)
        context.set("estimated_monthly_cost_usd", 1450 if "production" in size else 320)
        context.set("subnets_allocated", ["10.100.1.0/24", "10.100.2.0/24", "10.100.3.0/24"])

        return self.success(
            message=f"Validated infrastructure spec for {cloud} [{size}]. Estimated cost: ${context.get('estimated_monthly_cost_usd')}/mo",
            data={
                "cloud": cloud,
                "size": size,
                "subnets": context.get("subnets_allocated")
            }
        )

    @step(
        name="Synthesize Terraform Plan & Security Audit",
        order=2,
        requires=["Validate Infrastructure Spec"],
        tags=["terraform", "security"]
    )
    def synthesize_plan(self, context: WorkflowContext) -> StepResult:
        cloud = context.get("target_cloud")
        cost = context.get("estimated_monthly_cost_usd")

        # Simulate plan generation
        plan_summary = {
            "resources_to_create": 14,
            "resources_to_modify": 2,
            "resources_to_destroy": 0,
            "security_compliance_score": 98.5,
            "iam_policies_reviewed": True,
            "target_vpc_id": "vpc-084a92d4bfa"
        }

        context.set("terraform_plan_id", "tfplan_883a0f12")
        context.set("terraform_plan_summary", plan_summary)

        return self.success(
            message=f"Plan generated: +14 to add, ~2 to change, 0 to destroy. Security Score: 98.5%",
            data=plan_summary
        )

    @step(
        name="Provision Live Cloud Infrastructure",
        order=3,
        requires=["Synthesize Terraform Plan & Security Audit"],
        requires_approval=True,
        approval_prompt="Please verify the generated Terraform plan (+14 resources, VPC vpc-084a92d4bfa) and budget impact ($1,450/mo) before applying changes to live cloud.",
        approval_roles=["admin", "sre", "platform-lead"],
        tags=["provisioning", "cloud", "approval-required"]
    )
    def provision_infrastructure(self, context: WorkflowContext) -> StepResult:
        plan_id = context.get("terraform_plan_id")
        cloud = context.get("target_cloud")

        context.set("cluster_endpoint", f"https://k8s.{cloud}.valiant-cloud.net")
        context.set("nodes_ready", 3)
        context.set("provisioned_at", time.time())

        return self.success(
            message=f"Provisioned live cloud cluster on {cloud}. Endpoint: {context.get('cluster_endpoint')}",
            data={
                "endpoint": context.get("cluster_endpoint"),
                "nodes": 3,
                "status": "ready"
            }
        )

    @step(
        name="Deploy Application Services",
        order=4,
        requires=["Provision Live Cloud Infrastructure"],
        tags=["k8s", "deploy"]
    )
    def deploy_services(self, context: WorkflowContext) -> StepResult:
        endpoint = context.get("cluster_endpoint")

        services = [
            {"name": "valiant-api-gateway", "replicas": 3, "status": "healthy"},
            {"name": "valiant-worker-daemon", "replicas": 4, "status": "healthy"},
            {"name": "valiant-auth-service", "replicas": 2, "status": "healthy"}
        ]
        context.set("deployed_services", services)

        return self.success(
            message=f"Deployed 3 microservices with 9 total pods to {endpoint}",
            data={"services": services}
        )

    @step(
        name="Run Post-Deployment Smoke Tests",
        order=5,
        requires=["Deploy Application Services"],
        tags=["testing", "verification"]
    )
    def smoke_tests(self, context: WorkflowContext) -> StepResult:
        tests = {
            "api_health_check": "200 OK (14ms)",
            "database_read_write": "PASSED (8ms)",
            "ssl_certificate_valid": "VALID (expires in 89 days)",
            "ingress_route_verified": "PASSED"
        }
        context.set("smoke_tests_passed", True)

        return self.success(
            message="All 4/4 synthetic smoke tests passed with zero errors",
            data=tests
        )

    @step(
        name="Broadcast SRE Deployment Notification",
        order=6,
        requires=["Run Post-Deployment Smoke Tests"],
        tags=["alerts", "notification"]
    )
    def notify_sre(self, context: WorkflowContext) -> StepResult:
        channel = context.get("notification_channel", "#platform-infra-deployments")
        cloud = context.get("target_cloud")

        return self.success(
            message=f"Sent deployment confirmation report to {channel} for {cloud}",
            data={
                "channel": channel,
                "cloud": cloud,
                "cluster_endpoint": context.get("cluster_endpoint")
            }
        )
