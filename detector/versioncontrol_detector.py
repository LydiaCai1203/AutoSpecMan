"""
版本控制规范检测器
功能：
1. 分析项目的 Git 使用习惯（分支策略、Commit 规范、分支命名）
2. 生成简洁的习惯总结报告
"""

import re
from typing import Dict, List, Optional
from dataclasses import dataclass
from collections import defaultdict

from detector.base_detector import BaseDetector
from utils.git_utils import execute_git_command, is_git_repo, get_git_repo_path
from utils.logger import logger


@dataclass
class CommitPattern:
    """提交格式模式"""
    format_type: str  # conventional, simple, bracket, other
    type_distribution: Dict[str, int]  # {feat: 450, fix: 320, ...}
    dominant_types: List[str]  # 主要使用的类型（按频率排序）


@dataclass
class BranchPattern:
    """分支命名模式"""
    main_branch: str  # main/master
    develop_branch: Optional[str]  # develop/dev
    feature_prefix: Optional[str]  # feature/ 或 feat/
    fix_prefix: Optional[str]  # fix/ 或 bugfix/
    release_prefix: Optional[str]  # release/
    hotfix_prefix: Optional[str]  # hotfix/
    naming_pattern: str  # type/description 或 type-description


@dataclass
class GitWorkflowReport:
    """Git 工作流习惯报告"""
    branch_pattern: BranchPattern
    commit_pattern: CommitPattern
    summary: Dict[str, str]  # 简洁的习惯总结


