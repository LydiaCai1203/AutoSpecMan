"""
动态项目结构检测器 - 基于 CodeIndex 查询
功能：
1. 扫描目录树结构
2. 提取文件中的符号（类名/结构体名/函数名）
3. 使用 codeindex 查询这些符号，获取自然语言解释
4. 基于查询结果推断文件功能
5. 根据文件功能反推目录功能
6. 输出带注释的目录树结构
"""

import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass
from collections import defaultdict

from codeindex import CodeIndexClient

from config.config import StructureDetectorConfig, load_detector_config
from utils.codeindex_utils import find_codeindex_db, create_codeindex_client


# ============================================================================
# 数据类定义
# ============================================================================

@dataclass
class FileInfo:
    """文件信息"""
    path: str
    relative_path: str
    language: str
    size: int
    depth: int


@dataclass
class FileFunction:
    """文件功能信息"""
    description: str
    keywords: List[str]
    category: str
    confidence: float


@dataclass
class DirectoryFunction:
    """目录功能信息"""
    description: str
    category: str
    files_count: int
    subdirs_count: int


# ============================================================================
# 语言配置
# ============================================================================

# 文件扩展名到语言的映射
LANGUAGE_EXTENSIONS = {
    'go': ['.go'],
    'python': ['.py'],
    'typescript': ['.ts', '.tsx'],
    'javascript': ['.js', '.jsx'],
    'java': ['.java'],
    'rust': ['.rs'],
    'html': ['.html', '.htm'],
}

# CodeIndex 语言代码映射
CODEINDEX_LANGUAGE_MAP = {
    'go': 'go',
    'python': 'python',
    'typescript': 'ts',
    'javascript': 'js',
    'java': 'java',
    'rust': 'rust',
    'html': 'html',
}

# 符号提取正则模式
SYMBOL_PATTERNS = {
    'go': [
        (r'type\s+(\w+)\s+struct', 'struct'),
        (r'type\s+(\w+)\s+interface', 'interface'),
        (r'func\s+(?:\([^)]+\)\s+)?(\w+)', 'function'),
    ],
    'python': [
        (r'class\s+(\w+)', 'class'),
        (r'def\s+(\w+)', 'function'),
    ],
    'typescript': [
        (r'class\s+(\w+)', 'class'),
        (r'interface\s+(\w+)', 'interface'),
        (r'function\s+(\w+)', 'function'),
        (r'const\s+(\w+)\s*[:=]', 'constant'),
    ],
    'javascript': [
        (r'class\s+(\w+)', 'class'),
        (r'function\s+(\w+)', 'function'),
        (r'const\s+(\w+)\s*[:=]', 'constant'),
    ],
    'java': [
        (r'class\s+(\w+)', 'class'),
        (r'interface\s+(\w+)', 'interface'),
        (r'public\s+(?:static\s+)?(?:.*?\s+)?(\w+)\s*\(', 'function'),
    ],
    'rust': [
        (r'struct\s+(\w+)', 'struct'),
        (r'impl\s+(\w+)', 'impl'),
        (r'fn\s+(\w+)', 'function'),
    ],
}

# 排除目录模式
EXCLUDE_PATTERNS = [
    '.git', '.svn', '.hg',
    'node_modules', '__pycache__', '.pytest_cache',
    'vendor', 'dist', 'build', 'target',
    '.codeindex', '.idea', '.vscode',
]


# ============================================================================
# StructureDetector 主类
# ============================================================================

