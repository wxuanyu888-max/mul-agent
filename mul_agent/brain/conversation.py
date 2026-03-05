"""Conversation Manager - 对话历史管理器

提供对话历史的持久化、检索功能，与 Memory 系统整合。
"""

import json
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


class ConversationManager:
    """对话历史管理器

    功能：
    - 持久化对话历史到磁盘（JSONL 格式）
    - 按模板规范化存储
    - 自动分页（避免单文件过大）
    - 支持检索和查询
    - 与 Memory 系统整合
    """

    def __init__(self, memory=None, storage_path: str = "storage/conversations"):
        """初始化对话历史管理器

        Args:
            memory: Memory 实例（可选，用于整合）
            storage_path: 存储路径
        """
        self.memory = memory

        # 计算基础路径
        base_dir = Path(__file__).parent.parent.parent / storage_path
        self.base_path = base_dir
        self.base_path.mkdir(parents=True, exist_ok=True)

    def _get_conversation_path(self, agent_id: str, session_id: str) -> Path:
        """获取对话文件路径"""
        path = self.base_path / agent_id / session_id
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _generate_id(self, agent_id: str, session_id: str, content: str) -> str:
        """生成唯一ID"""
        raw = f"{agent_id}:{session_id}:{content}:{datetime.now().isoformat()}"
        return hashlib.md5(raw.encode()).hexdigest()[:16]

    def save_message(
        self,
        agent_id: str,
        session_id: str,
        role: str,
        content: Any,
        metadata: Optional[Dict] = None
    ) -> str:
        """保存单条消息

        Args:
            agent_id: Agent ID
            session_id: 会话 ID
            role: 角色 (user/assistant/system)
            content: 消息内容
            metadata: 附加元数据

        Returns:
            消息 ID
        """
        timestamp = datetime.now().isoformat()
        message_id = self._generate_id(agent_id, session_id, str(content))

        # 构建消息结构
        message = {
            "id": message_id,
            "role": role,
            "content": content if isinstance(content, str) else json.dumps(content, ensure_ascii=False),
            "timestamp": timestamp,
            "metadata": metadata or {}
        }

        # 获取对话文件路径
        conv_path = self._get_conversation_path(agent_id, session_id)

        # 使用日期分文件 (每天一个文件)
        date_str = datetime.now().strftime("%Y%m%d")
        filepath = conv_path / f"{date_str}.jsonl"

        # 追加写入
        with open(filepath, "a", encoding="utf-8") as f:
            f.write(json.dumps(message, ensure_ascii=False) + "\n")

        # 同时写入 Memory 系统（可选）
        if self.memory:
            self.memory.write("conversation", {
                "agent_id": agent_id,
                "session_id": session_id,
                "role": role,
                "content": content,
                "message_id": message_id
            })

        return message_id

    def save_messages(
        self,
        agent_id: str,
        session_id: str,
        messages: List[Dict[str, Any]]
    ) -> List[str]:
        """批量保存消息

        Args:
            agent_id: Agent ID
            session_id: 会话 ID
            messages: 消息列表

        Returns:
            消息 ID 列表
        """
        ids = []
        for msg in messages:
            msg_id = self.save_message(
                agent_id=agent_id,
                session_id=session_id,
                role=msg.get("role", "assistant"),
                content=msg.get("content", ""),
                metadata=msg.get("metadata")
            )
            ids.append(msg_id)
        return ids

    def get_history(
        self,
        agent_id: str,
        session_id: str,
        limit: int = 100,
        offset: int = 0,
        date: Optional[str] = None
    ) -> List[Dict]:
        """获取对话历史

        Args:
            agent_id: Agent ID
            session_id: 会话 ID
            limit: 返回数量限制
            offset: 偏移量
            date: 指定日期 (YYYYMMDD)，默认当天

        Returns:
            消息列表
        """
        conv_path = self._get_conversation_path(agent_id, session_id)

        if date:
            # 读取指定日期
            filepath = conv_path / f"{date}.jsonl"
            if not filepath.exists():
                return []
            files = [filepath]
        else:
            # 读取所有文件（按日期排序）
            files = sorted(conv_path.glob("*.jsonl"), key=lambda p: p.name)

        messages = []
        for filepath in files:
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            try:
                                msg = json.loads(line)
                                messages.append(msg)
                            except json.JSONDecodeError:
                                continue
            except Exception:
                continue

        # 应用分页
        return messages[offset:offset + limit]

    def get_history_with_summary(
        self,
        agent_id: str,
        session_id: str,
        limit: int = 100
    ) -> Dict[str, Any]:
        """获取对话历史及摘要

        Args:
            agent_id: Agent ID
            session_id: 会话 ID
            limit: 返回数量限制

        Returns:
            包含 messages 和 metadata 的字典
        """
        messages = self.get_history(agent_id, session_id, limit=limit)

        # 计算统计信息
        total_tokens = sum(
            len(msg.get("content", "")) // 4  # 粗略估算 token 数
            for msg in messages
        )

        return {
            "messages": messages,
            "metadata": {
                "total_messages": len(messages),
                "estimated_tokens": total_tokens,
                "session_id": session_id,
                "agent_id": agent_id
            }
        }

    def search_history(
        self,
        agent_id: str,
        session_id: Optional[str] = None,
        query: Optional[str] = None,
        role: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict]:
        """搜索对话历史

        Args:
            agent_id: Agent ID
            session_id: 会话 ID（可选）
            query: 搜索关键词
            role: 按角色过滤
            limit: 返回数量限制

        Returns:
            匹配的消息列表
        """
        results = []

        # 确定搜索路径
        if session_id:
            search_paths = [self._get_conversation_path(agent_id, session_id)]
        else:
            search_paths = [self.base_path / agent_id]

        for search_path in search_paths:
            if not search_path.exists():
                continue

            for filepath in search_path.glob("**/*.jsonl"):
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        for line in f:
                            line = line.strip()
                            if not line:
                                continue

                            try:
                                msg = json.loads(line)
                            except json.JSONDecodeError:
                                continue

                            # 过滤条件
                            if role and msg.get("role") != role:
                                continue

                            if query:
                                content = msg.get("content", "")
                                if query.lower() not in content.lower():
                                    continue

                            results.append(msg)

                            if len(results) >= limit:
                                break
                except Exception:
                    continue

            if len(results) >= limit:
                break

        return results[:limit]

    def list_sessions(self, agent_id: str) -> List[Dict]:
        """列出所有会话

        Args:
            agent_id: Agent ID

        Returns:
            会话列表（包含 ID、消息数、最后更新时间）
        """
        agent_path = self.base_path / agent_id
        if not agent_path.exists():
            return []

        sessions = []
        for session_dir in agent_path.iterdir():
            if not session_dir.is_dir():
                continue

            # 统计消息数量
            total_messages = 0
            latest_time = None

            for filepath in session_dir.glob("*.jsonl"):
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        for line in f:
                            if line.strip():
                                total_messages += 1
                                try:
                                    msg = json.loads(line)
                                    msg_time = msg.get("timestamp", "")
                                    if msg_time:
                                        if latest_time is None or msg_time > latest_time:
                                            latest_time = msg_time
                                except:
                                    continue
                except Exception:
                    continue

            sessions.append({
                "session_id": session_dir.name,
                "total_messages": total_messages,
                "last_updated": latest_time
            })

        # 按最后更新时间排序
        sessions.sort(key=lambda x: x.get("last_updated", ""), reverse=True)
        return sessions

    def delete_session(self, agent_id: str, session_id: str) -> bool:
        """删除会话

        Args:
            agent_id: Agent ID
            session_id: 会话 ID

        Returns:
            是否成功
        """
        conv_path = self._get_conversation_path(agent_id, session_id)

        if not conv_path.exists():
            return False

        try:
            import shutil
            shutil.rmtree(conv_path)
            return True
        except Exception:
            return False

    def compress_old_messages(
        self,
        agent_id: str,
        session_id: str,
        summary: str
    ) -> bool:
        """压缩旧消息（存储摘要）

        Args:
            agent_id: Agent ID
            session_id: 会话 ID
            summary: 压缩摘要

        Returns:
            是否成功
        """
        conv_path = self._get_conversation_path(agent_id, session_id)

        # 创建压缩文件
        compress_file = conv_path / "compressed_summary.md"

        try:
            with open(compress_file, "w", encoding="utf-8") as f:
                f.write(f"# 对话摘要\n\n")
                f.write(f"**会话**: {session_id}\n")
                f.write(f"**压缩时间**: {datetime.now().isoformat()}\n\n")
                f.write(f"## 摘要\n\n{summary}\n")
            return True
        except Exception:
            return False

    def get_compressed_summary(
        self,
        agent_id: str,
        session_id: str
    ) -> Optional[str]:
        """获取压缩摘要

        Args:
            agent_id: Agent ID
            session_id: 会话 ID

        Returns:
            压缩摘要内容，如果不存在则返回 None
        """
        conv_path = self._get_conversation_path(agent_id, session_id)
        compress_file = conv_path / "compressed_summary.md"

        if not compress_file.exists():
            return None

        try:
            with open(compress_file, "r", encoding="utf-8") as f:
                return f.read()
        except Exception:
            return None


# 便捷函数
def create_conversation_manager(memory=None) -> ConversationManager:
    """创建 ConversationManager 的便捷函数

    Args:
        memory: Memory 实例

    Returns:
        ConversationManager 实例
    """
    return ConversationManager(memory=memory)
