"""Brain - Agent 决策引擎

Brain 负责：
1. 接收用户输入
2. 路由到合适的处理器
3. 执行工具调用
4. 管理对话历史
5. 调用 Hook

架构：
- Brain: 主要协调器
- Handlers: 路由处理器（bash, file_edit, chat, etc.）
- LLM: LLM 客户端
"""

from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


@dataclass
class BrainConfig:
    """Brain 配置"""
    agent_id: str
    llm_model: Optional[str] = None
    llm_temperature: float = 0.7
    max_history_length: int = 100
    enable_hooks: bool = True
    enable_memory: bool = True


class Brain:
    """
    Agent 决策引擎

    使用示例:
    ```python
    brain = Brain(agent_id="alice")
    response = await brain.process("帮我写一个函数")
    ```
    """

    def __init__(
        self,
        agent_id: str,
        config: Optional[BrainConfig] = None,
        workspace_dir: Optional[Path] = None,
    ):
        """
        初始化 Brain

        Args:
            agent_id: Agent ID
            config: Brain 配置
            workspace_dir: 工作区目录
        """
        self.agent_id = agent_id
        self.workspace_dir = workspace_dir or Path.cwd()

        self.config = config or BrainConfig(agent_id=agent_id)

        # 状态
        self.session_id: Optional[str] = None
        self.context: Dict[str, Any] = {}
        self.history: List[Dict[str, Any]] = []

        # 组件（懒加载）
        self._router = None
        self._llm = None
        self._hooks = None
        self._skills_prompt = None

        logger.info(f"Brain initialized for agent: {self.agent_id}")

    async def process(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        history: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        处理消息

        Args:
            message: 用户消息
            context: 上下文
            history: 历史记录
            **kwargs: 额外参数

        Returns:
            响应结果
        """
        # 更新状态
        if context:
            self.context.update(context)
        if history:
            self.history = history

        # 构建完整上下文
        full_context = self._build_context(message)

        # 执行 Pre Hooks
        if self.config.enable_hooks:
            full_context = await self._run_pre_hooks(full_context)

        # 路由和执行
        result = await self._route_and_execute(full_context)

        # 执行 Post Hooks
        if self.config.enable_hooks:
            result = await self._run_post_hooks(result)

        return result

    def _build_context(self, message: str) -> Dict[str, Any]:
        """构建上下文"""
        # 加载 SKILL.md 提示词
        if self._skills_prompt is None:
            self._skills_prompt = self._load_skills_prompt()

        return {
            "agent_id": self.agent_id,
            "message": message,
            "context": self.context,
            "history": self.history[-10:],  # 最近 10 条
            "skills_prompt": self._skills_prompt,
        }

    def _load_skills_prompt(self) -> str:
        """加载 Skills 提示词"""
        try:
            from mul_agent.brain.skill_loader import build_skills_prompt
            return build_skills_prompt(self.workspace_dir / "agent-team")
        except Exception as e:
            logger.warning(f"Failed to load skills prompt: {e}")
            return ""

    async def _route_and_execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """路由和执行"""
        # 获取 Router
        if self._router is None:
            self._init_router()

        # 路由决策
        route = await self._router.route(context)

        # 执行路由
        result = await self._router.execute(route, context)

        return result

    def _init_router(self) -> None:
        """初始化 Router"""
        # 使用现有的 router 模块
        from mul_agent.brain.router import Router
        from mul_agent.brain.config_manager import ConfigManager

        config_manager = ConfigManager(self.workspace_dir)
        self._router = Router(config_manager, self.agent_id)

    async def _run_pre_hooks(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """执行 Pre Hooks"""
        # TODO: 实现 Hook 系统
        return context

    async def _run_post_hooks(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """执行 Post Hooks"""
        # TODO: 实现 Hook 系统
        return result

    @property
    def router(self):
        """获取 Router 实例"""
        return self._router

    @property
    def llm(self):
        """获取 LLM 实例"""
        if self._llm is None:
            from mul_agent.brain.llm import LLMClient
            self._llm = LLMClient(
                config={"model": self.config.llm_model},
                agent_id=self.agent_id,
            )
        return self._llm

    def __repr__(self) -> str:
        return f"Brain(agent_id={self.agent_id})"