class StructureDetector:
    """动态项目结构检测器"""
    
    def __init__(self, config: Optional[StructureDetectorConfig] = None, config_path: Optional[str] = None):
        """
        初始化检测器
        
        Args:
            config: 结构检测器配置（如果为 None，则从配置文件加载）
            config_path: 配置文件路径（仅在 config 为 None 时使用）
        """
        # 如果没有提供配置，尝试从配置文件加载
        if config is None:
            try:
                config = load_detector_config(config_path)
            except FileNotFoundError:
                # 如果配置文件不存在，使用默认配置
                config = StructureDetectorConfig(
                    root_path=os.getenv('DETECTOR_PROJECT_PATH', '.'),
                    codeindex_db_path=None,
                    max_depth=None,
                    languages=['go', 'python', 'typescript', 'javascript', 'java', 'rust']
                )
        
        self.config = config
        self.root_path = Path(config.root_path).resolve()
        self.codeindex_db_path = config.codeindex_db_path
        self.max_depth = config.max_depth
        self.languages = config.languages or ['go', 'python', 'typescript', 'javascript', 'java', 'rust']
        
        # 内部状态
        self._codeindex_client: Optional[CodeIndexClient] = None
        
    # ========================================================================
    # 工具函数
    # ========================================================================
    
    def _get_file_language(self, file_path: str) -> Optional[str]:
        """
        根据文件扩展名识别语言
        
        Args:
            file_path: 文件路径
            
        Returns:
            语言名称，如果无法识别返回 None
        """
        ext = Path(file_path).suffix.lower()
        for lang, extensions in LANGUAGE_EXTENSIONS.items():
            if ext in extensions:
                return lang
        return None
    
    def _should_exclude(self, path: str) -> bool:
        """
        判断路径是否应该被排除
        
        Args:
            path: 路径字符串
            
        Returns:
            如果应该排除返回 True
        """
        path_parts = Path(path).parts
        for part in path_parts:
            if any(pattern in part.lower() for pattern in EXCLUDE_PATTERNS):
                return True
        return False
    
    # ========================================================================
    # 文件扫描
    # ========================================================================
    
    def _scan_directory(self) -> Dict[str, Any]:
        """
        扫描目录，收集文件信息
        
        Returns:
            {
                'files': List[FileInfo],
                'tree': Dict,  # 目录树结构
                'stats': Dict   # 统计信息
            }
        """
        files: List[FileInfo] = []
        tree: Dict[str, Any] = {}
        
        # 遍历目录
        for root, dirs, filenames in os.walk(self.root_path):
            root_path = Path(root)
            relative_root = root_path.relative_to(self.root_path)
            
            # 过滤排除的目录
            dirs[:] = [d for d in dirs if not self._should_exclude(str(root_path / d))]
            
            # 检查深度限制
            depth = len(relative_root.parts)
            if self.max_depth and depth >= self.max_depth:
                dirs.clear()  # 不再深入
                continue
            
            # 处理文件
            for filename in filenames:
                file_path = root_path / filename
                relative_path = file_path.relative_to(self.root_path)
                
                # 检查是否排除
                if self._should_exclude(str(file_path)):
                    continue
                
                # 识别语言
                language = self._get_file_language(str(file_path))
                if not language or language not in self.languages:
                    continue
                
                # 获取文件大小
                try:
                    size = file_path.stat().st_size
                except OSError:
                    size = 0
                
                # 创建文件信息
                file_info = FileInfo(
                    path=str(file_path),
                    relative_path=str(relative_path),
                    language=language,
                    size=size,
                    depth=depth
                )
                files.append(file_info)
        
        # 构建统计信息
        stats = {
            'total_files': len(files),
            'by_language': defaultdict(int),
            'by_depth': defaultdict(int),
        }
        for file_info in files:
            stats['by_language'][file_info.language] += 1
            stats['by_depth'][file_info.depth] += 1
        
        return {
            'files': files,
            'tree': tree,  # TODO: 构建目录树结构
            'stats': stats
        }
    
    # ========================================================================
    # 符号提取
    # ========================================================================
    
    def _extract_symbols_from_file(self, file_path: str, language: str) -> List[str]:
        """
        从文件中提取符号名
        
        Args:
            file_path: 文件路径
            language: 语言类型
            
        Returns:
            符号名列表（去重）
        """
        if language not in SYMBOL_PATTERNS:
            return []
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
        except Exception:
            return []
        
        symbols: Set[str] = set()
        patterns = SYMBOL_PATTERNS[language]
        
        for pattern, _ in patterns:
            matches = re.finditer(pattern, content)
            for match in matches:
                symbol_name = match.group(1)
                if symbol_name and symbol_name[0].isupper() or language in ['python', 'javascript', 'typescript']:
                    symbols.add(symbol_name)
        
        return sorted(list(symbols))
    
    # ========================================================================
    # CodeIndex 查询
    # ========================================================================
    
    def _query_symbols_batch(self, symbol_names: List[str], language: str) -> List[Dict[str, Any]]:
        """
        批量查询符号
        
        Args:
            symbol_names: 符号名列表
            language: 语言类型
            
        Returns:
            符号记录列表
        """
        if not self._codeindex_client:
            return []
        
        codeindex_lang = CODEINDEX_LANGUAGE_MAP.get(language)
        if not codeindex_lang:
            return []
        
        all_symbols: List[Dict[str, Any]] = []
        
        for symbol_name in symbol_names:
            try:
                symbols = self._codeindex_client.find_symbols(
                    name=symbol_name,
                    language=codeindex_lang
                )
                # 过滤出匹配当前文件的符号（可选，这里先不过滤）
                all_symbols.extend(symbols)
            except Exception:
                # 查询失败，跳过
                continue
        
        return all_symbols
    
    def _get_symbol_summaries(self, symbols: List[Dict[str, Any]]) -> List[str]:
        """
        从符号记录中提取摘要
        
        Args:
            symbols: 符号记录列表
            
        Returns:
            摘要列表（过滤空值）
        """
        summaries = []
        for symbol in symbols:
            summary = symbol.get('chunkSummary')
            if summary and summary.strip():
                summaries.append(summary.strip())
        return summaries
    
    # ========================================================================
    # 功能推断
    # ========================================================================
    
    def _extract_keywords(self, summaries: List[str]) -> List[str]:
        """
        从摘要中提取关键词
        
        Args:
            summaries: 摘要列表
            
        Returns:
            关键词列表
        """
        if not summaries:
            return []
        
        # 简单的关键词提取：分词并过滤
        all_text = ' '.join(summaries).lower()
        # 移除标点符号
        all_text = re.sub(r'[^\w\s]', ' ', all_text)
        words = all_text.split()
        
        # 过滤停用词（简单版本）
        stop_words = {'的', '是', '在', '有', '和', '与', '或', '但', 'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 'to', 'of', 'and', 'or', 'but'}
        keywords = [w for w in words if len(w) > 2 and w not in stop_words]
        
        # 去重并返回前10个
        unique_keywords = list(dict.fromkeys(keywords))  # 保持顺序的去重
        return unique_keywords[:10]
    
    def _categorize_file(self, summaries: List[str], keywords: List[str]) -> str:
        """
        文件分类
        
        Args:
            summaries: 摘要列表
            keywords: 关键词列表
            
        Returns:
            分类字符串
        """
        all_text = ' '.join(summaries + keywords).lower()
        
        # 分类关键词匹配
        if any(word in all_text for word in ['service', '服务', '业务逻辑', 'business']):
            return 'service'
        elif any(word in all_text for word in ['model', '数据', 'entity', '结构', 'struct', 'class']):
            return 'model'
        elif any(word in all_text for word in ['controller', '处理', 'handle', '路由', 'route']):
            return 'controller'
        elif any(word in all_text for word in ['util', '工具', 'helper', 'common', '公共']):
            return 'utils'
        elif any(word in all_text for word in ['test', '测试', 'spec']):
            return 'test'
        elif any(word in all_text for word in ['config', '配置', 'setting']):
            return 'config'
        else:
            return 'other'
    
    def _infer_file_function(self, file_path: str, symbols: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        推断文件功能
        
        Args:
            file_path: 文件路径
            symbols: 符号记录列表
            
        Returns:
            文件功能信息字典
        """
        summaries = self._get_symbol_summaries(symbols)
        keywords = self._extract_keywords(summaries)
        category = self._categorize_file(summaries, keywords)
        
        # 生成描述
        if summaries:
            # 取前2-3个摘要的关键信息
            description_parts = []
            for summary in summaries[:3]:
                # 提取摘要的第一句话或前50个字符
                first_sentence = summary.split('。')[0].split('.')[0]
                if len(first_sentence) > 50:
                    first_sentence = first_sentence[:50] + '...'
                description_parts.append(first_sentence)
            description = '；'.join(description_parts[:2])
        else:
            # 降级处理：使用文件名和符号名
            file_name = Path(file_path).stem
            symbol_names = [s.get('name', '') for s in symbols[:3] if s.get('name')]
            if symbol_names:
                description = f"{file_name}：包含 {', '.join(symbol_names[:3])}"
            else:
                description = file_name
        
        # 计算置信度
        confidence = 0.5
        if summaries:
            confidence = min(0.9, 0.5 + len(summaries) * 0.1)
        
        return {
            'description': description,
            'keywords': keywords,
            'category': category,
            'confidence': confidence
        }
    
    # ========================================================================
    # 目录分析
    # ========================================================================
    
    def _analyze_directory(self, dir_path: str, file_functions: Dict[str, FileFunction]) -> Dict[str, Any]:
        """
        分析目录功能
        
        Args:
            dir_path: 目录路径
            file_functions: 文件功能映射
            
        Returns:
            目录功能信息字典
        """
        dir_path_obj = Path(dir_path)
        files_in_dir = []
        subdirs = []
        
        # 收集目录下的文件和子目录
        if dir_path_obj.exists() and dir_path_obj.is_dir():
            for item in dir_path_obj.iterdir():
                if item.is_file():
                    file_path = str(item)
                    if file_path in file_functions:
                        files_in_dir.append(file_path)
                elif item.is_dir():
                    subdirs.append(str(item))
        
        # 统计文件分类
        categories = defaultdict(int)
        descriptions = []
        for file_path in files_in_dir:
            func_info = file_functions.get(file_path)
            if func_info:
                categories[func_info['category']] += 1
                descriptions.append(func_info['description'])
        
        # 多数投票决定目录分类
        if categories:
            category = max(categories.items(), key=lambda x: x[1])[0]
        else:
            category = 'other'
        
        # 生成目录描述
        if descriptions:
            # 聚合描述
            description = '；'.join(descriptions[:2])
            if len(description) > 100:
                description = description[:100] + '...'
        else:
            description = Path(dir_path).name
        
        return {
            'description': description,
            'category': category,
            'files_count': len(files_in_dir),
            'subdirs_count': len(subdirs)
        }
    
    def _build_directory_tree(self, files: List[FileInfo]) -> Dict[str, Any]:
        """
        构建目录树结构
        
        Args:
            files: 文件信息列表
            
        Returns:
            目录树字典
        """
        tree: Dict[str, Any] = {}
        
        for file_info in files:
            parts = Path(file_info.relative_path).parts
            current = tree
            
            # 构建目录路径
            for part in parts[:-1]:  # 排除文件名
                if part not in current:
                    current[part] = {'type': 'directory', 'children': {}}
                current = current[part]['children']
            
            # 添加文件
            filename = parts[-1]
            current[filename] = {
                'type': 'file',
                'path': file_info.path,
                'language': file_info.language
            }
        
        return tree
    
    # ========================================================================
    # 格式化输出
    # ========================================================================
    
    def _format_tree_text(
        self,
        tree: Dict[str, Any],
        file_functions: Dict[str, Dict[str, Any]],
        dir_functions: Dict[str, Dict[str, Any]],
        prefix: str = "",
        current_path: Path = None
    ) -> str:
        """
        格式化树形结构为文本
        
        Args:
            tree: 目录树字典
            file_functions: 文件功能映射
            dir_functions: 目录功能映射
            prefix: 当前前缀
            current_path: 当前路径（Path对象）
            
        Returns:
            格式化的字符串
        """
        if current_path is None:
            current_path = Path(self.root_path)
        
        lines = []
        items = sorted(tree.items())
        
        for idx, (name, node) in enumerate(items):
            is_last_item = idx == len(items) - 1
            connector = "└── " if is_last_item else "├── "
            
            if node['type'] == 'directory':
                # 目录节点
                dir_path = current_path / name
                dir_path_str = str(dir_path)
                dir_func = dir_functions.get(dir_path_str, {})
                description = dir_func.get('description', '')
                
                line = prefix + connector + name
                if description:
                    line += f"  # {description}"
                lines.append(line)
                
                # 递归处理子节点
                next_prefix = prefix + ("    " if is_last_item else "│   ")
                child_lines = self._format_tree_text(
                    node['children'],
                    file_functions,
                    dir_functions,
                    next_prefix,
                    dir_path
                )
                if child_lines:
                    lines.append(child_lines)
            else:
                # 文件节点
                file_path = node['path']
                file_func = file_functions.get(file_path, {})
                description = file_func.get('description', '')
                
                line = prefix + connector + name
                if description:
                    line += f"  # {description}"
                lines.append(line)
        
        return '\n'.join(lines)
    
    def _format_tree(
        self,
        tree: Dict[str, Any],
        file_functions: Dict[str, Dict[str, Any]],
        dir_functions: Dict[str, Dict[str, Any]],
        format: str = 'text'
    ) -> str:
        """
        格式化目录树
        
        Args:
            tree: 目录树字典
            file_functions: 文件功能映射
            dir_functions: 目录功能映射
            format: 输出格式（'text' 或 'markdown'）
            
        Returns:
            格式化的字符串
        """
        if format == 'text':
            return self._format_tree_text(tree, file_functions, dir_functions)
        elif format == 'markdown':
            # TODO: 实现 Markdown 格式
            text = self._format_tree_text(tree, file_functions, dir_functions)
            return f"```\n{text}\n```"
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    # ========================================================================
    # 主入口
    # ========================================================================
    
    def detect(self) -> Dict[str, Any]:
        """
        执行检测流程
        
        Returns:
            {
                'tree': str,              # 格式化的目录树
                'file_functions': Dict,   # 文件功能映射
                'dir_functions': Dict,    # 目录功能映射
                'stats': Dict            # 统计信息
            }
        """
        # 1. 验证配置和数据库
        db_path = find_codeindex_db(str(self.root_path), self.codeindex_db_path)
        if not db_path:
            raise FileNotFoundError(
                f"CodeIndex 数据库未找到。请先使用 CodeIndex CLI 建立索引：\n"
                f"  node dist/cli/index.js index --root {self.root_path} --db .codeindex/project.db"
            )
        
        # 2. 初始化 CodeIndex 客户端
        self._codeindex_client = create_codeindex_client(db_path)
        
        try:
            # 3. 扫描目录
            print(f"📁 扫描目录: {self.root_path}")
            scan_result = self._scan_directory()
            files = scan_result['files']
            print(f"   找到 {len(files)} 个文件")
            
            # 4. 提取符号（每个文件）
            print(f"🔍 提取符号...")
            all_symbols: Dict[str, List[str]] = {}
            for file_info in files:
                symbols = self._extract_symbols_from_file(file_info.path, file_info.language)
                if symbols:
                    all_symbols[file_info.path] = symbols
            
            total_symbols = sum(len(s) for s in all_symbols.values())
            print(f"   提取到 {total_symbols} 个符号")
            
            # 5. 批量查询 CodeIndex
            print(f"📚 查询 CodeIndex...")
            file_symbols_map: Dict[str, List[Dict[str, Any]]] = {}
            for file_path, symbol_names in all_symbols.items():
                language = self._get_file_language(file_path)
                if language:
                    symbols = self._query_symbols_batch(symbol_names, language)
                    file_symbols_map[file_path] = symbols
            
            queried_count = sum(len(s) for s in file_symbols_map.values())
            print(f"   查询到 {queried_count} 个符号记录")
            
            # 6. 推断文件功能
            print(f"🧠 推断文件功能...")
            file_functions: Dict[str, Dict[str, Any]] = {}
            for file_path, symbols in file_symbols_map.items():
                function_info = self._infer_file_function(file_path, symbols)
                file_functions[file_path] = function_info
            
            print(f"   分析了 {len(file_functions)} 个文件")
            
            # 7. 分析目录功能
            print(f"📂 分析目录功能...")
            dir_functions: Dict[str, Dict[str, Any]] = {}
            
            # 收集所有目录
            all_dirs: Set[str] = set()
            for file_info in files:
                file_path_obj = Path(file_info.path)
                # 添加所有父目录
                for parent in file_path_obj.parents:
                    if self.root_path in parent.parents or parent == self.root_path:
                        all_dirs.add(str(parent))
            
            for dir_path in all_dirs:
                dir_func = self._analyze_directory(dir_path, file_functions)
                dir_functions[dir_path] = dir_func
            
            print(f"   分析了 {len(dir_functions)} 个目录")
            
            # 8. 构建目录树
            tree = self._build_directory_tree(files)
            
            # 9. 格式化输出
            print(f"📝 格式化输出...")
            # 添加根目录名称
            root_name = self.root_path.name or str(self.root_path)
            formatted_tree = root_name + '\n' + self._format_tree_text(tree, file_functions, dir_functions)
            
            return {
                'tree': formatted_tree,
                'file_functions': file_functions,
                'dir_functions': dir_functions,
                'stats': {
                    'files_count': len(files),
                    'symbols_count': total_symbols,
                    'queried_symbols': queried_count,
                    **scan_result['stats']
                }
            }
        
        finally:
            # 关闭 CodeIndex 客户端
            if self._codeindex_client:
                self._codeindex_client.close()
    
    def detect_to_file(self, output_path: str, format: str = 'markdown'):
        """
        检测并输出到文件
        
        Args:
            output_path: 输出文件路径
            format: 输出格式
        """
        result = self.detect()
        
        with open(output_path, 'w', encoding='utf-8') as f:
            if format == 'markdown':
                f.write("# 项目结构\n\n")
                f.write("```\n")
                f.write(result['tree'])
                f.write("\n```\n")
            else:
                f.write(result['tree'])
        
        print(f"✅ 结果已保存到: {output_path}")

