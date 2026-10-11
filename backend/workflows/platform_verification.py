"""
Complex Platform Verification Workflow
Demonstrates a production-grade 20-step validation pipeline with:
- Categories / Tags: [smoke, security, database, microservices, load, audit]
- Parallel Step Groups:
    - Group 'infra_probe': DNS check, Gateway check, Auth probe
    - Group 'db_probe': Primary DB, Replica DB, Redis Cache
    - Group 'service_probe': User Service, Order Service, Payment Service, Inventory Service
- Conditional Step: Deep latency audit (run only if deep_audit=True)
- Shared context passing across validation stages
"""
import time
from typing import List
from backend.valiant import Workflow, step, workflow, InputField, InputType


@workflow(
    name="platform_full_verification",
    description="Enterprise 20-step health verification across infrastructure, databases, and microservices with parallel probes",
    tags=["platform-verification", "smoke", "investigation", "deep-audit"]
)
class PlatformVerificationWorkflow(Workflow):
    name = "Platform Full Verification"
    description = "Enterprise 20-step health verification across infrastructure, databases, and microservices"
    version = "2.5.0"
    tags = ["platform-verification", "smoke", "investigation", "deep-audit"]

    def inputs(self) -> List[InputField]:
        return [
            InputField(
                name="environment",
                type=InputType.SELECT,
                default="production",
                options=["staging", "uat", "production"],
                help_text="Target environment to validate"
            ),
            InputField(
                name="deep_audit",
                type=InputType.CHECKBOX,
                default=True,
                help_text="Run deep diagnostic and stress checks"
            ),
            InputField(
                name="timeout_threshold_ms",
                type=InputType.NUMBER,
                default=500,
                min_value=50,
                help_text="Maximum acceptable latency SLA in ms"
            ),
            InputField(
                name="operator_email",
                type=InputType.EMAIL,
                default="sre-team@platform.internal",
                help_text="SRE team notified upon verification completion"
            )
        ]

    # --- PHASE 1: PRE-FLIGHT (Order 1) ---
    @step("Validate Environment Credentials", order=1, tags=["security", "pre-flight"])
    def step_01_creds(self, context):
        env = context.get("environment", "production")
        context["auth_token"] = f"jwt_mock_{env}_994821"
        res = self.success(
            message=f"Environment '{env}' verified with active service account credentials",
            data={"environment": env, "token_prefix": "jwt_mock_...", "expires_in": 3600}
        )
        res.add_metric("env_valid", 1)
        return res

    # --- PHASE 2: PARALLEL INFRASTRUCTURE PROBE (Order 2) ---
    @step("Probe Global DNS & CDN", order=2, parallel_group="infra_probe", tags=["infra", "smoke"])
    def step_02_dns(self, context):
        res = self.success(
            message="DNS resolution: 4 Edge PoPs responding in 12ms",
            data={"edge_pops": ["US-East", "US-West", "EU-Central", "AP-South"], "avg_dns_ms": 12.4}
        )
        res.add_metric("dns_latency_ms", 12.4)
        return res

    @step("Probe API Gateway & Ingress", order=2, parallel_group="infra_probe", tags=["infra", "smoke"])
    def step_03_gateway(self, context):
        res = self.success(
            message="Ingress Gateway healthy (Envoy proxies: 12/12 online)",
            data={"active_proxies": 12, "http2_support": True, "ssl_cert_days_left": 84}
        )
        res.add_metric("gateway_active", 12)
        return res

    @step("Probe OAuth / IAM Identity Provider", order=2, parallel_group="infra_probe", tags=["security", "smoke"])
    def step_04_auth(self, context):
        res = self.success(
            message="Keycloak / IAM cluster responsive, token issuance latency 24ms",
            data={"idp_status": "UP", "jwks_endpoint": "/auth/realms/platform/certs", "latency_ms": 24}
        )
        res.add_metric("idp_latency_ms", 24)
        return res

    # --- PHASE 3: PARALLEL DATA TIER PROBES (Order 3) ---
    @step("Check PostgreSQL Primary Cluster", order=3, parallel_group="db_probe", tags=["database", "storage"])
    def step_05_primary_db(self, context):
        context["db_primary_healthy"] = True
        res = self.success(
            message="PostgreSQL Primary active (Connection pool: 42/100, Lag: 0ms)",
            data={"role": "PRIMARY", "version": "16.2", "active_connections": 42, "replication_lag_ms": 0}
        )
        res.add_metric("db_pool_utilization_pct", 42)
        return res

    @step("Check Read-Replica Synchronization", order=3, parallel_group="db_probe", tags=["database", "storage"])
    def step_06_replica_db(self, context):
        res = self.success(
            message="All 3 Read-Replicas in sync (Max replication lag: 4ms)",
            data={"replicas": ["db-rep-01", "db-rep-02", "db-rep-03"], "max_lag_ms": 4.1}
        )
        res.add_metric("max_replica_lag_ms", 4.1)
        return res

    @step("Check Redis Distributed Cache Cluster", order=3, parallel_group="db_probe", tags=["database", "cache"])
    def step_07_redis_cache(self, context):
        res = self.success(
            message="Redis 6-node cluster healthy (Memory used: 1.4GB / 8GB, Hit rate: 94.2%)",
            data={"cluster_nodes": 6, "memory_mb": 1433, "cache_hit_rate": 0.942}
        )
        res.add_metric("cache_hit_rate", 94.2)
        return res

    @step("Check Kafka Event Bus & Partitions", order=3, parallel_group="db_probe", tags=["messaging", "infra"])
    def step_08_kafka_bus(self, context):
        context["kafka_topics_verified"] = 18
        res = self.success(
            message="Kafka cluster online: 3 brokers, 18 topics with 0 consumer lag",
            data={"brokers": 3, "topics": 18, "consumer_lag": 0}
        )
        res.add_metric("consumer_lag", 0)
        return res

    # --- PHASE 4: PARALLEL MICROSERVICES CHECKS (Order 4) ---
    @step("Health Check: User & Identity Service", order=4, parallel_group="service_probe", tags=["microservices", "smoke"])
    def step_09_user_service(self, context):
        res = self.success(
            message="User service OK (v3.2.1, 8 pods healthy, response time 18ms)",
            data={"service": "user-service", "version": "3.2.1", "healthy_pods": 8, "p95_latency_ms": 18.2}
        )
        res.add_metric("user_svc_latency_ms", 18.2)
        return res

    @step("Health Check: Order Management Service", order=4, parallel_group="service_probe", tags=["microservices", "smoke"])
    def step_10_order_service(self, context):
        res = self.success(
            message="Order service OK (v4.0.0, 10 pods healthy, queue size 0)",
            data={"service": "order-service", "version": "4.0.0", "healthy_pods": 10, "queue_depth": 0}
        )
        res.add_metric("order_svc_latency_ms", 22.1)
        return res

    @step("Health Check: Payment Processing Gateway", order=4, parallel_group="service_probe", tags=["microservices", "payments"])
    def step_11_payment_service(self, context):
        res = self.success(
            message="Payment service connected (Stripe & Adyen webhooks active)",
            data={"service": "payment-gateway", "connectors": ["stripe", "adyen"], "circuit_breaker": "CLOSED"}
        )
        res.add_metric("payment_circuit_open", 0)
        return res

    @step("Health Check: Inventory & Warehouse Service", order=4, parallel_group="service_probe", tags=["microservices", "smoke"])
    def step_12_inventory_service(self, context):
        res = self.success(
            message="Inventory service OK (v2.8.4, 6 pods healthy, sync delta 0)",
            data={"service": "inventory-service", "version": "2.8.4", "healthy_pods": 6}
        )
        res.add_metric("inventory_svc_latency_ms", 15.6)
        return res

    # --- PHASE 5: BUSINESS WORKFLOW & INTEGRATION VALIDATION (Orders 5-7) ---
    @step("Execute Synthetic Checkout Transaction", order=5, requires=["Health Check: Payment Processing Gateway"], tags=["integration", "e2e"])
    def step_13_synthetic_tx(self, context):
        context["synthetic_order_id"] = "ORD-TEST-84920"
        res = self.success(
            message="Synthetic end-to-end checkout successful in 210ms (Cart -> Payment -> Order)",
            data={"synthetic_id": "ORD-TEST-84920", "total_e2e_time_ms": 210, "status": "CONFIRMED"}
        )
        res.add_metric("e2e_checkout_time_ms", 210)
        return res

    @step("Rollback Synthetic Test Record", order=6, requires=["Execute Synthetic Checkout Transaction"], tags=["integration", "cleanup"])
    def step_14_rollback_synthetic(self, context):
        order_id = context.get("synthetic_order_id")
        res = self.success(
            message=f"Rolled back synthetic record '{order_id}' to maintain zero-trace test integrity",
            data={"rolled_back_id": order_id, "cleaned_tables": ["orders", "payments", "audit_log"]}
        )
        return res

    # --- PHASE 6: DEEP AUDIT & SLA CHECKS (Orders 7-8, Conditional) ---
    @step("Deep Latency & SLA Diagnostic Audit", order=7, condition="deep_audit", tags=["investigation", "deep-audit"])
    def step_15_deep_audit(self, context):
        threshold = context.get("timeout_threshold_ms", 500)
        p99_latency = 138.4
        passed = p99_latency < threshold
        res = self.success(
            message=f"SLA Verification Passed: Platform P99 is {p99_latency}ms (Threshold SLA: {threshold}ms)",
            data={"p50_ms": 22.0, "p90_ms": 68.1, "p99_ms": p99_latency, "sla_limit_ms": threshold, "compliant": passed}
        )
        res.add_metric("platform_p99_ms", p99_latency)
        return res

    @step("Scan Error Log Rates & Alert Spikes", order=8, condition="deep_audit", tags=["investigation", "observability"])
    def step_16_log_scan(self, context):
        res = self.success(
            message="Log cluster audit: 0 critical crash loops, 0 unhandled exceptions in trailing 60m",
            data={"log_aggregator": "Datadog / OpenSearch", "trailing_minutes": 60, "critical_errors": 0}
        )
        res.add_metric("critical_error_count", 0)
        return res

    @step("Audit Kubernetes Pod Resources & HPA", order=9, tags=["infra", "investigation"])
    def step_17_k8s_audit(self, context):
        res = self.success(
            message="Cluster resources healthy: CPU avg 34%, Memory avg 51%, HPA scaling limits normal",
            data={"cluster": "prod-useast-k8s", "node_count": 24, "cpu_pct": 34, "mem_pct": 51}
        )
        res.add_metric("cluster_cpu_pct", 34)
        res.add_metric("cluster_mem_pct", 51)
        return res

    @step("Security Compliance & TLS Certificate Audit", order=10, tags=["security", "audit"])
    def step_18_security_audit(self, context):
        res = self.success(
            message="TLS 1.3 enforced across all ingress points. Zero open high-severity vulnerabilities.",
            data={"tls_version": "TLSv1.3", "cipher_strength": "A+", "unpatched_cves": 0}
        )
        res.add_metric("unpatched_cves", 0)
        return res

    # --- PHASE 7: SYNTHESIS & AUDIT REPORTING (Orders 11-12) ---
    @step("Aggregate Diagnostic Metrics & Scorecard", order=11, tags=["audit", "reporting"])
    def step_19_scorecard(self, context):
        health_score = 99.8
        context["overall_health_score"] = health_score
        res = self.success(
            message=f"Platform Health Score: {health_score}/100. All operational tiers passed.",
            data={
                "health_score": health_score,
                "tiers_validated": ["Infra", "Databases", "Microservices", "Security", "SLA"],
                "recommendation": "Platform in GREEN state. Ready for traffic."
            }
        )
        res.add_metric("health_score", health_score)
        return res

    @step("Dispatch Verification Report & Audit Signoff", order=12, tags=["reporting", "notifications"])
    def step_20_dispatch(self, context):
        email = context.get("operator_email", "sre-team@platform.internal")
        score = context.get("overall_health_score", 100)
        res = self.success(
            message=f"Audit signoff dispatched to '{email}' (Score: {score}/100)",
            data={"recipient": email, "dispatch_method": "Email / Slack Webhook", "status": "DELIVERED"}
        )
        return res
