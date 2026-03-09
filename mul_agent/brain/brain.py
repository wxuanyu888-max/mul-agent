"""Brain - Core Agent Brain

Refactored architecture:
- Brain: Main coordinator (this file)
- Handlers: Route handlers (in handlers/ directory)
"""

from typing import Any, Dict, List, Optional, Optional
import re
import uuid
import time
import json
import httpx
from pathlib import Path

from mul_agent.brain.workspace import get_current_workspace, Workspace
from mul_agent.brain.stream import stream_manager, StreamEventType
from mul_agent.mcp.client import get_mcp_client


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
from mul_agent.brain.autonomous_loop import AutonomousLoop
from mul_agent.brain.subagent import SubagentManager
from mul_agent.memory.memory import Memory
from mul_agent.network.agent_network import AgentNetwork
from mul_agent.repositories import AgentRepository, TeamRepository

# Skill/Hook/Command 系统
from mul_agent.skills.manager import SkillManager
from mul_agent.hooks.manager import HookManager
from mul_agent.commands.manager import CommandManager
from mul_agent.hooks.base import HookEvent

# 会话状态持久化
from mul_agent.brain.session_state import session_state_manager, SessionStateManager

# 核心指挥官模块 - 用于团队任务委派
from mul_agent.brain.commander import get_commander, Commander


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

        # Initialize MCP client
        self.mcp_client = get_mcp_client()

        # Initialize state management (before observability which needs session_id)
        self.state = BrainState(agent_id=agent_id)
        self.context = self.state.context  # Backward compatibility

        # Initialize skill evolution system
        from mul_agent.skills.evolution import get_skill_evolution_system
        self.skill_evolution = get_skill_evolution_system()

        # Initialize observability platform
        from mul_agent.observability.platform import get_observability_platform
        self.observability = get_observability_platform(agent_id, self.state.get_session_id())

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

        # Initialize Agent network
        self.network = AgentNetwork()
        self._register_to_network()

        # Initialize subagent manager
        self.subagent = SubagentManager(self)

        # Initialize workspace awareness
        self.workspace = get_current_workspace()

        # Initialize Commander for team delegation (only for core_brain)
        self.commander: Optional[Commander] = None
        if agent_id == "core_brain" and self.use_llm:
            self.commander = get_commander(self, self.llm)

        # State tracking for UI
        self._current_route = None
        self._start_time = None

    def _update_state(self, status: str, action: str = None, details: dict = None):
        """Update agent state to API endpoint and write to file for streaming"""
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

            # Write state to file for streaming API to read
            try:
                from pathlib import Path
                state_dir = Path("storage/agent_states")
                state_dir.mkdir(parents=True, exist_ok=True)
                state_file = state_dir / f"{self.agent_id}.json"
                import json
                with open(state_file, 'w') as f:
                    json.dump(state_data, f, indent=2)
            except Exception:
                pass  # Don't let file write fail the main operation

            # Emit stream event for real-time updates
            try:
                stream_manager.emit(
                    event=self._status_to_stream_event(status),
                    agent_id=self.agent_id,
                    session_id=self.state.get_session_id(),
                    data=state_data
                )
            except Exception:
                pass  # Don't let stream event fail the main operation

            # Fire and forget - don't block execution
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.create_task(self._send_state_update(state_data))
                else:
                    loop.run_until_complete(self._send_state_update(state_data))
            except Exception:
                pass  # Don't let state update fail the main operation
        except Exception:
            pass  # Don't let state update fail the main operation

    def _status_to_stream_event(self, status: str) -> StreamEventType:
        """Convert status string to StreamEventType"""
        mapping = {
            "received": StreamEventType.INPUT_RECEIVED,
            "planning": StreamEventType.PLANNING,
            "deciding": StreamEventType.THOUGHT,
            "thinking": StreamEventType.THOUGHT,
            "executing": StreamEventType.EXECUTION_START,
            "iteration": StreamEventType.EXECUTION_PROGRESS,
            "completed": StreamEventType.COMPLETE,
            "error": StreamEventType.EXECUTION_ERROR,
            "autonomous_mode": StreamEventType.PLANNING,
            "autonomous_start": StreamEventType.SESSION_START,
        }
        return mapping.get(status, StreamEventType.EXECUTION_PROGRESS)

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
        """思考并决定下一步行动 - 仿照 Claude Code 的持续执行模式

        Claude Code 核心设计：
        1. 直接行动 - 不等待用户确认
        2. 持续执行 - 直到任务完成
        3. 透明执行 - 每一步都告诉用户在做什么
        """
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

        # ==================== Commander 模式：核心大脑委派团队（仅 core_brain） ====================
        # 当用户向 core_brain 提出复杂任务时，自动委派给 alice/bob/wangyue
        if self.agent_id == "core_brain" and self.commander and self._is_team_delegation_task(user_input):
            self._update_state("commander_mode", "分析任务并委派团队...")
            return self.commander.analyze_and_delegate(user_input)

        # 检测是否是复杂任务，如果是则使用自主模式
        if self._is_complex_task(user_input):
            self._update_state("autonomous_mode", "启动自主执行模式")
            return self._run_autonomous_task(user_input)

        # ==================== 计划模式：先输出计划，用户确认后再执行 ====================
        # 检测是否需要先看计划（通过关键词或配置）
        if self._needs_plan(user_input):
            self._update_state("planning", "分析任务并生成计划...")
            plan_result = self._plan_task(user_input, context={})
            # 返回计划让用户确认
            return {
                "status": "plan_ready",
                "route": "plan",
                "data": plan_result
            }

        # ==================== Claude Code 模式：持续执行循环 ====================
        # 核心改进：不只是一步，而是持续执行直到任务完成
        self._update_state("planning", "规划并执行任务")

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

        # 执行循环 - 最多 5 次迭代，避免无限循环
        max_iterations = 5
        iteration = 0
        all_results = []
        task_complete = False

        while not task_complete and iteration < max_iterations:
            iteration += 1
            self._update_state("iteration", f"执行迭代 {iteration}/{max_iterations}")

            # Build context (每轮迭代重新构建，包含上一轮结果)
            context = self.context_builder.build_context(
                agent_id=self.agent_id,
                user_input=user_input,
                options={
                    "include_text_content": True,
                    "include_memory": True,
                    "memory_limit": 5,
                    "include_team": False,
                    "include_history": True,
                    "history": self.state.get_history(),
                    "previous_results": all_results  # 添加上一轮结果
                }
            )

            # ==================== 改进的决策逻辑：LLM 优先 ====================
            # Claude Code 模式：让 LLM 主导决策，而非规则路由
            self._update_state("thinking", "LLM 分析并规划下一步...")

            # 第一轮：先用 LLM 分析意图（而非规则路由）
            if iteration == 1 and self.use_llm:
                action = self._llm_decide_action(user_input, context)
            else:
                # 后续迭代或 LLM 不可用时，使用规则路由 + LLM 修正
                action = self._decide_action(user_input)

            self._current_route = action.get("route")

            # Update state: deciding
            self._update_state("deciding", f"路由：{action.get('route')}", {"route": action.get("route")})

            # 如果路由是 uncertain，让 LLM 分析并决定路由
            if action.get("route") == "uncertain":
                self._update_state("thinking", "规则路由不确定，LLM 决定下一步...")
                if self.use_llm:
                    llm_result = self._decide_next_step_with_llm(
                        user_input=user_input,
                        context=context,
                        previous_results=all_results,
                        iteration=iteration
                    )
                    action = llm_result
                else:
                    # Fallback 到 file_edit
                    action = {"route": "file_edit", "params": {"description": user_input}}

            # 检查是否任务已完成（LLM 判断）
            if action.get("route") == "task_complete":
                task_complete = True
                result = {
                    "status": "success",
                    "route": "response",
                    "data": {"message": action.get("params", {}).get("message", "任务已完成")}
                }
                all_results.append(result)
                break

            # Execute action
            self._update_state("executing", f"执行：{action.get('route')}", {"params": action.get("params")})

            # 触发 PreToolUse 钩子（包括权限检查）
            pre_tool_data = self.hook_manager.trigger_pre_tool_use(
                action.get("route", "response"),
                action.get("params", {})
            )

            # 检查是否需要权限确认
            if pre_tool_data.get("requires_confirmation"):
                # 返回权限请求，等待用户确认
                permission_request = pre_tool_data.get("permission_request", {})
                return {
                    "route": "permission_request",
                    "status": "waiting_confirmation",
                    "data": {
                        "permission_request": permission_request,
                        "message": pre_tool_data.get("message", "请确认是否继续执行此操作"),
                        "action": action,
                    }
                }

            if pre_tool_data.get("blocked"):
                result = {
                    "route": "response",
                    "params": {"message": pre_tool_data.get("error", "Action blocked")},
                    "blocked": True
                }
                all_results.append(result)
                continue

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

            all_results.append(result)

            # 触发 PostToolUse 钩子
            post_tool_data = self.hook_manager.trigger_post_tool_use(
                action.get("route", "response"),
                action.get("params", {}),
                result
            )
            if post_tool_data.get("result"):
                result = post_tool_data["result"]

            # 让 LLM 判断任务是否完成
            if self.use_llm and iteration >= 1:
                completion_check = self._check_task_completion(
                    user_input=user_input,
                    results=all_results,
                    iteration=iteration
                )
                if completion_check.get("task_complete"):
                    task_complete = True
                    # 生成最终报告
                    final_result = self._generate_final_report(user_input, all_results)
                    result = final_result
                    break

        # 使用最后一轮的结果
        if all_results:
            result = all_results[-1]

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

    def _decide_next_step_with_llm(
        self,
        user_input: str,
        context: Dict[str, Any],
        previous_results: List[Dict[str, Any]],
        iteration: int
    ) -> Dict[str, Any]:
        """让 LLM 基于当前状态决定下一步做什么

        这是 Claude Code 的核心：观察结果 → 决定下一步 → 执行
        """
        # 构建执行历史
        history_summary = ""
        for i, r in enumerate(previous_results[-3:], 1):  # 只看最近 3 轮
            route = r.get("route", "unknown")
            status = r.get("status", "unknown")
            history_summary += f"步骤 {i}: {route} - {status}\n"

        # 获取工作区信息
        workspace_prompt = self.workspace.get_context_prompt()

        prompt = f"""用户原始请求：{user_input[:300]}

**工作区信息**:
{workspace_prompt}

**已执行步骤**:
{history_summary}

**当前是第 {iteration} 次迭代**。

请决定下一步做什么：
1. 如果任务已完成，返回：{{"route": "task_complete", "params": {{"message": "完成说明"}}}}
2. 如果需要继续，选择下一个最合适的路由（bash/file_edit/glob/grep/chat/response 等）
3. 解释为什么选择这个步骤

以 JSON 格式返回：
```json
{{
    "route": "路由名称",
    "params": {{"参数名": "参数值"}},
    "reason": "选择这个步骤的原因"
}}
```
"""
        try:
            llm_result = self.llm.think(prompt, context)
            content = llm_result.get("content", "")

            # 解析 JSON
            import re
            json_match = re.search(r'\{[\s\S]*\}', content)
            if json_match:
                return json.loads(json_match.group())
        except Exception as e:
            print(f"[LLM 决策下一步] 错误：{e}")

        # Fallback
        return {"route": "response", "params": {"message": "任务执行中..."}}

    def _check_task_completion(
        self,
        user_input: str,
        results: List[Dict[str, Any]],
        iteration: int
    ) -> Dict[str, Any]:
        """检查任务是否完成"""
        if not self.use_llm:
            return {"task_complete": False}

        # 构建执行摘要
        exec_summary = ""
        for i, r in enumerate(results, 1):
            route = r.get("route", "unknown")
            status = r.get("status", "unknown")
            exec_summary += f"{i}. {route}: {status}\n"

        prompt = f"""用户请求：{user_input[:300]}

已执行 {iteration} 步：
{exec_summary}

请判断：
1. 用户的原始请求是否已经满足？
2. 是否需要继续执行更多步骤？
3. 如果完成，生成一份简短的完成报告

以 JSON 格式返回：
```json
{{
    "task_complete": true/false,
    "reason": "判断原因",
    "final_report": "如果完成的总结报告"
}}
```
"""
        try:
            llm_result = self.llm.chat(prompt)
            content = llm_result.get("content", "")

            import re
            json_match = re.search(r'\{[\s\S]*\}', content)
            if json_match:
                return json.loads(json_match.group())
        except Exception as e:
            print(f"[检查完成] 错误：{e}")

        return {"task_complete": False}

    def _llm_decide_action(
        self,
        user_input: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """让 LLM 分析用户意图并决定初始行动

        这是 Claude Code 的核心：直接让 LLM 理解用户要什么，然后选择最合适的工具
        """
        # 获取工作区信息
        workspace_prompt = self.workspace.get_context_prompt()

        prompt = f"""用户请求：{user_input[:500]}

**工作区信息**:
{workspace_prompt}

**可用工具**:
- bash: 执行 shell 命令（如 ls, cd, find, grep 等）
- file_edit: 编辑或创建文件
- glob: 查找文件（支持通配符）
- grep: 搜索文件内容
- chat: 与其他 Agent 对话
- response: 直接回复（当不需要工具时）

请分析用户意图，选择最合适的工具：
1. 如果用户想要执行命令 → 选择 bash
2. 如果用户想要修改/创建文件 → 选择 file_edit
3. 如果用户想要查找文件 → 选择 glob
4. 如果用户想要搜索内容 → 选择 grep
5. 如果用户想要与其他 Agent 对话 → 选择 chat
6. 如果只是想询问或对话 → 选择 response

以 JSON 格式返回：
```json
{{
    "route": "工具名称",
    "params": {{}},
    "reason": "选择这个工具的原因",
    "plan": "如果需要多步执行，列出后续计划"
}}
```
"""
        try:
            llm_result = self.llm.think(prompt, context)
            content = llm_result.get("content", "")

            # 解析 JSON
            import re
            json_match = re.search(r'\{[\s\S]*\}', content)
            if json_match:
                result = json.loads(json_match.group())
                # 记录 LLM 的思考和计划
                if result.get("reason"):
                    self._update_state("planning", result["reason"])
                return result
        except Exception as e:
            print(f"[LLM 决策初始行动] 错误：{e}")

        # Fallback 到规则路由
        return self._decide_action(user_input)

    def _generate_final_report(
        self,
        user_input: str,
        results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """生成最终任务完成报告"""
        if not self.use_llm:
            return {
                "status": "success",
                "route": "response",
                "data": {"message": "任务已完成"}
            }

        # 构建执行历史
        history = []
        for r in results:
            route = r.get("route")
            status = r.get("status")
            history.append(f"- {route}: {status}")

        prompt = f"""用户请求：{user_input[:300]}

执行历史：
{chr(10).join(history)}

请生成一份简洁的任务完成报告：
1. 做了什么
2. 结果如何
3. 后续建议（如果有）

用 Markdown 格式，200 字以内。
"""
        try:
            llm_result = self.llm.chat(prompt)
            content = llm_result.get("content", "")

            return {
                "status": "success",
                "route": "response",
                "data": {"message": content}
            }
        except Exception:
            return {
                "status": "success",
                "route": "response",
                "data": {"message": "任务已完成"}
            }

    def cleanup(self):
        """清理资源，触发 SessionEnd 钩子并保存会话状态"""
        if hasattr(self, '_session_started') and self._session_started:
            self.hook_manager.trigger_session_end({
                "session_id": self.state.get_session_id(),
                "history_length": len(self.state.get_history())
            })

        # 保存会话状态
        self._save_session_state()

    def _save_session_state(self):
        """保存当前会话状态"""
        try:
            session_id = self.state.get_session_id()
            history = self.state.get_history()[-50:]  # 只保留最近 50 条

            session_state_manager.update_state(
                session_id=session_id,
                end_time=time.time(),
                current_task=getattr(self, '_current_task', None),
                history=history,
                working_directory=str(self.workspace.root) if hasattr(self, 'workspace') and self.workspace else None,
                metadata={
                    "last_route": self._current_route,
                    "skills_count": len(self.skill_manager.list_skills()),
                    "hooks_count": len(self.hook_manager.list_hooks())
                }
            )
        except Exception as e:
            print(f"Save session state error: {e}")

    def load_previous_session(self) -> Optional[Dict[str, Any]]:
        """加载上一个会话的状态

        Returns:
            Dict: 上一个会话的状态，如果不存在则返回 None
        """
        try:
            session_id = self.state.get_session_id()
            state = session_state_manager.load_state(session_id)

            if state:
                # 恢复历史
                history = state.get("history", [])
                if history:
                    self.state.context["history"] = history

                # 恢复工作目录
                working_dir = state.get("working_directory")
                if working_dir:
                    try:
                        import os
                        os.chdir(working_dir)
                    except Exception:
                        pass

            return state
        except Exception as e:
            print(f"Load previous session error: {e}")
            return None

    def list_sessions(self, limit: int = 20) -> List[Dict[str, Any]]:
        """列出最近的会话

        Args:
            limit: 限制数量

        Returns:
            List[Dict]: 会话列表
        """
        return session_state_manager.list_sessions(limit)

    def delete_session(self, session_id: str) -> bool:
        """删除会话

        Args:
            session_id: 会话 ID

        Returns:
            bool: 是否删除成功
        """
        return session_state_manager.delete_session(session_id)

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
        """基于规则的意图识别 - 核心路由

        核心路由:
        1. bash - 执行 shell 命令
        2. file_edit - 文件编辑
        3. glob - 文件名模式匹配
        4. grep - 文件内容搜索
        5. chat - 与其他 Agent 对话
        6. create - 创建 Agent 或团队

        其他情况交给 LLM 通过 uncertain 路由决定
        """
        import re

        input_lower = user_input.lower() if user_input else ""
        input_stripped = user_input.strip() if user_input else ""

        # 1. Bash 命令模式 - 检测命令前缀或特殊字符
        bash_explicit_patterns = [
            r'^\$ ',      # $ 开头
            r'^\$',       # $ 开头无空格
            r'^bash ',    # bash 开头
            r'^sh ',      # sh 开头
            r'^sudo ',    # sudo 开头
        ]
        bash_cmd_patterns = ["ls ", "cd ", "pwd", "cat ", "find ", "echo ", "rm ", "cp ", "mv ", "mkdir ", "head ", "tail ", "wc "]

        is_bash = False

        # 检查明确的前缀模式
        for pattern in bash_explicit_patterns:
            if re.search(pattern, input_stripped, re.IGNORECASE):
                is_bash = True
                break

        if not is_bash:
            for cmd in bash_cmd_patterns:
                if input_lower.startswith(cmd):
                    is_bash = True
                    break

        if not is_bash:
            if re.match(r'^[a-z]+\s+.*$', input_stripped) and len(input_stripped.split()) <= 5:
                first_word = input_stripped.split()[0].lower()
                common_commands = ["ls", "cd", "pwd", "cat", "find", "head", "tail", "wc", "echo", "mkdir", "rm", "cp", "mv"]
                if first_word in common_commands:
                    is_bash = True

        if is_bash:
            command = input_stripped[1:].strip() if input_stripped.startswith("$") else input_stripped
            return {"route": "bash", "params": {"command": command}}

        # 2. Glob - 文件名匹配 (检测 find + 模式)
        glob_patterns = ["find", "查找文件", "搜索文件", "*.py", "*.ts", "*.js", "*.md"]
        is_glob = any(kw in input_lower for kw in glob_patterns)
        if is_glob and any(kw in input_lower for kw in ["pattern", "模式", "extension", "扩展名"]):
            # 提取模式
            pattern_match = re.search(r'\*\.\w+', user_input)
            pattern = pattern_match.group(0) if pattern_match else "*"
            return {"route": "glob", "params": {"pattern": pattern, "path": "."}}

        # 3. Grep - 内容搜索 (检测 grep + 文本模式，或搜索关键词)
        grep_keywords = ["grep", "search for", "search text", "查找内容", "搜索文本", "TODO", "FIXME"]
        is_grep = any(kw in input_lower for kw in grep_keywords)
        if is_grep:
            # 提取搜索模式
            pattern_match = re.search(r'["\']([^"\']+)["\']', user_input)
            pattern = pattern_match.group(1) if pattern_match else user_input.split()[-1]
            return {"route": "grep", "params": {"pattern": pattern, "path": "."}}

        # 4. 创建 Agent/团队
        create_keywords = ["create", "new ", "add ", "创建", "新建"]
        is_create = any(kw in input_lower for kw in create_keywords)
        if is_create:
            has_target = any(t in input_lower for t in ["agent", "team", "助手", "bot", "robot"])
            if has_target:
                if any(t in input_lower for t in ["team", "团队", "group", "组"]):
                    return {"route": "create_team", "params": {"name": user_input}}
                return {"route": "create_user", "params": {"name": user_input}}

        # 5. 与其他 Agent 对话
        chat_patterns = ["和.*对话", "跟.*说话", "find agent", "tell agent", "send message"]
        for pattern in chat_patterns:
            if re.search(pattern, input_lower):
                return {"route": "chat", "params": {"message": user_input}}

        # 6. 文件编辑（检测文件路径或编辑关键词）
        file_edit_patterns = ["编辑", "修改", "创建文件", "write", "edit", "update", "create file"]
        if any(kw in input_lower for kw in file_edit_patterns):
            # 如果提到文件，路由到 file_edit
            if any(kw in input_lower for kw in ["文件", "file", ".py", ".ts", ".js", ".md", ".json"]):
                return {"route": "file_edit", "params": {"description": user_input}}

        # 7. 项目相关模糊请求 - 主动探索
        # 检测是否包含项目相关关键词：完善、改进、优化、查看项目等
        project_keywords = ["完善", "改进", "优化", "查看", "看看", "explore", "improve", "enhance"]
        project_indicators = ["项目", "project", "代码", "code", "dir", "folder"]

        has_project_keyword = any(kw in input_lower for kw in project_keywords)
        has_project_indicator = any(ind in input_lower for ind in project_indicators)

        # 检测是否提到特定项目名（crawler, spider 等）
        project_name_patterns = [
            r'([a-zA-Z0-9_-]+-crawler)',
            r'([a-zA-Z0-9_-]+-spider)',
            r'(爬虫)',
        ]
        mentioned_project = None
        for pattern in project_name_patterns:
            match = re.search(pattern, user_input, re.IGNORECASE)
            if match:
                mentioned_project = match.group(1)
                break

        if has_project_keyword or mentioned_project:
            # 这是一个项目相关的模糊请求，先探索项目结构
            # 返回 batch 命令：先查找项目，再查看结构
            search_name = mentioned_project.replace('项目', '').replace('-', '*') if mentioned_project else '*'
            return {
                "route": "batch",
                "commands": [
                    {
                        "route": "bash",
                        "params": {
                            "command": f"find /Users/agent/PycharmProjects -type d -iname '*{search_name}*' 2>/dev/null | head -5"
                        }
                    },
                    {
                        "route": "response",
                        "params": {
                            "message": f"我来帮您探索项目结构。以上是我找到的相关项目目录，接下来我可以帮您查看具体的代码结构或提供改进建议。"
                        }
                    }
                ]
            }

        # 其他情况 - 交给 LLM 决定使用哪个路由
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

    # Skill evolution methods
    def record_skill_evolution(self, user_input: str, route: str, params: Dict,
                                 result: Dict, success: bool, context: Dict = None):
        """记录技能进化"""
        self.skill_evolution.record_execution(user_input, route, params, result, success, context)

    def get_learned_skills(self) -> list:
        """获取已学习的技能"""
        return self.skill_evolution.list_patterns(min_confidence=0.5)

    def get_skill_evolution_stats(self) -> Dict[str, Any]:
        """获取技能进化统计"""
        return self.skill_evolution.get_stats()

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

    # ==================== Autonomous Mode Methods ====================

    def _run_autonomous_task(self, user_input: str) -> Dict[str, Any]:
        """运行自主任务执行循环

        用于复杂任务，让 Agent 自主规划、执行、反思
        """
        import asyncio

        # 创建自主执行循环实例
        loop = AutonomousLoop(self)

        # 运行任务
        result = asyncio.run(loop.run(user_input))

        # 将结果添加到历史记录
        self.state.add_to_history("assistant", result)

        # 保存对话
        self.conversation.save_message(
            agent_id=self.agent_id,
            session_id=self.state.get_session_id(),
            role="assistant",
            content=result
        )

        # 修剪历史记录
        self.state.trim_history()

        # 更新状态为完成
        self._update_state("completed", "自主执行完成")
        self._current_route = None

        return result

    def _is_complex_task(self, user_input: str) -> bool:
        """检测是否是复杂任务 - 放宽条件，让更多任务使用自主模式

        Claude Code 设计原则：宁可高估任务复杂度，也不要让用户一步步指引
        """
        # 首先使用规则快速判断（LLM 不可用时 fallback）
        if not self.llm.is_available():
            return self._is_complex_task_fallback(user_input)

        # 1. 先检查明确命令 - 这些不需要自主模式
        input_stripped = user_input.strip()
        simple_patterns = [
            r'^\$ ',           # $ 开头的命令
            r'^ls\s',          # ls 命令
            r'^cd\s',          # cd 命令
            r'^pwd\s*',        # pwd 命令
            r'^cat\s',         # cat 命令
            r'^echo\s',        # echo 命令
            r'^head\s',        # head 命令
            r'^tail\s',        # tail 命令
            r'^你好 |hello|hi\s',  # 问候
            r'^exit|quit',     # 退出
        ]
        for pattern in simple_patterns:
            if re.search(pattern, input_stripped, re.IGNORECASE):
                return False

        # 2. 宽松判断：只要不是简单命令，都使用自主模式
        # 这样可以让更多任务进入自主执行循环
        has_action_keyword = any(kw in user_input.lower() for kw in [
            '完善', '改进', '优化', '实现', '开发', '构建',
            '分析', '探索', '重构', '设计', '创建', '搭建',
            '修复', '调试', '添加', '查看', '看看',
            'improve', 'enhance', 'implement', 'develop', 'build',
            'analyze', 'explore', 'refactor', 'design', 'create', 'setup',
            'fix', 'debug', 'add', 'check', 'view',
        ])

        # 3. 使用 LLM 辅助判断（当没有明确关键词时）
        if not has_action_keyword:
            prompt = f"""判断用户输入是否需要多步骤执行：

用户输入：{user_input[:200]}

简单任务：单一命令（ls/cd 等）、问候、简单问答
复杂任务：需要先探索再行动、涉及多个文件/步骤、模糊的改进需求

返回 true/false"""
            try:
                result = self.llm.chat(prompt)
                content = result.get("content", "").lower()
                if "true" in content:
                    return True
            except Exception:
                pass

        # 默认：有关键词或是项目相关请求，都使用自主模式
        return has_action_keyword

    def _needs_plan(self, user_input: str) -> bool:
        """判断是否需要先输出计划

        触发条件：
        1. 用户明确要求先看计划（"先看计划"、"plan first"等）
        2. 超复杂任务（涉及多个文件/系统的大改动）
        3. 配置启用计划模式
        """
        # 检查明确请求
        plan_keywords = ['先看计划', '生成计划', '展示计划', 'plan first', 'show plan', '先规划']
        if any(kw in user_input.lower() for kw in plan_keywords):
            return True

        # 检查配置
        config = self.config_manager.load(self.agent_id, 'user')
        if config.get('plan_mode', False):
            return True

        # 超复杂任务判断：涉及多个系统/架构的改动
        complex_keywords = ['架构', '重构整个', '重写', 'migration', 'refactor all', 'rewrite']
        return any(kw in user_input.lower() for kw in complex_keywords)

    def _plan_task(self, user_input: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """生成任务执行计划

        使用 LLM 分析任务，输出多步执行计划
        """
        workspace_prompt = self.workspace.get_context_prompt()

        prompt = f"""用户请求：{user_input[:500]}

**工作区信息**:
{workspace_prompt}

**可用工具**:
- bash: 执行 shell 命令
- file_edit: 编辑或创建文件
- glob: 查找文件
- grep: 搜索内容
- subagent: 委派给子代理

请分析这个任务，生成一份执行计划：
1. 任务复杂度（简单/中等/复杂）
2. 需要执行的步骤（每步说明要做什么、用什么工具）
3. 预计影响范围（修改哪些文件/系统）
4. 潜在风险

以 JSON 格式返回：
```json
{{
    "complexity": "简单/中等/复杂",
    "steps": [
        {{"step": 1, "action": "动作描述", "tool": "工具名", "reason": "为什么做这步"}},
        ...
    ],
    "impact": "影响范围说明",
    "risks": ["风险 1", "风险 2"],
    "estimated_steps": 数字
}}
```
"""
        try:
            llm_result = self.llm.think(prompt, context)
            content = llm_result.get("content", "")

            import re
            json_match = re.search(r'\{[\s\S]*\}', content)
            if json_match:
                return json.loads(json_match.group())
        except Exception as e:
            print(f"[计划任务] 错误：{e}")

        # Fallback
        return {
            "complexity": "未知",
            "steps": [{"step": 1, "action": "执行任务", "tool": "auto", "reason": "完成用户请求"}],
            "impact": "未知",
            "risks": [],
            "estimated_steps": 1
        }

    def _is_complex_task_fallback(self, user_input: str) -> bool:
        """Fallback 复杂任务检测（基于规则）"""
        input_lower = user_input.lower()

        # 中文复杂任务关键词
        chinese_keywords = [
            '完善', '改进', '优化', '实现', '开发', '构建',
            '分析', '探索', '重构', '设计',
            '创建', '搭建',
            '修复', '调试',
            '添加', '看看', '帮助', '做什么',
        ]

        # 英文复杂任务关键词
        english_keywords = [
            'improve', 'enhance', 'implement', 'develop', 'build',
            'analyze', 'explore', 'refactor', 'design',
            'create', 'setup',
            'fix', 'debug',
            'add', 'what can', 'what do',
        ]

        # 检测是否包含项目名
        project_pattern = r'stock[-_]crawler|crawler|spider|爬虫'
        has_project = bool(re.search(project_pattern, input_lower, re.IGNORECASE))

        # 检测是否包含询问/探索意图
        exploration_patterns = [
            r'能为.*做什么',
            r'可以.*什么',
            r'帮.*看看',
            r'what can.*do',
            r'what can.*for',
        ]
        has_exploration = any(re.search(p, input_lower) for p in exploration_patterns)

        has_chinese_keyword = any(kw in input_lower for kw in chinese_keywords)
        has_english_keyword = any(kw in input_lower for kw in english_keywords)

        return (has_chinese_keyword or has_english_keyword) or (has_project and has_exploration)

    def confirm_permission(
        self,
        confirmed: bool,
        remember: bool = False,
        pending_action: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """确认权限请求

        Args:
            confirmed: 是否确认执行
            remember: 是否记住选择
            pending_action: 待执行的动作

        Returns:
            Dict: 执行结果
        """
        from mul_agent.hooks.permission import PermissionHook

        # 获取权限钩子
        permission_hook = None
        for hook in self.hook_manager._hooks.get(HookEvent.PRE_TOOL_USE, []):
            if isinstance(hook, PermissionHook):
                permission_hook = hook
                break

        if not permission_hook:
            return {"status": "error", "message": "Permission hook not found"}

        # 确认请求
        result = permission_hook.confirm_pending_request(confirmed, remember)

        if not result:
            return {"status": "error", "message": "No pending permission request"}

        if not confirmed:
            return {
                "status": "success",
                "message": "操作已拒绝",
                "permission_request": result.to_dict()
            }

        # 如果确认了，继续执行待处理的动作
        if pending_action:
            # 重新执行动作（跳过权限检查，因为已经确认）
            result = self.router.dispatch(
                pending_action.get("route", "response"),
                pending_action.get("params", {})
            )

            # 记录执行情况
            self._record_route_execution(
                route=pending_action.get("route", "response"),
                params=pending_action.get("params", {}),
                result=result,
                user_input="permission_confirmed"
            )

            return {
                "status": "success",
                "message": "操作已确认并执行",
                "result": result
            }

        return {"status": "success", "message": "操作已确认"}
