"""Code Search Index - 代码库搜索索引

实现 Claude Code 风格的代码库搜索功能：
1. 符号搜索 - 查找类、函数、变量定义
2. 引用查找 - 查找符号的所有引用
3. 全文索引 - 快速全文搜索
4. 智能排名 - 根据相关性排序结果
"""

import os
import re
import json
import hashlib
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum
import heapq


class SymbolType(str, Enum):
    """符号类型"""
    CLASS = "class"
    FUNCTION = "function"
    METHOD = "method"
    VARIABLE = "variable"
    CONSTANT = "constant"
    IMPORT = "import"
    MODULE = "module"


@dataclass
class Symbol:
    """代码符号"""
    name: str
    type: SymbolType
    file_path: str
    line_number: int
    column: int = 0
    end_line: int = 0
    signature: str = ""
    docstring: str = ""
    parent: str = ""  # 父级符号（如类名）
    language: str = "python"
    score: float = 0.0  # 相关性评分

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["type"] = self.type.value
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Symbol":
        data["type"] = SymbolType(data["type"])
        return cls(**data)


@dataclass
class SearchResult:
    """搜索结果"""
    symbol: Optional[Symbol]
    file_path: str
    line_number: int
    content: str
    match_type: str  # exact, partial, fuzzy
    score: float
    context: str = ""  # 上下文代码

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        if self.symbol:
            data["symbol"] = self.symbol.to_dict()
        else:
            data["symbol"] = None
        return data


