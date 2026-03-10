"""Memory Archiver - 记忆存档系统

负责：
1. 将压缩后的对话存档到向量数据库
2. 管理存档的生命周期
3. 支持按主题/时间检索存档
"""

import json
import hashlib
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime
from dataclasses import dataclass, field

from .memory_manager import MemoryIndexManager
from .embeddings import EmbeddingProvider


@dataclass
class MemoryArchive:
    """记忆存档"""
    id: str
    session_id: str
    agent_id: str
    content: Dict[str, Any]
    summary: str
    keywords: List[str]
    start_message_index: int
    end_message_index: int
    token_count: int
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    archived_at: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)


class MemoryArchiver:
    """记忆存档器"""

    def __init__(
        self,
        index_manager: MemoryIndexManager,
        embedding_provider: Optional[EmbeddingProvider] = None
    ):
        """初始化记忆存档器

        Args:
            index_manager: MemoryIndexManager 实例
            embedding_provider: 嵌入提供商（可选）
        """
        self.index_manager = index_manager
        self.embedding_provider = embedding_provider

        # 存档存储路径
        self.storage_path = Path(__file__).parent.parent.parent / "storage" / "memory_archives"
        self.storage_path.mkdir(parents=True, exist_ok=True)

    def create_archive(
        self,
        session_id: str,
        agent_id: str,
        messages: List[Dict[str, Any]],
        summary: str,
        keywords: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> MemoryArchive:
        """创建记忆存档

        Args:
            session_id: 会话 ID
            agent_id: Agent ID
            messages: 要存档的消息列表
            summary: 压缩摘要
            keywords: 关键词列表
            metadata: 附加元数据

        Returns:
            MemoryArchive 实例
        """
        # 生成存档 ID
        archive_id = self._generate_archive_id(agent_id, session_id, messages)

        # 计算 token 数
        token_count = sum(
            len(msg.get("content", "")) // 4
            for msg in messages
        )

        # 确定消息索引范围
        start_index = metadata.get("start_message_index", 0) if metadata else 0
        end_index = start_index + len(messages)

        # 创建存档
        archive = MemoryArchive(
            id=archive_id,
            session_id=session_id,
            agent_id=agent_id,
            content={
                "messages": messages,
                "summary": summary
            },
            summary=summary,
            keywords=keywords or self._extract_keywords(summary),
            start_message_index=start_index,
            end_message_index=end_index,
            token_count=token_count,
            metadata=metadata or {}
        )

        # 保存到磁盘
        self._save_archive(archive)

        # 索引到向量数据库
        self._index_archive(archive)

        return archive

    def _generate_archive_id(
        self,
        agent_id: str,
        session_id: str,
        messages: List[Dict[str, Any]]
    ) -> str:
        """生成存档唯一 ID"""
        content = f"{agent_id}:{session_id}:{len(messages)}"
        if messages:
            content += f":{messages[0].get('timestamp', '')}"
        return hashlib.md5(content.encode()).hexdigest()[:16]

    def _extract_keywords(self, summary: str, max_keywords: int = 10) -> List[str]:
        """从摘要中提取关键词

        简单实现：可以使用 LLM 或 TF-IDF 提取
        这里使用简单的关键词提取
        """
        # 简单分词（中文）
        import re
        words = re.findall(r'[\u4e00-\u9fff]{2,}', summary)

        # 去重并按频率排序
        word_count: Dict[str, int] = {}
        for word in words:
            word_count[word] = word_count.get(word, 0) + 1

        sorted_words = sorted(word_count.items(), key=lambda x: x[1], reverse=True)
        return [word for word, _ in sorted_words[:max_keywords]]

    def _save_archive(self, archive: MemoryArchive) -> None:
        """保存存档到磁盘"""
        agent_path = self.storage_path / archive.agent_id
        agent_path.mkdir(parents=True, exist_ok=True)

        archive_file = agent_path / f"{archive.id}.json"
        with open(archive_file, "w", encoding="utf-8") as f:
            json.dump({
                "id": archive.id,
                "session_id": archive.session_id,
                "agent_id": archive.agent_id,
                "content": archive.content,
                "summary": archive.summary,
                "keywords": archive.keywords,
                "start_message_index": archive.start_message_index,
                "end_message_index": archive.end_message_index,
                "token_count": archive.token_count,
                "created_at": archive.created_at,
                "archived_at": archive.archived_at,
                "metadata": archive.metadata
            }, f, ensure_ascii=False, indent=2)

    def _index_archive(self, archive: MemoryArchive) -> None:
        """索引存档到向量数据库"""
        # 创建索引文本
        index_text = f"""
会话：{archive.session_id}
摘要：{archive.summary}
关键词：{', '.join(archive.keywords)}
时间范围：消息 {archive.start_message_index}-{archive.end_message_index}
"""

        # 注意：实际的向量索引需要异步调用嵌入 API
        # 这里只保存文本到 FTS
        # 完整实现需要调用 memory_indexer 来分块和嵌入

    def search_archives(
        self,
        agent_id: str,
        query: str,
        max_results: int = 10
    ) -> List[MemoryArchive]:
        """搜索存档

        Args:
            agent_id: Agent ID
            query: 搜索查询
            max_results: 最大结果数

        Returns:
            匹配的存档列表
        """
        # 首先尝试向量搜索
        if self.index_manager.provider:
            vector_results = self.index_manager.search(
                query=query,
                max_results=max_results,
                use_hybrid=True
            )
            if vector_results:
                # 从向量搜索结果中加载存档
                return self._load_archives_from_results(agent_id, vector_results)

        # Fallback 到文件系统搜索
        return self._search_filesystem(agent_id, query, max_results)

    def _load_archives_from_results(
        self,
        agent_id: str,
        results: List[Any]
    ) -> List[MemoryArchive]:
        """从向量搜索结果加载存档"""
        archives = []
        agent_path = self.storage_path / agent_id

        for result in results:
            # 从结果中提取存档 ID
            archive_id = result.id.split(":")[0] if ":" in result.id else result.id
            archive_file = agent_path / f"{archive_id}.json"

            if archive_file.exists():
                try:
                    with open(archive_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        archives.append(MemoryArchive(**data))
                except Exception:
                    continue

        return archives

    def _search_filesystem(
        self,
        agent_id: str,
        query: str,
        max_results: int
    ) -> List[MemoryArchive]:
        """在文件系统中搜索存档"""
        agent_path = self.storage_path / agent_id
        if not agent_path.exists():
            return []

        results = []
        query_lower = query.lower()

        for archive_file in agent_path.glob("*.json"):
            try:
                with open(archive_file, "r", encoding="utf-8") as f:
                    data = json.load(f)

                # 搜索摘要和关键词
                summary = data.get("summary", "").lower()
                keywords = " ".join(data.get("keywords", [])).lower()

                if query_lower in summary or query_lower in keywords:
                    results.append(MemoryArchive(**data))

                    if len(results) >= max_results:
                        break
            except Exception:
                continue

        return results

    def list_archives(
        self,
        agent_id: str,
        limit: int = 20,
        offset: int = 0
    ) -> List[MemoryArchive]:
        """列出存档

        Args:
            agent_id: Agent ID
            limit: 数量限制
            offset: 偏移量

        Returns:
            存档列表
        """
        agent_path = self.storage_path / agent_id
        if not agent_path.exists():
            return []

        archives = []
        for archive_file in sorted(agent_path.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
            try:
                with open(archive_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                archives.append(MemoryArchive(**data))
            except Exception:
                continue

        return archives[offset:offset + limit]

    def delete_archive(self, agent_id: str, archive_id: str) -> bool:
        """删除存档

        Args:
            agent_id: Agent ID
            archive_id: 存档 ID

        Returns:
            是否成功删除
        """
        agent_path = self.storage_path / agent_id
        archive_file = agent_path / f"{archive_id}.json"

        if archive_file.exists():
            archive_file.unlink()
            return True
        return False

    def get_archive_stats(self, agent_id: str) -> Dict[str, Any]:
        """获取存档统计

        Args:
            agent_id: Agent ID

        Returns:
            统计信息
        """
        agent_path = self.storage_path / agent_id
        if not agent_path.exists():
            return {"total_archives": 0, "total_tokens": 0}

        total_archives = 0
        total_tokens = 0
        sessions: Dict[str, int] = {}

        for archive_file in agent_path.glob("*.json"):
            try:
                with open(archive_file, "r", encoding="utf-8") as f:
                    data = json.load(f)

                total_archives += 1
                total_tokens += data.get("token_count", 0)

                session_id = data.get("session_id", "unknown")
                sessions[session_id] = sessions.get(session_id, 0) + 1
            except Exception:
                continue

        return {
            "total_archives": total_archives,
            "total_tokens": total_tokens,
            "unique_sessions": len(sessions),
            "sessions_count": len(sessions)
        }
