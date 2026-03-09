"""Chain of Thought Engine - 推理链执行引擎

实现多步骤推理、思考过程记录、回溯机制
"""

import uuid
import time
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
import json
from pathlib import Path


class ThoughtStatus(Enum):
    """思考状态"""
    PENDING = "pending"
    THINKING = "thinking"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    BACKTRACKED = "backtracked"


@dataclass
class ThoughtNode:
    """思考节点"""
    id: str
    step: int
    description: str
    status: ThoughtStatus = ThoughtStatus.PENDING
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    parent_id: Optional[str] = None
    children: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None


@dataclass
class ThoughtChain:
    """思考链"""
    id: str
    goal: str
    status: ThoughtStatus = ThoughtStatus.PENDING
    nodes: Dict[str, ThoughtNode] = field(default_factory=dict)
    current_node: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None

    def add_node(self, description: str, parent_id: Optional[str] = None,
                 metadata: Dict[str, Any] = None) -> str:
        """添加思考节点"""
        node_id = str(uuid.uuid4())[:8]
        step = len(self.nodes) + 1

        node = ThoughtNode(
            id=node_id,
            step=step,
            description=description,
            parent_id=parent_id,
            metadata=metadata or {}
        )
        self.nodes[node_id] = node

        # 更新父节点的 children
        if parent_id and parent_id in self.nodes:
            self.nodes[parent_id].children.append(node_id)

        return node_id

    def update_node(self, node_id: str, status: ThoughtStatus,
                    result: Optional[Dict] = None, error: Optional[str] = None):
        """更新节点状态"""
        if node_id not in self.nodes:
            return

        node = self.nodes[node_id]
        node.status = status
        node.result = result
        node.error = error

        if status in [ThoughtStatus.COMPLETED, ThoughtStatus.FAILED]:
            node.completed_at = time.time()

    def get_execution_path(self) -> List[ThoughtNode]:
        """获取当前执行路径"""
        path = []
        current = None

        # 找到第一个节点
        for node_id, node in self.nodes.items():
            if node.parent_id is None:
                current = node_id
                break

        # 沿着 children 走
        while current:
            node = self.nodes[current]
            path.append(node)
            current = node.children[0] if node.children else None

        return path

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "goal": self.goal,
            "status": self.status.value,
            "nodes": {
                nid: {
                    "id": n.id,
                    "step": n.step,
                    "description": n.description,
                    "status": n.status.value,
                    "result": n.result,
                    "error": n.error,
                    "parent_id": n.parent_id,
                    "children": n.children,
                    "metadata": n.metadata,
                    "created_at": n.created_at,
                    "completed_at": n.completed_at
                }
                for nid, n in self.nodes.items()
            },
            "current_node": self.current_node,
            "created_at": self.created_at,
            "completed_at": self.completed_at
        }


