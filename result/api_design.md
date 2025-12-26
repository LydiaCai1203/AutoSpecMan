# API 设计规范

## API 架构类型

- **主要架构**: gRPC
- **框架**: echo

## URL 路径规范

- **命名风格**: `unknown`
- **平均深度**: 1.0 层

**示例**:
  - `/health`

## HTTP 方法使用规范


## 请求/响应格式规范

- **请求格式**: JSON（推断）
- **响应格式**: JSON（推断）
- **统一封装**: AuthenticateResponse (main.AuthenticateResponse)

## 状态码使用规范

- **状态码**: 未检测到状态码使用

## API 版本管理

- **版本管理**: 未检测到明确的版本管理方式
