"""
API 设计规范检测器
使用自然语言查询检测项目的 API 设计规范，包括：
- RESTful/GraphQL/gRPC 设计原则
- URL 路径规范
- HTTP 方法使用规范
- 请求/响应格式规范
- 状态码使用规范
- API 版本管理
"""

import re
from pathlib import Path
from typing import Dict, List, Optional, Any
from collections import defaultdict, Counter

from detector.base_detector import BaseDetector, CodeIndexQuery
from utils.logger import logger


# ============================================================================
# 路由提取正则表达式（按语言和框架）
# ============================================================================

ROUTE_PATTERNS = {
    'go': [
        # Echo: e.GET("/path", handler)
        (r'(?:router|e|r)\.(GET|POST|PUT|DELETE|PATCH)\(["\']([^"\']+)["\']', 'echo'),
        # Gin: router.GET("/path", handler)
        (r'router\.(GET|POST|PUT|DELETE|PATCH)\(["\']([^"\']+)["\']', 'gin'),
    ],
    'python': [
        # FastAPI: @app.get("/path")
        (r'@(?:app|router)\.(get|post|put|delete|patch)\(["\']([^"\']+)["\']', 'fastapi'),
        # Flask: @app.route("/path", methods=["GET"])
        (r'@(?:app|router)\.route\(["\']([^"\']+)["\'],\s*methods=\[["\'](GET|POST|PUT|DELETE|PATCH)["\']', 'flask'),
    ],
    'typescript': [
        # Express: router.get("/path", handler)
        (r'(?:router|app)\.(get|post|put|delete|patch)\(["\']([^"\']+)["\']', 'express'),
    ],
    'javascript': [
        # Express: router.get("/path", handler)
        (r'(?:router|app)\.(get|post|put|delete|patch)\(["\']([^"\']+)["\']', 'express'),
    ],
    'java': [
        # Spring: @GetMapping("/path")
        (r'@(?:GetMapping|PostMapping|PutMapping|DeleteMapping|RequestMapping)\(["\']([^"\']+)["\']', 'spring'),
    ],
}

# HTTP 状态码模式
STATUS_CODE_PATTERN = re.compile(r'\b(200|201|204|400|401|403|404|500|502|503)\b')

# HTTP 方法模式
HTTP_METHOD_PATTERN = re.compile(r'\b(GET|POST|PUT|DELETE|PATCH|HEAD|OPTIONS)\b', re.IGNORECASE)