class ChainOfThoughtEngine:
    """推理链执行引擎"""

    def __init__(self, executor: Callable = None):
        """初始化推理链引擎

        Args:
            executor: 执行函数，接收 (action, params) 参数，返回执行结果
        """
        self.executor = executor
        self.chains: Dict[str, ThoughtChain] = {}
        self.history: List[str] = []  # 记录 chain id

    def create_chain(self, goal: str, initial_thoughts: List[str] = None) -> str:
        """创建思考链

        Args:
            goal: 目标
            initial_thoughts: 初始思考步骤列表

        Returns:
            chain_id
        """
        chain_id = str(uuid.uuid4())
        chain = ThoughtChain(id=chain_id, goal=goal)

        # 添加初始思考步骤
        if initial_thoughts:
            parent_id = None
            for thought in initial_thoughts:
                parent_id = chain.add_node(thought, parent_id)

        self.chains[chain_id] = chain
        self.history.append(chain_id)

        return chain_id

    def get_chain(self, chain_id: str) -> Optional[ThoughtChain]:
        """获取思考链"""
        return self.chains.get(chain_id)

    def execute_step(self, chain_id: str, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """执行思考链中的单一步骤

        Args:
            chain_id: 思考链 ID
            action: 要执行的动作（路由名）
            params: 动作参数

        Returns:
            执行结果
        """
        chain = self.get_chain(chain_id)
        if not chain:
            return {"status": "error", "message": f"Chain {chain_id} not found"}

        # 创建新的思考节点
        node_id = chain.add_node(
            description=f"执行 {action}",
            parent_id=chain.current_node,
            metadata={"action": action, "params": params}
        )

        chain.current_node = node_id
        chain.update_node(node_id, ThoughtStatus.EXECUTING)

        try:
            # 执行动作
            if self.executor:
                result = self.executor(action, params)
            else:
                result = {"status": "simulated", "message": "No executor configured"}

            # 更新节点状态
            if result.get("status") == "success":
                chain.update_node(node_id, ThoughtStatus.COMPLETED, result=result)
            else:
                chain.update_node(node_id, ThoughtStatus.FAILED, result=result,
                                  error=result.get("message", "Execution failed"))

            return result

        except Exception as e:
            chain.update_node(node_id, ThoughtStatus.FAILED, error=str(e))
            return {"status": "error", "message": str(e)}

    def backtrack(self, chain_id: str, steps: int = 1) -> Optional[str]:
        """回溯到之前的步骤

        Args:
            chain_id: 思考链 ID
            steps: 回溯步数

        Returns:
            回溯到的节点 ID
        """
        chain = self.get_chain(chain_id)
        if not chain:
            return None

        # 找到当前节点
        if not chain.current_node:
            return None

        current = chain.nodes[chain.current_node]

        # 回溯指定步数
        for _ in range(steps):
            if current.parent_id:
                current = chain.nodes[current.parent_id]
            else:
                break

        chain.current_node = current.id
        chain.update_node(current.id, ThoughtStatus.BACKTRACKED)

        return current.id

    def add_reflection(self, chain_id: str, reflection: str) -> str:
        """添加反思节点

        Args:
            chain_id: 思考链 ID
            reflection: 反思内容

        Returns:
            节点 ID
        """
        chain = self.get_chain(chain_id)
        if not chain:
            return None

        node_id = chain.add_node(
            description=f"反思：{reflection}",
            parent_id=chain.current_node,
            metadata={"type": "reflection"}
        )

        return node_id

    def complete_chain(self, chain_id: str, status: ThoughtStatus = ThoughtStatus.COMPLETED):
        """完成思考链"""
        chain = self.get_chain(chain_id)
        if not chain:
            return

        chain.status = status
        chain.completed_at = time.time()

    def get_summary(self, chain_id: str) -> Dict[str, Any]:
        """获取思考链摘要"""
        chain = self.get_chain(chain_id)
        if not chain:
            return {"status": "error", "message": "Chain not found"}

        path = chain.get_execution_path()

        return {
            "id": chain.id,
            "goal": chain.goal,
            "status": chain.status.value,
            "total_steps": len(chain.nodes),
            "execution_path": [
                {"step": n.step, "description": n.description, "status": n.status.value}
                for n in path
            ],
            "duration": (chain.completed_at or time.time()) - chain.created_at
        }

    def export_trace(self, chain_id: str) -> str:
        """导出执行轨迹为 JSON"""
        chain = self.get_chain(chain_id)
        if not chain:
            return ""

        return json.dumps(chain.to_dict(), indent=2, ensure_ascii=False)

    def visualize_ascii(self, chain_id: str) -> str:
        """ASCII 可视化思考链"""
        chain = self.get_chain(chain_id)
        if not chain:
            return "Chain not found"

        lines = []
        lines.append(f"🎯 目标：{chain.goal}")
        lines.append(f"状态：{chain.status.value}")
        lines.append("")

        path = chain.get_execution_path()

        for i, node in enumerate(path):
            icon = {
                ThoughtStatus.PENDING: "⏳",
                ThoughtStatus.THINKING: "💭",
                ThoughtStatus.EXECUTING: "⚙️",
                ThoughtStatus.COMPLETED: "✅",
                ThoughtStatus.FAILED: "❌",
                ThoughtStatus.BACKTRACKED: "🔙",
            }.get(node.status, "•")

            lines.append(f"{icon} 步骤 {node.step}: {node.description}")

            if node.result:
                if isinstance(node.result, dict):
                    lines.append(f"     结果：{json.dumps(node.result, ensure_ascii=False)[:100]}")
                else:
                    lines.append(f"     结果：{str(node.result)[:100]}")

            if node.error:
                lines.append(f"     错误：{node.error}")

        return "\n".join(lines)


# 全局实例
cot_engine = ChainOfThoughtEngine()
