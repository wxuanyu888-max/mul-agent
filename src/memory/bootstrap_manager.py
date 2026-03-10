"""Bootstrap Memory Manager - 引导记忆管理器

负责：
1. 维护动态 bootstrap 文件夹
2. Token 上限检测
3. 自动压缩旧内容
"""

import json
import hashlib
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class BootstrapEntry:
    """Bootstrap 条目"""
    id: str
    key: str
    content: Any
    token_count: int
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    access_count: int = 0
    priority: str = "normal"  # "high", "normal", "low"
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BootstrapFolder:
    """Bootstrap 文件夹"""
    agent_id: str
    session_id: str
    entries: Dict[str, BootstrapEntry] = field(default_factory=dict)
    total_tokens: int = 0
    max_tokens: int = 8000
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())


class BootstrapMemoryManager:
    """Bootstrap 记忆管理器"""

    def __init__(
        self,
        storage_path: str = "storage/bootstrap",
        max_tokens: int = 8000,
        warning_threshold: float = 0.8
    ):
        """初始化 Bootstrap 管理器

        Args:
            storage_path: 存储路径
            max_tokens: 最大 token 数
            warning_threshold: 警告阈值（0-1）
        """
        self.storage_path = Path(__file__).parent.parent.parent / storage_path
        self.storage_path.mkdir(parents=True, exist_ok=True)

        self.max_tokens = max_tokens
        self.warning_threshold = warning_threshold
        self.warning_tokens = int(max_tokens * warning_threshold)

        self.folder_cache: Dict[str, BootstrapFolder] = {}

    def get_folder_path(self, agent_id: str, session_id: str) -> Path:
        """获取文件夹路径"""
        path = self.storage_path / agent_id / session_id
        path.mkdir(parents=True, exist_ok=True)
        return path

    def load_folder(
        self,
        agent_id: str,
        session_id: str
    ) -> BootstrapFolder:
        """加载 bootstrap 文件夹

        Args:
            agent_id: Agent ID
            session_id: 会话 ID

        Returns:
            BootstrapFolder 实例
        """
        cache_key = f"{agent_id}:{session_id}"

        if cache_key in self.folder_cache:
            return self.folder_cache[cache_key]

        folder_path = self.get_folder_path(agent_id, session_id)
        folder = BootstrapFolder(
            agent_id=agent_id,
            session_id=session_id,
            max_tokens=self.max_tokens
        )

        # 加载条目
        index_file = folder_path / "index.json"
        if index_file.exists():
            with open(index_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                folder.total_tokens = data.get("total_tokens", 0)
                folder.created_at = data.get("created_at", folder.created_at)
                folder.updated_at = data.get("updated_at", folder.updated_at)

                for entry_data in data.get("entries", []):
                    entry = BootstrapEntry(**entry_data)
                    folder.entries[entry.key] = entry

        self.folder_cache[cache_key] = folder
        return folder

    def get_or_create_bootstrap(
        self,
        agent_id: str,
        session_id: str
    ) -> BootstrapFolder:
        """获取或创建 bootstrap 文件夹（便捷方法）

        Args:
            agent_id: Agent ID
            session_id: 会话 ID

        Returns:
            BootstrapFolder 实例
        """
        return self.load_folder(agent_id, session_id)

    def add_entry(
        self,
        agent_id: str,
        session_id: str,
        key: str,
        content: Any,
        priority: str = "normal",
        metadata: Optional[Dict[str, Any]] = None
    ) -> BootstrapFolder:
        """添加条目到 bootstrap

        Args:
            agent_id: Agent ID
            session_id: 会话 ID
            key: 条目键
            content: 条目内容
            priority: 优先级
            metadata: 附加元数据

        Returns:
            更新后的 BootstrapFolder
        """
        folder = self.load_folder(agent_id, session_id)

        # 计算 token
        content_text = json.dumps(content, ensure_ascii=False) if isinstance(content, (dict, list)) else str(content)
        token_count = len(content_text) // 4

        # 创建或更新条目
        entry_id = hashlib.md5(f"{agent_id}:{session_id}:{key}".encode()).hexdigest()[:16]
        now = datetime.now().isoformat()

        if key in folder.entries:
            # 更新现有条目
            existing = folder.entries[key]
            folder.total_tokens -= existing.token_count
            existing.content = content
            existing.token_count = token_count
            existing.updated_at = now
            existing.metadata = metadata or {}
        else:
            # 创建新条目
            folder.entries[key] = BootstrapEntry(
                id=entry_id,
                key=key,
                content=content,
                token_count=token_count,
                priority=priority,
                metadata=metadata or {}
            )

        folder.total_tokens += token_count
        folder.updated_at = now

        # 检查是否需要压缩
        self._check_compression_needed(folder)

        # 持久化
        self._save_folder(folder)

        return folder

    def get_entry(
        self,
        agent_id: str,
        session_id: str,
        key: str
    ) -> Optional[BootstrapEntry]:
        """获取条目"""
        folder = self.load_folder(agent_id, session_id)
        entry = folder.entries.get(key)

        if entry:
            entry.access_count += 1
            self._save_folder(folder)

        return entry

    def remove_entry(
        self,
        agent_id: str,
        session_id: str,
        key: str
    ) -> bool:
        """移除条目"""
        folder = self.load_folder(agent_id, session_id)

        if key not in folder.entries:
            return False

        entry = folder.entries[key]
        folder.total_tokens -= entry.token_count
        del folder.entries[key]
        folder.updated_at = datetime.now().isoformat()

        self._save_folder(folder)
        return True

    def list_entries(
        self,
        agent_id: str,
        session_id: str,
        priority: Optional[str] = None
    ) -> List[BootstrapEntry]:
        """列出条目

        Args:
            agent_id: Agent ID
            session_id: 会话 ID
            priority: 按优先级过滤

        Returns:
            条目列表
        """
        folder = self.load_folder(agent_id, session_id)
        entries = list(folder.entries.values())

        if priority:
            entries = [e for e in entries if e.priority == priority]

        # 按优先级和更新时间排序
        priority_order = {"high": 0, "normal": 1, "low": 2}
        entries.sort(key=lambda e: (priority_order.get(e.priority, 1), e.updated_at), reverse=True)

        return entries

    def _check_compression_needed(self, folder: BootstrapFolder) -> Dict[str, Any]:
        """检查是否需要压缩

        Returns:
            压缩需求信息
        """
        needs_compression = False
        reason = ""

        if folder.total_tokens >= self.max_tokens:
            needs_compression = True
            reason = f"Bootstrap tokens ({folder.total_tokens}) exceed max ({self.max_tokens})"
        elif folder.total_tokens >= self.warning_tokens:
            needs_compression = True
            reason = f"Bootstrap tokens ({folder.total_tokens}) approaching max ({self.max_tokens})"

        if needs_compression:
            return {
                "needs_compression": True,
                "reason": reason,
                "current_tokens": folder.total_tokens,
                "max_tokens": self.max_tokens,
                "suggestion": self._generate_compression_suggestion(folder)
            }

        return {"needs_compression": False}

    def _generate_compression_suggestion(self, folder: BootstrapFolder) -> Dict[str, Any]:
        """生成压缩建议

        返回应该被压缩的条目列表
        """
        entries = list(folder.entries.values())

        # 按优先级和访问频率排序
        # 低优先级 + 低访问频率的条目应该先被压缩
        def entry_score(entry: BootstrapEntry) -> tuple:
            priority_score = {"high": 0, "normal": 1, "low": 2}.get(entry.priority, 1)
            access_score = min(entry.access_count, 10)  # 最多 10 次
            return (priority_score, -access_score)

        entries.sort(key=entry_score)

        # 计算需要压缩多少
        tokens_to_free = folder.total_tokens - int(self.max_tokens * 0.5)

        # 选择要压缩的条目
        to_compress = []
        freed_tokens = 0

        for entry in entries:
            if freed_tokens >= tokens_to_free:
                break

            to_compress.append({
                "key": entry.key,
                "tokens": entry.token_count,
                "priority": entry.priority,
                "access_count": entry.access_count
            })
            freed_tokens += entry.token_count

        return {
            "to_compress": to_compress,
            "estimated_free_tokens": freed_tokens,
            "target_tokens": int(self.max_tokens * 0.5)
        }

    def compress_folder(
        self,
        agent_id: str,
        session_id: str,
        entries_to_archive: List[str],
        archive_callback: Optional[Callable[[str, Any], None]] = None
    ) -> BootstrapFolder:
        """压缩 bootstrap 文件夹

        Args:
            agent_id: Agent ID
            session_id: 会话 ID
            entries_to_archive: 要存档的条目键列表
            archive_callback: 存档回调函数 (key, content) -> None

        Returns:
            更新后的 BootstrapFolder
        """
        folder = self.load_folder(agent_id, session_id)

        archived_entries = []

        for key in entries_to_archive:
            if key not in folder.entries:
                continue

            entry = folder.entries[key]

            # 调用存档回调
            if archive_callback:
                archive_callback(key, entry.content)

            archived_entries.append({
                "key": key,
                "content": entry.content,
                "archived_at": datetime.now().isoformat()
            })

            # 从 folder 中移除
            folder.total_tokens -= entry.token_count
            del folder.entries[key]

        folder.updated_at = datetime.now().isoformat()

        # 保存存档记录
        self._save_archive_log(agent_id, session_id, archived_entries)

        # 持久化
        self._save_folder(folder)

        return folder

    def _save_folder(self, folder: BootstrapFolder) -> None:
        """保存文件夹到磁盘"""
        folder_path = self.get_folder_path(folder.agent_id, folder.session_id)

        index_file = folder_path / "index.json"
        data = {
            "agent_id": folder.agent_id,
            "session_id": folder.session_id,
            "total_tokens": folder.total_tokens,
            "max_tokens": folder.max_tokens,
            "created_at": folder.created_at,
            "updated_at": folder.updated_at,
            "entries": [
                {
                    "id": e.id,
                    "key": e.key,
                    "content": e.content,
                    "token_count": e.token_count,
                    "created_at": e.created_at,
                    "updated_at": e.updated_at,
                    "access_count": e.access_count,
                    "priority": e.priority,
                    "metadata": e.metadata
                }
                for e in folder.entries.values()
            ]
        }

        with open(index_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        # 更新缓存
        cache_key = f"{folder.agent_id}:{folder.session_id}"
        self.folder_cache[cache_key] = folder

    def _save_archive_log(
        self,
        agent_id: str,
        session_id: str,
        archived_entries: List[Dict[str, Any]]
    ) -> None:
        """保存存档日志"""
        folder_path = self.get_folder_path(agent_id, session_id)
        archive_log = folder_path / "archive_log.jsonl"

        with open(archive_log, "a", encoding="utf-8") as f:
            for entry in archived_entries:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def get_compression_hint(
        self,
        agent_id: str,
        session_id: str
    ) -> Dict[str, Any]:
        """获取压缩提示词

        Returns:
            压缩提示词字典
        """
        folder = self.load_folder(agent_id, session_id)
        compression_info = self._check_compression_needed(folder)

        if not compression_info.get("needs_compression"):
            return {
                "needs_compression": False,
                "hint": None
            }

        # 构建提示词
        hint = {
            "needs_compression": True,
            "type": "bootstrap",
            "current_tokens": folder.total_tokens,
            "max_tokens": self.max_tokens,
            "reason": compression_info.get("reason", ""),
            "suggestion": compression_info.get("suggestion", {}),
            "prompt": self._build_compression_prompt(folder, compression_info)
        }

        return hint

    def _build_compression_prompt(
        self,
        folder: BootstrapFolder,
        compression_info: Dict[str, Any]
    ) -> str:
        """构建压缩提示词"""
        suggestion = compression_info.get("suggestion", {})
        to_compress = suggestion.get("to_compress", [])

        return f"""【压缩请求】Bootstrap 内容接近 token 上限

当前 Bootstrap Token 数：{folder.total_tokens}
最大允许：{self.max_tokens}
警告阈值：{self.warning_tokens}

建议压缩以下条目（按优先级从低到高排序）：
""" + "\n".join([
            f"- `{e['key']}`: {e['tokens']} tokens (优先级：{e['priority']}, 访问：{e['access_count']}次)"
            for e in to_compress[:10]
        ]) + f"""

请将上述条目存档到 memory 系统，并从 bootstrap 中移除。
压缩后目标 token 数：{suggestion.get('target_tokens', int(self.max_tokens * 0.5))}

当前 bootstrap 条目列表：
""" + "\n".join([
            f"- `{e.key}` ({e.priority}): {str(e.content)[:50]}..."
            for e in list(folder.entries.values())[:15]
        ])
