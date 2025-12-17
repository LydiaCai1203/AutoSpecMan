# 开发进程记录

## 1. 2025-12-17
```markdown
1. 项目结构规范
目录组织方式
文件命名约定
模块划分原则
```

## 2. 2025-12-17 - 结构检测器实现规划

### 实现步骤（分阶段实施）

#### Phase 1: 基础框架搭建 ✅
- [x] 更新 `requirements.txt`（添加 caicai-codeindex）
- [x] 规划单文件架构设计

#### Phase 2: 核心功能实现（按顺序）

**Step 1: 初始化和工具函数**
- [ ] 导入依赖（codeindex, pathlib, os, re, typing）
- [ ] 定义数据类（FileInfo, FileFunction, DirectoryFunction）
- [ ] 实现 `_find_codeindex_db()` - 自动查找数据库路径
  - 查找 `.codeindex/*.db` 文件
  - 支持配置指定路径
- [ ] 实现 `_get_file_language()` - 根据扩展名识别语言
  - 支持：go, py, ts, js, java, rs 等

**Step 2: 文件扫描功能**
- [ ] 实现 `_scan_directory()` - 递归扫描目录
  - 使用 `pathlib.Path.rglob()` 或 `os.walk()`
  - 过滤文件（按语言扩展名）
  - 排除常见目录（.git, node_modules, __pycache__ 等）
  - 构建文件列表和目录树结构
- [ ] 实现 `_should_exclude()` - 判断是否排除路径

**Step 3: 符号提取功能**
- [ ] 定义语言正则模式字典 `_SYMBOL_PATTERNS`
  - Go: `type (\w+) struct`, `func (\w+)`, `type (\w+) interface`
  - Python: `class (\w+)`, `def (\w+)`
  - TypeScript: `class (\w+)`, `interface (\w+)`, `function (\w+)`
  - Java: `class (\w+)`, `interface (\w+)`
- [ ] 实现 `_extract_symbols_from_file()` - 从文件提取符号名
  - 读取文件内容
  - 使用正则匹配符号名
  - 返回符号名列表（去重）

**Step 4: CodeIndex 查询封装**
- [ ] 初始化 CodeIndexClient（在 `__init__` 或 `detect()` 中）
- [ ] 实现 `_query_symbols_batch()` - 批量查询符号
  - 使用 `client.find_symbols()` 查询
  - 返回符号记录列表（包含 chunkSummary）
- [ ] 实现 `_get_symbol_summaries()` - 提取摘要
  - 从符号记录中提取 `chunkSummary` 字段
  - 过滤空摘要

**Step 5: 功能推断逻辑**
- [ ] 实现 `_extract_keywords()` - 从摘要提取关键词
  - 简单分词（按空格、标点）
  - 过滤停用词（可选）
- [ ] 实现 `_categorize_file()` - 文件分类
  - 基于关键词匹配：service/model/controller/utils/test
  - 返回分类字符串
- [ ] 实现 `_infer_file_function()` - 推断文件功能
  - 聚合所有符号的摘要
  - 提取关键词
  - 生成简洁描述（取前2-3个摘要的关键信息）
  - 返回 FileFunction 字典

**Step 6: 目录分析逻辑**
- [ ] 实现 `_analyze_directory()` - 分析目录功能
  - 统计目录下文件的分类
  - 多数投票决定目录分类
  - 聚合文件描述生成目录描述
- [ ] 实现 `_build_directory_tree()` - 构建目录树结构
  - 递归分析子目录
  - 从叶子目录向上分析

**Step 7: 格式化输出**
- [ ] 实现 `_format_tree_text()` - 文本格式输出
  - 构建树形结构（使用 `├──`, `└──`, `│` 等符号）
  - 添加文件注释（文件名 + 功能描述）
  - 添加目录注释（目录名 + 功能描述）
- [ ] 实现 `_format_tree()` - 格式化入口
  - 支持 text/markdown 格式（先实现 text）

**Step 8: 主入口整合**
- [ ] 实现 `detect()` - 主检测流程
  - 1. 验证配置和数据库
  - 2. 扫描目录
  - 3. 提取符号（每个文件）
  - 4. 批量查询 CodeIndex
  - 5. 推断文件功能
  - 6. 分析目录功能
  - 7. 格式化输出
  - 8. 返回结果字典
- [ ] 实现 `detect_to_file()` - 输出到文件（可选）

#### Phase 3: 测试和优化
- [ ] 错误处理完善
  - 数据库不存在时的友好提示
  - 符号未找到时的降级处理
  - 摘要缺失时的处理
- [ ] 日志输出（使用 print 或 logging）
- [ ] 性能优化（批量查询优化）

### 技术要点

1. **CodeIndex SDK 使用**：
   ```python
   from codeindex import CodeIndexClient
   client = CodeIndexClient(db_path)
   client.start()
   symbols = client.find_symbols(name="SymbolName", language="go")
   # symbols[0]['chunkSummary'] 包含摘要
   client.close()
   ```

2. **符号提取策略**：
   - 先用正则快速提取符号名
   - 再用 CodeIndex 精确查询和获取摘要
   - 避免直接解析 AST（CodeIndex 已处理）

3. **功能推断策略**：
   - 优先使用 `chunkSummary`（AI 生成的摘要）
   - 如果摘要缺失，使用符号名和文件路径推断
   - 分类基于关键词匹配（简单但有效）

4. **输出格式**：
   ```
   project/
   ├── src/                    # 源代码目录
   │   ├── service/            # 服务层：处理业务逻辑
   │   │   ├── user_service.go # 用户服务：用户CRUD操作
   │   │   └── auth_service.go # 认证服务：登录/注册/权限
   │   └── model/              # 数据模型层
   │       └── user.go         # 用户模型：用户数据结构定义
   └── tests/                  # 测试目录
   ```
