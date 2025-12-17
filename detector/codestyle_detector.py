"""
代码风格检测器
功能：
1. 分析项目的命名习惯（变量、函数、类、常量）- 驼峰、下划线等
2. 检测语言类型
"""

import re
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from collections import defaultdict

from detector.base_detector import BaseDetector, CodeIndexQuery
from utils.logger import logger


@dataclass
class NamingPattern:
    """ 命名模式统计 """
    pattern_name: str  # snake_case, camelCase, PascalCase 等
    count: int
    examples: List[str]
    percentage: float = 0.0


@dataclass
class LanguageNamingStyle:
    """ 语言的命名风格总结 """
    language: str
    total_symbols: int
    by_type: Dict[str, Dict[str, NamingPattern]]  # {symbol_type: {pattern_name: NamingPattern}}
    summary: Dict[str, str]  # {symbol_type: dominant_pattern}


@dataclass
class StyleReport:
    """ 代码风格报告 """
    total_files: int
    languages: Dict[str, LanguageNamingStyle]
    overall_summary: Dict[str, Any]


# 命名模式识别函数
def classify_naming_pattern(name: str) -> str:
    """
    识别命名模式
    
    Returns:
        模式名称: snake_case, camelCase, PascalCase, UPPER_SNAKE_CASE, _private, 或其他
    """
    if not name:
        return 'unknown'
    
    # 私有成员（以下划线开头）
    if name.startswith('_'):
        if re.match(r'^_[a-z][a-z0-9_]*$', name):
            return '_private_snake'
        elif re.match(r'^_[a-z][a-zA-Z0-9]*$', name):
            return '_private_camel'
        else:
            return '_private_other'
    
    # 全大写（常量）
    if re.match(r'^[A-Z][A-Z0-9_]*$', name):
        return 'UPPER_SNAKE_CASE'
    
    # PascalCase（首字母大写，后续大小写混合）
    if re.match(r'^[A-Z][a-zA-Z0-9]*$', name):
        return 'PascalCase'
    
    # camelCase（首字母小写，后续大小写混合）
    if re.match(r'^[a-z][a-zA-Z0-9]*$', name):
        return 'camelCase'
    
    # snake_case（全小写，用下划线分隔）
    if re.match(r'^[a-z][a-z0-9_]*$', name):
        return 'snake_case'
    
    # 其他模式
    return 'other'


