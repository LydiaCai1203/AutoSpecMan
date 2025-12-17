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

import re
from pathlib import Path
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass
from collections import defaultdict

from detector.base_detector import BaseDetector, CodeIndexQuery
from utils.logger import logger


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


# ============================================================================
# StructureDetector 主类
# ============================================================================

class StructureDetector(BaseDetector, CodeIndexQuery):
    """动态项目结构检测器"""
    
    def __init__(
        self, 
        config_path: Optional[str] = None,
        config_type: Optional[str] = 'structure'
    ):
        """
        初始化检测器
        
        Args:
            config_path: 配置文件路径
            config_type: 配置类型
        """
        BaseDetector.__init__(self, config_path=config_path, config_type=config_type)
        CodeIndexQuery.__init__(self, codeindex_db_path=self.config.codeindex_db_path or '')

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
        # 使用基类的 _scan_files() 方法获取文件列表
        file_paths = self._scan_files()
        
        files: List[FileInfo] = []
        tree: Dict[str, Any] = {}
        
        # 将文件路径转换为 FileInfo 对象
        for file_path_str in file_paths:
            file_path = Path(file_path_str)
            relative_path = file_path.relative_to(self.config.root_path)
            
            # 检查深度限制
            depth = len(relative_path.parts) - 1  # 减去文件名本身
            if self.config.max_depth and depth >= self.config.max_depth:
                continue
            
            # 识别语言（使用基类方法）
            language = self._get_file_language(file_path_str)
            if not language:
                continue
            
            # 获取文件大小
            try:
                size = file_path.stat().st_size
            except OSError:
                size = 0
            
            # 创建文件信息
            file_info = FileInfo(
                path=file_path_str,
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
            current_path = Path(self.config.root_path)
        
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
            text = self._format_tree_text(tree, file_functions, dir_functions)
            return f"```\n{text}\n```"
        else:
            raise ValueError(f"Unsupported format: {format}")
    
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
        # 1. 扫描文件
        scan_result = self._scan_directory()
        files = scan_result['files']
        
        # 2. 提取符号
        all_symbols: Dict[str, List[str]] = {}
        for file_info in files:
            symbols = self._extract_symbols_from_file(file_info.path, file_info.language)
            if symbols:
                all_symbols[file_info.path] = symbols
        
        total_symbols = sum(len(s) for s in all_symbols.values())
        logger.info(f"提取到 {total_symbols} 个符号")
        
        # 3. 查询符号含义
        file_symbols_map: Dict[str, List[Dict[str, Any]]] = {}
        for file_path, symbol_names in all_symbols.items():
            language = self._get_file_language(file_path)
            if language:
                symbols = self._query_symbols_batch(symbol_names, language)
                file_symbols_map[file_path] = symbols
        
        queried_count = sum(len(s) for s in file_symbols_map.values())
        logger.info(f"查询到 {queried_count} 个符号记录")
        
        # 4. 推断文件功能
        file_functions: Dict[str, Dict[str, Any]] = {}
        for file_path, symbols in file_symbols_map.items():
            function_info = self._infer_file_function(file_path, symbols)
            file_functions[file_path] = function_info
        
        logger.info(f"   分析了 {len(file_functions)} 个文件")
        
        # 5. 分析目录功能
        dir_functions: Dict[str, Dict[str, Any]] = {}
        all_dirs: Set[str] = set()
        for file_info in files:
            file_path_obj = Path(file_info.path)
            for parent in file_path_obj.parents:
                if self.config.root_path in parent.parents or parent == Path(self.config.root_path):
                    all_dirs.add(str(parent))
        
        for dir_path in all_dirs:
            dir_func = self._analyze_directory(dir_path, file_functions)
            dir_functions[dir_path] = dir_func
        
        logger.info(f"   分析了 {len(dir_functions)} 个目录")
        
        # 6. 构建目录树
        tree = self._build_directory_tree(files)
        
        # 7. 格式化输出
        root_path_obj = Path(self.config.root_path)
        root_name = root_path_obj.name or str(root_path_obj)
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
        
        logger.info(f"✅ 结果已保存到: {output_path}")

