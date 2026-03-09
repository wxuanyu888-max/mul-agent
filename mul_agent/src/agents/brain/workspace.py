"""Workspace - 工作区感知系统

参考 Claude Code 的设计：
1. 启动时自动扫描工作区
2. 识别项目类型（Python/Node.js/Go 等）
3. 在提示词中注入工作区信息
4. 智能识别相关文件
"""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
from dataclasses import dataclass, field
from enum import Enum


class ProjectType(Enum):
    """项目类型"""
    PYTHON = "python"
    NODEJS = "nodejs"
    GO = "golang"
    RUST = "rust"
    JAVA = "java"
    TYPESCRIPT = "typescript"
    UNKNOWN = "unknown"


@dataclass
class WorkspaceInfo:
    """工作区信息"""
    name: str
    root_path: Path
    project_type: ProjectType = ProjectType.UNKNOWN
    description: str = ""

    # 项目文件
    package_files: List[str] = field(default_factory=list)  # package.json, setup.py, go.mod 等
    source_dirs: List[str] = field(default_factory=list)  # src, lib, app 等
    test_dirs: List[str] = field(default_factory=list)  # tests, test, __tests__ 等

    # 配置文件
    config_files: List[str] = field(default_factory=list)

    # 依赖信息
    dependencies: List[str] = field(default_factory=list)
    dev_dependencies: List[str] = field(default_factory=list)

    # 脚本
    scripts: Dict[str, str] = field(default_factory=dict)

    # Git 信息
    git_repo: bool = False
    current_branch: str = ""

    # 最近修改的文件
    recently_modified: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "name": self.name,
            "root_path": str(self.root_path),
            "project_type": self.project_type.value,
            "description": self.description,
            "package_files": self.package_files,
            "source_dirs": self.source_dirs,
            "test_dirs": self.test_dirs,
            "config_files": self.config_files,
            "dependencies": self.dependencies[:20],  # 限制数量
            "dev_dependencies": self.dev_dependencies[:10],
            "scripts": dict(list(self.scripts.items())[:10]),
            "git_repo": self.git_repo,
            "current_branch": self.current_branch,
            "recently_modified": self.recently_modified[:10]
        }

    def to_prompt(self) -> str:
        """生成提示词格式"""
        lines = [
            f"## 工作区：{self.name}",
            f"项目类型：{self.project_type.value}",
            f"根目录：{self.root_path}",
        ]

        if self.description:
            lines.append(f"描述：{self.description}")

        if self.source_dirs:
            lines.append(f"源码目录：{', '.join(self.source_dirs)}")

        if self.test_dirs:
            lines.append(f"测试目录：{', '.join(self.test_dirs)}")

        if self.dependencies:
            deps = self.dependencies[:10]
            lines.append(f"主要依赖：{', '.join(deps)}{'...' if len(self.dependencies) > 10 else ''}")

        if self.scripts:
            lines.append("可用脚本:")
            for name, cmd in list(self.scripts.items())[:5]:
                lines.append(f"  - `{name}`: {cmd[:50]}...")

        if self.git_repo:
            lines.append(f"Git 分支：{self.current_branch}")

        return "\n".join(lines)