class ApiDesignDetector(BaseDetector, CodeIndexQuery):
    """API 设计规范检测器"""
    
    def __init__(
        self,
        config_path: Optional[str] = None,
        config_type: Optional[str] = 'api'
    ):
        """
        初始化检测器
        
        Args:
            config_path: 配置文件路径
            config_type: 配置类型
        """
        BaseDetector.__init__(self, config_path=config_path, config_type=config_type)
        CodeIndexQuery.__init__(self, codeindex_db_path=self.config.codeindex_db_path or '')
    
    def _read_file_from_location(self, location: Dict[str, Any]) -> Optional[str]:
        """
        从 location 信息读取文件内容
        
        Args:
            location: 位置信息字典，包含 path 字段（可能是相对路径）
            
        Returns:
            文件内容字符串，如果读取失败返回 None
        """
        file_path = location.get('path')
        if not file_path:
            return None
        
        # 如果是相对路径，转换为绝对路径
        if not Path(file_path).is_absolute():
            file_path = str(Path(self.config.root_path) / file_path)
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()
        except Exception as e:
            logger.warning(f"无法读取文件 {file_path}: {e}")
            return None
    
    def _extract_routes_from_code(self, code: str, language: str) -> List[Dict[str, str]]:
        """
        从代码中提取路由定义
        
        Args:
            code: 代码内容
            language: 语言类型
            
        Returns:
            路由列表，每个路由包含 method 和 path
        """
        routes = []
        patterns = ROUTE_PATTERNS.get(language, [])
        
        for pattern, framework in patterns:
            matches = re.finditer(pattern, code)
            for match in matches:
                if language == 'python' and framework == 'flask':
                    # Flask 的特殊格式：route("/path", methods=["GET"])
                    path = match.group(1)
                    method = match.group(2).upper()
                else:
                    # 标准格式：method("/path")
                    method = match.group(1).upper()
                    path = match.group(2)
                
                routes.append({
                    'method': method,
                    'path': path,
                    'framework': framework
                })
        
        return routes
    
    def _extract_http_methods_from_code(self, code: str) -> List[str]:
        """
        从代码中提取 HTTP 方法调用
        
        Args:
            code: 代码内容
            
        Returns:
            HTTP 方法列表
        """
        methods = []
        matches = HTTP_METHOD_PATTERN.finditer(code)
        for match in matches:
            method = match.group(1).upper()
            methods.append(method)
        return methods
    
    def _extract_status_codes_from_code(self, code: str) -> List[int]:
        """
        从代码中提取状态码使用
        
        Args:
            code: 代码内容
            
        Returns:
            状态码列表
        """
        status_codes = []
        matches = STATUS_CODE_PATTERN.finditer(code)
        for match in matches:
            status_code = int(match.group(1))
            status_codes.append(status_code)
        return status_codes
    
    def _analyze_path_naming_style(self, paths: List[str]) -> str:
        """
        分析路径命名风格
        
        Args:
            paths: 路径列表
            
        Returns:
            命名风格：'camelCase', 'snake_case', 'kebab-case', 'mixed', 'unknown'
        """
        if not paths:
            return 'unknown'
        
        camel_case_count = 0
        snake_case_count = 0
        kebab_case_count = 0
        
        for path in paths:
            # 移除路径参数（如 :id, {id}）
            clean_path = re.sub(r'[:{][^}/]+', '', path)
            # 移除前导斜杠
            clean_path = clean_path.lstrip('/')
            
            if not clean_path:
                continue
            
            # 检查命名风格
            if re.search(r'[a-z][A-Z]', clean_path):
                camel_case_count += 1
            elif '_' in clean_path:
                snake_case_count += 1
            elif '-' in clean_path:
                kebab_case_count += 1
        
        total = camel_case_count + snake_case_count + kebab_case_count
        if total == 0:
            return 'unknown'
        
        # 多数投票
        if camel_case_count >= snake_case_count and camel_case_count >= kebab_case_count:
            return 'camelCase'
        elif snake_case_count >= kebab_case_count:
            return 'snake_case'
        else:
            return 'kebab-case'
    
    def _calculate_path_depth(self, path: str) -> int:
        """
        计算路径深度
        
        Args:
            path: URL 路径
            
        Returns:
            路径深度（层级数）
        """
        # 移除路径参数
        clean_path = re.sub(r'[:{][^}/]+', '', path)
        # 移除前导和尾随斜杠，分割
        parts = [p for p in clean_path.strip('/').split('/') if p]
        return len(parts)
    
    def _detect_api_architecture(self) -> Dict[str, Any]:
        """
        检测 API 架构类型
        
        Returns:
            架构信息字典
        """
        logger.info("检测 API 架构类型...")
        
        # 查询架构类型
        arch_results = self.semantic_search(
            "REST RESTful GraphQL gRPC API 架构",
            top_k=10,
            min_similarity=0.6
        )
        
        # 查询框架类型
        framework_results = self.semantic_search(
            "echo gin express fastapi flask spring 框架",
            top_k=10,
            min_similarity=0.6
        )
        
        # 分析架构类型
        arch_type = "RESTful API"  # 默认值
        arch_keywords = {
            'rest': 0,
            'restful': 0,
            'graphql': 0,
            'grpc': 0,
        }
        
        for result in arch_results:
            symbol = result.get('symbol', {})
            summary = symbol.get('chunkSummary', '').lower()
            name = symbol.get('name', '').lower()
            qualified_name = symbol.get('qualifiedName', '').lower()
            
            text = f"{summary} {name} {qualified_name}"
            for keyword in arch_keywords:
                if keyword in text:
                    arch_keywords[keyword] += 1
        
        # 确定架构类型
        if arch_keywords['graphql'] > arch_keywords['rest'] and arch_keywords['graphql'] > arch_keywords['restful']:
            arch_type = "GraphQL"
        elif arch_keywords['grpc'] > arch_keywords['rest'] and arch_keywords['grpc'] > arch_keywords['restful']:
            arch_type = "gRPC"
        elif arch_keywords['restful'] > 0 or arch_keywords['rest'] > 0:
            arch_type = "RESTful API"
        
        # 分析框架类型
        framework = None
        framework_keywords = {
            'echo': 0,
            'gin': 0,
            'express': 0,
            'fastapi': 0,
            'flask': 0,
            'spring': 0,
        }
        
        for result in framework_results:
            symbol = result.get('symbol', {})
            summary = symbol.get('chunkSummary', '').lower()
            name = symbol.get('name', '').lower()
            qualified_name = symbol.get('qualifiedName', '').lower()
            
            text = f"{summary} {name} {qualified_name}"
            for keyword in framework_keywords:
                if keyword in text:
                    framework_keywords[keyword] += 1
        
        # 确定框架（选择出现次数最多的）
        if any(framework_keywords.values()):
            framework = max(framework_keywords.items(), key=lambda x: x[1])[0]
        
        return {
            'architecture': arch_type,
            'framework': framework
        }
    
    def _detect_url_path_standards(self) -> Dict[str, Any]:
        """
        检测 URL 路径规范
        
        Returns:
            路径规范信息字典
        """
        logger.info("检测 URL 路径规范...")
        
        # 查询路由相关代码
        results = self.semantic_search(
            "URL 路径规范 路由路径 路由注册",
            top_k=30,
            min_similarity=0.6
        )
        
        all_routes = []
        file_paths = set()
        
        # 从查询结果中提取文件路径
        for result in results:
            location = result.get('location', {})
            file_path = location.get('path')
            
            if file_path and file_path not in file_paths:
                file_paths.add(file_path)
                code = self._read_file_from_location(location)
                if code:
                    # 转换为绝对路径用于语言识别
                    abs_file_path = str(Path(self.config.root_path) / file_path) if not Path(file_path).is_absolute() else file_path
                    language = self._get_file_language(abs_file_path)
                    if language:
                        routes = self._extract_routes_from_code(code, language)
                        all_routes.extend(routes)
        
        # 如果没有找到路由，尝试更广泛的查询
        if not all_routes:
            logger.info("未找到路由，尝试更广泛的查询...")
            results = self.semantic_search(
                "router GET POST 路由定义",
                top_k=30,
                min_similarity=0.5
            )
            for result in results:
                location = result.get('location', {})
                file_path = location.get('path')
                if file_path and file_path not in file_paths:
                    file_paths.add(file_path)
                    code = self._read_file_from_location(location)
                    if code:
                        # 转换为绝对路径用于语言识别
                        abs_file_path = str(Path(self.config.root_path) / file_path) if not Path(file_path).is_absolute() else file_path
                        language = self._get_file_language(abs_file_path)
                        if language:
                            routes = self._extract_routes_from_code(code, language)
                            all_routes.extend(routes)
        
        if not all_routes:
            return {
                'naming_style': 'unknown',
                'average_depth': 0.0,
                'examples': []
            }
        
        # 提取所有路径
        paths = [route['path'] for route in all_routes]
        
        # 分析命名风格
        naming_style = self._analyze_path_naming_style(paths)
        
        # 计算平均深度
        depths = [self._calculate_path_depth(path) for path in paths]
        average_depth = sum(depths) / len(depths) if depths else 0.0
        
        # 获取示例路径（去重，最多5个）
        unique_paths = list(dict.fromkeys(paths))[:5]
        
        return {
            'naming_style': naming_style,
            'average_depth': round(average_depth, 1),
            'examples': unique_paths,
            'total_routes': len(all_routes)
        }
    
    def _detect_http_methods(self) -> Dict[str, Any]:
        """
        检测 HTTP 方法使用规范
        
        Returns:
            HTTP 方法使用信息字典
        """
        logger.info("检测 HTTP 方法使用规范...")
        
        # 查询 HTTP 方法相关代码
        results = self.semantic_search(
            "HTTP 方法 GET POST PUT DELETE",
            top_k=30,
            min_similarity=0.6
        )
        
        method_counter = Counter()
        route_methods = defaultdict(list)
        
        # 从查询结果中提取文件路径
        file_paths = set()
        for result in results:
            location = result.get('location', {})
            file_path = location.get('path')
            if file_path and file_path not in file_paths:
                file_paths.add(file_path)
                code = self._read_file_from_location(location)
                if code:
                    methods = self._extract_http_methods_from_code(code)
                    method_counter.update(methods)
                    
                    # 同时提取路由信息（用于统计每个路径的方法）
                    # 转换为绝对路径用于语言识别
                    abs_file_path = str(Path(self.config.root_path) / file_path) if not Path(file_path).is_absolute() else file_path
                    language = self._get_file_language(abs_file_path)
                    if language:
                        routes = self._extract_routes_from_code(code, language)
                        for route in routes:
                            route_methods[route['path']].append(route['method'])
                            method_counter[route['method']] += 1
        
        # 如果没有找到方法，尝试更广泛的查询
        if not method_counter:
            logger.info("未找到 HTTP 方法，尝试更广泛的查询...")
            results = self.semantic_search(
                "router GET POST 路由方法",
                top_k=30,
                min_similarity=0.5
            )
            for result in results:
                location = result.get('location', {})
                file_path = location.get('path')
                if file_path and file_path not in file_paths:
                    file_paths.add(file_path)
                    code = self._read_file_from_location(location)
                    if code:
                        # 转换为绝对路径用于语言识别
                        abs_file_path = str(Path(self.config.root_path) / file_path) if not Path(file_path).is_absolute() else file_path
                        language = self._get_file_language(abs_file_path)
                        if language:
                            routes = self._extract_routes_from_code(code, language)
                            for route in routes:
                                route_methods[route['path']].append(route['method'])
                                method_counter[route['method']] += 1
        
        # 格式化结果
        method_stats = {}
        for method, count in method_counter.most_common():
            method_stats[method] = count
        
        # 按路径分组统计
        path_method_stats = {}
        for path, methods in route_methods.items():
            unique_methods = list(set(methods))
            path_method_stats[path] = {
                'methods': unique_methods,
                'count': len(unique_methods)
            }
        
        return {
            'method_stats': method_stats,
            'path_method_stats': path_method_stats
        }
    
    def _detect_request_response_formats(self) -> Dict[str, Any]:
        """
        检测请求/响应格式规范
        
        Returns:
            请求/响应格式信息字典
        """
        logger.info("检测请求/响应格式规范...")
        
        # 查询统一响应封装
        wrapper_results = self.semantic_search(
            "统一响应封装 BaseResponse ResponseWrapper",
            top_k=10,
            min_similarity=0.6
        )
        
        unified_wrapper = None
        for result in wrapper_results:
            symbol = result.get('symbol', {})
            name = symbol.get('name', '')
            qualified_name = symbol.get('qualifiedName', '')
            
            # 检查是否是响应封装类
            if any(keyword in name.lower() or keyword in qualified_name.lower() 
                   for keyword in ['response', 'wrapper', 'result', 'result']):
                location = result.get('location', {})
                code = self._read_file_from_location(location)
                if code:
                    unified_wrapper = {
                        'name': name,
                        'qualified_name': qualified_name,
                        'location': location.get('path')
                    }
                    break
        
        # 查询请求/响应格式
        format_results = self.semantic_search(
            "请求响应格式 request response body JSON",
            top_k=10,
            min_similarity=0.6
        )
        
        # 分析格式类型
        request_format = "JSON（推断）"
        response_format = "JSON（推断）"
        
        json_count = 0
        xml_count = 0
        protobuf_count = 0
        
        for result in format_results:
            symbol = result.get('symbol', {})
            summary = symbol.get('chunkSummary', '').lower()
            name = symbol.get('name', '').lower()
            
            text = f"{summary} {name}"
            if 'json' in text:
                json_count += 1
            if 'xml' in text:
                xml_count += 1
            if 'protobuf' in text or 'proto' in text:
                protobuf_count += 1
        
        # 确定格式（多数投票）
        if protobuf_count > json_count and protobuf_count > xml_count:
            request_format = "Protobuf"
            response_format = "Protobuf"
        elif xml_count > json_count:
            request_format = "XML"
            response_format = "XML"
        else:
            request_format = "JSON（推断）"
            response_format = "JSON（推断）"
        
        return {
            'request_format': request_format,
            'response_format': response_format,
            'unified_wrapper': unified_wrapper
        }
    
    def _detect_status_codes(self) -> Dict[str, Any]:
        """
        检测状态码使用规范
        
        Returns:
            状态码使用信息字典
        """
        logger.info("检测状态码使用规范...")
        
        # 查询状态码相关代码
        results = self.semantic_search(
            "状态码 HTTP status code 200 404 500",
            top_k=30,
            min_similarity=0.6
        )
        
        status_code_counter = Counter()
        file_paths = set()
        
        for result in results:
            location = result.get('location', {})
            file_path = location.get('path')
            if file_path and file_path not in file_paths:
                file_paths.add(file_path)
                code = self._read_file_from_location(location)
                if code:
                    status_codes = self._extract_status_codes_from_code(code)
                    status_code_counter.update(status_codes)
        
        if not status_code_counter:
            return {
                'status_codes': [],
                'message': '未检测到状态码使用'
            }
        
        # 格式化结果
        status_codes = []
        for code, count in status_code_counter.most_common():
            status_codes.append({
                'code': code,
                'count': count
            })
        
        return {
            'status_codes': status_codes,
            'message': None
        }
    
    def _detect_api_versioning(self) -> Dict[str, Any]:
        """
        检测 API 版本管理
        
        Returns:
            版本管理信息字典
        """
        logger.info("检测 API 版本管理...")
        
        # 查询版本管理相关代码
        results = self.semantic_search(
            "API 版本管理 version control v1 v2",
            top_k=20,
            min_similarity=0.6
        )
        
        version_patterns = []
        
        # 从查询结果中查找版本模式
        for result in results:
            symbol = result.get('symbol', {})
            summary = symbol.get('chunkSummary', '')
            name = symbol.get('name', '')
            qualified_name = symbol.get('qualifiedName', '')
            
            text = f"{summary} {name} {qualified_name}"
            
            # 查找版本路径模式
            version_matches = re.finditer(r'[/]v(\d+)[/]|[/]api[/]v(\d+)[/]|version[\s:=]+["\']?v(\d+)', text, re.IGNORECASE)
            for match in version_matches:
                version = match.group(1) or match.group(2) or match.group(3)
                if version:
                    version_patterns.append(f"v{version}")
        
        # 同时从路径规范中查找版本模式
        path_standards = self._detect_url_path_standards()
        for path in path_standards.get('examples', []):
            version_match = re.search(r'[/]v(\d+)[/]|[/]api[/]v(\d+)[/]', path)
            if version_match:
                version = version_match.group(1) or version_match.group(2)
                if version:
                    version_patterns.append(f"v{version}")
        
        if version_patterns:
            unique_versions = sorted(list(set(version_patterns)))
            return {
                'versioning': f"路径版本管理（检测到版本: {', '.join(unique_versions)}）"
            }
        else:
            return {
                'versioning': '未检测到明确的版本管理方式'
            }
    
    def detect(self) -> Dict[str, Any]:
        """
        执行检测流程
        
        Returns:
            检测结果字典
        """
        logger.info("开始 API 设计规范检测...")
        
        # 执行各项检测
        architecture = self._detect_api_architecture()
        url_path_standards = self._detect_url_path_standards()
        http_methods = self._detect_http_methods()
        request_response_formats = self._detect_request_response_formats()
        status_codes = self._detect_status_codes()
        api_versioning = self._detect_api_versioning()
        
        return {
            'architecture': architecture,
            'url_path_standards': url_path_standards,
            'http_methods': http_methods,
            'request_response_formats': request_response_formats,
            'status_codes': status_codes,
            'api_versioning': api_versioning
        }
    
    def _format_output(self, results: Dict[str, Any]) -> str:
        """
        格式化输出为 Markdown
        
        Args:
            results: 检测结果字典
            
        Returns:
            Markdown 格式字符串
        """
        lines = ["# API 设计规范", ""]
        
        # API 架构类型
        lines.append("## API 架构类型")
        lines.append("")
        arch = results.get('architecture', {})
        arch_type = arch.get('architecture', 'RESTful API')
        framework = arch.get('framework')
        if framework:
            lines.append(f"- **主要架构**: {arch_type}")
            lines.append(f"- **框架**: {framework}")
        else:
            lines.append(f"- **主要架构**: {arch_type}")
        lines.append("")
        
        # URL 路径规范
        lines.append("## URL 路径规范")
        lines.append("")
        url_standards = results.get('url_path_standards', {})
        naming_style = url_standards.get('naming_style', 'unknown')
        avg_depth = url_standards.get('average_depth', 0.0)
        examples = url_standards.get('examples', [])
        
        lines.append(f"- **命名风格**: `{naming_style}`")
        lines.append(f"- **平均深度**: {avg_depth} 层")
        lines.append("")
        
        if examples:
            lines.append("**示例**:")
            for example in examples[:5]:
                lines.append(f"  - `{example}`")
        else:
            lines.append("**示例**: 未检测到路径示例")
        lines.append("")
        
        # HTTP 方法使用规范
        lines.append("## HTTP 方法使用规范")
        lines.append("")
        http_methods_info = results.get('http_methods', {})
        method_stats = http_methods_info.get('method_stats', {})
        path_method_stats = http_methods_info.get('path_method_stats', {})
        
        if method_stats:
            # 按方法分组统计路径
            method_paths = defaultdict(list)
            for path, info in path_method_stats.items():
                for method in info['methods']:
                    method_paths[method].append(path)
            
            # 按路径分组，显示每个路径使用的方法
            path_method_groups = defaultdict(list)
            for path, info in path_method_stats.items():
                methods = info['methods']
                if len(methods) == 1:
                    method_name = methods[0]
                else:
                    method_name = "多种方法"
                path_method_groups[method_name].append(path)
            
            # 输出格式：- **路径**: 方法 (数量)
            for method, paths in sorted(path_method_groups.items()):
                if len(paths) == 1:
                    lines.append(f"- **{paths[0]}**: {method} (1 个路由)")
                else:
                    # 显示第一个路径和总数
                    lines.append(f"- **{paths[0]}**: {method} ({len(paths)} 个路由)")
        else:
            lines.append("- **HTTP 方法**: 未检测到 HTTP 方法使用")
        lines.append("")
        
        # 请求/响应格式规范
        lines.append("## 请求/响应格式规范")
        lines.append("")
        formats = results.get('request_response_formats', {})
        request_format = formats.get('request_format', 'JSON（推断）')
        response_format = formats.get('response_format', 'JSON（推断）')
        unified_wrapper = formats.get('unified_wrapper')
        
        lines.append(f"- **请求格式**: {request_format}")
        lines.append(f"- **响应格式**: {response_format}")
        if unified_wrapper:
            lines.append(f"- **统一封装**: {unified_wrapper.get('name', '')} ({unified_wrapper.get('qualified_name', '')})")
        lines.append("")
        
        # 状态码使用规范
        lines.append("## 状态码使用规范")
        lines.append("")
        status_info = results.get('status_codes', {})
        status_codes_list = status_info.get('status_codes', [])
        status_message = status_info.get('message')
        
        if status_codes_list:
            status_display = ", ".join([f"{s['code']} ({s['count']}次)" for s in status_codes_list[:10]])
            lines.append(f"- **状态码**: {status_display}")
        elif status_message:
            lines.append(f"- **状态码**: {status_message}")
        else:
            lines.append("- **状态码**: 未检测到状态码使用")
        lines.append("")
        
        # API 版本管理
        lines.append("## API 版本管理")
        lines.append("")
        versioning = results.get('api_versioning', {})
        versioning_str = versioning.get('versioning', '未检测到明确的版本管理方式')
        lines.append(f"- **版本管理**: {versioning_str}")
        lines.append("")
        
        return "\n".join(lines)
    
    def detect_to_file(self, output_path: str):
        """
        检测并输出到文件
        
        Args:
            output_path: 输出文件路径
        """
        result = self.detect()
        formatted_output = self._format_output(result)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(formatted_output)
        
        logger.info(f"✅ 结果已保存到: {output_path}")
