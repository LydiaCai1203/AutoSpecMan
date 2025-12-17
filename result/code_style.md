# 项目命名习惯分析报告

## 概览

- 检测文件数: 121
- 检测到的语言: go, typescript, python

## GO 命名习惯

**总符号数**: 4552

### exported_function

**主要命名风格**: `PascalCase` (99.5%)

| 命名模式 | 数量 | 占比 | 示例 |
|---------|------|------|------|
| `PascalCase` | 2860 | 99.5% | NewAgentServiceClient, Sync, Terminal... |
| `other` | 13 | 0.5% | TestRequestID_MarshalJSON, TestRequestID_UnmarshalJSON, TestJSONRPCMessage_Request... |

### function

**主要命名风格**: `camelCase` (68.3%)

| 命名模式 | 数量 | 占比 | 示例 |
|---------|------|------|------|
| `camelCase` | 522 | 68.3% | mustEmbedUnimplementedAgentServiceServer, testEmbeddedByValue, init... |
| `other` | 230 | 30.1% | isAgentTTL_Ttl, isAgentTTL_Ttl, isAgentTTL_Ttl... |
| `_private_other` | 8 | 1.0% | _AgentService_Sync_Handler, _AgentService_Terminal_Handler, _AgentService_FileManager_Handler... |
| `snake_case` | 4 | 0.5% | file_agent_proto_init, file_orchestrator_proto_init, file_agent_proto_init... |

### type

**主要命名风格**: `PascalCase` (64.6%)

| 命名模式 | 数量 | 占比 | 示例 |
|---------|------|------|------|
| `PascalCase` | 591 | 64.6% | AgentServiceClient, AgentServiceServer, UnimplementedAgentServiceServer... |
| `other` | 282 | 30.8% | AgentService_SyncClient, AgentService_TerminalClient, AgentService_FileManagerClient... |
| `camelCase` | 42 | 4.6% | agentServiceClient, x, x... |

## TYPESCRIPT 命名习惯

**总符号数**: 1

### function

**主要命名风格**: `camelCase` (100.0%)

| 命名模式 | 数量 | 占比 | 示例 |
|---------|------|------|------|
| `camelCase` | 1 | 100.0% | handleResize |

## PYTHON 命名习惯

**总符号数**: 16

### class

**主要命名风格**: `PascalCase` (100.0%)

| 命名模式 | 数量 | 占比 | 示例 |
|---------|------|------|------|
| `PascalCase` | 2 | 100.0% | GatewayMonitor, OpenAIToolTester |

### function

**主要命名风格**: `snake_case` (90.0%)

| 命名模式 | 数量 | 占比 | 示例 |
|---------|------|------|------|
| `snake_case` | 9 | 90.0% | start_gateway, stop_gateway, get_tool_call_summary... |
| `camelCase` | 1 | 10.0% | main |

### private_function

**主要命名风格**: `_private_other` (50.0%)

| 命名模式 | 数量 | 占比 | 示例 |
|---------|------|------|------|
| `_private_other` | 2 | 50.0% | __init__, __init__ |
| `_private_snake` | 2 | 50.0% | _monitor_logs, _is_tool_call_log |

## 总结

### GO

- **exported_function**: 主要使用 `PascalCase`
- **function**: 主要使用 `camelCase`
- **type**: 主要使用 `PascalCase`

### TYPESCRIPT

- **function**: 主要使用 `camelCase`

### PYTHON

- **class**: 主要使用 `PascalCase`
- **function**: 主要使用 `snake_case`
- **private_function**: 主要使用 `_private_other`

