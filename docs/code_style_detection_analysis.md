# 代码风格规范静态检测可行性分析

## 概述

基于项目现有的 Tree-sitter AST 解析能力和静态分析技术，分析各项代码风格规范的检测可行性。

---

## 1. 缩进、换行、括号使用 ✅ **完全可检测**

### 检测方法
- **AST + 源码文本分析**：结合 AST 节点位置信息和原始源码文本

### 具体检测项

#### 1.1 缩进一致性
- ✅ **可检测**：分析每行开头的空白字符
  - 检测混合使用空格和 Tab
  - 检测缩进宽度不一致（如 2 空格 vs 4 空格）
  - 检测缩进层级错误
  
**实现方式**：
```python
# 读取文件原始内容，逐行分析
for line_num, line in enumerate(file_content.splitlines(), 1):
    leading_whitespace = len(line) - len(line.lstrip())
    if '\t' in line[:leading_whitespace]:
        # 检测到 Tab
    # 统计缩进宽度
```

#### 1.2 换行规范
- ✅ **可检测**：
  - 行尾空格/制表符
  - 文件末尾空行
  - 连续空行数量
  - 操作符换行位置（如 `+` 在行首还是行尾）

**实现方式**：
```python
# 检测行尾空格
if line.rstrip() != line:
    violations.append("行尾有空格")

# 检测文件末尾空行
if not file_content.endswith('\n'):
    violations.append("文件末尾缺少空行")
```

#### 1.3 括号使用风格
- ✅ **可检测**：通过 AST 节点位置信息
  - K&R 风格：`if (condition) {`
  - Allman 风格：`if (condition)\n{`
  - 括号位置一致性

**实现方式**：
```python
# 通过 AST 获取括号位置
if_node = ast.get_if_statement()
opening_brace_line = ast.get_brace_position(if_node)
if_line = if_node.start_line

# 检测括号是否在同一行
if opening_brace_line != if_line:
    # Allman 风格
else:
    # K&R 风格
```

#### 1.4 行长度限制
- ✅ **可检测**：直接统计每行字符数
```python
if len(line) > max_line_length:
    violations.append(f"第 {line_num} 行超过 {max_line_length} 字符")
```

---

## 2. 命名约定（变量、函数、类、常量）✅ **完全可检测**

### 检测方法
- **AST 符号提取**：项目已有符号提取能力，可直接复用

### 具体检测项

#### 2.1 变量命名
- ✅ **可检测**：通过 AST 提取变量声明节点
  - Python: `snake_case` (如 `user_name`)
  - JavaScript/TypeScript: `camelCase` (如 `userName`)
  - Go: `camelCase` 或 `mixedCaps`
  - Java: `camelCase`

**实现方式**：
```python
# 从 AST 提取变量节点
variables = ast.extract_variables()

for var in variables:
    name = var.name
    # Python: 检查 snake_case
    if not re.match(r'^[a-z][a-z0-9_]*$', name):
        violations.append(f"变量 {name} 不符合 snake_case 规范")
    
    # TypeScript: 检查 camelCase
    if not re.match(r'^[a-z][a-zA-Z0-9]*$', name):
        violations.append(f"变量 {name} 不符合 camelCase 规范")
```

#### 2.2 函数/方法命名
- ✅ **可检测**：通过 AST 提取函数节点
  - Python: `snake_case` (如 `get_user_info`)
  - JavaScript/TypeScript: `camelCase` (如 `getUserInfo`)
  - Go: `PascalCase` 导出，`camelCase` 私有
  - Java: `camelCase`

**实现方式**：
```python
functions = ast.extract_functions()

for func in functions:
    name = func.name
    is_exported = func.is_exported
    
    # Go: 导出函数 PascalCase，私有函数 camelCase
    if is_exported:
        if not re.match(r'^[A-Z]', name):
            violations.append(f"导出函数 {name} 应以大写字母开头")
    else:
        if not re.match(r'^[a-z]', name):
            violations.append(f"私有函数 {name} 应以小写字母开头")
```

