"""Brain V2 - 纯 LLM 决策版本（实验性）

这是 mul-agent 的改进版本，展示简化后的架构：
- 删除硬编码规则路由
- 完全信任 LLM 决策
- 简化提示词

使用方法：
    # 原版本（保留规则路由）
    from mul_agent.brain.brain import Brain
    brain = Brain("core_brain", config_manager)
    result = brain.think(user_input)

    # V2 版本（纯 LLM 决策）
    from mul_agent.brain.brain_v2 import BrainV2
    brain_v2 = BrainV2("core_brain", config_manager)
    result = brain_v2.think_v2(user_input)
"""

from typing import Any, Dict, List, Optional
import re
import uuid
import time
import json
from pathlib import Path

# 导入原 Brain 类的依赖
from mul_agent.brain.workspace import get_current_workspace, Workspace
from mul_agent.brain.stream import stream_manager, StreamEventType
from mul_agent.brain.router import Router
from mul_agent.brain.llm import LLMClient
from mul_agent.brain.context_builder import ContextBuilder
from mul_agent.brain.conversation import ConversationManager
from mul_agent.brain.compressor import ContextCompressor
from mul_agent.brain.memory_decision import MemoryDecisionSystem
from mul_agent.brain.session_state import session_state_manager, SessionStateManager
from mul_agent.memory.memory import Memory
from mul_agent.network.agent_network import AgentNetwork
from mul_agent.repositories import AgentRepository, TeamRepository
from mul_agent.skills.manager import SkillManager
from mul_agent.hooks.manager import HookManager
from mul_agent.hooks.base import HookEvent
from mul_agent.commands.manager import CommandManager


class BrainState:
    """大脑状态管理器（复用原实现）"""

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


