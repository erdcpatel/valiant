# GitHub Copilot & AI Instructions

All AI assistants, including GitHub Copilot, must adhere to the core architectural boundaries, code conventions, environment separation, and safety rules defined in the master configuration file:

👉 **See [`AGENTS.md`](../AGENTS.md)**

### Key Directives for AI Assistants:
1. **Architectural Separation**: Keep domain workflows in `backend/workflows/` completely decoupled from `backend/valiant/` platform engine internals.
2. **Strictly Polars (Zero Pandas)**: All tabular data handling, SQL query result processing, and analytics workflows must use **Polars** (`import polars as pl`). Pandas is strictly forbidden.
3. **Environment DB Partitioning**: Always respect environment separation (`valiant_{env}.db`). Never hardcode or mix database states across `dev`, `uat`, and `prod`.
4. **Human-in-the-Loop Governance**: Use `@step(requires_approval=True, approval_prompt="...", approval_roles=[...])` for sensitive infrastructure or production workflows.
5. **Secret Masking & Hygiene**: Always preserve secret masking (`mask_secrets=True`, `sensitive=True`) and never log or persist raw credentials.
6. **Self-Contained Reports**: HTML reports generated via `backend/valiant/core/report.py` must remain 100% self-contained with browser-native `@media print` styling (no external CDNs, no third-party PDF binaries).
7. **Cross-Platform Compatibility**: Always use `pathlib.Path` and `.as_posix()` for file URLs and SQLite engine paths; ensure all file operations specify `encoding="utf-8"`.
8. **Pydantic v2**: Use `model_dump()`, `model_validate()`, and `Field()`; never use deprecated Pydantic v1 `.dict()`.
9. **Commands & Build**: Refer to [`AGENTS.md`](../AGENTS.md) for official CLI, test, and frontend build commands.