#### 2.3 类命名
- ✅ **可检测**：通过 AST 提取类节点
  - Python: `PascalCase` (如 `UserService`)
  - TypeScript/Java: `PascalCase`
  - Go: 接口 `PascalCase`，结构体 `PascalCase`

**实现方式**：
```python
classes = ast.extract_classes()

for cls in classes:
    name = cls.name
    if not re.match(r'^[A-Z][a-zA-Z0-9]*$', name):
        violations.append(f"类 {name} 不符合 PascalCase 规范")
```

#### 2.4 常量命名
- ✅ **可检测**：通过 AST 识别常量声明
  - Python: `UPPER_SNAKE_CASE` (如 `MAX_RETRY_COUNT`)
  - TypeScript/JavaScript: `UPPER_SNAKE_CASE` 或 `UPPER_CAMEL_CASE`
  - Go: `UPPER_SNAKE_CASE`
  - Java: `UPPER_SNAKE_CASE`

**实现方式**：
```python
constants = ast.extract_constants()

for const in constants:
    name = const.name
    if not re.match(r'^[A-Z][A-Z0-9_]*$', name):
        violations.append(f"常量 {name} 不符合 UPPER_SNAKE_CASE 规范")
```

#### 2.5 私有成员命名
- ✅ **可检测**：结合可见性信息
  - Python: `_private_method` (单下划线) 或 `__private_method` (双下划线)
  - TypeScript: `private _privateField`
  - Go: 小写开头为包内私有

**实现方式**：
```python
# Python: 检测私有方法
if name.startswith('_') and not name.startswith('__'):
    # 单下划线私有
elif name.startswith('__'):
    # 双下划线私有（名称改写）
```

---

## 3. 注释规范（何时注释、格式）⚠️ **部分可检测**

### 检测方法
- **AST + 文本分析**：提取注释节点，分析格式和位置

### 具体检测项

#### 3.1 注释格式 ✅ **可检测**
- ✅ **可检测**：
  - Python: docstring 格式（`"""..."""`）
  - JavaScript/TypeScript: JSDoc 格式（`/** ... */`）
  - Go: 注释格式（`//` 或 `/* */`）
  - Java: Javadoc 格式（`/** ... */`）

**实现方式**：
```python
# 从 AST 提取注释节点
comments = ast.extract_comments()

for func in functions:
    docstring = func.docstring
    if docstring:
        # Python: 检查 docstring 格式
        if not docstring.startswith('"""') or not docstring.endswith('"""'):
            violations.append(f"函数 {func.name} 的 docstring 格式不正确")
        
        # 检查 docstring 内容格式（参数、返回值等）
        if 'Args:' not in docstring and 'Returns:' not in docstring:
            violations.append(f"函数 {func.name} 缺少标准的 docstring 结构")
```

#### 3.2 函数/类是否有文档注释 ✅ **可检测**
- ✅ **可检测**：检查公共函数/类是否有文档注释

**实现方式**：
```python
for func in functions:
    if func.is_exported and not func.docstring:
        violations.append(f"导出函数 {func.name} 缺少文档注释")

for cls in classes:
    if cls.is_exported and not cls.docstring:
        violations.append(f"导出类 {cls.name} 缺少文档注释")
```

#### 3.3 注释与代码同步性 ⚠️ **部分可检测**
- ⚠️ **部分可检测**：
  - 可以检测注释中的函数名/参数名是否与代码一致
  - 难以检测注释内容是否准确描述代码逻辑

**实现方式**：
```python
# 提取 docstring 中的参数名
docstring_params = extract_params_from_docstring(func.docstring)
# 提取函数实际参数名
actual_params = [p.name for p in func.parameters]

# 检查参数名是否一致
if set(docstring_params) != set(actual_params):
    violations.append(f"函数 {func.name} 的文档注释参数与实际参数不一致")
```

