"""Message Queue - Agent 间消息队列"""

import json
import hashlib
import os
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field, asdict
from enum import Enum


class MessageStatus(Enum):
    """消息状态"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    EXPIRED = "expired"


class MessageType(Enum):
    """消息类型"""
    TASK = "task"           # 任务委派
    RESPONSE = "response"   # 响应回复
    BROADCAST = "broadcast" # 广播消息
    HANDOVER = "handover"   # 交接文档


@dataclass
class Message:
    """消息数据结构"""
    id: str
    from_agent: str
    to_agent: str
    msg_type: str
    content: Dict[str, Any]
    status: str = MessageStatus.PENDING.value
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    processed_at: Optional[str] = None
    error: Optional[str] = None
    priority: int = 5  # 1-10, 1 最高
    ttl_seconds: int = 3600  # 消息存活时间（秒）
    retry_count: int = 0
    max_retries: int = 3

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Message":
        """从字典创建"""
        return cls(**data)


class MessageQueue:
    """消息队列实现

    支持：
    - 点对点消息
    - 广播消息
    - 消息优先级
    - 消息过期
    - 重试机制
    """

    def __init__(self, storage_path: Optional[str] = None):
        """初始化消息队列

        Args:
            storage_path: 消息存储路径，默认使用 storage/message_queue
        """
        if storage_path:
            self.storage_path = Path(storage_path)
        else:
            self.storage_path = Path(__file__).parent.parent.parent / "storage" / "message_queue"

        self.storage_path.mkdir(parents=True, exist_ok=True)

        # 按 Agent ID 分目录存储
        self.agent_queues_path = self.storage_path / "queues"
        self.agent_queues_path.mkdir(parents=True, exist_ok=True)

        # 广播消息
        self.broadcast_path = self.storage_path / "broadcasts"
        self.broadcast_path.mkdir(parents=True, exist_ok=True)

        # 已处理消息
        self.processed_path = self.storage_path / "processed"
        self.processed_path.mkdir(parents=True, exist_ok=True)

        # 内存缓存（提高性能）
        self._cache: Dict[str, List[Message]] = {}

    def _generate_message_id(self, from_agent: str, to_agent: str, content: Dict) -> str:
        """生成消息 ID"""
        timestamp = datetime.now().isoformat()
        raw = f"{from_agent}:{to_agent}:{timestamp}:{json.dumps(content, sort_keys=True)}"
        return hashlib.md5(raw.encode()).hexdigest()[:16]

    def _get_agent_queue_path(self, agent_id: str) -> Path:
        """获取 Agent 的消息队列路径"""
        path = self.agent_queues_path / agent_id
        path.mkdir(parents=True, exist_ok=True)
        return path

    def send(self, from_agent: str, to_agent: str, content: Dict[str, Any],
             msg_type: MessageType = MessageType.TASK,
             priority: int = 5,
             ttl_seconds: int = 3600) -> str:
        """发送消息

        Args:
            from_agent: 发送方 Agent ID
            to_agent: 接收方 Agent ID
            content: 消息内容
            msg_type: 消息类型
            priority: 优先级（1-10，1 最高）
            ttl_seconds: 消息存活时间（秒）

        Returns:
            消息 ID
        """
        message = Message(
            id=self._generate_message_id(from_agent, to_agent, content),
            from_agent=from_agent,
            to_agent=to_agent,
            msg_type=msg_type.value,
            content=content,
            priority=priority,
            ttl_seconds=ttl_seconds
        )

        # 保存到文件
        queue_path = self._get_agent_queue_path(to_agent)
        filepath = queue_path / f"{message.id}.json"

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(message.to_dict(), f, ensure_ascii=False, indent=2)

        # 更新缓存
        if to_agent not in self._cache:
            self._cache[to_agent] = []
        self._cache[to_agent].append(message)

        return message.id

    def receive(self, agent_id: str, limit: int = 10,
                msg_type: Optional[MessageType] = None,
                status: Optional[MessageStatus] = None) -> List[Message]:
        """接收消息

        Args:
            agent_id: 接收方 Agent ID
            limit: 最大返回数量
            msg_type: 消息类型过滤
            status: 消息状态过滤

        Returns:
            消息列表，按优先级排序
        """
        queue_path = self._get_agent_queue_path(agent_id)

        if not queue_path.exists():
            return []

        messages = []
        now = datetime.now()

        for msg_file in queue_path.glob("*.json"):
            try:
                with open(msg_file, "r", encoding="utf-8") as f:
                    data = json.load(f)

                msg = Message.from_dict(data)

                # 检查过期
                created = datetime.fromisoformat(msg.created_at)
                if (now - created).total_seconds() > msg.ttl_seconds:
                    msg.status = MessageStatus.EXPIRED.value
                    self._update_message_status(msg)
                    continue

                # 过滤状态
                if status and msg.status != status.value:
                    continue

                # 过滤类型
                if msg_type and msg.msg_type != msg_type.value:
                    continue

                # 只返回待处理的消息
                if msg.status == MessageStatus.PENDING.value:
                    messages.append(msg)

            except Exception:
                continue

        # 按优先级排序（数字越小优先级越高）
        messages.sort(key=lambda m: (m.priority, m.created_at))

        return messages[:limit]

    def mark_processed(self, message_id: str, agent_id: str,
                       status: MessageStatus = MessageStatus.COMPLETED,
                       error: Optional[str] = None) -> bool:
        """标记消息为已处理

        Args:
            message_id: 消息 ID
            agent_id: 接收方 Agent ID
            status: 处理状态
            error: 错误信息（如果失败）

        Returns:
            是否成功
        """
        queue_path = self._get_agent_queue_path(agent_id)
        filepath = queue_path / f"{message_id}.json"

        if not filepath.exists():
            return False

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)

            msg = Message.from_dict(data)
            msg.status = status.value
            msg.processed_at = datetime.now().isoformat()
            msg.updated_at = datetime.now().isoformat()

            if error:
                msg.error = error

            # 更新文件
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(msg.to_dict(), f, ensure_ascii=False, indent=2)

            # 移动已处理的消息到 processed 目录
            processed_agent_path = self.processed_path / agent_id
            processed_agent_path.mkdir(parents=True, exist_ok=True)
            processed_filepath = processed_agent_path / f"{message_id}.json"

            os.rename(filepath, processed_filepath)

            # 清除缓存
            if agent_id in self._cache:
                self._cache[agent_id] = [
                    m for m in self._cache[agent_id] if m.id != message_id
                ]

            return True

        except Exception:
            return False

    def _update_message_status(self, message: Message) -> bool:
        """更新消息状态"""
        queue_path = self._get_agent_queue_path(message.to_agent)
        filepath = queue_path / f"{message.id}.json"

        if not filepath.exists():
            return False

        message.updated_at = datetime.now().isoformat()

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(message.to_dict(), f, ensure_ascii=False, indent=2)

        return True

    def broadcast(self, from_agent: str, content: Dict[str, Any],
                  msg_type: MessageType = MessageType.BROADCAST,
                  exclude_agents: Optional[List[str]] = None) -> List[str]:
        """广播消息给所有 Agent

        Args:
            from_agent: 发送方 Agent ID
            content: 消息内容
            msg_type: 消息类型
            exclude_agents: 排除的 Agent ID 列表

        Returns:
            接收消息的 Agent ID 列表
        """
        exclude = set(exclude_agents or [])

        # 获取所有 Agent 队列
        agent_ids = set()
        for agent_dir in self.agent_queues_path.iterdir():
            if agent_dir.is_dir():
                agent_ids.add(agent_dir.name)

        # 排除发送方和指定 Agent
        agent_ids.discard(from_agent)
        agent_ids -= exclude

        message_ids = []
        for agent_id in agent_ids:
            msg_id = self.send(
                from_agent=from_agent,
                to_agent=agent_id,
                content=content,
                msg_type=msg_type,
                priority=5  # 广播消息默认优先级
            )
            message_ids.append(msg_id)

        return message_ids

    def get_pending_count(self, agent_id: str) -> int:
        """获取待处理消息数量"""
        messages = self.receive(agent_id, limit=1000)
        return len(messages)

    def clear_expired(self, agent_id: Optional[str] = None) -> int:
        """清理过期消息

        Args:
            agent_id: Agent ID，None 表示清理所有

        Returns:
            清理的消息数量
        """
        count = 0
        now = datetime.now()

        if agent_id:
            queue_paths = [self._get_agent_queue_path(agent_id)]
        else:
            queue_paths = list(self.agent_queues_path.iterdir())

        for queue_path in queue_paths:
            if not queue_path.is_dir():
                continue

            for msg_file in queue_path.glob("*.json"):
                try:
                    with open(msg_file, "r", encoding="utf-8") as f:
                        data = json.load(f)

                    msg = Message.from_dict(data)
                    created = datetime.fromisoformat(msg.created_at)

                    if (now - created).total_seconds() > msg.ttl_seconds:
                        msg_file.unlink()
                        count += 1

                except Exception:
                    continue

        return count

    def get_statistics(self) -> Dict[str, Any]:
        """获取消息队列统计信息"""
        stats = {
            "total_agents": 0,
            "pending_messages": 0,
            "processed_messages": 0,
            "agents": {}
        }

        # 统计每个 Agent
        for agent_dir in self.agent_queues_path.iterdir():
            if not agent_dir.is_dir():
                continue

            agent_id = agent_dir.name
            stats["total_agents"] += 1

            pending = 0
            for msg_file in agent_dir.glob("*.json"):
                try:
                    with open(msg_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    msg = Message.from_dict(data)
                    if msg.status == MessageStatus.PENDING.value:
                        pending += 1
                except Exception:
                    continue

            stats["pending_messages"] += pending
            stats["agents"][agent_id] = {"pending": pending}

        # 统计已处理消息
        for processed_dir in self.processed_path.iterdir():
            if not processed_dir.is_dir():
                continue

            count = len(list(processed_dir.glob("*.json")))
            stats["processed_messages"] += count

        return stats
