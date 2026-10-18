---
name: code-review
description: Standard operating procedure for reviewing code in this repo
---

# Code Review Standard Operating Procedure (SOP)

This skill defines the rigorous criteria and checklist an AI agent or human reviewer must follow when inspecting pull requests, commits, and code changes in the Valiant platform.

---

## 1. Architectural Boundary Checks

### ❌ Critical Violations to Block:
- **Use of Pandas**: Strict zero-tolerance ban on `import pandas` or Pandas DataFrames. All tabular operations must use Polars (`import polars as pl`).
- **Unbounded In-Memory Tables**: Dumping entire multi-million row datasets directly into SQLite context or WebSocket payloads instead of using the dual-tier preview (max 50 rows) + Parquet artifact writer.
- **Core Leaks in Workflows**: Workflows in `backend/workflows/` importing directly from `backend.valiant.api`, `backend.valiant.db`, or external HTTP route internals.
- **Workflow Logic in Framework Core**: Business-logic or domain-specific assumptions hardcoded into `backend/valiant/core/`.
- **Direct Database Access from Workflows**: Workflows writing directly to SQLAlchemy models or raw SQL queries rather than passing outputs through `WorkflowContext` (`self.success(data=...)`).
- **Cross-Environment Database Bleed**: Any persistence or query logic in `backend/valiant/db/` that bypasses the `env` parameter or writes to a single shared `valiant.db` instead of `valiant_{env}.db`.
- **External CDN or PDF Binaries in Reports**: Introducing external CDN scripts/fonts or third-party PDF binaries (wkhtmltopdf/weasyprint) into execution reports. HTML reports must remain 100% self-contained with browser-native `@media print` styling.
- **Direct Pushes to Main**: Bypassing PR review with direct pushes to `main`. All go-forward code changes must be submitted via feature branch Pull Request (`gh pr create`).

---

## 2. Security & Data Protection Checklist

- [ ] **Secret Masking**: Are passwords, tokens, API keys, or certificates scrubbed using `context.to_dict(mask_secrets=True)` before returning to the UI or saving to execution logs?
- [ ] **Data Lineage & Scoped Context Hygiene**: Does context mutation tracking isolate step reads/writes via `ScopedStepContext` to prevent state contamination under async parallelism?
- [ ] **Comparator Data Masking**: Does the regression comparator scrub secrets before diffing baseline and target contexts?
- [ ] **Production Guardrails**: Does any trigger or mutation in `prod` enforce explicit authorization (`requires_confirmation`)?
- [ ] **SQL Injection Prevention**: Are all database interactions mediated by SQLAlchemy Core/ORM or explicitly parameterized? No f-string raw SQL queries allowed.
- [ ] **Human-in-the-Loop Breakpoints**: Are sensitive mutations (infrastructure provisioning, production releases, data migrations) guarded with `@step(requires_approval=True)`? Does the runner safely suspend without thread blocking?
- [ ] **Approval Audit Trail**: Are operator decisions, timestamps, and justification notes persisted to the environment database upon approve or reject?
- [ ] **Webhook Authentication**: Do inbound webhooks validate the secret header (`X-Valiant-Secret`) via constant-time comparison (`hmac.compare_digest`) if configured, and return 202 Accepted rather than blocking the caller?
- [ ] **SQLite Concurrency & WAL Mode**: Does SQLite database connection configuration enforce WAL journal mode (`PRAGMA journal_mode=WAL;`), busy timeouts (5000ms), and scoped connection timeouts to prevent concurrency locks?
- [ ] **Input Sanitization & Coercion**: Are workflow parameters validated and auto-coerced to annotated types (`int`, `float`, `bool`) without unhandled runtime exceptions?

---

## 3. Python Backend Standards

- [ ] **Pydantic v2 Idioms**: Confirm that all Pydantic schemas use `.model_dump()`, `.model_validate()`, and `Field()`, rather than legacy v1 `.dict()` or `.parse_obj()`.
- [ ] **Async & Concurrency Correctness**:
  - Parallel step tiers must be safely awaited using `asyncio.gather(*tasks, return_exceptions=True)`.
  - Non-blocking I/O in API routes (`async def`).