class BrainV2:
    """核心大脑 V2 - 纯 LLM 决策版本

    与原 Brain 的核心区别：
    1. 删除 _decide_action() 规则路由，完全信任 LLM
    2. 简化系统提示词，删除装饰性内容
    3. 只支持 2 种输出格式（# 命令 或 JSON）
    4. 移除复杂任务检测，所有任务一视同仁

    架构优势：
    - 代码更少（删除 200+ 行规则代码）
    - 模型更聪明（学会理解意图而非匹配规则）
    - 更易维护（规则都在提示词里，不在代码里）
    """

    def __init__(self, agent_id: str, config_manager):
        self.agent_id = agent_id
        self.config_manager = config_manager

        # Initialize repositories
        self.agent_repo = AgentRepository(config_manager)
        self.team_repo = TeamRepository(config_manager)

        # Load configurations
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

        # Use LLM for decision making
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
        self.context = self.state.context

        # Initialize Agent network
        self.network = AgentNetwork()
        self._register_to_network()

        # Initialize workspace awareness
        self.workspace = get_current_workspace()

        # State tracking for UI
        self._current_route = None
        self._start_time = None

    def think_v2(self, user_input: str) -> Dict[str, Any]:
        """V2 思考函数 - 纯 LLM 决策，无规则路由

        核心设计原则：
        1. 信任模型 - LLM 能理解意图，不需要规则匹配
        2. 简洁提示 - 只告诉模型可用路由和基本原则
        3. 直接执行 - 拿到决策就执行，不二次猜测
        """
        self._start_time = time.time()

        # 触发 SessionStart 钩子
        if not hasattr(self, '_session_started'):
            self.hook_manager.trigger_session_start()
            self._session_started = True

        # 更新状态
        self._update_state("received", "处理用户输入")

        # 触发 PreMessage 钩子
        pre_message_data = self.hook_manager.trigger_hooks(
            HookEvent.PRE_MESSAGE,
            {"user_input": user_input}
        )
        user_input = pre_message_data.get("user_input", user_input)

        # 检查是否是命令（以 / 或！开头）- 这个保留，因为是明确的用户意图
        if user_input.startswith(("/", "!", ".")):
            command_result = self.command_manager.execute_from_input(user_input)
            return {
                "route": "command",
                "command": command_result.status.value,
                "data": command_result.to_dict()
            }

        # ==================== V2 核心：纯 LLM 决策循环 ====================

        self._update_state("planning", "LLM 决策中...")

        # 添加到历史
        self.state.add_to_history("user", user_input)

        # 保存对话
        self.conversation.save_message(
            agent_id=self.agent_id,
            session_id=self.state.get_session_id(),
            role="user",
            content=user_input
        )

        # 上下文压缩检查
        if self.should_compress_context({"user_input": user_input, "history_length": len(self.state.get_history())}):
            self._compress_history()

        # 执行循环 - 最多 5 次迭代
        max_iterations = 5
        iteration = 0
        all_results = []
        task_complete = False

        while not task_complete and iteration < max_iterations:
            iteration += 1
            self._update_state("iteration", f"执行迭代 {iteration}/{max_iterations}")

            # 构建上下文
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
                    "previous_results": all_results
                }
            )

            # ========== V2 核心区别：直接调用 LLM，不使用规则路由 ==========
            self._update_state("deciding", "LLM 分析并决定下一步...")

            action = self._decide_action_with_llm_only(
                user_input=user_input,
                context=context,
                iteration=iteration
            )

            # 检查是否任务已完成
            if action.get("route") == "task_complete":
                task_complete = True
                result = {
                    "status": "success",
                    "route": "response",
                    "data": {"message": action.get("params", {}).get("message", "任务已完成")}
                }
                all_results.append(result)
                break

            # 执行动作
            self._current_route = action.get("route")
            self._update_state("executing", f"执行：{action.get('route')}", {"params": action.get("params")})

            # 触发 PreToolUse 钩子
            pre_tool_data = self.hook_manager.trigger_pre_tool_use(
                action.get("route", "response"),
                action.get("params", {})
            )

            if pre_tool_data.get("blocked"):
                result = {
                    "route": "response",
                    "params": {"message": pre_tool_data.get("error", "Action blocked")},
                    "blocked": True
                }
                all_results.append(result)
                continue

            # 执行路由
            result = self.router.dispatch(
                action.get("route", "response"),
                pre_tool_data.get("params", action.get("params", {}))
            )

            # 记录路由执行
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

            # LLM 判断任务是否完成
            if self.use_llm and iteration >= 1:
                completion_check = self._check_task_completion(
                    user_input=user_input,
                    results=all_results,
                    iteration=iteration
                )
                if completion_check.get("task_complete"):
                    task_complete = True
                    final_result = self._generate_final_report(user_input, all_results)
                    result = final_result
                    break

        # 使用最后一轮的结果
        if all_results:
            result = all_results[-1]

        # 保存到记忆
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

        # 添加到历史
        self.state.add_to_history("assistant", result)

        # 保存对话
        self.conversation.save_message(
            agent_id=self.agent_id,
            session_id=self.state.get_session_id(),
            role="assistant",
            content=result
        )

        # 修剪历史
        self.state.trim_history()

        # 更新状态
        self._update_state("completed", "响应完成")
        self._current_route = None

        return result

    def _decide_action_with_llm_only(
        self,
        user_input: str,
        context: Dict[str, Any],
        iteration: int
    ) -> Dict[str, Any]:
        """V2 核心：纯 LLM 决策，无规则路由

        原 Brain._decide_action() 有 150+ 行规则匹配代码
        这里完全删除，直接让 LLM 决定

        Args:
            user_input: 用户输入
            context: 上下文信息
            iteration: 当前迭代次数

        Returns:
            路由决策，如 {"route": "bash", "params": {"command": "ls -la"}}
        """
        if not self.use_llm:
            # Fallback：简单的问候语检测
            return self._decide_action_fallback(user_input)

        # 获取工作区信息
        workspace_info = self.workspace.get_context_prompt()

        # 构建简化的系统提示词
        system_prompt = self._build_simple_system_prompt(workspace_info)

        # 构建执行历史
        history_summary = ""
        if iteration > 1:
            history_summary = "已执行步骤:\n"
            # 这里可以添加更多上下文

        # 构建用户消息
        user_message = f"""用户请求：{user_input}

{history_summary if history_summary else ''}
请决定下一步做什么。支持的路由：
- bash: 执行 shell 命令
- file_edit: 编辑文件
- glob: 查找文件
- grep: 搜索内容
- chat: 与其他 Agent 对话
- memory: 写入记忆
- heart: 自我反思
- response: 直接回复

如果任务已完成，返回：{{"route": "task_complete", "params": {{"message": "完成总结"}}}}

请用 JSON 格式返回，例如：
{{"route": "bash", "params": {{"command": "ls -la"}}}}
"""

        try:
            # 调用 LLM
            response = self.llm.chat(
                message=user_message,
                system_prompt=system_prompt,
                history=context.get("history", [])[-5:]  # 最近 5 条历史
            )

            # 解析响应
            content = response.get("content", "")
            action = self._parse_simple_response(content, user_input)

            return action

        except Exception as e:
            print(f"[V2 LLM 决策] 错误：{e}")
            # Fallback 到 response
            return {"route": "response", "params": {"message": f"处理中...（发生错误：{e}）"}}

    def _build_simple_system_prompt(self, workspace_info: str = None) -> str:
        """构建简化的系统提示词

        原版（llm.py 中）有 200+ 行，包含大量装饰符号和详细规则
        这里只保留核心信息
        """
        role = self.user.get("role", {}).get("title", "AI 助手")
        personality = self.soul.get("core_traits", {}).get("personality", "乐于助人")

        # 团队成员信息
        team_info = """
团队成员：
- alice: 代码实现、Bug 修复
- bob: 任务规划、架构设计
- wangyue: 日常任务、问题解答
"""

        workspace_section = f"\n当前工作区：{workspace_info}" if workspace_info else ""

        return f"""你是 {role}，人格：{personality}。运行在用户本地电脑。
{team_info}
{workspace_section}

核心原则：
1. 直接行动 - 不要等待用户确认
2. 复杂任务分解为多个步骤
3. 代码任务找 alice，规划找 bob
4. 完成后写入记忆并反思

可用路由格式（选一种）：
1. # bash <命令>
2. # file_edit path:<路径> action:<操作>
3. # chat agent_id:<id> message:<内容>
4. # memory action:<动作> content:<内容>
5. # heart
6. # response <回复>
7. {{"route": "xxx", "params": {{...}}}}

用中文回答。一次可以返回多个命令，系统会按顺序执行。"""

    def _parse_simple_response(self, content: str, user_input: str) -> Dict[str, Any]:
        """简化的响应解析器

        原版（llm.py 中）有 250+ 行，支持 7 种格式
        这里只支持 2 种：# 命令格式 和 JSON 格式
        """
        content = content.strip()

        # 1. 尝试解析 # 格式
        lines = [line.strip() for line in content.split('\n') if line.strip().startswith('# ')]

        if lines:
            commands = []
            for line in lines:
                # 解析 # route params
                match = re.match(r'^#\s*(\w+)\s+(.+?)$', line)
                if match:
                    route = match.group(1).lower()
                    params_str = match.group(2)

                    # 解析参数
                    params = {}
                    param_matches = re.findall(r'(\w+):(\S+)', params_str)
                    for key, value in param_matches:
                        params[key] = value

                    # 如果没有 key:value 格式，整个作为 message 或 command
                    if not params:
                        if route in ['bash', 'shell']:
                            params['command'] = params_str
                        elif route == 'response':
                            params['message'] = params_str

                    commands.append({"route": route, "params": params})

            if len(commands) == 1:
                return commands[0]
            elif len(commands) > 1:
                return {"route": "batch", "commands": commands}

        # 2. 尝试解析 JSON 格式
        try:
            # 查找 JSON
            json_match = re.search(r'\{[\s\S]*\}', content)
            if json_match:
                result = json.loads(json_match.group())
                if isinstance(result, dict) and "route" in result:
                    return result
        except (json.JSONDecodeError, Exception):
            pass

        # 3. 默认 response
        return {"route": "response", "params": {"message": content}}

    def _decide_action_fallback(self, user_input: str) -> Dict[str, Any]:
        """Fallback 决策（LLM 不可用时）"""
        input_lower = user_input.lower()

        # 简单问候语检测
        if any(kw in input_lower for kw in ["你好", "hello", "hi", "早上好"]):
            return {"route": "response", "params": {"message": "你好！有什么可以帮你？"}}

        return {"route": "response", "params": {"message": f"我是{self.user.get('role', {}).get('title', 'AI 助手')}，请告诉我您的需求。"}}

    # ========== 复用原 Brain 的辅助方法 ==========

    def _update_state(self, status: str, action: str = None, details: dict = None):
        """更新状态（复用原实现）"""
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

            # Write state to file
            try:
                state_dir = Path("storage/agent_states")
                state_dir.mkdir(parents=True, exist_ok=True)
                state_file = state_dir / f"{self.agent_id}.json"
                with open(state_file, 'w') as f:
                    json.dump(state_data, f, indent=2)
            except Exception:
                pass

            # Emit stream event
            try:
                stream_manager.emit(
                    event=self._status_to_stream_event(status),
                    agent_id=self.agent_id,
                    session_id=self.state.get_session_id(),
                    data=state_data
                )
            except Exception:
                pass

            # Async state update
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.create_task(self._send_state_update(state_data))
                else:
                    loop.run_until_complete(self._send_state_update(state_data))
            except Exception:
                pass
        except Exception:
            pass

    def _status_to_stream_event(self, status: str) -> StreamEventType:
        """状态转事件类型"""
        mapping = {
            "received": StreamEventType.INPUT_RECEIVED,
            "planning": StreamEventType.PLANNING,
            "deciding": StreamEventType.THOUGHT,
            "thinking": StreamEventType.THOUGHT,
            "executing": StreamEventType.EXECUTION_START,
            "iteration": StreamEventType.EXECUTION_PROGRESS,
            "completed": StreamEventType.COMPLETE,
            "error": StreamEventType.EXECUTION_ERROR,
        }
        return mapping.get(status, StreamEventType.EXECUTION_PROGRESS)

    async def _send_state_update(self, state_data: dict):
        """发送状态更新"""
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                await client.post(
                    f"http://localhost:8080/api/v1/agent/state/{self.agent_id}",
                    json=state_data
                )
        except Exception:
            pass

    def _register_to_network(self) -> None:
        """注册到 Agent 网络"""
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
        """提取能力列表"""
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

    def _record_route_execution(
        self,
        route: str,
        params: Dict[str, Any],
        result: Dict[str, Any],
        user_input: str
    ) -> None:
        """记录路由执行到 Token Usage Center"""
        if not self.llm.token_center:
            return

        function = f"route_{route}"
        extra = {
            "route": route,
            "user_input": user_input[:500] if user_input else "",
        }

        # 根据路由类型添加额外信息
        if route == "bash":
            extra["command"] = params.get("command", "")
        elif route == "chat":
            extra["target_agent"] = params.get("agent_id", "")
        elif route == "batch":
            extra["batch_command_count"] = len(params.get("commands", []))

        if result:
            extra["result_status"] = result.get("status", "unknown")

        self.llm.token_center.record_usage(
            agent_id=self.agent_id,
            model="route_execution",
            function=function,
            input_tokens=0,
            output_tokens=1,
            extra=extra
        )

    def _check_task_completion(
        self,
        user_input: str,
        results: List[Dict[str, Any]],
        iteration: int
    ) -> Dict[str, Any]:
        """检查任务是否完成"""
        if not self.use_llm:
            return {"task_complete": False}

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