class CodeIndex:
    """代码索引器"""

    # 语言特定的文件扩展名
    LANGUAGE_EXTENSIONS = {
        ".py": "python",
        ".js": "javascript",
        ".ts": "typescript",
        ".jsx": "javascript",
        ".tsx": "typescript",
        ".java": "java",
        ".go": "go",
        ".rs": "rust",
        ".cpp": "cpp",
        ".cc": "cpp",
        ".h": "cpp",
        ".hpp": "cpp",
        ".c": "c",
        ".rb": "ruby",
        ".php": "php",
        ".swift": "swift",
        ".kt": "kotlin",
        ".scala": "scala",
        ".ex": "elixir",
        ".exs": "elixir",
        ".erl": "erlang",
        ".hs": "haskell",
        ".ml": "ocaml",
        ".r": "r",
        ".R": "r",
        ".sh": "bash",
        ".bash": "bash",
        ".zsh": "bash",
    }

    # 语言特定的符号模式
    SYMBOL_PATTERNS = {
        "python": {
            "class": r"^\s*class\s+(\w+)",
            "function": r"^\s*(?:async\s+)?def\s+(\w+)",
            "import": r"^\s*(?:from|import)\s+",
        },
        "javascript": {
            "class": r"(?:export\s+)?class\s+(\w+)",
            "function": r"(?:export\s+)?(?:async\s+)?function\s+(\w+)",
            "const": r"const\s+(\w+)\s*=",
            "let": r"let\s+(\w+)\s*=",
            "var": r"var\s+(\w+)\s*=",
            "arrow": r"(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?\(",
        },
        "typescript": {
            "class": r"(?:export\s+)?(?:abstract\s+)?class\s+(\w+)",
            "interface": r"(?:export\s+)?interface\s+(\w+)",
            "function": r"(?:export\s+)?(?:async\s+)?function\s+(\w+)",
            "type": r"(?:export\s+)?type\s+(\w+)\s*=",
            "enum": r"(?:export\s+)?enum\s+(\w+)",
        },
        "go": {
            "function": r"^func\s+(?:\([^)]+\)\s+)?(\w+)",
            "struct": r"^type\s+(\w+)\s+struct",
            "interface": r"^type\s+(\w+)\s+interface",
        },
        "java": {
            "class": r"(?:public\s+)?(?:abstract\s+)?class\s+(\w+)",
            "interface": r"(?:public\s+)?interface\s+(\w+)",
            "method": r"(?:public|private|protected)\s+(?:static\s+)?\w+\s+(\w+)\s*\(",
        },
    }

    # 忽略的目录
    IGNORE_DIRS = {
        "__pycache__",
        "node_modules",
        ".git",
        ".svn",
        ".hg",
        "vendor",
        "dist",
        "build",
        "target",
        ".idea",
        ".vscode",
        "coverage",
        ".pytest_cache",
        ".mypy_cache",
        "venv",
        ".venv",
        "env",
        ".env",
    }

    def __init__(self, root_path: str = "."):
        self.root_path = Path(root_path).resolve()
        self.index_file = self.root_path / ".code_index.json"
        self.symbols: Dict[str, List[Symbol]] = {}  # name -> symbols
        self.file_cache: Dict[str, str] = {}  # file_path -> content
        self._file_hashes: Dict[str, str] = {}  # file_path -> hash
        self._index_dirty = False

    def build(self, incremental: bool = True) -> Dict[str, Any]:
        """构建索引

        Args:
            incremental: 是否增量更新

        Returns:
            Dict: 构建统计信息
        """
        stats = {
            "files_indexed": 0,
            "symbols_found": 0,
            "errors": [],
        }

        # 加载现有索引
        if incremental and self.index_file.exists():
            self._load_index()

        # 遍历所有文件
        for file_path in self._walk_files():
            try:
                if self._should_reindex(file_path):
                    self._index_file(file_path)
                    stats["files_indexed"] += 1
            except Exception as e:
                stats["errors"].append(f"{file_path}: {e}")

        # 保存索引
        self._save_index()

        return stats

    def _walk_files(self) -> List[Path]:
        """遍历所有代码文件"""
        files = []
        for root, dirs, filenames in os.walk(self.root_path):
            # 移除忽略的目录
            dirs[:] = [d for d in dirs if d not in self.IGNORE_DIRS]

            for filename in filenames:
                ext = Path(filename).suffix.lower()
                if ext in self.LANGUAGE_EXTENSIONS:
                    files.append(Path(root) / filename)

        return files

    def _should_reindex(self, file_path: Path) -> bool:
        """检查文件是否需要重新索引"""
        try:
            with open(file_path, "rb") as f:
                content = f.read()
            current_hash = hashlib.md5(content).hexdigest()

            if str(file_path) in self._file_hashes:
                return self._file_hashes[str(file_path)] != current_hash

            return True
        except Exception:
            return False

    def _index_file(self, file_path: Path) -> None:
        """索引单个文件"""
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
        except Exception:
            return

        # 计算哈希
        file_hash = hashlib.md5(content.encode()).hexdigest()
        self._file_hashes[str(file_path)] = file_hash

        # 缓存内容
        self.file_cache[str(file_path)] = content

        # 检测语言
        ext = file_path.suffix.lower()
        language = self.LANGUAGE_EXTENSIONS.get(ext, "unknown")

        # 提取符号
        symbols = self._extract_symbols(content, str(file_path), language)

        # 添加到索引
        rel_path = str(file_path.relative_to(self.root_path))
        for symbol in symbols:
            symbol.file_path = rel_path
            symbol.language = language

            if symbol.name not in self.symbols:
                self.symbols[symbol.name] = []
            self.symbols[symbol.name].append(symbol)

        self._index_dirty = True

    def _extract_symbols(
        self,
        content: str,
        file_path: str,
        language: str
    ) -> List[Symbol]:
        """从文件中提取符号"""
        symbols = []
        lines = content.split("\n")

        patterns = self.SYMBOL_PATTERNS.get(language, {})

        for line_num, line in enumerate(lines, 1):
            for symbol_type, pattern in patterns.items():
                match = re.search(pattern, line)
                if match:
                    name = match.group(1)
                    symbol = Symbol(
                        name=name,
                        type=SymbolType(symbol_type),
                        file_path=file_path,
                        line_number=line_num,
                        column=match.start(1),
                        language=language,
                    )
                    symbols.append(symbol)

        return symbols

    def _load_index(self) -> None:
        """加载索引"""
        try:
            with open(self.index_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            self.symbols = {}
            for name, symbol_list in data.get("symbols", {}).items():
                self.symbols[name] = [
                    Symbol.from_dict(s) for s in symbol_list
                ]

            self._file_hashes = data.get("file_hashes", {})
        except Exception:
            self.symbols = {}
            self._file_hashes = {}

    def _save_index(self) -> None:
        """保存索引"""
        if not self._index_dirty:
            return

        try:
            data = {
                "symbols": {
                    name: [s.to_dict() for s in symbols]
                    for name, symbols in self.symbols.items()
                },
                "file_hashes": self._file_hashes,
            }

            with open(self.index_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)

            self._index_dirty = False
        except Exception as e:
            print(f"Failed to save index: {e}")

    def search(
        self,
        query: str,
        limit: int = 20,
        file_filter: str = None,
        language_filter: str = None,
        symbol_type_filter: List[SymbolType] = None
    ) -> List[SearchResult]:
        """搜索符号

        Args:
            query: 搜索关键词
            limit: 结果数量限制
            file_filter: 文件过滤模式
            language_filter: 语言过滤
            symbol_type_filter: 符号类型过滤

        Returns:
            List[SearchResult]: 搜索结果列表
        """
        results = []

        # 1. 精确匹配符号名
        if query in self.symbols:
            for symbol in self.symbols[query]:
                if self._matches_filters(symbol, file_filter, language_filter, symbol_type_filter):
                    results.append(self._create_result(symbol, "exact", 100.0))

        # 2. 前缀匹配
        for name, symbols in self.symbols.items():
            if name.startswith(query) and name != query:
                for symbol in symbols:
                    if self._matches_filters(symbol, file_filter, language_filter, symbol_type_filter):
                        score = 90.0 - (len(name) - len(query)) * 2
                        results.append(self._create_result(symbol, "prefix", score))

        # 3. 子串匹配
        for name, symbols in self.symbols.items():
            if query in name and name not in [r.symbol.name for r in results]:
                for symbol in symbols:
                    if self._matches_filters(symbol, file_filter, language_filter, symbol_type_filter):
                        score = 80.0 - (len(name) - len(query)) * 2
                        results.append(self._create_result(symbol, "substring", score))

        # 4. 如果符号搜索没有结果，进行全文搜索
        if not results:
            results.extend(self._full_text_search(
                query, limit, file_filter, language_filter
            ))

        # 排序并返回
        results.sort(key=lambda r: r.score, reverse=True)
        return results[:limit]

    def _matches_filters(
        self,
        symbol: Symbol,
        file_filter: str,
        language_filter: str,
        symbol_type_filter: List[SymbolType]
    ) -> bool:
        """检查符号是否匹配过滤器"""
        if file_filter and file_filter not in symbol.file_path:
            return False
        if language_filter and symbol.language != language_filter:
            return False
        if symbol_type_filter and symbol.type not in symbol_type_filter:
            return False
        return True

    def _create_result(
        self,
        symbol: Symbol,
        match_type: str,
        score: float
    ) -> SearchResult:
        """创建搜索结果"""
        content = self._get_line_content(symbol.file_path, symbol.line_number)
        context = self._get_context(symbol.file_path, symbol.line_number)

        return SearchResult(
            symbol=symbol,
            file_path=symbol.file_path,
            line_number=symbol.line_number,
            content=content,
            match_type=match_type,
            score=score,
            context=context
        )

    def _full_text_search(
        self,
        query: str,
        limit: int,
        file_filter: str,
        language_filter: str
    ) -> List[SearchResult]:
        """全文搜索"""
        results = []

        for file_path, content in self.file_cache.items():
            if file_filter and file_filter not in file_path:
                continue

            lines = content.split("\n")
            for line_num, line in enumerate(lines, 1):
                if query.lower() in line.lower():
                    # 计算相关性分数
                    score = self._calculate_text_score(query, line)

                    results.append(SearchResult(
                        symbol=None,
                        file_path=file_path,
                        line_number=line_num,
                        content=line.strip(),
                        match_type="text",
                        score=score,
                        context=self._get_context_for_line(file_path, line_num, lines)
                    ))

                    if len(results) >= limit * 2:  # 获取更多结果用于排序
                        break

        return sorted(results, key=lambda r: r.score, reverse=True)[:limit]

    def _calculate_text_score(self, query: str, line: str) -> float:
        """计算文本匹配分数"""
        score = 0.0
        line_lower = line.lower()
        query_lower = query.lower()

        # 精确匹配
        if query_lower in line_lower:
            score += 50.0

        # 完整单词匹配
        if re.search(rf"\b{re.escape(query_lower)}\b", line_lower):
            score += 30.0

        # 靠近行首的匹配（可能是定义）
        idx = line_lower.find(query_lower)
        if idx >= 0 and idx < 20:
            score += 20.0 - idx

        return score

    def _get_line_content(self, file_path: str, line_number: int) -> str:
        """获取指定行的内容"""
        try:
            content = self.file_cache.get(file_path)
            if not content:
                full_path = self.root_path / file_path
                with open(full_path, "r", encoding="utf-8") as f:
                    content = f.read()
                self.file_cache[file_path] = content

            lines = content.split("\n")
            if 0 < line_number <= len(lines):
                return lines[line_number - 1].strip()
        except Exception:
            pass
        return ""

    def _get_context(
        self,
        file_path: str,
        line_number: int,
        context_lines: int = 3
    ) -> str:
        """获取上下文代码"""
        try:
            content = self.file_cache.get(file_path)
            if not content:
                return ""

            lines = content.split("\n")
            start = max(0, line_number - context_lines - 1)
            end = min(len(lines), line_number + context_lines)

            context_lines_list = lines[start:end]
            return "\n".join(context_lines_list)
        except Exception:
            return ""

    def _get_context_for_line(
        self,
        file_path: str,
        line_number: int,
        all_lines: List[str],
        context_lines: int = 2
    ) -> str:
        """获取指定行的上下文"""
        start = max(0, line_number - context_lines - 1)
        end = min(len(all_lines), line_number + context_lines)
        return "\n".join(all_lines[start:end])

    def find_references(
        self,
        symbol_name: str,
        include_definitions: bool = False
    ) -> List[SearchResult]:
        """查找符号引用

        Args:
            symbol_name: 符号名称
            include_definitions: 是否包含定义

        Returns:
            List[SearchResult]: 引用列表
        """
        results = []

        # 获取符号定义
        definitions = self.symbols.get(symbol_name, [])

        if not include_definitions:
            # 排除定义位置
            def_positions = {
                (s.file_path, s.line_number) for s in definitions
            }
        else:
            def_positions = set()

        # 在所有文件中搜索引用
        for file_path, content in self.file_cache.items():
            lines = content.split("\n")
            for line_num, line in enumerate(lines, 1):
                if symbol_name in line:
                    if (file_path, line_num) not in def_positions:
                        results.append(SearchResult(
                            symbol=None,
                            file_path=file_path,
                            line_number=line_num,
                            content=line.strip(),
                            match_type="reference",
                            score=50.0,
                            context=self._get_context_for_line(file_path, line_num, lines)
                        ))

        return results

    def get_stats(self) -> Dict[str, Any]:
        """获取索引统计信息"""
        symbol_counts = {}
        for name, symbols in self.symbols.items():
            for s in symbols:
                key = f"{s.language}:{s.type.value}"
                symbol_counts[key] = symbol_counts.get(key, 0) + 1

        return {
            "total_symbols": sum(len(symbols) for symbols in self.symbols.values()),
            "unique_symbols": len(self.symbols),
            "indexed_files": len(self.file_cache),
            "symbol_by_type": symbol_counts,
        }

    def clear(self) -> None:
        """清除索引"""
        self.symbols = {}
        self.file_cache = {}
        self._file_hashes = {}
        self._index_dirty = True

        if self.index_file.exists():
            self.index_file.unlink()


# 全局索引实例
_global_index: Optional[CodeIndex] = None


def get_code_index(root_path: str = ".") -> CodeIndex:
    """获取全局代码索引"""
    global _global_index
    if _global_index is None:
        _global_index = CodeIndex(root_path)
    return _global_index


def search_code(
    query: str,
    limit: int = 20,
    **kwargs
) -> List[Dict[str, Any]]:
    """搜索代码（便捷函数）

    Args:
        query: 搜索关键词
        limit: 结果数量
        **kwargs: 其他过滤参数

    Returns:
        List[Dict]: 搜索结果字典列表
    """
    index = get_code_index()
    results = index.search(query, limit, **kwargs)
    return [r.to_dict() for r in results]