#### 3.4 复杂逻辑是否有注释 ❌ **难以检测**
- ❌ **难以检测**：需要语义理解，判断代码复杂度
  - 可以通过**圈复杂度**作为代理指标
  - 但无法判断注释内容是否合适

**实现方式（代理方案）**：
```python
# 计算圈复杂度
complexity = calculate_cyclomatic_complexity(func)

if complexity > threshold:
    # 检查是否有注释
    if not has_comment_near(func):
        violations.append(f"高复杂度函数 {func.name} (复杂度: {complexity}) 缺少注释")
```

#### 3.5 TODO/FIXME 注释 ✅ **可检测**
- ✅ **可检测**：文本搜索 TODO/FIXME 标记

**实现方式**：
```python
# 搜索 TODO/FIXME 注释
for comment in comments:
    if 'TODO' in comment.text or 'FIXME' in comment.text:
        # 记录 TODO/FIXME 位置
        todos.append({
            'file': file_path,
            'line': comment.line,
            'text': comment.text
        })
```

---

## 4. 代码长度限制（行数、复杂度）✅ **完全可检测**

### 检测方法
- **AST 分析 + 统计计算**

### 具体检测项

#### 4.1 函数行数 ✅ **可检测**
- ✅ **可检测**：通过 AST 节点位置信息计算

**实现方式**：
```python
for func in functions:
    line_count = func.end_line - func.start_line + 1
    if line_count > max_function_lines:
        violations.append(
            f"函数 {func.name} 有 {line_count} 行，超过限制 {max_function_lines} 行"
        )
```

#### 4.2 文件行数 ✅ **可检测**
- ✅ **可检测**：直接统计文件总行数

**实现方式**：
```python
total_lines = len(file_content.splitlines())
if total_lines > max_file_lines:
    violations.append(f"文件有 {total_lines} 行，超过限制 {max_file_lines} 行")
```

#### 4.3 圈复杂度（Cyclomatic Complexity）✅ **可检测**
- ✅ **可检测**：基于 AST 控制流分析

**计算方法**：
- 复杂度 = 1（基础复杂度）
- + 每个 `if`、`while`、`for`、`switch` 语句：+1
- + 每个 `&&`、`||` 逻辑运算符：+1
- + 每个 `catch` 语句：+1

**实现方式**：
```python
def calculate_complexity(func_node):
    complexity = 1  # 基础复杂度
    
    # 遍历 AST 节点
    for node in ast.walk(func_node):
        if node.type in ['if_statement', 'while_statement', 'for_statement']:
            complexity += 1
        elif node.type == 'binary_expression':
            if node.operator in ['&&', '||']:
                complexity += 1
        elif node.type == 'catch_clause':
            complexity += 1
    
    return complexity

for func in functions:
    complexity = calculate_complexity(func.ast_node)
    if complexity > max_complexity:
        violations.append(
            f"函数 {func.name} 圈复杂度为 {complexity}，超过限制 {max_complexity}"
        )
```

#### 4.4 嵌套深度 ✅ **可检测**
- ✅ **可检测**：通过 AST 节点层级计算

**实现方式**：
```python
def calculate_max_nesting_depth(func_node):
    max_depth = 0
    
    def traverse(node, depth):
        nonlocal max_depth
        max_depth = max(max_depth, depth)
        
        # 嵌套结构：if, while, for, try-catch 等
        if node.type in ['if_statement', 'while_statement', 'for_statement', 'try_statement']:
            for child in node.children:
                traverse(child, depth + 1)
        else:
            for child in node.children:
                traverse(child, depth)
    
    traverse(func_node, 0)
    return max_depth

for func in functions:
    nesting_depth = calculate_max_nesting_depth(func.ast_node)
    if nesting_depth > max_nesting_depth:
        violations.append(
            f"函数 {func.name} 最大嵌套深度为 {nesting_depth}，超过限制 {max_nesting_depth}"
        )
```

#### 4.5 参数数量 ✅ **可检测**
- ✅ **可检测**：通过 AST 提取函数参数