返回 JSON: {{"task_complete": true/false, "reason": "判断原因"}}
"""
        try:
            llm_result = self.llm.chat(prompt)
            content = llm_result.get("content", "")

            json_match = re.search(r'\{[\s\S]*\}', content)
            if json_match:
                return json.loads(json_match.group())
        except Exception as e:
            print(f"[检查完成] 错误：{e}")

        return {"task_complete": False}

    def _generate_final_report(
        self,
        user_input: str,
        results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """生成最终报告"""
        if not self.use_llm:
            return {
                "status": "success",
                "route": "response",
                "data": {"message": "任务已完成"}
            }

        history = []
        for r in results:
            route = r.get("route")
            status = r.get("status")
            history.append(f"- {route}: {status}")

        prompt = f"""用户请求：{user_input[:300]}

执行历史：
{chr(10).join(history)}

生成简短的任务完成报告（200 字以内）。
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
        """清理资源"""
        if hasattr(self, '_session_started') and self._session_started:
            self.hook_manager.trigger_session_end({
                "session_id": self.state.get_session_id(),
                "history_length": len(self.state.get_history())
            })

        self._save_session_state()

    def _save_session_state(self):
        """保存会话状态"""
        try:
            session_id = self.state.get_session_id()
            history = self.state.get_history()[-50:]

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
