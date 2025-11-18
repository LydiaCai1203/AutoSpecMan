# AutoSpecMan

AutoSpecMan 是一个用来从现有仓库自动推断规范（spec）的 MVP 工具。目标是为后续的分层规范体系打下基础：它可以扫描仓库结构、配置与 Git 历史，生成一份包含语言栈、工具链、工作流与质量门槛的仓库级 spec。

## 检测覆盖
- **语言栈**：自动识别 Python/TypeScript/Go 等主流语言及其占比
- **工具链**：包管理器、格式化器、Lint、测试框架、CI 平台、安全扫描工具
- **结构模式**：顶层目录形态、routes/controllers/migrations 等服务目录
- **API 资产**：OpenAPI/Swagger、GraphQL、路由实现文件、Postman/Insomnia 集合
- **数据资产**：SQL DDL、Prisma/schema 文件、迁移目录、ORM 配置
- **工作流**：Git 提交节奏、活跃贡献者、发布信号、分支策略、提交消息规范、分支命名模式、tag 命名规范（支持 LLM 增强分析）
- **输出形式**：所有推断项附带置信度，可生成 YAML/JSON（支持写文件或直接打印）

## 快速开始

### 1. 安装依赖

准备 Python 3.11 环境并安装基础依赖：
```bash
make setup
```
该命令会创建 `.venv/`、安装开发依赖与 `autospecman` 可执行文件。

### 2. 配置 LLM（可选，用于增强 Git 历史分析）

AutoSpecMan 支持使用 LLM 来分析 Git 提交规范、分支命名模式和 tag 命名规范。如果不需要 LLM 功能，可以跳过此步骤（会自动回退到基于规则的检测）。

#### 安装 LLM 依赖
```bash
# 安装 OpenAI 支持
.venv/bin/pip install openai>=1.0.0

# 或使用可选依赖组
.venv/bin/pip install -e .[llm]
```

#### 配置方式（按优先级从高到低）

**方式一：配置文件（推荐，最方便）**

在项目根目录创建 `autospecman.toml` 或 `.autospecman.toml`：

```toml
# Git 历史分析配置
max_commits = 400

# LLM 配置
[llm]
use_llm = true
provider = "openai"  # 仅用于标识，不影响实际调用
model = "gpt-3.5-turbo"
# api_key = "your-api-key-here"  # 可选，建议使用环境变量
# api_base_url = "https://api.example.com/v1"  # 第三方供应商的 API 地址
```

或者创建用户级配置 `~/.autospecman/config.toml` 或 `~/.config/autospecman/config.toml`（适用于所有项目）。

**使用第三方 LLM 供应商：**

只需在配置文件中设置 `api_base_url` 指向你的供应商端点（需要兼容 OpenAI API 格式）：

```toml
[llm]
use_llm = true
model = "your-model-name"
api_key = "your-api-key"
api_base_url = "https://your-provider.com/v1"  # 第三方供应商地址
```

**方式二：环境变量**
```bash
export LLM_API_KEY="your-api-key-here"  # 或使用 OPENAI_API_KEY（兼容）
export LLM_API_BASE_URL="https://api.example.com/v1"  # 第三方供应商地址
# 可选的其他环境变量
export AUTOSPECMAN_USE_LLM="true"
export AUTOSPECMAN_LLM_MODEL="gpt-4"
```

**方式三：CLI 参数**
```bash
autospecman --llm-api-key "your-api-key" --llm-api-base-url "https://api.example.com/v1" --repo /path/to/repo
```

#### 使用 LLM 功能

配置完成后，直接运行即可自动使用 LLM 分析：

```bash
# 使用配置文件中的设置（推荐）
autospecman --repo /path/to/repo

# 临时覆盖配置
autospecman --no-llm --repo /path/to/repo  # 禁用 LLM
autospecman --llm-model "gpt-4" --repo /path/to/repo  # 使用不同模型
```

**配置优先级**：CLI 参数 > 项目配置文件 > 用户配置文件 > 环境变量 > 默认值

### 3. 生成 spec

生成 spec（默认扫描当前仓库，可用 `REPO=/path/to/other` 覆盖）。输出会保存在 `specs/spec-<仓库名>.yaml`：
```bash
make run                      # 生成 specs/spec-<cwd>.yaml
REPO=/some/repo make run      # 生成 specs/spec-some.yaml
# 或手动
.venv/bin/python -m autospecman.cli --repo /path/to/repo --format yaml --output ./spec.yaml
```

### 4. 测试和验证

#### 基本功能测试（不使用 LLM）

直接运行 `make smoke` 即可测试基本功能，会自动使用基于规则的检测：

```bash
make smoke
# 或测试其他仓库
REPO=/path/to/other/repo make smoke
```

这会生成两个文件：
- `/tmp/spec-<仓库名>.json`
- `/tmp/spec-<仓库名>.yaml`

检查输出文件中的 `workflow` 部分，应该包含：
- `branch_strategy`: 分支策略（基于规则检测）
- `commit_convention`: 提交消息规范（如果有）
- `branch_naming_pattern`: 分支命名模式（如果有）
- `tag_naming_convention`: tag 命名规范（如果有）

#### 测试 LLM 功能

如果要测试 LLM 增强分析，需要先配置 API key：

**方式一：使用配置文件**
```bash
# 1. 创建配置文件（如果还没有）
cp autospecman.toml.example autospecman.toml

# 2. 编辑配置文件，设置 api_key 和 api_base_url
# 或使用环境变量

# 3. 运行测试
make smoke
```

**方式二：使用环境变量**
```bash
# 设置 API key
export LLM_API_KEY="your-api-key"
export LLM_API_BASE_URL="https://api.example.com/v1"  # 可选，第三方供应商

# 运行测试
make smoke
```

**方式三：使用 CLI 参数**
```bash
.venv/bin/python -m autospecman.cli \
  --repo . \
  --llm-api-key "your-api-key" \
  --llm-api-base-url "https://api.example.com/v1" \
  --format yaml \
  --output /tmp/test-spec.yaml
```

#### 验证输出

检查生成的 spec 文件，LLM 分析的结果会在 `workflow` 部分：

```yaml
workflow:
  commit_convention: "conventional-commits with scope: feat(scope): description"
  branch_naming_pattern: "feat-{ticket-id}"
  tag_naming_convention: "semantic-versioning (v1.0.0)"
```

如果这些字段有值且比基于规则的检测更详细，说明 LLM 分析成功。

#### 测试回退机制

测试当 LLM 不可用时的自动回退：

```bash
# 禁用 LLM，强制使用基于规则的检测
.venv/bin/python -m autospecman.cli --no-llm --repo . --format yaml
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
  branch_strategy: git-flow
  commit_convention: conventional-commits with scope: feat(scope): description
  branch_naming_pattern: feat-{ticket-id}
  tag_naming_convention: semantic-versioning (v1.0.0)
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


当我确定我喜欢上你的时候，我们已经不能在一起了。