class VersionControlDetector(BaseDetector):
    """版本控制规范检测器 - 分析项目 Git 使用习惯"""
    
    def __init__(
        self, 
        config_path: Optional[str] = None,
        config_type: Optional[str] = 'git'
    ):
        """
        初始化检测器
        
        Args:
            config_path: 配置文件路径
            config_type: 配置类型
        """
        super().__init__(config_path=config_path, config_type=config_type)
        self.repo_path: Optional[str] = None
        
    def _find_git_repo(self) -> bool:
        """
        查找 Git 仓库路径
        
        Returns:
            如果找到 Git 仓库返回 True
        """
        repo_path = get_git_repo_path(self.config.root_path)
        if repo_path:
            self.repo_path = repo_path
            return True
        
        logger.warning(f"未找到 Git 仓库: {self.config.root_path}")
        return False
    
    def _get_branches(self) -> List[str]:
        """获取所有分支列表"""
        if not self.repo_path:
            return []
        
        output = execute_git_command(self.repo_path, ['branch', '-a'])
        if not output:
            return []
        
        branches = []
        for line in output.split('\n'):
            line = line.strip()
            if not line:
                continue
            
            # 移除 * 标记和远程分支标记
            branch = line.replace('*', '').strip()
            if branch.startswith('remotes/'):
                branch = branch.replace('remotes/', '').split('/', 1)[-1]
            
            if branch and branch not in branches:
                branches.append(branch)
        
        return branches
    
    def _get_current_branch(self) -> Optional[str]:
        """获取当前分支"""
        if not self.repo_path:
            return None
        
        output = execute_git_command(self.repo_path, ['branch', '--show-current'])
        return output if output else None
    
    def _get_commits(self, count: int = 100) -> List[Dict[str, str]]:
        """
        获取最近的提交信息
        
        Args:
            count: 获取的提交数量
            
        Returns:
            提交信息列表
        """
        if not self.repo_path:
            return []
        
        # 格式: hash|subject|body|author|date
        output = execute_git_command(
            self.repo_path,
            ['log', f'-{count}', '--pretty=format:%H|%s|%b|%an|%ad', '--date=iso']
        )
        
        if not output:
            return []
        
        commits = []
        for line in output.split('\n'):
            if not line.strip():
                continue
            
            parts = line.split('|', 4)
            if len(parts) >= 5:
                commits.append({
                    'hash': parts[0],
                    'subject': parts[1],
                    'body': parts[2],
                    'author': parts[3],
                    'date': parts[4]
                })
        
        return commits
    
    def _analyze_branch_pattern(self, branches: List[str]) -> BranchPattern:
        """分析分支命名模式"""
        # 识别主分支
        main_branch = None
        develop_branch = None
        
        # 常见主分支名称
        main_branches = ['main', 'master', 'trunk']
        develop_branches = ['develop', 'dev', 'development']
        
        for branch in branches:
            if branch in main_branches:
                main_branch = branch
            elif branch in develop_branches:
                develop_branch = branch
        
        # 如果没找到，使用第一个分支作为主分支
        if not main_branch and branches:
            main_branch = branches[0]
        
        # 统计分支命名模式
        feature_patterns = defaultdict(int)
        fix_patterns = defaultdict(int)
        release_patterns = defaultdict(int)
        hotfix_patterns = defaultdict(int)
        
        feature_prefixes = ['feature/', 'feat/']
        fix_prefixes = ['fix/', 'bugfix/']
        release_prefixes = ['release/', 'version/']
        hotfix_prefixes = ['hotfix/', 'hot-fix/']
        
        for branch in branches:
            # 跳过主分支和开发分支
            if branch in main_branches + develop_branches:
                continue
            
            # 功能分支
            for prefix in feature_prefixes:
                if branch.startswith(prefix):
                    feature_patterns[prefix] += 1
                    break
            
            # 修复分支
            for prefix in fix_prefixes:
                if branch.startswith(prefix):
                    fix_patterns[prefix] += 1
                    break
            
            # 发布分支
            for prefix in release_prefixes:
                if branch.startswith(prefix):
                    release_patterns[prefix] += 1
                    break
            
            # 热修复分支
            for prefix in hotfix_prefixes:
                if branch.startswith(prefix):
                    hotfix_patterns[prefix] += 1
                    break
        
        # 找出使用最多的前缀
        feature_prefix = max(feature_patterns.items(), key=lambda x: x[1])[0] if feature_patterns else None
        fix_prefix = max(fix_patterns.items(), key=lambda x: x[1])[0] if fix_patterns else None
        release_prefix = max(release_patterns.items(), key=lambda x: x[1])[0] if release_patterns else None
        hotfix_prefix = max(hotfix_patterns.items(), key=lambda x: x[1])[0] if hotfix_patterns else None
        
        # 识别命名模式（type/description 或 type-description）
        naming_pattern = 'type/description'
        if feature_prefix:
            if '/' in feature_prefix:
                naming_pattern = 'type/description'
            elif '-' in feature_prefix or '_' in feature_prefix:
                naming_pattern = 'type-description'
        
        return BranchPattern(
            main_branch=main_branch or 'main',
            develop_branch=develop_branch,
            feature_prefix=feature_prefix,
            fix_prefix=fix_prefix,
            release_prefix=release_prefix,
            hotfix_prefix=hotfix_prefix,
            naming_pattern=naming_pattern
        )
    
    def _analyze_commit_pattern(self, commits: List[Dict[str, str]]) -> CommitPattern:
        """分析 Commit 消息格式"""
        if not commits:
            return CommitPattern(
                format_type='other',
                type_distribution={},
                dominant_types=[]
            )
        
        # 识别格式类型
        conventional_count = 0
        simple_count = 0
        bracket_count = 0
        other_count = 0
        
        # Conventional Commits: type(scope): subject
        conventional_pattern = r'^(\w+)(?:\([^)]+\))?:\s+.+'
        # 简化格式: type: subject
        simple_pattern = r'^(\w+):\s+.+'
        # 方括号格式: [type] subject
        bracket_pattern = r'^\[(\w+)\]\s+.+'
        
        type_distribution = defaultdict(int)
        
        for commit in commits:
            subject = commit.get('subject', '').strip()
            if not subject:
                continue
            
            # 检查格式类型
            if re.match(conventional_pattern, subject):
                conventional_count += 1
                match = re.match(conventional_pattern, subject)
                if match:
                    commit_type = match.group(1).lower()
                    type_distribution[commit_type] += 1
            elif re.match(simple_pattern, subject):
                simple_count += 1
                match = re.match(simple_pattern, subject)
                if match:
                    commit_type = match.group(1).lower()
                    type_distribution[commit_type] += 1
            elif re.match(bracket_pattern, subject):
                bracket_count += 1
                match = re.match(bracket_pattern, subject)
                if match:
                    commit_type = match.group(1).lower()
                    type_distribution[commit_type] += 1
            else:
                other_count += 1
        
        # 确定主要格式
        format_counts = {
            'conventional': conventional_count,
            'simple': simple_count,
            'bracket': bracket_count,
            'other': other_count
        }
        dominant_format = max(format_counts.items(), key=lambda x: x[1])[0]
        
        # 找出主要使用的提交类型（按频率排序，取前5个）
        sorted_types = sorted(type_distribution.items(), key=lambda x: x[1], reverse=True)
        dominant_types = [t[0] for t in sorted_types[:5]]
        
        return CommitPattern(
            format_type=dominant_format,
            type_distribution=dict(type_distribution),
            dominant_types=dominant_types
        )
    
    def detect(self) -> GitWorkflowReport:
        """
        执行检测流程 - 分析项目 Git 使用习惯
        
        Returns:
            GitWorkflowReport 对象
        """
        logger.info(f"📁 分析 Git 仓库: {self.config.root_path}")
        
        # 查找 Git 仓库
        if not self._find_git_repo():
            logger.warning("⚠️  未找到 Git 仓库，跳过分析")
            # 返回默认值
            return GitWorkflowReport(
                branch_pattern=BranchPattern(
                    main_branch='main',
                    develop_branch=None,
                    feature_prefix=None,
                    fix_prefix=None,
                    release_prefix=None,
                    hotfix_prefix=None,
                    naming_pattern='type/description'
                ),
                commit_pattern=CommitPattern(
                    format_type='other',
                    type_distribution={},
                    dominant_types=[]
                ),
                summary={}
            )
        
        logger.info(f"✅ 找到 Git 仓库: {self.repo_path}")
        
        # 分析分支
        logger.info("🔍 分析分支命名习惯...")
        branches = self._get_branches()
        branch_pattern = self._analyze_branch_pattern(branches)
        
        # 分析提交
        logger.info(f"🔍 分析最近 {self.config.analyze_commits_count} 条提交...")
        commits = self._get_commits(self.config.analyze_commits_count)
        commit_pattern = self._analyze_commit_pattern(commits)
        
        # 生成总结
        summary = self._generate_summary(branch_pattern, commit_pattern)
        
        return GitWorkflowReport(
            branch_pattern=branch_pattern,
            commit_pattern=commit_pattern,
            summary=summary
        )
    
    def _generate_summary(self, branch_pattern: BranchPattern, commit_pattern: CommitPattern) -> Dict[str, str]:
        """生成习惯总结"""
        summary = {}
        
        # 分支策略总结
        branch_strategy = []
        branch_strategy.append(f"主分支: `{branch_pattern.main_branch}`")
        if branch_pattern.develop_branch:
            branch_strategy.append(f"开发分支: `{branch_pattern.develop_branch}`")
        if branch_pattern.feature_prefix:
            branch_strategy.append(f"功能分支: `{branch_pattern.feature_prefix}*`")
        if branch_pattern.fix_prefix:
            branch_strategy.append(f"修复分支: `{branch_pattern.fix_prefix}*`")
        if branch_pattern.release_prefix:
            branch_strategy.append(f"发布分支: `{branch_pattern.release_prefix}*`")
        if branch_pattern.hotfix_prefix:
            branch_strategy.append(f"热修复分支: `{branch_pattern.hotfix_prefix}*`")
        
        summary['branch_strategy'] = '\n'.join(branch_strategy)
        
        # Commit 规范总结
        commit_summary = []
        if commit_pattern.format_type == 'conventional':
            commit_summary.append(f"格式: Conventional Commits (`type(scope): subject`)")
        elif commit_pattern.format_type == 'simple':
            commit_summary.append(f"格式: 简化格式 (`type: subject`)")
        elif commit_pattern.format_type == 'bracket':
            commit_summary.append(f"格式: 方括号格式 (`[type] subject`)")
        else:
            commit_summary.append(f"格式: 其他格式")
        
        if commit_pattern.dominant_types:
            types_str = ', '.join([f"`{t}`" for t in commit_pattern.dominant_types])
            commit_summary.append(f"主要类型: {types_str}")
        
        summary['commit_convention'] = '\n'.join(commit_summary)
        
        # 分支命名规范总结
        naming_summary = []
        naming_summary.append(f"命名模式: `{branch_pattern.naming_pattern}`")
        if branch_pattern.feature_prefix:
            naming_summary.append(f"功能分支: `{branch_pattern.feature_prefix}功能名称`")
        if branch_pattern.fix_prefix:
            naming_summary.append(f"修复分支: `{branch_pattern.fix_prefix}问题描述`")
        if branch_pattern.release_prefix:
            naming_summary.append(f"发布分支: `{branch_pattern.release_prefix}版本号`")
        
        summary['branch_naming'] = '\n'.join(naming_summary)
        
        return summary
    
    def detect_to_file(self, output_path: str):
        """
        检测并输出到文件
        
        Args:
            output_path: 输出文件路径
        """
        report = self.detect()
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("# Git 工作流习惯\n\n")
            
            # 分支策略
            f.write("## 分支策略\n\n")
            if report.summary.get('branch_strategy'):
                for line in report.summary['branch_strategy'].split('\n'):
                    f.write(f"- **{line}**\n")
            else:
                f.write("- **主分支**: `main`\n")
            f.write("\n")
            
            # Commit 信息规范
            f.write("## Commit 信息规范\n\n")
            if report.summary.get('commit_convention'):
                for line in report.summary['commit_convention'].split('\n'):
                    f.write(f"- **{line}**\n")
                
                # 添加示例
                if report.commit_pattern.dominant_types:
                    f.write("\n**示例**:\n")
                    examples = []
                    for commit_type in report.commit_pattern.dominant_types[:3]:
                        if report.commit_pattern.format_type == 'conventional':
                            examples.append(f"  - `{commit_type}(scope): description`")
                        elif report.commit_pattern.format_type == 'simple':
                            examples.append(f"  - `{commit_type}: description`")
                        elif report.commit_pattern.format_type == 'bracket':
                            examples.append(f"  - `[{commit_type}] description`")
                        else:
                            examples.append(f"  - `{commit_type}: description`")
                    f.write('\n'.join(examples))
                    f.write("\n")
            else:
                f.write("- **格式**: 未检测到明确的格式规范\n")
            f.write("\n")
            
            # 分支命名规范
            f.write("## 分支命名规范\n\n")
            if report.summary.get('branch_naming'):
                for line in report.summary['branch_naming'].split('\n'):
                    f.write(f"- **{line}**\n")
                
                # 添加示例
                examples = []
                if report.branch_pattern.feature_prefix:
                    examples.append(f"  - `{report.branch_pattern.feature_prefix}user-auth`")
                if report.branch_pattern.fix_prefix:
                    examples.append(f"  - `{report.branch_pattern.fix_prefix}login-bug`")
                if report.branch_pattern.release_prefix:
                    examples.append(f"  - `{report.branch_pattern.release_prefix}v1.2.0`")
                
                if examples:
                    f.write("\n**示例**:\n")
                    f.write('\n'.join(examples))
                    f.write("\n")
            else:
                f.write("- **命名模式**: `type/description`\n")
            f.write("\n")
        
        logger.info(f"✅ 报告已保存到: {output_path}")