**实现方式**：
```python
for func in functions:
    param_count = len(func.parameters)
    if param_count > max_parameters:
        violations.append(
            f"函数 {func.name} 有 {param_count} 个参数，超过限制 {max_parameters} 个"
        )
```

---

## 技术实现方案

### 1. 利用现有基础设施

项目已有：
- ✅ Tree-sitter AST 解析能力
- ✅ 多语言符号提取器（Python、Go、TypeScript、JavaScript、Java、Rust）
- ✅ 文件扫描和索引能力

### 2. 需要新增的能力

#### 2.1 源码文本分析
- 读取文件原始内容（保留空白字符）
- 逐行分析缩进、换行、行长度

#### 2.2 规则引擎
- 可配置的规则系统
- 语言特定的规则集
- 规则优先级和严重程度

#### 2.3 复杂度计算
- 圈复杂度算法
- 嵌套深度计算
- 代码行数统计

### 3. 推荐的技术栈

#### Python 实现（推荐）
- **AST 解析**：复用 CodeIndex 的 Tree-sitter（通过 Python 绑定或调用 Node.js）
- **Python 原生 AST**：对于 Python 文件，可使用 `ast` 模块
- **复杂度计算**：`radon` 库（Python 代码复杂度分析）
- **文本分析**：直接读取文件内容分析

#### 多语言支持
- **Python**: `ast` 模块 + `radon`
- **Go**: 通过 Tree-sitter 解析 + 自定义规则
- **TypeScript/JavaScript**: ESLint 规则引擎（可集成）
- **Java**: Checkstyle 规则（可集成）

---

## 检测能力总结

| 检测项 | 可检测性 | 检测难度 | 备注 |
|--------|---------|---------|------|
| **缩进、换行、括号使用** | ✅ 完全可检测 | 低 | 文本分析 + AST 位置信息 |
| **命名约定** | ✅ 完全可检测 | 低 | AST 符号提取 + 正则匹配 |
| **注释格式** | ✅ 完全可检测 | 低 | AST 注释节点提取 |
| **注释存在性** | ✅ 完全可检测 | 低 | 检查公共符号是否有注释 |
| **注释同步性** | ⚠️ 部分可检测 | 中 | 可检测参数名一致性，难以检测内容准确性 |
| **复杂逻辑注释** | ⚠️ 部分可检测 | 中 | 可通过复杂度代理，但无法判断注释质量 |
| **代码长度限制** | ✅ 完全可检测 | 低 | AST 节点位置信息 |
| **圈复杂度** | ✅ 完全可检测 | 中 | AST 控制流分析 |
| **嵌套深度** | ✅ 完全可检测 | 中 | AST 节点层级分析 |
| **参数数量** | ✅ 完全可检测 | 低 | AST 函数参数提取 |

---

## 结论

**约 85-90% 的代码风格规范可以通过静态检测实现**，主要包括：

✅ **完全可检测**（约 80%）：
- 缩进、换行、括号使用
- 命名约定
- 注释格式和存在性
- 代码长度限制
- 复杂度指标

⚠️ **部分可检测**（约 10%）：
- 注释内容准确性（可通过参数名一致性检测）
- 复杂逻辑注释需求（可通过复杂度代理）

❌ **难以检测**（约 5-10%）：
- 注释内容是否准确描述代码逻辑
- 注释是否"恰到好处"（需要语义理解）

---

## 推荐实现策略

1. **第一阶段**：实现完全可检测的规则（80%）
   - 缩进、换行、括号使用
   - 命名约定
   - 注释格式和存在性
   - 代码长度限制

2. **第二阶段**：实现复杂度相关检测（10%）
   - 圈复杂度计算
   - 嵌套深度检测
   - 基于复杂度的注释建议

3. **第三阶段**：优化和扩展（10%）
   - 注释同步性检测（参数名一致性）
   - 集成现有工具（ESLint、Pylint 等）
   - 规则配置化和可扩展性

