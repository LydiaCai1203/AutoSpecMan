# 项目级 Spec 可覆盖的条目

本文将 `AutoSpecMan` 当前仓库的真实情况按章节写实，并给出推荐的规则与验证方式，方便后续把“事实（Facts）”与“期望（Rules）”沉淀到 spec 中，为 AI/自动化提供唯一依据。

## 1. 基础环境
### Facts
- 语言与运行时：`pyproject.toml` 要求 `Python >= 3.11` (`setuptools` 构建)。
- 包管理：使用 `pip`/`venv`，通过 `make setup` 自动创建 `.venv` 并执行 `pip install -e .[extras]`；`requirements-dev.txt` 记录开发依赖（`pyyaml`, `pip`, `setuptools`）。
- CLI 入口：在 `pyproject.toml` 中注册 `autospecman = autospecman.cli:main`。
- 目标平台：macOS/Linux，本地运行即可，无额外系统依赖。

-### Rules / Decisions
- 保持 Python 3.11 系列，生产运行统一到 `3.11.8`，并在 CI 中锁定镜像。
- 推荐统一使用 `pip + venv`，通过 `make setup` 进入 `.venv`，并执行 `pip install -e .[extras]` 以启用 YAML 支持。
- 所有 CLI/脚本应通过 `python -m autospecman.cli ...` 或 `autospecman ...` 统一调用；`Makefile` 暴露 `setup/run/smoke` 三个入口。

### Verification
- `python --version` 必须返回 3.11.x；CI 中运行 `python -V`.
- `make smoke`（或手动运行 `python -m autospecman.cli --repo . --format json`、`--format yaml`）必须成功生成 spec。
- 依赖一致性：`pip check` / `pip list --outdated` 作为发布前检查。

## 2. 目录与模块结构
### Facts
- 顶层目录：`autospecman/`（核心代码）、`docs/`（文档）、`README.md`。
- `autospecman/` 下包含核心模块：`cli.py`, `inference.py`, `repository.py`, `schema.py` 与 `detectors/`（`language`, `tooling`, `history`, `structure` 等）。
- 文档集中在 `docs/`，目前包含 `project-spec-scope.md`。

### Rules / Decisions
- 所有新的核心逻辑放在 `autospecman/`，模块命名使用 `snake_case`。
- 探测器（detectors）全部放在 `autospecman/detectors/`，并在 `__init__.py` 中显式导出。
- 文档统一放入 `docs/`，命名为 `*.md`，与 README 链接。
- 目录示例：
  ```
  autospecman/
    cli.py
    inference.py
    repository.py
    schema.py
    detectors/
      language.py
      tooling.py
      history.py
      structure.py
  docs/
    project-spec-scope.md
  ```

### Verification
- 运行 `python -m autospecman.cli --repo .`，应自动发现新 detector。
- `tree -L 2` 输出需与上方模板一致（除 tests、examples 等扩展目录）。

## 3. 命名与分类规范
### Facts
- 现有 Python 模块/变量均使用 `snake_case`；类名为 `PascalCase`。
- CLI 标志使用 `--kebab-case`（如 `--max-commits`）。
- 尚未引入数据库或 HTTP 接口，但 spec schema 中的键使用 `snake_case`。

### Rules / Decisions
- **Python 代码**：文件、模块、函数、变量使用 `snake_case`；类与异常用 `PascalCase`；常量使用 `UPPER_SNAKE_CASE`。
- **未来数据库**：表命名 `domain_entity`（复数），字段 `lower_snake_case`，必须包含前缀区分域，例如 `spec_runs`, `spec_run_items`。
- **接口/路由（若引入）**：统一 `/api/v1/<resource>`，资源名使用复数 `kebab-case`，动作使用子路径，例如 `/api/v1/spec-runs/replay`.
- **目录分类**：新领域模块应位于 `autospecman/<domain>/...` 或 `autospecman/detectors/<domain>.py`，并在 README 中登记。

### Verification
- 静态检查：运行 `python -m compileall autospecman` + `ruff check`（未来接入）以捕捉命名不规范。
- 对数据库/接口命名的校验先由脚本统计前缀，人工确认；后续可在 `autospecman` 中实现自动 detector。

## 4. 接口与协议
### Facts
- 当前只提供 CLI 接口：`autospecman --repo <path> [--format yaml|json] [--output file] [--max-commits N]`。
- CLI 默认输出 YAML（若安装 `pyyaml`），否则使用内置 YAML fallback。
- 无 HTTP/GraphQL/gRPC API。

### Rules / Decisions
- 保持 CLI 作为第一入口；所有新功能优先以 CLI flag 暴露，命名遵循 `--kebab-case`。
- 预留未来 HTTP API：路径命名遵循上节规则；响应使用 `application/json`，字段与 spec schema 对应。
- CLI 必须返回非 0 exit code 表示失败，并打印友好信息到 stderr。

### Verification
- `autospecman --help` 输出需涵盖所有 flag；新增 flag 前在 README/Docs 更新。
- 一旦增加 HTTP API，需要补充 OpenAPI 文档存放路径并纳入本章节。

## 5. 数据模型与迁移
### Facts
- 当前无持久化数据库；`autospecman.schema.empty_spec` 定义的 in-memory 结构即“数据模型”。
- Spec 字段包括：`metadata`, `language_stack`, `tooling`, `workflow`, `quality_gates`, `structure`, `api_surface`, `data_assets`, `confidence`, `notes`。

