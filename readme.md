# AutoSpecMan

<div align="center">

**🤖 自动规范管理器 | 让 AI 代码生成更符合团队规范**

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

</div>

---

## 📖 项目简介

**AutoSpecMan** (Automatic Specification Manager) 是一个智能代码规范分析工具，旨在减少 Vibe coding 中 AI 脱离团队开发规范的行为。通过自动分析项目的代码结构和命名习惯，为 AI 代码生成提供准确的规范参考，确保生成的代码符合团队既有的开发风格。

### 🎯 核心价值

- **规范一致性**：自动识别项目命名习惯，避免 AI 生成不符合规范的代码
- **智能分析**：基于 CodeIndex 进行深度代码分析，理解项目结构和功能
- **多语言支持**：支持 Go、Python、TypeScript、JavaScript、Java、Rust 等多种语言
- **即用即得**：生成 Markdown 格式的规范报告，便于查阅和分享

---

## ✨ 主要功能

### 🔍 代码风格分析 (Code Style Detection)

自动分析项目的命名习惯，识别团队实际使用的代码风格：

- **命名模式识别**：自动识别 `snake_case`、`camelCase`、`PascalCase`、`UPPER_SNAKE_CASE` 等命名模式
- **统计分析**：统计各类型符号（类、函数、常量等）的命名风格分布
- **习惯总结**：输出项目的主要命名习惯，为 AI 代码生成提供参考

**输出示例**：
```markdown
## GO 命名习惯

**总符号数**: 4552

### exported_function
**主要命名风格**: `PascalCase` (99.5%)

| 命名模式 | 数量 | 占比 | 示例 |
|---------|------|------|------|
| `PascalCase` | 2860 | 99.5% | NewAgentServiceClient, Sync, Terminal... |
```

### 🏗️ 项目结构分析 (Structure Detection)

智能分析项目结构，理解文件和目录的功能：

- **目录树扫描**：自动扫描项目目录结构
- **符号提取**：提取文件中的类、函数、结构体等符号
- **功能推断**：基于 CodeIndex 查询，推断文件和目录的功能
- **注释生成**：生成带功能注释的目录树结构

**输出示例**：
```markdown
codingmatrix
├── agent
│   ├── cmd
│   │   ├── main.go  # 该方法是服务管理的入口函数...
│   │   └── root.go  # Execute函数是程序的主入口点...
```

---

## 🚀 快速开始

### 安装依赖

```bash
pip install -r requirements.txt
```

### 配置项目

编辑 `config/config.yaml`：

```yaml
project:
  root_path: "/path/to/your/project"
  max_depth: 5
  languages:
    - go
    - python
    - typescript
    - javascript
    - java
    - rust

codeindex:
  db_path: /path/to/codeindex.db
```

### 运行分析

#### 代码风格分析

```python
from detector.codestyle_detector import CodeStyleDetector

detector = CodeStyleDetector(
    config_path="config/config.yaml",
    config_type="codestyle"
)
detector.detect_to_file(output_path="result/code_style.md")
```

#### 项目结构分析

```python
from detector.structure_detector import StructureDetector

detector = StructureDetector(
    config_path="config/config.yaml",
    config_type="structure"
)
detector.detect_to_file(output_path="result/structure.md")
```

### 命令行运行

```bash
python main.py
```

---

## 📁 项目结构

```
AutoSpecMan/
├── config/                 # 配置文件
│   ├── config.py           # 配置加载逻辑
│   └── config.yaml         # 项目配置文件
├── detector/               # 检测器模块
│   ├── base_detector.py    # 基础检测器类
│   ├── codestyle_detector.py    # 代码风格检测器
│   └── structure_detector.py    # 结构检测器
├── utils/                  # 工具模块
│   ├── codeindex_utils.py  # CodeIndex 客户端管理
│   └── logger.py          # 日志工具
├── result/                 # 输出结果目录
│   ├── code_style.md      # 代码风格分析报告
│   └── structure.md       # 项目结构分析报告
├── docs/                   # 文档目录
├── main.py                 # 主入口文件
└── requirements.txt        # 依赖列表
```

---

## 🔧 技术栈

- **Python 3.8+**：核心开发语言
- **CodeIndex**：代码符号索引和查询引擎
- **PyYAML**：配置文件解析
- **Loguru**：日志管理
- **正则表达式**：代码符号提取和模式匹配

---

## 📊 输出报告

### 代码风格报告

报告包含：
- 📈 各语言的命名习惯统计
- 📋 各符号类型的命名模式分布
- 💡 主要命名风格总结
- 📝 命名示例

### 结构分析报告

报告包含：
- 🌳 带注释的目录树结构
- 📄 文件功能描述
- 🏷️ 目录功能推断
- 📊 统计信息

---

## 💡 使用场景

1. **AI 代码生成规范**：为 Vibe coding 等 AI 工具提供项目规范参考
2. **代码审查准备**：快速了解项目的代码风格和结构
3. **新成员 onboarding**：帮助新成员快速了解项目规范
4. **规范文档生成**：自动生成项目的代码规范文档

---

## 🎓 设计理念

本项目基于以下理念：

- **规范优先**：通过分析现有代码，识别团队实际使用的规范，而非强制统一
- **分层设计**：需要工程师有分层思想和设计模式的基础知识
- **智能适配**：让 AI 理解并遵循项目既有的代码风格，而非生搬硬套

---

## 📝 配置说明

### config.yaml 配置项

| 配置项 | 说明 | 示例 |
|--------|------|------|
| `project.root_path` | 项目根目录路径 | `/path/to/project` |
| `project.max_depth` | 扫描最大深度 | `5` |
| `project.languages` | 支持的语言列表 | `['go', 'python']` |
| `codeindex.db_path` | CodeIndex 数据库路径 | `/path/to/codeindex.db` |

---

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

---

## 📄 License

MIT License

---

<div align="center">

**Made with ❤️ for better AI coding**

</div>


### 迷思

> 指定设计模式 AI 会实现的更好，应该先从基类开始设计
> 之后可以加上 mcp, 但感觉会很慢，spec 生成的太慢了
> claude code 支持 skills 了

chatgpt 的解释是：
> spec 只负责约束和评判
spec 是规则说明书，用来告诉模型 什么是正确的、什么是不允许的，输出必须符合哪些标准，判断好坏的依据;
> skills 是可执行的任务模块
skills 用于告诉模型，任务分几步，每一步怎么做，什么时候调用工具，如何把输入转化成最终输出;
skills 通常引用一个或多个 spec