class CodeStyleDetector(BaseDetector, CodeIndexQuery):
    """ 代码风格检测器 - 分析项目命名习惯 """
    
    def __init__(
        self, 
        config_path: Optional[str] = None,
        config_type: Optional[str] = 'codestyle'
    ):
        """
        初始化检测器
        
        Args:
            config_path: 配置文件路径
            config_type: 配置类型
        """
        BaseDetector.__init__(self, config_path=config_path, config_type=config_type)
        CodeIndexQuery.__init__(self, codeindex_db_path=self.config.codeindex_db_path or '')
        self.naming_stats: Dict[str, Dict[str, Dict[str, List[str]]]] = defaultdict(
            lambda: defaultdict(lambda: defaultdict(list))
        )  # {language: {symbol_type: {pattern: [names]}}}
    
    def _collect_python_symbols(self, file_path: str) -> None:
        """ 收集 Python 文件中的符号 """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.splitlines()
        except Exception:
            return
        
        # 提取类定义
        class_pattern = r'^\s*class\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*[:\(]'
        for line in lines:
            match = re.match(class_pattern, line)
            if match:
                class_name = match.group(1)
                pattern = classify_naming_pattern(class_name)
                self.naming_stats['python']['class'][pattern].append(class_name)
        
        # 提取函数定义
        function_pattern = r'^\s*def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\('
        for line in lines:
            match = re.match(function_pattern, line)
            if match:
                func_name = match.group(1)
                symbol_type = 'private_function' if func_name.startswith('_') else 'function'
                pattern = classify_naming_pattern(func_name)
                self.naming_stats['python'][symbol_type][pattern].append(func_name)
        
        # 提取常量（全大写的变量）
        constant_pattern = r'^\s*([A-Z][A-Z0-9_]*)\s*='
        for line in lines:
            match = re.match(constant_pattern, line)
            if match:
                const_name = match.group(1)
                pattern = classify_naming_pattern(const_name)
                self.naming_stats['python']['constant'][pattern].append(const_name)
    
    def _collect_go_symbols(self, file_path: str) -> None:
        """ 收集 Go 文件中的符号 """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        except Exception:
            return
        
        # 提取函数定义
        func_pattern = r'^\s*func\s+(?:\([^)]+\)\s+)?([a-zA-Z_][a-zA-Z0-9_]*)\s*\('
        for line in lines:
            match = re.match(func_pattern, line)
            if match:
                func_name = match.group(1)
                # Go 中首字母大写的是导出函数，小写的是私有函数
                symbol_type = 'exported_function' if func_name[0].isupper() else 'function'
                pattern = classify_naming_pattern(func_name)
                self.naming_stats['go'][symbol_type][pattern].append(func_name)
        
        # 提取类型定义
        type_pattern = r'^\s*type\s+([a-zA-Z_][a-zA-Z0-9_]*)\s+'
        for line in lines:
            match = re.match(type_pattern, line)
            if match:
                type_name = match.group(1)
                pattern = classify_naming_pattern(type_name)
                self.naming_stats['go']['type'][pattern].append(type_name)
    
    def _collect_typescript_symbols(self, file_path: str) -> None:
        """ 收集 TypeScript 文件中的符号 """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        except Exception:
            return
        
        # 提取类定义
        class_pattern = r'^\s*(?:export\s+)?(?:abstract\s+)?class\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*'
        for line in lines:
            match = re.match(class_pattern, line)
            if match:
                class_name = match.group(1)
                pattern = classify_naming_pattern(class_name)
                self.naming_stats['typescript']['class'][pattern].append(class_name)
        
        # 提取函数定义
        func_pattern = r'^\s*(?:export\s+)?(?:async\s+)?function\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\('
        for line in lines:
            match = re.match(func_pattern, line)
            if match:
                func_name = match.group(1)
                symbol_type = 'private_function' if func_name.startswith('_') else 'function'
                pattern = classify_naming_pattern(func_name)
                self.naming_stats['typescript'][symbol_type][pattern].append(func_name)
        
        # 提取箭头函数（const/let 声明）
        arrow_pattern = r'^\s*(?:export\s+)?(?:const|let)\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*[:=]\s*(?:\([^)]*\)\s*)?=>'
        for line in lines:
            match = re.match(arrow_pattern, line)
            if match:
                func_name = match.group(1)
                symbol_type = 'private_function' if func_name.startswith('_') else 'function'
                pattern = classify_naming_pattern(func_name)
                self.naming_stats['typescript'][symbol_type][pattern].append(func_name)
    
    def _analyze_language_style(self, language: str) -> LanguageNamingStyle:
        """ 分析语言的命名风格 """
        by_type: Dict[str, Dict[str, NamingPattern]] = {}
        summary: Dict[str, str] = {}
        
        language_stats = self.naming_stats[language]
        
        for symbol_type, patterns in language_stats.items():
            total = sum(len(names) for names in patterns.values())
            if total == 0:
                continue
            
            type_patterns: Dict[str, NamingPattern] = {}
            max_count = 0
            dominant_pattern = 'unknown'
            
            for pattern_name, names in patterns.items():
                count = len(names)
                percentage = (count / total * 100) if total > 0 else 0.0
                
                # 取前5个示例
                examples = names[:5]
                
                type_patterns[pattern_name] = NamingPattern(
                    pattern_name=pattern_name,
                    count=count,
                    examples=examples,
                    percentage=percentage
                )
                
                if count > max_count:
                    max_count = count
                    dominant_pattern = pattern_name
            
            by_type[symbol_type] = type_patterns
            summary[symbol_type] = dominant_pattern
        
        return LanguageNamingStyle(
            language=language,
            total_symbols=sum(
                sum(len(names) for names in patterns.values())
                for patterns in language_stats.values()
            ),
            by_type=by_type,
            summary=summary
        )
    
    def detect(self) -> StyleReport:
        """
        执行检测流程 - 分析项目命名习惯
        
        Returns:
            StyleReport 对象
        """
        logger.info(f"📁 扫描目录: {self.config.root_path}")
        files = self._scan_files()
        logger.info(f"   找到 {len(files)} 个文件")
        
        logger.info(f"🔍 分析命名习惯...")
        
        # 按语言收集符号
        for file_path in files:
            language = self._get_file_language(file_path)
            
            if language == 'python':
                self._collect_python_symbols(file_path)
            elif language == 'go':
                self._collect_go_symbols(file_path)
            elif language in ['typescript', 'javascript']:
                self._collect_typescript_symbols(file_path)
        
        # 分析各语言的命名风格
        languages: Dict[str, LanguageNamingStyle] = {}
        for language in self.naming_stats.keys():
            languages[language] = self._analyze_language_style(language)
        
        overall_summary = {
            'total_languages': len(languages),
            'languages_detected': list(languages.keys())
        }
        
        return StyleReport(
            total_files=len(files),
            languages=languages,
            overall_summary=overall_summary
        )
    
    def detect_to_file(self, output_path: str):
        """
        检测并输出到文件
        
        Args:
            output_path: 输出文件路径
        """
        report = self.detect()
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("# 项目命名习惯分析报告\n\n")
            f.write(f"## 概览\n\n")
            f.write(f"- 检测文件数: {report.total_files}\n")
            f.write(f"- 检测到的语言: {', '.join(report.languages.keys())}\n\n")
            
            # 按语言输出
            for language, style in report.languages.items():
                f.write(f"## {language.upper()} 命名习惯\n\n")
                
                if style.total_symbols == 0:
                    f.write("未检测到符号。\n\n")
                    continue
                
                f.write(f"**总符号数**: {style.total_symbols}\n\n")
                
                # 输出各类型的命名习惯
                for symbol_type, patterns in sorted(style.by_type.items()):
                    f.write(f"### {symbol_type}\n\n")
                    
                    # 找出主要模式
                    dominant_pattern = style.summary.get(symbol_type, 'unknown')
                    total = sum(p.count for p in patterns.values())
                    
                    f.write(f"**主要命名风格**: `{dominant_pattern}` ({patterns[dominant_pattern].percentage:.1f}%)\n\n")
                    
                    # 列出所有模式及其统计
                    f.write("| 命名模式 | 数量 | 占比 | 示例 |\n")
                    f.write("|---------|------|------|------|\n")
                    
                    for pattern_name in sorted(patterns.keys(), key=lambda x: patterns[x].count, reverse=True):
                        pattern = patterns[pattern_name]
                        examples_str = ', '.join(pattern.examples[:3])
                        if len(pattern.examples) > 3:
                            examples_str += '...'
                        f.write(f"| `{pattern_name}` | {pattern.count} | {pattern.percentage:.1f}% | {examples_str} |\n")
                    
                    f.write("\n")
            
            # 总结
            f.write("## 总结\n\n")
            for language, style in report.languages.items():
                if style.total_symbols == 0:
                    continue
                f.write(f"### {language.upper()}\n\n")
                for symbol_type, pattern in sorted(style.summary.items()):
                    f.write(f"- **{symbol_type}**: 主要使用 `{pattern}`\n")
                f.write("\n")
        
        logger.info(f"✅ 报告已保存到: {output_path}")
