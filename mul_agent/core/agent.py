"""Core Agent - Agent 核心类"""

from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


@dataclass
class AgentConfig:
    """Agent 配置"""
    agent_id: str
    name: str
    role: str
    title: str
    tools: List[str] = field(default_factory=list)
    llm_model: Optional[str] = None
    llm_temperature: float = 0.7
    max_history_length: int = 100
    config_path: Optional[Path] = None


class Agent:
    """
    Agent 核心类

    每个 Agent 都有一个：
    - 身份配置（agent_id, name, role）
    - 工具集合
    - 记忆系统
    - Brain（决策引擎）

    使用示例:
    ```python
    agent = Agent(
        agent_id="alice",
        name="Alice",
        role="代码工程师"
    )
    response = await agent.run("帮我实现一个加法函数")
    ```
    """

    def __init__(
        self,
        agent_id: str,
        name: Optional[str] = None,
        role: Optional[str] = None,
        config: Optional[AgentConfig] = None,
        workspace_dir: Optional[Path] = None,
    ):
        """
        初始化 Agent

        Args:
            agent_id: Agent 唯一标识
            name: Agent 名称
            role: Agent 角色描述
            config: Agent 配置（可选，优先使用）
            workspace_dir: 工作区目录
        """
        # 基本属性
        self.agent_id = agent_id
        self.name = name or agent_id
        self.role = role or "通用助手"
        self.workspace_dir = workspace_dir or Path.cwd()

        # 配置
        self.config = config or AgentConfig(
            agent_id=agent_id,
            name=self.name,
            role=self.role,
        )

        # 状态
        self.session_id: Optional[str] = None
        self.context: Dict[str, Any] = {}
        self.history: List[Dict[str, Any]] = []

        # 组件（懒加载）
        self._brain = None
        self._memory = None
        self._tools = None

        logger.info(f"Agent initialized: {self.agent_id} ({self.name})")

    async def run(self, message: str, **kwargs) -> Dict[str, Any]:
        """
        运行 Agent 处理消息

        Args:
            message: 用户消息
            **kwargs: 额外参数

        Returns:
            响应结果
        """
        # 初始化 Brain（如果还未初始化）
        if self._brain is None:
            self._init_brain()

        # 添加到历史
        self.history.append({"role": "user", "content": message})
        self._trim_history()

        # 使用 Brain 处理
        response = await self._brain.process(
            message=message,
            context=self.context,
            history=self.history,
            **kwargs
        )

        # 记录响应
        if response:
            self.history.append({"role": "assistant", "content": response})

        return response

    def _init_brain(self) -> None:
        """初始化 Brain"""
        from mul_agent.core.brain import Brain

        self._brain = Brain(
            agent_id=self.agent_id,
            config=self.config,
            workspace_dir=self.workspace_dir,
        )

    def _trim_history(self, max_length: Optional[int] = None) -> None:
        """修剪历史记录"""
        max_len = max_length or self.config.max_history_length
        if len(self.history) > max_len:
            # 保留最初 2 条和最近 max_len 条
            self.history = self.history[:2] + self.history[-max_len:]

    @property
    def brain(self):
        """获取 Brain 实例"""
        return self._brain

    @property
    def memory(self):
        """获取 Memory 实例"""
        if self._memory is None:
            from mul_agent.memory.base import MemoryManager
            self._memory = MemoryManager(agent_id=self.agent_id)
        return self._memory

    @property
    def tools(self):
        """获取工具管理器"""
        if self._tools is None:
            # 从插件运行时获取
            from mul_agent.plugins.discovery import PluginRuntime
            runtime = PluginRuntime(workspace_dir=self.workspace_dir)
            runtime.load_all()
            self._tools = runtime.tool_registry
        return self._tools

    def __repr__(self) -> str:
        return f"Agent(id={self.agent_id}, name={self.name}, role={self.role})"