class Workspace:
    """工作区扫描和管理器"""

    # 项目类型识别文件
    PROJECT_INDICATORS = {
        ProjectType.PYTHON: ["setup.py", "pyproject.toml", "requirements.txt", "Pipfile"],
        ProjectType.NODEJS: ["package.json", "package-lock.json", "yarn.lock"],
        ProjectType.GO: ["go.mod", "go.sum", "Gopkg.toml"],
        ProjectType.RUST: ["Cargo.toml", "Cargo.lock"],
        ProjectType.JAVA: ["pom.xml", "build.gradle", "build.gradle.kts"],
        ProjectType.TYPESCRIPT: ["tsconfig.json"],
    }

    # 常见的源码目录
    SOURCE_DIR_NAMES = ["src", "lib", "app", "source", "sources", "main"]

    # 常见的测试目录
    TEST_DIR_NAMES = ["test", "tests", "__tests__", "spec", "specs", "testing"]

    # 常见的配置文件
    CONFIG_FILES = [
        ".gitignore", ".editorconfig", "tsconfig.json", "jsconfig.json",
        "mypy.ini", "setup.cfg", ".prettierrc", ".eslintrc",
        "pytest.ini", "tox.ini", "Makefile"
    ]

    def __init__(self, root_path: Optional[str] = None):
        """初始化工作区

        Args:
            root_path: 工作区根目录，默认为当前目录
        """
        self.root_path = Path(root_path) if root_path else Path.cwd()
        self.info: Optional[WorkspaceInfo] = None

    def scan(self) -> WorkspaceInfo:
        """扫描工作区，收集项目信息"""
        self.info = WorkspaceInfo(
            name=self.root_path.name,
            root_path=self.root_path
        )

        # 1. 识别项目类型
        self._detect_project_type()

        # 2. 扫描目录结构
        self._scan_directories()

        # 3. 扫描配置文件
        self._scan_config_files()

        # 4. 解析项目元数据
        self._parse_project_metadata()

        # 5. 检查 Git
        self._check_git()

        # 6. 获取最近修改的文件
        self._get_recently_modified()

        return self.info

    def _detect_project_type(self):
        """检测项目类型"""
        for project_type, indicators in self.PROJECT_INDICATORS.items():
            for indicator in indicators:
                if (self.root_path / indicator).exists():
                    self.info.project_type = project_type
                    self.info.package_files.append(indicator)
                    return

        # 如果没有匹配，检查是否有主要语言的文件
        py_files = list(self.root_path.glob("**/*.py"))
        ts_files = list(self.root_path.glob("**/*.ts"))
        go_files = list(self.root_path.glob("**/*.go"))
        rs_files = list(self.root_path.glob("**/*.rs"))

        if len(py_files) > len(ts_files) and len(py_files) > len(go_files):
            self.info.project_type = ProjectType.PYTHON
        elif len(ts_files) > len(go_files):
            self.info.project_type = ProjectType.NODEJS
        elif len(go_files) > 0:
            self.info.project_type = ProjectType.GO
        elif len(rs_files) > 0:
            self.info.project_type = ProjectType.RUST

    def _scan_directories(self):
        """扫描目录结构"""
        for item in self.root_path.iterdir():
            if not item.is_dir():
                continue

            name_lower = item.name.lower()

            # 跳过常见忽略目录
            if name_lower in ["node_modules", "__pycache__", ".git", ".venv", "vendor", "dist", "build"]:
                continue

            # 识别源码目录
            if name_lower in self.SOURCE_DIR_NAMES:
                self.info.source_dirs.append(str(item.relative_to(self.root_path)))

            # 识别测试目录
            if name_lower in self.TEST_DIR_NAMES:
                self.info.test_dirs.append(str(item.relative_to(self.root_path)))

        # 如果没找到源码目录，当前目录可能就是源码
        if not self.info.source_dirs:
            self.info.source_dirs.append(".")

    def _scan_config_files(self):
        """扫描配置文件"""
        for config_file in self.CONFIG_FILES:
            config_path = self.root_path / config_file
            if config_path.exists():
                self.info.config_files.append(config_file)

    def _parse_project_metadata(self):
        """解析项目元数据（package.json, setup.py 等）"""
        # package.json
        package_json_path = self.root_path / "package.json"
        if package_json_path.exists():
            try:
                import json
                with open(package_json_path) as f:
                    data = json.load(f)

                self.info.dependencies.extend(data.get("dependencies", {}).keys())
                self.info.dev_dependencies.extend(data.get("devDependencies", {}).keys())
                self.info.scripts = data.get("scripts", {})

                if "description" in data:
                    self.info.description = data["description"]
            except Exception:
                pass

        # pyproject.toml
        pyproject_path = self.root_path / "pyproject.toml"
        if pyproject_path.exists():
            try:
                import tomllib
                with open(pyproject_path, "rb") as f:
                    data = tomllib.load(f)

                project = data.get("project", {})
                self.info.dependencies.extend(project.get("dependencies", []))
                if "description" in project:
                    self.info.description = project["description"]

                # 脚本
                scripts = project.get("scripts", {})
                self.info.scripts.update(scripts)
            except Exception:
                pass

        # setup.py
        setup_py_path = self.root_path / "setup.py"
        if setup_py_path.exists():
            try:
                # 简单解析
                with open(setup_py_path) as f:
                    content = f.read()

                if "name=" in content:
                    import re
                    name_match = re.search(r'name=["\']([^"\']+)["\']', content)
                    if name_match:
                        self.info.description = f"Python package: {name_match.group(1)}"
            except Exception:
                pass

        # go.mod
        go_mod_path = self.root_path / "go.mod"
        if go_mod_path.exists():
            try:
                with open(go_mod_path) as f:
                    lines = f.readlines()

                for line in lines:
                    if line.startswith("require"):
                        # 解析依赖
                        parts = line.split()
                        if len(parts) >= 2:
                            self.info.dependencies.append(parts[1])
            except Exception:
                pass

    def _check_git(self):
        """检查 Git 状态"""
        git_dir = self.root_path / ".git"
        self.info.git_repo = git_dir.exists()

        if self.info.git_repo:
            try:
                import subprocess
                result = subprocess.run(
                    ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                    cwd=self.root_path,
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    self.info.current_branch = result.stdout.strip()
            except Exception:
                pass

    def _get_recently_modified(self, limit: int = 10):
        """获取最近修改的文件"""
        files = []

        try:
            for item in self.root_path.rglob("*"):
                if item.is_file():
                    # 跳过忽略的目录
                    if any(skip in str(item) for skip in ["node_modules", "__pycache__", ".git", ".venv"]):
                        continue

                    try:
                        mtime = item.stat().st_mtime
                        files.append((str(item.relative_to(self.root_path)), mtime))
                    except Exception:
                        continue
        except Exception:
            pass

        # 按修改时间排序
        files.sort(key=lambda x: x[1], reverse=True)
        self.info.recently_modified = [f[0] for f in files[:limit]]

    def find_files(self, pattern: str, max_results: int = 50) -> List[str]:
        """查找匹配的文件

        Args:
            pattern: glob 模式，如 "*.py", "src/**/*.ts"
            max_results: 最大结果数

        Returns:
            匹配的文件路径列表
        """
        results = []

        try:
            for item in self.root_path.glob(pattern):
                if item.is_file():
                    results.append(str(item.relative_to(self.root_path)))
                if len(results) >= max_results:
                    break
        except Exception:
            pass

        return results

    def search_content(self, query: str, file_pattern: str = "*.py", max_results: int = 20) -> List[Dict[str, Any]]:
        """搜索文件内容

        Args:
            query: 搜索关键词
            file_pattern: 文件匹配模式
            max_results: 最大结果数

        Returns:
            匹配结果列表
        """
        results = []
        import re

        query_pattern = re.compile(re.escape(query), re.IGNORECASE)

        for item in self.root_path.glob(file_pattern):
            if not item.is_file():
                continue

            try:
                with open(item, "r", encoding="utf-8", errors="ignore") as f:
                    for line_num, line in enumerate(f, 1):
                        if query_pattern.search(line):
                            results.append({
                                "file": str(item.relative_to(self.root_path)),
                                "line": line_num,
                                "content": line.strip()[:200]
                            })
                            if len(results) >= max_results:
                                break
            except Exception:
                continue

            if len(results) >= max_results:
                break

        return results

    def get_context_prompt(self) -> str:
        """获取工作区上下文提示词"""
        if not self.info:
            self.scan()

        return self.info.to_prompt()


class WorkspaceManager:
    """工作区管理器 - 管理多个工作区"""

    _instance = None
    _workspaces: Dict[str, Workspace] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def get_instance(cls) -> "WorkspaceManager":
        """获取单例实例"""
        return cls()

    def get_or_create(self, path: str) -> Workspace:
        """获取或创建工作区"""
        path = str(Path(path).absolute())

        if path not in self._workspaces:
            self._workspaces[path] = Workspace(path)
            self._workspaces[path].scan()

        return self._workspaces[path]

    def list_workspaces(self) -> List[Workspace]:
        """列出所有工作区"""
        return list(self._workspaces.values())

    def clear(self):
        """清除所有工作区缓存"""
        self._workspaces.clear()


# 全局工作区管理器
workspace_manager = WorkspaceManager.get_instance()


def get_current_workspace() -> Workspace:
    """获取当前工作区"""
    return workspace_manager.get_or_create(str(Path.cwd()))