### Rules / Decisions
- 继续把 spec 视为权威数据模型；任何新字段必须先在 `autospecman/schema.py` 声明，附文档说明。
- 若引入数据库（SQLite/Postgres），需维护迁移目录 `db/migrations`，文件命名 `YYYYMMDDHHMM_<description>.sql`。
- 数据字典（字段描述、类型、默认值）保存在 `docs/data-dictionary.md`（待创建）。

### Verification
- 运行 `python - <<'PY' ...` 断言 `schema.SPEC_VERSION` 与 README 示例一致。
- 一旦有 DB，CI 中运行迁移干跑（`alembic upgrade head --sql` / `prisma migrate diff` 等）。

## 6. 错误管理
### Facts
- CLI 使用 `argparse.ArgumentParser.error()` 处理异常；`infer_spec` 未定义自有异常类型。
- 错误信息直接输出到 stderr，缺少统一错误码或追踪 ID。

### Rules / Decisions
- 引入基础异常 `AutoSpecError(code: str, message: str, detail: dict)` 并在 CLI/核心逻辑中使用。
- 约定错误分类：`INPUT`, `IO`, `ANALYSIS`, `INTERNAL`；HTTP API（未来）中映射为 `400/404/500` 等。
- 日志/监控：错误需在 CLI 中打印 `code`, `message`, `hint`；若接入监控，统一使用 `autospecman_error` 事件。

### Verification
- 单元测试覆盖：对错误路径断言 `AutoSpecError.code` 与消息。
- Smoke：执行 `autospecman --repo /path/does/not/exist`，应返回非零并输出结构化错误。

## 7. 工具链与质量门槛
### Facts
- 目前仅通过手动运行 CLI 来验证；尚未接入 lint/test。
- Repo 没有 `pytest`/`ruff` 配置，也没有 CI Workflow。

### Rules / Decisions
- 质量工具计划：
  - Lint：`ruff` + 规则 `E,F,I,B`.
  - 格式化：`black`（line length 100）。
  - 类型：`mypy --strict` 针对 `autospecman/`.
  - 测试：`pytest`，覆盖率目标 70% 起步。
- CI：GitHub Actions workflow `ci.yml`，阶段包括 `lint`, `typecheck`, `test`, `package`.
- 安全：后续引入 `bandit`/`pip-audit`。

### Verification
- 本地与 CI 统一运行：
  ```bash
  ruff check autospecman
  black --check autospecman
  mypy autospecman
  pytest
  ```
- 发布前 checklist 包括 `python -m build` + `pip install dist/*.whl`.

## 8. 协作与流程
### Facts
- 目前单人维护，`main` 为默认分支，尚无正式 PR 流程。
- 文档与代码同仓维护。

### Rules / Decisions
- 分支策略：`main` 保持稳定；功能分支命名 `feature/<slug>`，修复分支 `fix/<slug>`。
- Commit 规范：`<type>(scope): summary`（type ∈ feat/fix/docs/refactor/chore/test）。
- PR 模板需回答“是否更新 spec / 文档 / CLI 帮助”。
- 发布节奏：按需发布 `0.x` 版本；每次发布需要更新 `CHANGELOG.md`（待创建）。

### Verification
- 手动：检查 PR 是否链接 issue 并更新 docs。
- 自动：可用 GitHub Action 检查分支/commit 模式（后续添加）。

## 9. AI / 自动化 Guardrails
### Facts
- AutoSpecMan 自身是“spec 推断器”；尚未把 spec 强制接入 AI 生成工作流。
- 当前没有记录 AI 行为或例外。

### Rules / Decisions
- 所有 AI Agent（含 AutoSpecMan 自己）在修改代码前必须读取最新 spec，并在变更描述中引用相关章节。
- 若 AI 输出的命名/目录/错误处理不符合规则，CI 必须拒绝并提供反馈。
- 新增或放宽规则需在 docs 中记录审批人和原因。

### Verification
- 在未来的 AI 工作流中，注入“spec 校验”步骤：例如调用 AutoSpecMan CLI 对 diff 做 dry-run 检查。
- 记录 AI 操作日志，定期回顾偏差并更新 spec。

## 10. 遥测与合规
### Facts
- 当前未接入任何遥测或合规记录；CLI 运行仅在本地。

### Rules / Decisions
- 指标：至少收集 `spec_generation_duration`, `detector_failures`, `spec_fields_detected`.
- 告警：当 `detector_failures > 0` 或 spec 输出缺少关键字段时触发。
- 审计：未来若写入集中存储，需记录“生成者、生成时间、仓库路径”并保留 90 天。

### Verification
- 一旦接入遥测，需在 docs 中链接仪表盘（Grafana/Looker）。
- 每季度复盘一次 spec 覆盖率与规则执行情况，更新本文档。

> 以上章节可直接映射到 spec 的 Facts/Rules 字段：Facts 来自自动扫描或人工确认的现状；Rules 由项目 owner 或治理负责人签名确认；Verification 给出落地检查方式，方便 AI/CI 执行。将三者同步维护，可以帮助 AutoSpecMan 在后续自动生成/审查时拥有明确的输入。

