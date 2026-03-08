"""Brain - Core Agent Brain

Refactored architecture:
- Brain: Main coordinator (this file)
- Handlers: Route handlers (in handlers/ directory)
"""

from typing import Any, Dict
import uuid
import time
import httpx


class BrainState:
    """大脑状态管理器（内联到 brain.py）"""

    _state_bar = None

    @classmethod
    def set_state_bar(cls, state_bar) -> None:
        cls._state_bar = state_bar

    @classmethod
    def clear_state_bar(cls) -> None:
        cls._state_bar = None

    def __init__(self, agent_id: str, max_history_length: int = 100):
        self.agent_id = agent_id
        self.max_history_length = max_history_length
        self.context: Dict[str, Any] = {
            "agent_id": agent_id,
            "session_id": str(uuid.uuid4()),
            "history": []
        }

    def add_to_history(self, role: str, content: Any) -> None:
        self.context["history"].append({"role": role, "content": content})

    def trim_history(self) -> None:
        if len(self.context["history"]) > self.max_history_length:
            self.context["history"] = self.context["history"][:2] + self.context["history"][-self.max_history_length:]

    def get_history(self) -> list:
        return self.context["history"]

    def get_session_id(self) -> str:
        return self.context["session_id"]


from mul_agent.brain.router import Router
from mul_agent.brain.llm import LLMClient
from mul_agent.brain.context_builder import ContextBuilder
from mul_agent.brain.conversation import ConversationManager
from mul_agent.brain.compressor import ContextCompressor
from mul_agent.brain.memory_decision import MemoryDecisionSystem
from mul_agent.memory.memory import Memory
from mul_agent.network.agent_network import AgentNetwork
from mul_agent.repositories import AgentRepository, TeamRepository

# Skill/Hook/Command 系统
from mul_agent.skills.manager import SkillManager
from mul_agent.hooks.manager import HookManager
from mul_agent.commands.manager import CommandManager
from mul_agent.hooks.base import HookEvent