- [ ] **Type Annotations**: All new functions, step handlers, and API router methods must include accurate type annotations (`Optional[T]`, `Dict[str, Any]`, `List[T]`).
- [ ] **Preservation of Comments**: Preserve existing documentation and docstrings unless intentionally modifying functionality.

---

## 4. Frontend (React / TypeScript / Tailwind) Standards

- [ ] **API Client Centralization**: Are all HTTP and WebSocket calls routed through `frontend/src/api.ts`?
- [ ] **Environment Header Propagation**: Does every API interaction include the `X-Valiant-Env` header to maintain environment isolation?
- [ ] **TypeScript Strictness**: Zero use of unjustified `any`; all components, props, and API payloads must have defined interfaces in `frontend/src/types.ts`.
- [ ] **Theme & UI/UX Consistency**:
  - Uses Tailwind CSS dark palette (`slate-900`, `slate-950`, `border-slate-800`).
  - Environment badges follow color conventions (`DEV`: Emerald, `UAT`: Amber, `PROD`: Rose).
  - Responsive layouts accommodating both standard views and fullscreen expanded states.
- [ ] **Clean Lint & Build**: PR must pass `npm run lint` (`oxlint`) and `npm run build` (`tsc -b && vite build`) without new errors.

---

## 5. Desktop Local DevOps & CLI Subprocess Standards

- [ ] **Windows Cross-Platform Pathing & Binaries**: Are CLI binaries resolved through `shutil.which` before execution? (e.g. `mvn` -> `mvn.cmd` on Windows).
- [ ] **Responsive Process Group Termination**: Are child subprocesses started in separate process groups and killed cleanly via `taskkill /F /T` on Windows or `os.killpg` on POSIX?
- [ ] **Non-Blocking Polling**: Does polling use async `context.poll_until` with reasonable interval and timeout, rather than thread-blocking `time.sleep`?
- [ ] **Untruncated Run Logging**: Are all stdout/stderr streams written cleanly to `.valiant/logs/{env}/{run_id}.log` via `RunLogManager`?
- [ ] **Self-Contained Multi-Tab HTML Reports**: Does the standalone report generator in `backend/valiant/core/report.py` produce a 100% self-contained document with 5 tabs, dark/light mode toggle, client-side tabular search/sort, governance verification seal, raw logs, secret masking, and `@media print` expansion?

---

## 6. Mandatory Testing & Quality Assurance Checklist

Prior to submitting or pushing any feature, the following validation gates MUST be completed:
1. **Full Pytest Suite**: Execute `pytest tests/` and verify 100% passing tests (zero failures/errors).
2. **TypeScript & Frontend Quality**: Execute `cd frontend && npm run build` (zero type errors) and `npm run lint` (zero warnings/errors).
3. **Visual UI/UX Inspection**: Capture visual browser snapshots of all modified or introduced UI pages/drawers/modals to verify styling, alignment, and interactive behavior.
4. **Dependency Review**: Confirm zero unwanted dependencies introduced (strictly Polars, zero Pandas).
5. **Cross-Platform Compatibility**: Validate that file paths use `pathlib.Path` or `Path.as_posix()` and UTF-8 encoding is explicitly specified.

---

## 7. Review Output Format

When generating a code review report, structure the response using this template:

```markdown
### Code Review Summary
- **Target Component**: [Backend Core / Workflows / API / Frontend]
- **Status**: [✅ Approved / ⚠️ Changes Requested / 🚫 Blocked]

#### 1. Architectural Boundaries & Isolation
- [Notes on separation of concerns & environment isolation]

#### 2. Security & Guardrails
- [Notes on secret masking, SQL safety, and prod controls]

#### 3. Code Quality & Type Safety
- [Notes on typing, Pydantic v2, async patterns, or TypeScript interfaces]

#### 4. Actionable Recommendations
1. [Line-specific suggestion or code improvement]
```
