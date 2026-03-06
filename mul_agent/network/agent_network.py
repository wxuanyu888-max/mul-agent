"""Agent Network - Agent 间直接通信网络"""

import json
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List, Optional, Callable
from mul_agent.network.message_queue import MessageQueue, Message, MessageType, MessageStatus


class AgentNetwork:
    """Agent 网络通信管理器

    功能：
    - Agent 注册与发现
    - 消息路由
    - 任务委派
    - 响应收集
    """

    def __init__(self, storage_path: Optional[str] = None):
        """初始化 Agent 网络

        Args:
            storage_path: 存储路径，默认使用 storage/network
        """
        if storage_path:
            self.storage_path = Path(storage_path)
        else:
            self.storage_path = Path(__file__).parent.parent.parent / "storage" / "network"

        self.storage_path.mkdir(parents=True, exist_ok=True)

        # 消息队列
        self.queue = MessageQueue(storage_path=str(self.storage_path / "queue"))

        # Agent 注册表
        self.registry_path = self.storage_path / "registry"
        self.registry_path.mkdir(parents=True, exist_ok=True)

        # Agent 注册文件
        self.registry_file = self.registry_path / "agents.json"

        # 内存缓存
        self._agents: Dict[str, Dict[str, Any]] = {}
        self._callbacks: Dict[str, Callable] = {}  # Agent ID -> 回调函数

        # 加载已注册的 Agent
        self._load_registry()

    def _load_registry(self) -> None:
        """加载 Agent 注册表"""
        if self.registry_file.exists():
            try:
                with open(self.registry_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._agents = data.get("agents", {})
            except Exception:
                self._agents = {}

    def _save_registry(self) -> None:
        """保存 Agent 注册表"""
        with open(self.registry_file, "w", encoding="utf-8") as f:
            json.dump({"agents": self._agents, "updated_at": datetime.now().isoformat()},
                      f, ensure_ascii=False, indent=2)

    def register(self, agent_id: str, metadata: Optional[Dict[str, Any]] = None,
                 callback: Optional[Callable] = None) -> bool:
        """注册 Agent 到网络

        Args:
            agent_id: Agent ID
            metadata: Agent 元数据（能力、状态等）
            callback: 消息回调函数

        Returns:
            是否成功
        """
        self._agents[agent_id] = {
            "id": agent_id,
            "status": "active",
            "registered_at": datetime.now().isoformat(),
            "last_seen": datetime.now().isoformat(),
            "metadata": metadata or {},
            "capabilities": (metadata or {}).get("capabilities", [])
        }
        self._save_registry()

        if callback:
            self._callbacks[agent_id] = callback

        return True

    def unregister(self, agent_id: str) -> bool:
        """注销 Agent"""
        if agent_id in self._agents:
            self._agents[agent_id]["status"] = "inactive"
            self._agents[agent_id]["unregistered_at"] = datetime.now().isoformat()
            self._save_registry()

            if agent_id in self._callbacks:
                del self._callbacks[agent_id]

            return True
        return False

    def get_agent(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """获取 Agent 信息"""
        return self._agents.get(agent_id)

    def list_agents(self, status: Optional[str] = None,
                    capability: Optional[str] = None) -> List[Dict[str, Any]]:
        """列出 Agent

        Args:
            status: 状态过滤（active/inactive）
            capability: 能力过滤

        Returns:
            Agent 列表
        """
        agents = list(self._agents.values())

        if status:
            agents = [a for a in agents if a.get("status") == status]

        if capability:
            agents = [
                a for a in agents
                if capability in (a.get("capabilities") or [])
            ]

        return agents

    def find_specialist(self, task_type: str) -> Optional[str]:
        """查找专业 Agent

        Args:
            task_type: 任务类型（如 coding/security/testing/writing）

        Returns:
            匹配的 Agent ID，无则返回 None
        """
        # 任务类型到能力的映射
        capability_map = {
            "coding": ["code", "development", "programming"],
            "security": ["security", "audit", "review"],
            "testing": ["testing", "qa", "validation"],
            "writing": ["writing", "documentation", "content"],
            "research": ["research", "search", "analysis"],
            "planning": ["planning", "architecture", "design"]
        }

        capabilities = capability_map.get(task_type, [task_type])

        for agent_id, agent in self._agents.items():
            if agent.get("status") != "active":
                continue

            agent_caps = agent.get("capabilities", [])
            for cap in capabilities:
                if cap in agent_caps:
                    return agent_id

        return None

    def send(self, from_agent: str, to_agent: str, content: Dict[str, Any],
             msg_type: MessageType = MessageType.TASK,
             priority: int = 5,
             expect_response: bool = False) -> str:
        """发送消息

        Args:
            from_agent: 发送方 Agent ID
            to_agent: 接收方 Agent ID
            content: 消息内容
            msg_type: 消息类型
            priority: 优先级
            expect_response: 是否期待响应

        Returns:
            消息 ID
        """
        # 检查接收方是否存在
        if to_agent not in self._agents:
            # 尝试发送（可能是外部 Agent）
            pass

        # 更新发送方 last_seen
        if from_agent in self._agents:
            self._agents[from_agent]["last_seen"] = datetime.now().isoformat()
            self._save_registry()

        # 添加到消息内容的元数据
        full_content = {
            "from": from_agent,
            "to": to_agent,
            "expect_response": expect_response,
            "sent_at": datetime.now().isoformat(),
            **content
        }

        msg_id = self.queue.send(
            from_agent=from_agent,
            to_agent=to_agent,
            content=full_content,
            msg_type=msg_type,
            priority=priority
        )

        # 如果有回调，立即触发
        if to_agent in self._callbacks:
            try:
                self._callbacks[to_agent](full_content)
            except Exception:
                pass

        return msg_id

    def receive(self, agent_id: str, limit: int = 10,
                msg_type: Optional[MessageType] = None) -> List[Message]:
        """接收消息

        Args:
            agent_id: Agent ID
            limit: 最大数量
            msg_type: 消息类型过滤

        Returns:
            消息列表
        """
        # 更新 last_seen
        if agent_id in self._agents:
            self._agents[agent_id]["last_seen"] = datetime.now().isoformat()
            self._save_registry()

        return self.queue.receive(agent_id, limit=limit, msg_type=msg_type)

    def respond(self, from_agent: str, original_message: Message,
                response_content: Dict[str, Any],
                success: bool = True) -> str:
        """响应消息

        Args:
            from_agent: 响应方 Agent ID
            original_message: 原始消息
            response_content: 响应内容
            success: 是否成功

        Returns:
            响应消息 ID
        """
        return self.send(
            from_agent=from_agent,
            to_agent=original_message.from_agent,
            content={
                "in_response_to": original_message.id,
                "success": success,
                "response": response_content
            },
            msg_type=MessageType.RESPONSE
        )

    def delegate_task(self, from_agent: str, to_agent: str,
                      task: Dict[str, Any],
                      callback_msg_id: Optional[str] = None) -> str:
        """委派任务

        Args:
            from_agent: 委托方 Agent ID
            to_agent: 接收方 Agent ID
            task: 任务详情
            callback_msg_id: 回调消息 ID（用于关联响应）

        Returns:
            委派消息 ID
        """
        content = {
            "action": "delegate",
            "task": task,
            "callback_msg_id": callback_msg_id
        }

        return self.send(
            from_agent=from_agent,
            to_agent=to_agent,
            content=content,
            msg_type=MessageType.TASK,
            priority=task.get("priority", 5),
            expect_response=True
        )

    def broadcast(self, from_agent: str, content: Dict[str, Any],
                  exclude_agents: Optional[List[str]] = None) -> List[str]:
        """广播消息

        Args:
            from_agent: 发送方 Agent ID
            content: 消息内容
            exclude_agents: 排除的 Agent ID 列表

        Returns:
            接收消息的 Agent ID 列表
        """
        return self.queue.broadcast(
            from_agent=from_agent,
            content=content,
            exclude_agents=exclude_agents
        )

    def mark_message_processed(self, message_id: str, agent_id: str,
                               success: bool = True,
                               error: Optional[str] = None) -> bool:
        """标记消息为已处理"""
        status = MessageStatus.COMPLETED if success else MessageStatus.FAIRED
        return self.queue.mark_processed(
            message_id=message_id,
            agent_id=agent_id,
            status=status,
            error=error
        )

    def get_pending_tasks(self, agent_id: str) -> List[Message]:
        """获取待处理任务"""
        return self.queue.receive(
            agent_id=agent_id,
            limit=100,
            msg_type=MessageType.TASK,
            status=MessageStatus.PENDING
        )

    def get_network_stats(self) -> Dict[str, Any]:
        """获取网络统计信息"""
        queue_stats = self.queue.get_statistics()

        return {
            "total_agents": len(self._agents),
            "active_agents": len([a for a in self._agents.values() if a.get("status") == "active"]),
            "registered_agents": list(self._agents.keys()),
            "queue_stats": queue_stats
        }

    def create_handover(self, from_agent: str, to_agent: str,
                        handover_data: Dict[str, Any]) -> str:
        """创建交接

        Args:
            from_agent: 交出方 Agent ID
            to_agent: 接收方 Agent ID
            handover_data: 交接数据

        Returns:
            交接消息 ID
        """
        content = {
            "action": "handover",
            "handover": handover_data
        }

        return self.send(
            from_agent=from_agent,
            to_agent=to_agent,
            content=content,
            msg_type=MessageType.HANDOVER,
            priority=1  # 交接消息高优先级
        )
