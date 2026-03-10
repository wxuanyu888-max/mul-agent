"""Memory Search Tool - 记忆搜索工具

提供：
1. 语义搜索
2. 混合搜索（向量 + 全文）
3. 相关记忆检索
4. 存档检索
"""

import json
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from pathlib import Path

from .memory_manager import MemoryIndexManager, MemorySearchResult
from .archiver import MemoryArchiver


@dataclass
class MemorySearchOptions:
    """搜索选项"""
    max_results: int = 20
    min_score: float = 0.3
    use_hybrid: bool = True
    include_archives: bool = True
    include_short_term: bool = True
    include_long_term: bool = True
    memory_type: Optional[str] = None  # 指定类型则只搜索该类型


@dataclass
class MemorySearchResponse:
    """搜索响应"""
    query: str
    results: List[Dict[str, Any]]
    total: int
    search_type: str  # "vector", "keyword", "hybrid"
    sources: List[str]  # ["memory", "archive", "conversation"]


class MemorySearchTool:
    """记忆搜索工具"""

    def __init__(
        self,
        index_manager: MemoryIndexManager,
        archiver: Optional[MemoryArchiver] = None
    ):
        """初始化记忆搜索工具

        Args:
            index_manager: MemoryIndexManager 实例
            archiver: MemoryArchiver 实例（可选）
        """
        self.index_manager = index_manager
        self.archiver = archiver

        # 记忆存储路径
        self.memory_path = Path(__file__).parent.parent.parent / "storage" / "memory"

    def search(
        self,
        query: str,
        options: Optional[MemorySearchOptions] = None
    ) -> MemorySearchResponse:
        """搜索记忆

        Args:
            query: 搜索查询
            options: 搜索选项

        Returns:
            搜索响应
        """
        options = options or MemorySearchOptions()
        results = []
        search_type = "unknown"
        sources = []

        # 1. 搜索向量索引
        if self.index_manager.provider and options.use_hybrid:
            index_results = self.index_manager.search(
                query=query,
                max_results=options.max_results,
                min_score=options.min_score,
                use_hybrid=True
            )
            results.extend([self._convert_index_result(r) for r in index_results])
            search_type = "hybrid"
            sources.append("memory_index")

        # 2. 搜索存档
        if options.include_archives and self.archiver:
            archive_results = self.archiver.search_archives(
                agent_id="wang",  # 默认 agent
                query=query,
                max_results=options.max_results
            )
            for archive in archive_results:
                results.append({
                    "type": "archive",
                    "id": archive.id,
                    "session_id": archive.session_id,
                    "summary": archive.summary,
                    "keywords": archive.keywords,
                    "score": 0.8,  # 默认分数
                    "token_count": archive.token_count,
                    "created_at": archive.created_at
                })
            if archive_results:
                sources.append("archive")

        # 3. 搜索短期记忆
        if options.include_short_term:
            st_results = self._search_memory_type("short_term", query, options.max_results)
            results.extend(st_results)
            if st_results:
                sources.append("short_term")

        # 4. 搜索长期记忆
        if options.include_long_term:
            lt_results = self._search_memory_type("long_term", query, options.max_results)
            results.extend(lt_results)
            if lt_results:
                sources.append("long_term")

        # 去重和排序
        results = self._deduplicate_and_sort(results, query)

        # 应用数量限制
        results = results[:options.max_results]

        return MemorySearchResponse(
            query=query,
            results=results,
            total=len(results),
            search_type=search_type,
            sources=sources
        )

    def _convert_index_result(self, result: MemorySearchResult) -> Dict[str, Any]:
        """转换索引结果为字典"""
        return {
            "type": "memory_index",
            "id": result.id,
            "path": result.path,
            "start_line": result.start_line,
            "end_line": result.end_line,
            "score": result.score,
            "snippet": result.snippet,
            "source": result.source,
            "citation": result.citation
        }

    def _search_memory_type(
        self,
        memory_type: str,
        query: str,
        limit: int
    ) -> List[Dict[str, Any]]:
        """搜索特定类型的记忆"""
        memory_file = self.memory_path / "short_term" / "wang" / "*.md"
        if memory_type == "long_term":
            memory_file = self.memory_path / "long_term" / "wang" / "*.md"

        results = []
        query_lower = query.lower()

        for md_file in memory_file.parent.glob("*.md"):
            try:
                content = md_file.read_text(encoding="utf-8")
                content_lower = content.lower()

                if query_lower in content_lower:
                    # 计算相关度
                    score = self._calculate_relevance(content, query)

                    if score >= 0.3:
                        results.append({
                            "type": memory_type,
                            "id": md_file.stem,
                            "path": str(md_file),
                            "content": content[:500],
                            "score": score,
                            "memory_type": memory_type
                        })
            except Exception:
                continue

        return sorted(results, key=lambda x: x["score"], reverse=True)[:limit]

    def _calculate_relevance(self, content: str, query: str) -> float:
        """计算相关度分数"""
        content_lower = content.lower()
        query_lower = query.lower()

        # 完全匹配
        if query_lower in content_lower:
            return 1.0

        # 关键词匹配
        query_words = query_lower.split()
        matches = sum(1 for word in query_words if word in content_lower)

        return matches / len(query_words) if query_words else 0.0

    def _deduplicate_and_sort(
        self,
        results: List[Dict[str, Any]],
        query: str
    ) -> List[Dict[str, Any]]:
        """去重并排序结果"""
        seen_ids = set()
        unique_results = []

        for result in results:
            result_id = f"{result.get('type', '')}:{result.get('id', '')}"
            if result_id not in seen_ids:
                seen_ids.add(result_id)
                unique_results.append(result)

        # 按分数排序
        return sorted(unique_results, key=lambda x: x.get("score", 0), reverse=True)

    def retrieve_context(
        self,
        query: str,
        max_tokens: int = 4000
    ) -> str:
        """检索相关上下文

        用于构建 Agent 的上下文提示词

        Args:
            query: 当前查询/任务
            max_tokens: 最大 token 数

        Returns:
            格式化的上下文字符串
        """
        response = self.search(query, MemorySearchOptions(
            max_results=10,
            min_score=0.4
        ))

        if not response.results:
            return "未找到相关记忆"

        # 构建上下文
        context_parts = ["## 相关记忆\n"]

        current_tokens = 0
        for result in response.results:
            snippet = result.get("snippet", result.get("content", result.get("summary", "")))
            snippet_tokens = len(snippet) // 4

            if current_tokens + snippet_tokens > max_tokens:
                break

            context_parts.append(f"### {result.get('type', 'memory')} (分数：{result.get('score', 0):.2f})")
            context_parts.append(snippet)
            context_parts.append("")

            current_tokens += snippet_tokens

        return "\n".join(context_parts)

    def get_memory_summary(self, agent_id: str) -> Dict[str, Any]:
        """获取记忆系统摘要

        Args:
            agent_id: Agent ID

        Returns:
            摘要信息
        """
        summary = {
            "index_status": None,
            "archive_stats": None,
            "memory_stats": None
        }

        # 索引状态
        try:
            status = self.index_manager.status()
            summary["index_status"] = {
                "provider": status.provider,
                "model": status.model,
                "files": status.files,
                "chunks": status.chunks,
                "fts_enabled": status.fts_enabled
            }
        except Exception as e:
            summary["index_status"] = {"error": str(e)}

        # 存档统计
        if self.archiver:
            summary["archive_stats"] = self.archiver.get_archive_stats(agent_id)

        # 记忆统计
        st_count = len(list((self.memory_path / "short_term" / agent_id).glob("*.md"))) if (self.memory_path / "short_term" / agent_id).exists() else 0
        lt_count = len(list((self.memory_path / "long_term" / agent_id).glob("*.md"))) if (self.memory_path / "long_term" / agent_id).exists() else 0

        summary["memory_stats"] = {
            "short_term_count": st_count,
            "long_term_count": lt_count
        }

        return summary
