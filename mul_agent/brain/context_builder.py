"""Context Builder - 构建 Agent 上下文"""

from typing import Any, Dict, List, Optional
from pathlib import Path

from mul_agent.brain.compressor import ContextCompressor


class ContextBuilder:
    """上下文构建器 - 智能聚合多个文本来源

    这个类负责构建 Agent 的完整上下文，包括：
    - 配置文件（soul/user/skill/memory）
    - 记忆系统（短期/长期记忆）
    - 团队成员信息
    - 历史对话

    使用方式：
        builder = ContextBuilder(config_manager, memory)
        context = builder.build_context(agent_id, user_input)
    """

    def __init__(self, config_manager, memory=None):
        """初始化上下文构建器

        Args:
            config_manager: ConfigManager 实例
            memory: Memory 实例（可选）
        """
        self.config_manager = config_manager
        self.memory = memory

    def build_context(
        self,
        agent_id: str,
        user_input: str,
        options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """构建完整的上下文

        Args:
            agent_id: Agent ID
            user_input: 用户输入
            options: 构建选项，可选字段：
                - include_text_content: bool, 是否包含完整文本内容 (default: True)
                - include_memory: bool, 是否包含记忆 (default: True)
                - memory_limit: int, 记忆数量限制 (default: 5)
                - include_team: bool, 是否包含团队信息 (default: False)
                - include_history: bool, 是否包含对话历史 (default: False)

        Returns:
            Dict: 完整的上下文字典
        """
        options = options or {}
        include_text = options.get("include_text_content", True)
        include_memory = options.get("include_memory", True)
        memory_limit = options.get("memory_limit", 5)
        include_team = options.get("include_team", False)
        include_history = options.get("include_history", False)

        # 1. 加载结构化配置
        configs = self.config_manager.load_all(agent_id)

        # 2. 加载完整文本内容（如果需要）
        text_contents = {}
        if include_text:
            text_contents = self.config_manager.load_all_text_contents(agent_id)

        # 3. 获取记忆（如果需要）
        recent_memories = []
        if include_memory and self.memory:
            recent_memories = self.memory.get_recent(limit=memory_limit)

        # 4. 获取团队信息（如果需要）
        team_info = {}
        if include_team:
            team_info = self._get_team_info()

        # 构建上下文
        context = {
            "agent_id": agent_id,
            "configs": configs,
            "text_contents": text_contents,  # 完整的 Markdown 文本
            "recent_memory": recent_memories,
            "team_info": team_info,
            "user_input": user_input
        }

        # 5. 添加可选的历史信息
        if include_history:
            context["history"] = options.get("history", [])

        return context

    def build_system_prompt(
        self,
        agent_id: str,
        format: str = "markdown"
    ) -> str:
        """构建系统提示词 - 从配置文件加载

        根据配置文件生成系统提示词，用于 LLM 调用。

        Args:
            agent_id: Agent ID
            format: 输出格式，可选 "markdown" 或 "text"

        Returns:
            str: 格式化的系统提示词
        """
        # 获取配置
        soul = self.config_manager.load(agent_id, "soul")
        user = self.config_manager.load(agent_id, "user")
        text_contents = self.config_manager.load_all_text_contents(agent_id)

        # 提取关键信息
        personality = soul.get("core_traits", {}).get("personality", "")
        role_title = user.get("role", {}).get("title", "Assistant")
        responsibilities = user.get("role", {}).get("responsibilities", [])

        # 尝试从配置文件加载提示词模板
        prompt_template = self.config_manager.load_prompt(agent_id, "context_prompt")

        if format == "markdown":
            # 如果配置文件中没有提示词，使用默认 Markdown 格式
            if not prompt_template or prompt_template.startswith("Current Task:"):
                # Markdown 格式的系统提示
                prompt_parts = [
                    f"# {role_title}",
                    "",
                    "## 角色定义",
                    f"- **类型**: {user.get('role', {}).get('type', 'worker')}",
                    f"- **职责**: {', '.join(responsibilities)}" if responsibilities else "",
                    "",
                    "## 核心特质",
                    f"- **人格**: {personality}",
                    f"- **价值观**: {', '.join(soul.get('core_traits', {}).get('values', []))}",
                    "",
                ]

                # 添加完整的文本描述（如果有的话）
                if text_contents.get("soul"):
                    prompt_parts.extend([
                        "## 完整描述",
                        text_contents["soul"],
                        ""
                    ])

                if text_contents.get("user"):
                    prompt_parts.extend([
                        "## 用户配置详情",
                        text_contents["user"],
                        ""
                    ])

                return "\n".join([p for p in prompt_parts if p])
            else:
                # 使用配置文件中的模板
                return prompt_template.format(
                    user_input="",
                    memory_context="",
                    soul_personality=personality,
                    role_title=role_title,
                    user_text=text_contents.get("user", ""),
                    soul_text=text_contents.get("soul", "")
                )

        else:
            # 纯文本格式 - 从配置文件加载
            default_text = f"{role_title}. Personality: {personality}. Responsibilities: {', '.join(responsibilities)}"
            return prompt_template if prompt_template and not prompt_template.startswith("Current Task:") else default_text

    def _get_team_info(self) -> Dict[str, Any]:
        """获取团队信息"""
        agents = self.config_manager.list_agents()
        team_info = {
            "total_count": len(agents),
            "agents": []
        }

        for agent_id in agents:
            try:
                user_config = self.config_manager.load(agent_id, "user")
                team_info["agents"].append({
                    "agent_id": agent_id,
                    "role": user_config.get("role", {}).get("title", "Unknown"),
                    "type": user_config.get("role", {}).get("type", "worker"),
                    "capabilities": user_config.get("capabilities", {})
                })
            except Exception:
                continue

        return team_info

    def get_context_summary(self, context: Dict[str, Any]) -> str:
        """获取上下文的摘要文本

        将上下文转换为适合 LLM 使用的摘要格式。

        Args:
            context: build_context() 返回的上下文字典

        Returns:
            str: 格式化的上下文摘要
        """
        parts = []

        # Agent 信息
        agent_id = context.get("agent_id", "unknown")
        configs = context.get("configs", {})
        user = configs.get("user", {})
        soul = configs.get("soul", {})

        parts.append(f"## 当前 Agent: {agent_id}")
        parts.append(f"- 角色: {user.get('role', {}).get('title', 'Unknown')}")
        parts.append(f"- 人格: {soul.get('core_traits', {}).get('personality', '')}")
        parts.append("")

        # 记忆
        recent_memory = context.get("recent_memory", [])
        if recent_memory:
            parts.append("## 最近记忆")
            for m in recent_memory[-3:]:
                content = m.get("content", {})
                input_text = content.get("input", "")[:100]
                if input_text:
                    parts.append(f"- {input_text}...")
            parts.append("")

        # 文本内容摘要
        text_contents = context.get("text_contents", {})
        if text_contents.get("user"):
            parts.append("## 用户配置")
            # 只取前 500 字符
            user_text = text_contents["user"][:500]
            parts.append(user_text)
            if len(text_contents["user"]) > 500:
                parts.append("...")
            parts.append("")

        return "\n".join(parts)

    def build_compressed_context(
        self,
        agent_id: str,
        user_input: str,
        history: List[Dict],
        llm_client=None,
        options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """构建压缩后的上下文（用于长对话）

        当对话历史过长时，自动压缩早期消息，生成摘要，
        保留最近的消息完整，以减少 token 消耗。

        Args:
            agent_id: Agent ID
            user_input: 用户输入
            history: 对话历史
            llm_client: LLM 客户端（用于生成摘要）
            options: 构建选项

        Returns:
            Dict: 压缩后的上下文字典
        """
        options = options or {}

        # 创建压缩器
        compressor = ContextCompressor(llm_client=llm_client)

        # 检查是否需要压缩
        if compressor.should_compress(history):
            # 压缩历史
            compressed_history = compressor.compress(history)
        else:
            compressed_history = history

        # 构建上下文
        context = self.build_context(
            agent_id=agent_id,
            user_input=user_input,
            options={
                **options,
                "include_history": True,
                "history": compressed_history
            }
        )

        # 标记为压缩上下文
        context["_compressed"] = True
        context["_compression_applied"] = compressor.should_compress(history)

        return context

    def get_compression_prompt(
        self,
        messages: List[Dict],
        target_tokens: Optional[int] = None
    ) -> str:
        """获取压缩用的 Prompt（供 Agent 调用）

        Agent 可以调用此方法获取压缩提示，然后调用 LLM 生成摘要。

        Args:
            messages: 消息列表
            target_tokens: 目标 token 数量

        Returns:
            压缩提示
        """
        compressor = ContextCompressor()
        return compressor.create_compression_prompt(messages, target_tokens)


# 便捷函数
def build_agent_context(
    config_manager,
    agent_id: str,
    user_input: str,
    memory=None,
    **options
) -> Dict[str, Any]:
    """构建 Agent 上下文的便捷函数

    Args:
        config_manager: ConfigManager 实例
        agent_id: Agent ID
        user_input: 用户输入
        memory: Memory 实例（可选）
        **options: build_context() 的其他选项

    Returns:
        Dict: 完整的上下文
    """
    builder = ContextBuilder(config_manager, memory)
    return builder.build_context(agent_id, user_input, options)


def get_agent_system_prompt(
    config_manager,
    agent_id: str,
    format: str = "markdown"
) -> str:
    """获取 Agent 系统提示的便捷函数

    Args:
        config_manager: ConfigManager 实例
        agent_id: Agent ID
        format: 输出格式

    Returns:
        str: 系统提示词
    """
    builder = ContextBuilder(config_manager)
    return builder.build_system_prompt(agent_id, format)