class Brain:
    """核心大脑 - 自主决策中心

    架构说明:
    - 使用组合模式委托职责到专门模块
    - Brain 作为协调器，不直接实现复杂逻辑
    """

    def __init__(self, agent_id: str, config_manager):
        self.agent_id = agent_id
        self.config_manager = config_manager

        # Initialize repositories
        self.agent_repo = AgentRepository(config_manager)
        self.team_repo = TeamRepository(config_manager)

        # Load configurations using repository
        self.soul = self.agent_repo.find_by_type(agent_id, "soul")
        self.user = self.agent_repo.find_by_type(agent_id, "user")
        self.skill = self.agent_repo.find_by_type(agent_id, "skill")
        self.memory_config = self.agent_repo.find_by_type(agent_id, "memory")

        # Initialize core components
        self.router = Router(config_manager, agent_id)
        self.llm = LLMClient(
            self.user.get("llm", {}),
            config_manager=config_manager,
            agent_id=agent_id
        )

        # Use LLM for decision making - MUST be before memory_decision and compressor
        self.use_llm = self.llm.is_available()

        self.memory = Memory(agent_id=agent_id, config=self.memory_config)

        # Initialize autonomous memory decision system
        self.memory_decision = MemoryDecisionSystem(
            llm_client=self.llm if self.use_llm else None,
            memory=self.memory,
            agent_id=agent_id
        )

        # Initialize Skill/Hook/Command managers
        self.skill_manager = SkillManager(config_manager, agent_id)
        self.hook_manager = HookManager(config_manager, agent_id)
        self.command_manager = CommandManager(config_manager, agent_id)

        # Initialize context components
        self.context_builder = ContextBuilder(
            config_manager,
            memory=self.memory,
            memory_decision=self.memory_decision
        )
        self.conversation = ConversationManager(memory=self.memory)
        self.compressor = ContextCompressor(
            llm_client=self.llm if self.use_llm else None,
            max_tokens=8000
        )

        # Initialize state management
        self.state = BrainState(agent_id=agent_id)
        self.context = self.state.context  # Backward compatibility

        # Initialize Agent network
        self.network = AgentNetwork()
        self._register_to_network()

        # State tracking for UI
        self._current_route = None
        self._start_time = None

    def _update_state(self, status: str, action: str = None, details: dict = None):
        """Update agent state to API endpoint"""
        try:
            import asyncio
            import httpx

            elapsed_ms = int((time.time() - self._start_time) * 1000) if self._start_time else 0

            state_data = {
                "status": status,
                "current_action": action,
                "route": self._current_route,
                "elapsed_ms": elapsed_ms,
                "details": details
            }

            # Fire and forget - don't block execution
            asyncio.create_task(self._send_state_update(state_data))
        except Exception:
            pass  # Don't let state update fail the main operation

    async def _send_state_update(self, state_data: dict):
        """Send state update to API endpoint asynchronously"""
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                await client.post(
                    f"http://localhost:8080/api/v1/agent/state/{self.agent_id}",
                    json=state_data
                )
        except Exception:
            pass  # Ignore state update errors

    def _register_to_network(self) -> None:
        """注册自身到 Agent 网络"""
        capabilities = self._extract_capabilities()
        self.network.register(
            agent_id=self.agent_id,
            metadata={
                "role": self.user.get("role", {}).get("title", ""),
                "description": self.soul.get("description", ""),
                "capabilities": capabilities
            }
        )

    def _extract_capabilities(self) -> list:
        """从配置中提取能力列表"""
        capabilities = []
        role_title = self.user.get("role", {}).get("title", "").lower()

        capability_map = {
            "code": ["coding", "development"],
            "developer": ["coding", "development"],
            "security": ["security", "review"],
            "auditor": ["security", "review"],
            "test": ["testing", "validation"],
            "qa": ["testing", "validation"],
            "writer": ["writing", "documentation"],
            "doc": ["writing", "documentation"],
            "research": ["research", "analysis"],
            "coordinator": ["planning", "coordination"],
            "brain": ["planning", "coordination"],
        }

        for keyword, caps in capability_map.items():
            if keyword in role_title:
                capabilities.extend(caps)

        return capabilities

    def think(self, user_input: str) -> Dict[str, Any]:
        """思考并决定下一步行动"""
        self._start_time = time.time()

        # 触发 SessionStart 钩子（如果是第一次调用）
        if not hasattr(self, '_session_started'):
            self.hook_manager.trigger_session_start()
            self._session_started = True

        # Update state: received input
        self._update_state("received", "处理用户输入")
        self._current_route = "routing"

        # 触发 PreMessage 钩子
        pre_message_data = self.hook_manager.trigger_hooks(
            HookEvent.PRE_MESSAGE,
            {"user_input": user_input}
        )
        user_input = pre_message_data.get("user_input", user_input)

        # 检查是否是命令（以 / 或！开头）
        if user_input.startswith(("/", "!", ".")):
            command_result = self.command_manager.execute_from_input(user_input)
            return {
                "route": "command",
                "command": command_result.status.value,
                "data": command_result.to_dict()
            }

        # Add to history
        self.state.add_to_history("user", user_input)

        # Save conversation
        self.conversation.save_message(
            agent_id=self.agent_id,
            session_id=self.state.get_session_id(),
            role="user",
            content=user_input
        )

        # Check if context compression is needed
        compression_context = {
            "user_input": user_input,
            "history_length": len(self.state.get_history())
        }
        if self.should_compress_context(compression_context):
            self._compress_history()

        # Build context
        context = self.context_builder.build_context(
            agent_id=self.agent_id,
            user_input=user_input,
            options={
                "include_text_content": True,
                "include_memory": True,
                "memory_limit": 5,
                "include_team": False,
                "include_history": True,
                "history": self.state.get_history()
            }
        )

        # 先使用规则路由（更可靠、更快速）
        action = self._decide_action(user_input)
        self._current_route = action.get("route")

        # Update state: deciding
        self._update_state("deciding", f"路由：{action.get('route')}", {"route": action.get("route")})

        # 如果路由是 uncertain，让 LLM 分析并决定路由
        if action.get("route") == "uncertain":
            self._update_state("thinking", "LLM 分析并决定路由...")
            if self.use_llm:
                llm_result = self.llm.think(user_input, context)
                # 使用 LLM 选择的路由和参数
                # 支持两种格式：
                # 1. {"route": "bash", "params": {...}} - 标准格式
                # 2. {"route": "batch", "commands": [...]} - batch 格式（commands 在根级别）
                action = {
                    "route": llm_result.get("route", "response"),
                    "params": llm_result.get("params", {})
                }
                # 如果是 batch 路由，需要保留 commands
                if action["route"] == "batch" and "commands" in llm_result:
                    action["params"]["commands"] = llm_result["commands"]
            else:
                # Fallback 到简化响应
                action = self._decide_action_fallback(user_input)

        # Execute action
        self._update_state("executing", f"执行：{action.get('route')}", {"params": action.get("params")})

        # 触发 PreToolUse 钩子
        pre_tool_data = self.hook_manager.trigger_pre_tool_use(
            action.get("route", "response"),
            action.get("params", {})
        )
        if pre_tool_data.get("blocked"):
            # 被钩子阻止
            return {
                "route": "response",
                "params": {"message": pre_tool_data.get("error", "Action blocked")},
                "blocked": True
            }

        result = self.router.dispatch(
            action.get("route", "response"),
            pre_tool_data.get("params", action.get("params", {}))
        )

        # 记录路由执行情况到 Token Usage Center
        self._record_route_execution(
            route=action.get("route", "response"),
            params=action.get("params", {}),
            result=result,
            user_input=user_input
        )

        # 如果是 batch 路由，执行完成后让 LLM 汇总结果
        if action.get("route") == "batch" and result.get("status") == "success":
            self._update_state("thinking", "汇总批量执行结果...")
            batch_results = result.get("data", {}).get("batch_results", [])
            # 构建汇总上下文
            summary_context = "以下是执行的结果：\n\n"
            for i, r in enumerate(batch_results, 1):
                cmd_route = r.get("route")
                cmd_result = r.get("result", {})
                if cmd_route == "bash":
                    stdout = cmd_result.get("data", {}).get("stdout", "")
                    summary_context += f"命令 {i} ({cmd_route}): {stdout[:500]}\n\n"
                else:
                    summary_context += f"命令 {i} ({cmd_route}): {str(cmd_result.get('data', cmd_result))[:500]}\n\n"

            # 让 LLM 汇总结果生成报告
            if self.use_llm:
                summary_prompt = f"""用户请求：{user_input}

{summary_context}

请根据以上执行结果，为用户生成一份完整的报告或回答。"""
                llm_summary = self.llm.think(summary_prompt, context)
                # 返回 LLM 汇总的结果
                result = {
                    "status": "success",
                    "route": "response",
                    "data": {
                        "message": llm_summary.get("params", {}).get("message", llm_summary.get("content", ""))
                    }
                }

        # 触发 PostToolUse 钩子
        post_tool_data = self.hook_manager.trigger_post_tool_use(
            action.get("route", "response"),
            action.get("params", {}),
            result
        )
        if post_tool_data.get("result"):
            result = post_tool_data["result"]

        # Save to memory - using autonomous decision system
        memory_decision = self.memory_decision.should_remember(
            user_input=user_input,
            result=result,
            context={"scope": "conversation", "task_type": self._current_route}
        )

        if memory_decision.get("should_remember"):
            self.memory.write(
                memory_type=memory_decision.get("memory_type", "short_term"),
                content=memory_decision.get("content_to_save", {"input": user_input, "result": result})
            )

        # Add to history
        self.state.add_to_history("assistant", result)

        # Save conversation
        self.conversation.save_message(
            agent_id=self.agent_id,
            session_id=self.state.get_session_id(),
            role="assistant",
            content=result
        )

        # Trim history
        self.state.trim_history()

        # Update state: completed
        self._update_state("completed", "响应完成")
        self._current_route = None

        return result

    def cleanup(self):
        """清理资源，触发 SessionEnd 钩子"""
        if hasattr(self, '_session_started') and self._session_started:
            self.hook_manager.trigger_session_end({
                "session_id": self.state.get_session_id(),
                "history_length": len(self.state.get_history())
            })

    def _record_route_execution(
        self,
        route: str,
        params: Dict[str, Any],
        result: Dict[str, Any],
        user_input: str
    ) -> None:
        """记录路由执行情况到 Token Usage Center

        记录每次路由执行的详细信息，包括：
        - 路由类型（bash, chat, response, batch 等）
        - 执行的参数（命令、目标 Agent 等）
        - 执行结果

        Args:
            route: 路由类型
            params: 路由参数
            result: 执行结果
            user_input: 用户原始输入
        """
        if not self.llm.token_center:
            return

        # 根据路由类型确定 function 和 extra 信息
        function = f"route_{route}"
        extra = {
            "route": route,
            "user_input": user_input[:500] if user_input else "",
        }

        # 根据路由类型添加额外信息
        if route == "bash":
            extra["command"] = params.get("command", "")
            extra["function_detail"] = f"bash:{params.get('command', '')[:100]}"
        elif route == "chat":
            extra["target_agent"] = params.get("agent_id", "")
            extra["chat_message"] = params.get("message", "")[:500]
            extra["function_detail"] = f"chat:{params.get('agent_id', '')}"
        elif route == "batch":
            commands = params.get("commands", [])
            extra["batch_command_count"] = len(commands)
            extra["batch_commands"] = [
                {"route": cmd.get("route"), "params": cmd.get("params", {})}
                for cmd in commands[:10]  # 只记录前 10 个
            ]
            extra["function_detail"] = f"batch:{len(commands)} commands"
        elif route == "response":
            extra["function_detail"] = "response"
        elif route == "memory":
            extra["memory_action"] = params.get("action", "")
            extra["function_detail"] = f"memory:{params.get('action', '')}"
        elif route == "skill":
            extra["skill_id"] = params.get("skill_id", "")
            extra["function_detail"] = f"skill:{params.get('skill_id', '')}"
        elif route == "command":
            extra["command_name"] = params.get("command", "")
            extra["function_detail"] = f"command:{params.get('command', '')}"
        elif route == "heart":
            extra["function_detail"] = "heart:self-reflection"
        elif route == "create_user":
            extra["new_agent_name"] = params.get("name", "")
            extra["function_detail"] = f"create_user:{params.get('name', '')}"
        elif route == "file_edit":
            extra["file_path"] = params.get("path", "")
            extra["function_detail"] = f"file_edit:{params.get('path', '')}"
        else:
            extra["function_detail"] = route

        # 添加结果信息
        if result:
            extra["result_status"] = result.get("status", "unknown")
            if result.get("status") == "success":
                result_data = result.get("data", {})
                if isinstance(result_data, dict):
                    # 提取简要结果
                    if "message" in result_data:
                        extra["result_preview"] = str(result_data["message"])[:500]
                    elif "output" in result_data:
                        extra["result_preview"] = str(result_data["output"])[:500]

        # 记录 Token 使用（使用固定的 1 token 作为占位符，因为这不是 LLM 调用）
        # 实际目的是记录路由执行情况
        self.llm.token_center.record_usage(
            agent_id=self.agent_id,
            model="route_execution",
            function=function,
            input_tokens=0,
            output_tokens=1,  # 用 1 token 占位，表示一次路由执行
            extra=extra
        )

    def should_compress_context(self, context: Dict[str, Any]) -> bool:
        """判断是否需要压缩上下文"""
        return self.compressor.should_compress(
            self.state.get_history(),
            context
        )

    def _compress_history(self):
        """压缩对话历史"""
        summary = self.compressor.create_llm_summary(
            self.state.get_history()[:-self.compressor.recent_count]
        )
        compressed = self.compressor.compress(
            self.state.get_history(),
            summary=summary
        )
        self.conversation.compress_old_messages(
            agent_id=self.agent_id,
            session_id=self.state.get_session_id(),
            summary=summary
        )
        self.state.context["history"] = compressed

    def get_context_analysis(self) -> Dict[str, Any]:
        """获取上下文分析"""
        return self.compressor.analyze_context_complexity(
            self.state.get_history(),
            ""
        )

    def _load_response_prompt(self, prompt_name: str, default: str) -> str:
        """从配置加载响应 prompt

        加载优先级：
        1. 先从 wang/agent-team/{agent_id}/prompt.md 加载（Agent 自定义）
        2. 再从 wang/agent-team/.templates/prompt.md.template 加载（标准模板）
        3. 最后返回默认值
        """
        # 1. 尝试从 Agent 自定义的 prompt.md 加载
        loaded = self.config_manager.load_prompt(self.agent_id, prompt_name)
        if loaded:
            return loaded

        # 2. 从标准模板加载（config_manager.load_prompt 已经处理）
        # 如果 config_manager.load_prompt 返回 None，直接返回默认值
        return default

    def _decide_action(self, user_input: str) -> Dict[str, Any]:
        """基于规则的意图识别 - 优先使用规则路由，更可靠快速

        意图识别优先级:
        1. 空输入 -> 直接响应
        2. 命令模式（/开头）-> 已经在 think 方法中处理
        3. bash 命令模式 -> 执行命令
        4. 问候语 -> LLM 生成友好响应
        5. 帮助请求 -> 帮助菜单
        6. 创建 Agent -> 创建流程
        7. 记忆相关 -> 记忆管理
        8. 自省/进化 -> 自省流程
        9. Skill 执行 -> 执行技能
        10. 对话相关（与其他 Agent 对话）-> chat
        11. 其他 -> LLM 生成响应内容
        """
        import re

        input_lower = user_input.lower() if user_input else ""
        input_stripped = user_input.strip() if user_input else ""

        # 1. 空输入
        if not input_lower:
            response = self._load_response_prompt("empty_input_style", "我在听。")
            return {"route": "response", "params": {"message": response}}

        # 2. Bash 命令模式 - 检测命令前缀或特殊字符
        # 只有明确的命令格式才匹配，避免误判
        bash_explicit_patterns = [
            r'^\$ ',      # $ 开头
            r'^\$',       # $ 开头无空格
            r'^bash ',    # bash 开头
            r'^sh ',      # sh 开头
            r'^sudo ',    # sudo 开头
        ]
        # 英文命令关键词（后面跟具体命令）
        bash_cmd_patterns = ["ls ", "cd ", "pwd", "cat ", "grep ", "find ", "echo ", "rm ", "cp ", "mv ", "mkdir ", "head ", "tail ", "wc "]

        is_bash = False
        command = input_stripped

        # 检查明确的前缀模式
        for pattern in bash_explicit_patterns:
            if re.search(pattern, input_stripped, re.IGNORECASE):
                is_bash = True
                break

        # 检查是否以常见命令开头（包含命令后跟空格或参数）
        if not is_bash:
            for cmd in bash_cmd_patterns:
                if input_lower.startswith(cmd):
                    is_bash = True
                    break

        # 检查纯命令格式（简短的英数组合，可能是命令）
        if not is_bash:
            # 纯命令格式：字母 + 空格 + 参数，不超过 5 个词
            if re.match(r'^[a-z]+\s+.*$', input_stripped) and len(input_stripped.split()) <= 5:
                # 第一个词是常见命令
                first_word = input_stripped.split()[0].lower()
                common_commands = ["ls", "cd", "pwd", "cat", "grep", "find", "head", "tail", "wc", "echo", "mkdir", "rm", "cp", "mv"]
                if first_word in common_commands:
                    is_bash = True

        if is_bash:
            # 提取命令
            if command.startswith("$"):
                command = command[1:].strip()
            return {"route": "bash", "params": {"command": command}}

        # 3. 问候语 - 使用 LLM 生成友好响应
        greeting_patterns = ["你好", "hello", "hi ", "早上好", "下午好", "晚上好", "再见", "bye"]
        if any(kw in input_lower for kw in greeting_patterns):
            # 返回 uncertain，让 LLM 生成内容
            return {"route": "uncertain", "params": {"input": user_input}}

        # 4. 帮助请求
        if any(kw in input_lower for kw in ["help", "?", "帮助", "怎么用", "如何使用", "what can you do"]):
            response = self._load_response_prompt("help_menu_style", "可用命令：create, bash, memory, heart, chat")
            return {"route": "response", "params": {"message": response}}

        # 5. 创建 Agent - 需要更精确的匹配，避免误判
        create_keywords = ["create", "new ", "add ", "创建", "新建"]
        # 检查是否包含创建关键词，并且后面跟 agent/team/助手等词
        is_create = any(kw in input_lower for kw in create_keywords)
        has_target = any(t in input_lower for t in ["agent", "team", "助手", "bot", "robot"])
        if is_create and has_target:
            return {"route": "create_user", "params": {"name": user_input}}
        # 检查是否是创建团队
        if any(t in input_lower for t in ["team", "团队", "group", "组"]) and is_create:
            return {"route": "create_team", "params": {"name": user_input}}

        # 6. 记忆相关
        if any(kw in input_lower for kw in ["memory", "remember", "记住", "记忆", "forget", "忘记", "recall"]):
            return {"route": "memory", "params": {"action": "list", "memory_type": "long_term"}}

        # 7. 项目探索/分析报告（复杂任务，交给 LLM 决定使用 skill 还是 batch）
        explore_keywords = ["探索项目", "分析项目", "explore", "analyze project", "项目结构", "扫描项目", "scan project", "list files", "查看项目", "写报告", "project report", "analysis report"]
        if any(kw in input_lower for kw in explore_keywords):
            # 不直接路由到 skill，而是让 LLM 决定使用 skill 还是 batch
            return {"route": "uncertain", "params": {"input": user_input}}

        # 8. 自省/进化
        if any(kw in input_lower for kw in ["heart", "reflect", "evolve", "自省", "反思", "进化", "改进", "evolution"]):
            return {"route": "heart", "params": {}}

        # 9. Skill 执行（如："execute skill bash_executor command=ls"）
        skill_patterns = ["execute skill", "run skill", "skill execute", "使用 skill", "调用 skill"]
        for pattern in skill_patterns:
            if pattern in input_lower:
                # 解析 skill_id 和参数
                parts = user_input.split()
                skill_id = None
                params = {}

                for i, part in enumerate(parts):
                    if part == "skill" and i + 1 < len(parts):
                        skill_id = parts[i + 1]
                    if "=" in part:
                        key, value = part.split("=", 1)
                        params[key] = value

                if skill_id:
                    return {"route": "skill", "params": {"skill_id": skill_id, **params}}

        # 10. 对话相关（与其他 Agent 对话）
        chat_patterns = ["和.*对话", "跟.*说话", "find agent", "tell agent", "send message"]
        for pattern in chat_patterns:
            if re.search(pattern, input_lower):
                return {"route": "chat", "params": {"message": user_input}}

        # 11. 其他 - 让 LLM 生成响应内容
        return {"route": "uncertain", "params": {"input": user_input}}

    def _decide_action_fallback(self, user_input: str) -> Dict[str, Any]:
        """Fallback 决策逻辑 - 当 LLM 不可用时的简化响应"""
        input_lower = user_input.lower() if user_input else ""

        # 问候语
        if any(kw in input_lower for kw in ["你好", "hello", "hi ", "早上好", "下午好"]):
            return {"route": "response", "params": {"message": "你好！有什么我可以帮你的吗？"}}

        # 默认响应
        role_title = self.user.get('role', {}).get('title', 'Agent')
        return {"route": "response", "params": {"message": f"我是{role_title}，请告诉我您的需求。"}}

    # ==================== Delegated Methods ====================
    # These methods delegate to specialized modules

    # Skill methods
    def execute_skill(self, skill_id: str, **kwargs) -> Any:
        """执行技能"""
        return self.skill_manager.execute_skill(skill_id, **kwargs)

    def list_skills(self) -> list:
        """列出所有技能"""
        return self.skill_manager.list_skills()

    # Hook methods
    def register_hook(self, hook_class) -> str:
        """注册钩子"""
        return self.hook_manager.register_hook(hook_class)

    def list_hooks(self) -> list:
        """列出所有钩子"""
        return self.hook_manager.list_hooks()

    # Command methods
    def execute_command(self, command_name: str, args_str: str = "") -> dict:
        """执行命令"""
        result = self.command_manager.execute(command_name, args_str)
        return result.to_dict()

    def list_commands(self) -> list:
        """列出所有命令"""
        return self.command_manager.list_commands()

    def evolve(self, focus: str = "all", require_confirmation: bool = False) -> Dict[str, Any]:
        """自我进化"""
        return self._evolve(focus, require_confirmation)

    def apply_evolution(self, changes: list) -> Dict[str, Any]:
        """应用进化变更"""
        return self._apply_evolution(changes)

    def create_agent(self, config: Dict) -> Dict[str, Any]:
        """创建新 Agent"""
        return self._create_agent(config)

    # Agent Network Collaboration methods
    def delegate_task(self, to_agent: str, task: Dict[str, Any], callback_msg_id: str = None) -> Dict[str, Any]:
        """委派任务"""
        msg_id = self.network.delegate_task(from_agent=self.agent_id, to_agent=to_agent, task=task, callback_msg_id=callback_msg_id)
        self.memory.write(memory_type="short_term", content={"action": "delegate_task", "to_agent": to_agent, "task": task, "message_id": msg_id})
        return {"status": "success", "message_id": msg_id, "delegated_to": to_agent}

    def send_message(self, to_agent: str, content: Dict[str, Any], msg_type: str = "task", priority: int = 5, expect_response: bool = False) -> Dict[str, Any]:
        """发送消息"""
        from mul_agent.network.agent_network import MessageType
        msg_type_map = {"task": MessageType.TASK, "response": MessageType.RESPONSE, "broadcast": MessageType.BROADCAST, "handover": MessageType.HANDOVER}
        msg_id = self.network.send(from_agent=self.agent_id, to_agent=to_agent, content=content, msg_type=msg_type_map.get(msg_type, MessageType.TASK), priority=priority, expect_response=expect_response)
        return {"status": "success", "message_id": msg_id, "sent_to": to_agent}

    def check_messages(self, limit: int = 10, msg_type: str = None) -> Dict[str, Any]:
        """检查消息"""
        from mul_agent.network.agent_network import MessageType
        msg_type_map = {"task": MessageType.TASK, "response": MessageType.RESPONSE, "broadcast": MessageType.BROADCAST, "handover": MessageType.HANDOVER}
        messages = self.network.receive(agent_id=self.agent_id, limit=limit, msg_type=msg_type_map.get(msg_type) if msg_type else None)
        return {"status": "success", "message_count": len(messages), "messages": [m.to_dict() for m in messages]}

    def process_message(self, message_id: str, success: bool = True, error: str = None) -> Dict[str, Any]:
        """处理消息"""
        result = self.network.mark_message_processed(message_id=message_id, agent_id=self.agent_id, success=success, error=error)
        return {"status": "success" if result else "failed", "message_id": message_id, "processed": result}

    def broadcast_message(self, content: Dict[str, Any], exclude_agents: list = None) -> Dict[str, Any]:
        """广播消息"""
        msg_ids = self.network.broadcast(from_agent=self.agent_id, content=content, exclude_agents=exclude_agents)
        return {"status": "success", "broadcast_count": len(msg_ids), "message_ids": msg_ids}

    def get_network_stats(self) -> Dict[str, Any]:
        """获取网络统计"""
        return self.network.get_network_stats()

    def find_specialist(self, task_type: str) -> Dict[str, Any]:
        """查找专业 Agent"""
        specialist_id = self.network.find_specialist(task_type)
        if specialist_id:
            return {"status": "success", "found": True, "agent_id": specialist_id, "agent_info": self.network.get_agent(specialist_id)}
        return {"status": "success", "found": False, "message": f"No specialist found for: {task_type}"}

    def list_available_agents(self, only_active: bool = True) -> Dict[str, Any]:
        """列出可用 Agent"""
        agents = self.network.list_agents(status="active" if only_active else None)
        return {"status": "success", "agent_count": len(agents), "agents": agents}

    def create_handover(self, to_agent: str, handover_data: Dict[str, Any]) -> Dict[str, Any]:
        """创建交接"""
        msg_id = self.network.create_handover(from_agent=self.agent_id, to_agent=to_agent, handover_data=handover_data)
        return {"status": "success", "message_id": msg_id, "handed_over_to": to_agent}

    # ==================== Evolution Methods ====================

    def _evolve(self, focus: str = "all", require_confirmation: bool = False) -> Dict[str, Any]:
        """自我进化 - 简化版"""
        analysis = {
            "current_state": {
                "soul_version": self.soul.get("version"),
                "user_config": self.user.get("role", {}).get("title"),
                "skills_count": len(self.skill.get("skills", []))
            },
            "issues_found": [],
            "can_evolve": self.soul.get("evolution_rules", {}).get("can_modify_self", False)
        }
        return {"status": "success", "analysis": analysis, "evolutions_applied": [], "suggestions": []}

    def _apply_evolution(self, changes: list) -> Dict[str, Any]:
        """应用进化变更"""
        return {"status": "success", "applied_count": len(changes), "changes": changes}

    def _create_agent(self, config: Dict) -> Dict[str, Any]:
        """创建新 Agent"""
        new_agent_id = config.get("agent_id", f"agent_{hash(config.get('name', ''))}")
        return {"status": "success", "agent_id": new_agent_id, "message": f"Agent {new_agent_id} created"}
