# AutoSpecMan

AutoSpecMan 是一个用来从现有仓库自动推断规范（spec）的 MVP 工具。目标是为后续的分层规范体系打下基础：它可以扫描仓库结构、配置与 Git 历史，生成一份包含语言栈、工具链、工作流与质量门槛的仓库级 spec。

## 检测覆盖
- **语言栈**：自动识别 Python/TypeScript/Go 等主流语言及其占比
- **工具链**：包管理器、格式化器、Lint、测试框架、CI 平台、安全扫描工具
- **结构模式**：顶层目录形态、routes/controllers/migrations 等服务目录
- **API 资产**：OpenAPI/Swagger、GraphQL、路由实现文件、Postman/Insomnia 集合
- **数据资产**：SQL DDL、Prisma/schema 文件、迁移目录、ORM 配置
- **工作流**：Git 提交节奏、活跃贡献者、发布信号
- **输出形式**：所有推断项附带置信度，可生成 YAML/JSON（支持写文件或直接打印）

## 快速开始
1. 准备 Python 3.11 环境：
```bash
make setup
```
该命令会创建 `.venv/`、安装开发依赖与 `autospecman` 可执行文件。

2. 生成 spec：
```bash
make run
# 或手动
.venv/bin/python -m autospecman.cli --repo /path/to/repo --format yaml --output ./spec.yaml
```

3. 验证 CLI：
```bash
make smoke   # 生成 JSON/YAML 各一份
```

不指定 `--output` 时，结果会直接打印到终端。默认会采样最近 400 条提交，必要时可以用 `--max-commits` 调整。

## 输出示例
```yaml
metadata:
  spec_version: 0.1.0
  generated_at: 2025-01-01T00:00:00+00:00
  repository: /abs/path/demo
language_stack:
  - language: python
    ratio: 0.95
tooling:
  package_managers: [python-pyproject]
  formatters: [black, isort]
  linters: [ruff]
  test_frameworks: [pytest]
  ci_systems: [github-actions]
workflow:
  commit_cadence_per_week: 8.4
  active_contributors: 5
  release_signal: weekly-release
structure:
  top_level_patterns: [src-root]
  service_markers: [routes, controllers, models]
  notable_directories:
    - src/routes
    - src/controllers
    - src/models
api_surface:
  openapi_files: [docs/openapi.yaml]
  graphql_files: [schema.graphql]
  route_files: [src/routes/items.py]
  client_collections: [docs/postman_collection.json]
data_assets:
  ddl_files: [db/schema.sql]
  migration_dirs: [db/migrations]
  orm_configs: [schema.prisma (prisma)]
quality_gates:
  required_checks:
    - github-actions-default
  security_tools: [bandit]
confidence:
  language_stack: 0.8
  tooling.linters: 0.8
notes: []
```

## 现状与下一步
当前版本聚焦于“从仓库反推 spec”。后续可逐步接入：

1. 更丰富的配置解析器（如 Gradle、Maven、Bazel 等）
2. 将推断结果与企业/项目级模板合并
3. 在 AI Agent 与 CI 中强制执行规范

欢迎基于此 MVP 继续扩展，实现完整的 Spec-driven Development 闭环。
