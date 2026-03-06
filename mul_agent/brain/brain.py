"""Brain - Core Agent Brain"""

import json
from typing import Any, Dict, List, Optional

from mul_agent.brain.router import Router
from mul_agent.brain.llm import LLMClient
from mul_agent.brain.context_builder import ContextBuilder
from mul_agent.brain.conversation import ConversationManager
from mul_agent.brain.compressor import ContextCompressor
from mul_agent.memory.memory import Memory
from mul_agent.network.agent_network import AgentNetwork, MessageType


class Brain:
    """核心大脑 - 自主决策中心"""

    # 类级别的状态栏实例（可选）
    _state_bar = None

    @classmethod
    def set_state_bar(cls, state_bar):
        """设置全局状态栏实例"""
        cls._state_bar = state_bar

    @classmethod
    def clear_state_bar(cls):
        """清除全局状态栏"""
        cls._state_bar = None

    def _update_state(self, state, action=None):
        """更新状态栏"""
        if Brain._state_bar:
            Brain._state_bar.set_state(state, action)

    def __init__(self, agent_id: str, config_manager):
        self.agent_id = agent_id
        self.config_manager = config_manager

        # Load configurations
        self.soul = config_manager.load(agent_id, "soul")
        self.user = config_manager.load(agent_id, "user")
        self.skill = config_manager.load(agent_id, "skill")
        self.memory_config = config_manager.load(agent_id, "memory")

        # Initialize components
        self.router = Router(config_manager)
        self.llm = LLMClient(self.user.get("llm", {}), config_manager=config_manager, agent_id=agent_id)
        self.memory = Memory(
            agent_id=agent_id,
            config=self.memory_config
        )

        # Use LLM for decision making? (must be before compressor init)
        self.use_llm = self.llm.is_available()

        # 初始化上下文构建器
        self.context_builder = ContextBuilder(config_manager, self.memory)

        # 初始化对话历史管理器
        self.conversation = ConversationManager(memory=self.memory)

        # 初始化上下文压缩器
        self.compressor = ContextCompressor(
            llm_client=self.llm if self.use_llm else None,
            max_tokens=8000
        )

        # Short-term context
        self.context: Dict[str, Any] = {
            "agent_id": agent_id,
            "session_id": None,
            "history": []
        }

        # 会话 ID 管理
        import uuid
        self.context["session_id"] = str(uuid.uuid4())

        # Maximum history length to prevent memory issues
        self.max_history_length = 100

        # 初始化 Agent 网络（注册自身到网络）
        self.network = AgentNetwork()
        self._register_to_network()

    def _register_to_network(self) -> None:
        """注册自身到 Agent 网络"""
        # 从配置中提取能力
        capabilities = []

        # 根据角色提取能力
        role_title = self.user.get("role", {}).get("title", "").lower()
        if "code" in role_title or "developer" in role_title:
            capabilities.append("coding")
            capabilities.append("development")
        if "security" in role_title or "auditor" in role_title:
            capabilities.append("security")
            capabilities.append("review")
        if "test" in role_title or "qa" in role_title:
            capabilities.append("testing")
            capabilities.append("validation")
        if "writer" in role_title or "doc" in role_title:
            capabilities.append("writing")
            capabilities.append("documentation")
        if "research" in role_title:
            capabilities.append("research")
            capabilities.append("analysis")
        if "coordinator" in role_title or "brain" in role_title:
            capabilities.append("planning")
            capabilities.append("coordination")

        # 注册
        self.network.register(
            agent_id=self.agent_id,
            metadata={
                "role": self.user.get("role", {}).get("title", ""),
                "description": self.soul.get("description", ""),
                "capabilities": capabilities
            }
        )

    def think(self, user_input: str) -> Dict[str, Any]:
        """思考并决定下一步行动"""
        # Add to history
        self.context["history"].append({
            "role": "user",
            "content": user_input
        })

        # 保存对话到历史管理器（持久化）
        self.conversation.save_message(
            agent_id=self.agent_id,
            session_id=self.context["session_id"],
            role="user",
            content=user_input
        )

        # Agent 自我判断是否需要压缩上下文
        # 根据上下文复杂度自主决定
        compression_context = {
            "user_input": user_input,
            "history_length": len(self.context["history"])
        }
        if self.should_compress_context(compression_context):
            self._compress_history()

        # 使用 ContextBuilder 构建完整上下文（包含完整文本内容）
        context = self.context_builder.build_context(
            agent_id=self.agent_id,
            user_input=user_input,
            options={
                "include_text_content": True,  # 包含完整的 Markdown 文本
                "include_memory": True,
                "memory_limit": 5,
                "include_team": False,
                "include_history": True,
                "history": self.context["history"]
            }
        )

        # 使用 LLM 进行决策（如果可用）
        if self.use_llm:
            action = self.llm.think(user_input, context)
        else:
            # 构建上下文提示（现在包含完整的文本内容）
            context_prompt = self._build_context_prompt(user_input, context)
            action = self._decide_action(context_prompt, user_input)

        # 执行 action
        result = self.router.dispatch(action.get("route", "heart"), action.get("params", {}))

        # Add LLM response if present
        if "response" in action:
            result["response"] = action["response"]

        # 保存到记忆
        self.memory.write(
            memory_type="short_term",
            content={
                "input": user_input,
                "action": action,
                "result": result
            }
        )

        self.context["history"].append({
            "role": "assistant",
            "content": result
        })

        # 保存助手回复到对话历史
        self.conversation.save_message(
            agent_id=self.agent_id,
            session_id=self.context["session_id"],
            role="assistant",
            content=result
        )

        # Trim history to prevent unlimited growth
        if len(self.context["history"]) > self.max_history_length:
            # Keep first 2 entries (system) and last N entries
            self.context["history"] = (
                self.context["history"][:2] +
                self.context["history"][-self.max_history_length:]
            )

        return result

    def should_compress_context(self, context: Dict[str, Any]) -> bool:
        """Agent 自我判断是否需要压缩上下文

        根据以下因素自主判断：
        - 当前 Token 数量
        - 对话复杂度
        - 任务性质
        - 用户输入长度

        Args:
            context: 包含判断所需信息的字典

        Returns:
            是否需要压缩
        """
        # 使用压缩器进行分析
        return self.compressor.should_compress(
            self.context["history"],
            context
        )

    def _compress_history(self):
        """压缩对话历史

        将早期消息压缩为摘要，保留最近的消息完整。
        """
        # 使用 LLM 生成摘要
        summary = self.compressor.create_llm_summary(
            self.context["history"][:-self.compressor.recent_count]
        )

        # 压缩消息
        compressed = self.compressor.compress(
            self.context["history"],
            summary=summary
        )

        # 保存压缩摘要到磁盘
        self.conversation.compress_old_messages(
            agent_id=self.agent_id,
            session_id=self.context["session_id"],
            summary=summary
        )

        # 更新内存中的历史
        self.context["history"] = compressed

    def get_context_analysis(self) -> Dict[str, Any]:
        """获取上下文分析（供 Agent 参考）

        返回当前上下文的复杂度分析和建议。
        """
        return self.compressor.analyze_context_complexity(
            self.context["history"],
            ""
        )

    def _build_context_prompt(self, user_input: str, context: Dict[str, Any]) -> str:
        """构建上下文提示

        Args:
            user_input: 用户输入
            context: 完整的上下文字典（来自 ContextBuilder）
        """
        # 从上下文中提取信息
        recent_memory = context.get("recent_memory", [])
        text_contents = context.get("text_contents", {})
        configs = context.get("configs", {})
        soul = configs.get("soul", self.soul)
        user = configs.get("user", self.user)

        # 记忆上下文
        memory_context = "\n".join([
            f"- {m.get('content', '')[:100] if isinstance(m.get('content'), str) else m.get('content', {}).get('input', '')}"
            for m in recent_memory[-3:]
        ])

        # 完整的文本内容
        user_text = text_contents.get("user", "")
        soul_text = text_contents.get("soul", "")

        prompt = f"""
Current Task: {user_input}

Recent Memory:
{memory_context}

Agent Soul: {soul.get('core_traits', {}).get('personality', '')}
Agent Role: {user.get('role', {}).get('title', '')}

"""

        # 添加完整的文本内容（如果有）
        if user_text:
            prompt += f"""
## User Configuration:
{user_text}
"""
        if soul_text:
            prompt += f"""
## Soul Configuration:
{soul_text}
"""

        prompt += "\nPlease decide what action to take."

        return prompt

    def _decide_action(self, context_prompt: str, original_input: str = "") -> Dict[str, Any]:
        """决定执行什么动作 - 简化的决策逻辑"""
        # Use original input if provided, otherwise extract from prompt
        user_input = original_input.lower() if original_input else ""
        if not user_input:
            try:
                user_input = context_prompt.split("Current Task:")[1].split("\n")[0].strip().lower()
            except IndexError:
                user_input = ""

        # Empty input - just acknowledge (系统固定响应)
        if not user_input:
            # 尝试加载用户自定义风格，如果没有则使用默认
            custom_response = self.config_manager.load_prompt(self.agent_id, "empty_input_style")
            return {
                "route": "heart",
                "params": {"trigger": "manual", "focus": "status"},
                "response": custom_response if custom_response else "我在听。请告诉我你需要什么？"
            }

        # Simple routing based on keywords
        if "create" in user_input or "new" in user_input or "add" in user_input or "创建" in user_input or "新建" in user_input:
            return {"route": "create_user", "params": {"name": user_input}}

        if "bash" in user_input or "command" in user_input or user_input.startswith("$") or "执行" in user_input or "运行" in user_input:
            # 尝试提取命令
            command = user_input.replace("$", "").strip()
            return {"route": "bash", "params": {"command": command}}

        # 创建文件的任务 -> 使用 bash 执行 echo 或 cat
        if "文件" in user_input or "创建" in user_input or "写" in user_input:
            return {"route": "bash", "params": {"command": original_input}}

        if "memory" in user_input or "remember" in user_input or "记住" in user_input or "记忆" in user_input:
            return {"route": "memory", "params": {"action": "list", "memory_type": "long_term"}}

        if "heart" in user_input or "reflect" in user_input or "evolve" in user_input or "自省" in user_input or "反思" in user_input:
            return {"route": "heart", "params": {}}

        # Agent 自己决定是否需要和其他 Agent 对话
        # 根据用户需求，Brain 自动决定调用哪个 Agent
        target_agent = self._decide_target_agent(user_input)
        if target_agent:
            # Agent 决定把任务发送给其他 Agent
            return {"route": "chat", "params": {"action": "send", "agent_id": target_agent, "message": user_input}}

        # Help menu (系统固定响应)
        if "help" in user_input or "?" in user_input:
            custom_help = self.config_manager.load_prompt(self.agent_id, "help_menu_style")
            return {
                "route": "heart",
                "params": {"trigger": "manual", "focus": "help"},
                "response": custom_help if custom_help else "可用命令：create/新建，bash/$执行命令，memory/记忆，heart/自省，chat/对话"
            }

        # Default: return status info (系统固定响应)
        role_title = self.user.get('role', {}).get('title', 'Agent')
        custom_status = self.config_manager.load_prompt(self.agent_id, "status_style")
        status_template = custom_status if custom_status else "我是 {role_title}，当前状态正常。"
        return {
            "route": "heart",
            "params": {"trigger": "manual", "focus": "status"},
            "response": status_template.format(role_title=role_title) if "{role_title}" in status_template else f"我是 {role_title}，当前状态正常。"
        }

    def _decide_target_agent(self, user_input: str) -> Optional[str]:
        """Agent 自己决定把任务发送给哪个 Agent - 增强版

        使用 Agent Network 查找最合适的专业 Agent。
        """
        input_lower = user_input.lower()

        # 首先尝试使用 Agent Network 查找专业 Agent
        # 确定任务类型
        task_type = self._identify_task_type(input_lower)

        if task_type:
            # 使用网络查找专业 Agent
            specialist = self.network.find_specialist(task_type)
            if specialist and specialist != self.agent_id:
                return specialist

        # 回退到基于关键词的查找
        return self._decide_target_agent_keywords(input_lower)

    def _identify_task_type(self, input_lower: str) -> Optional[str]:
        """识别任务类型"""
        # 编程相关
        coding_keywords = ["code", "写代码", "编程", "coder", "developer", "function", "class", "bug", "error", "调试", "程序", "implement", "refactor"]
        if any(kw in input_lower for kw in coding_keywords):
            return "coding"

        # 安全相关
        security_keywords = ["security", "安全", "audit", "review", "审查", "vulnerability", "认证", "授权", "secret", "password"]
        if any(kw in input_lower for kw in security_keywords):
            return "security"

        # 测试相关
        testing_keywords = ["test", "测试", "coverage", "unit test", "e2e", "qa", "pytest", "junit"]
        if any(kw in input_lower for kw in testing_keywords):
            return "testing"

        # 写作相关
        writing_keywords = ["write", "写作", "文章", "文档", "doc", "写", "创作", "内容", "文本", "readme", "markdown"]
        if any(kw in input_lower for kw in writing_keywords):
            return "writing"

        # 研究相关
        research_keywords = ["search", "搜索", "查找", "research", "查询", "how to", "怎么", "what is", "find"]
        if any(kw in input_lower for kw in research_keywords):
            return "research"

        # 规划相关
        planning_keywords = ["plan", "design", "架构", "architecture", "system", "设计", "pattern", "structure"]
        if any(kw in input_lower for kw in planning_keywords):
            return "planning"

        return None

    def _decide_target_agent_keywords(self, input_lower: str) -> Optional[str]:
        """基于关键词的 Agent 查找（回退逻辑）"""
        # 编程相关 -> 发送给 coder
        coding_keywords = ["code", "写代码", "编程", "coder", "developer", "function", "class", "bug", "error", "调试", "程序"]
        for kw in coding_keywords:
            if kw in input_lower:
                return "coder"

        # 写作相关 -> 发送给 writer
        writing_keywords = ["write", "写作", "文章", "文档", "doc", "写", "创作", "内容", "文本"]
        for kw in writing_keywords:
            if kw in input_lower:
                return "writer"

        # 搜索相关 -> 发送给 researcher
        search_keywords = ["search", "搜索", "查找", "research", "查询", "什么", "how to", "怎么"]
        for kw in search_keywords:
            if kw in input_lower:
                return "researcher"

        # 普通对话 -> 保持当前 Agent
        conversation_keywords = ["hello", "hi", "你好", "聊", "对话", "说话", "天气", "news", "消息"]
        for kw in conversation_keywords:
            if kw in input_lower:
                return None  # 不需要转发，自己处理

        # 默认不转发，让当前 Agent 处理
        return None

        # 写作相关 -> 发送给 writer
        writing_keywords = ["write", "写作", "文章", "文档", "doc", "写", "创作", "内容", "文本"]
        for kw in writing_keywords:
            if kw in input_lower:
                return "writer"

        # 搜索相关 -> 发送给 researcher
        search_keywords = ["search", "搜索", "查找", "找", "research", "查询", "什么", "how to", "怎么"]
        for kw in search_keywords:
            if kw in input_lower:
                return "researcher"

        # 普通对话 -> 保持当前 Agent
        conversation_keywords = ["hello", "hi", "你好", "聊", "对话", "说话", "天气", "news", "消息"]
        for kw in conversation_keywords:
            if kw in input_lower:
                return None  # 不需要转发，自己处理

        # 默认不转发，让当前 Agent 处理
        return None

    def evolve(self, focus: str = "all", require_confirmation: bool = False) -> Dict[str, Any]:
        """自我进化 - 修改自身配置

        Args:
            focus: 进化焦点 (all/soul/user/skill/memory)
            require_confirmation: 是否需要用户确认（生产环境建议开启）

        Returns:
            进化结果字典
        """
        analysis = self._analyze_current_state()

        # Based on analysis, propose changes using LLM
        proposed_changes = self._generate_evolution(analysis)

        # Apply changes ONLY if they have valid config_type
        applied = []
        evolution_rules = self.soul.get("evolution_rules", {})
        can_modify_self = evolution_rules.get("can_modify_self", False)

        if can_modify_self:
            # 如果需要确认，返回建议等待用户确认
            if require_confirmation:
                return {
                    "status": "pending_confirmation",
                    "analysis": analysis,
                    "proposed_changes": proposed_changes,
                    "message": "Changes proposed. Call apply_evolution() to apply."
                }

            # 检查是否需要快照
            if evolution_rules.get("snapshot_before_change", True):
                self.config_manager._create_snapshot(self.agent_id, "soul")
                self.config_manager._create_snapshot(self.agent_id, "user")

            for change in proposed_changes:
                # Only apply if it has a valid type
                if change.get("type") in self.config_manager.CONFIG_TYPES:
                    if self._apply_change(change):
                        applied.append(change)

            # 自检验（如果配置要求）
            if evolution_rules.get("self_check_required", False):
                validation = self.config_manager.validate_config(self.agent_id)
                if not validation["valid"]:
                    # 配置验证失败，回滚
                    return {
                        "status": "rollback",
                        "reason": "Config validation failed after evolution",
                        "errors": validation["errors"],
                        "evolutions_applied": applied
                    }

        # Update analysis with LLM suggestions
        analysis["issues_found"] = [c.get("suggestion", "") for c in proposed_changes]
        analysis["can_evolve"] = can_modify_self

        return {
            "status": "success" if applied or not proposed_changes else "no_changes",
            "analysis": analysis,
            "evolutions_applied": applied,
            "suggestions": proposed_changes
        }

    def apply_evolution(self, changes: list) -> Dict[str, Any]:
        """应用进化变更（用于需要确认的场景）

        Args:
            changes: 用户确认的变更列表

        Returns:
            应用结果
        """
        applied = []
        for change in changes:
            if change.get("type") in self.config_manager.CONFIG_TYPES:
                if self._apply_change(change):
                    applied.append(change)

        return {
            "status": "success",
            "applied_count": len(applied),
            "changes": applied
        }

    def _analyze_current_state(self) -> Dict[str, Any]:
        """分析当前状态"""
        return {
            "current_state": {
                "soul_version": self.soul.get("version"),
                "user_config": self.user.get("role", {}).get("title"),
                "skills_count": len(self.skill.get("skills", []))
            },
            "issues_found": [],
            "metrics": {
                "total_routes": len(self.router.ROUTES),
                "tools_enabled": len(self.user.get("tools", {}).get("enabled", []))
            }
        }

    def _generate_evolution(self, analysis: Dict) -> list:
        """生成进化方案 - 使用 LLM 分析并提出改进建议"""
        if not self.use_llm:
            return []

        # 构建分析提示
        prompt = f"""你是一个AI系统的自我进化分析器。请分析以下当前状态，提出可能的改进建议。

当前状态:
- 灵魂版本: {analysis.get('current_state', {}).get('soul_version')}
- 角色: {analysis.get('current_state', {}).get('user_config')}
- 技能数量: {analysis.get('current_state', {}).get('skills_count')}
- 可用路由数: {analysis.get('metrics', {}).get('total_routes')}
- 启用的工具: {analysis.get('metrics', {}).get('tools_enabled')}

请分析并提出可能的改进建议。回复JSON格式:
{{"suggestions": ["建议1", "建议2"], "reasoning": "分析理由"}}
"""

        try:
            result = self.llm.chat(prompt, system_prompt="你是一个AI系统分析专家，擅长发现系统改进机会。")
            content = result.get("content", "")

            # 尝试解析建议
            import json
            import re
            # 提取JSON
            match = re.search(r'\{.*\}', content, re.DOTALL)
            if match:
                suggestions = json.loads(match.group())
                suggestion_list = suggestions.get("suggestions", [])

                # 将建议转换为变更记录
                changes = []
                for i, sug in enumerate(suggestion_list):
                    changes.append({
                        "id": i + 1,
                        "suggestion": sug,
                        "type": "analysis",
                        "status": "proposed"
                    })
                return changes
        except Exception as e:
            print(f"Evolution analysis error: {e}")

        return []

    def _apply_change(self, change: Dict) -> bool:
        """应用配置变更"""
        config_type = change.get("type")
        new_data = change.get("data")

        if config_type == "soul":
            self.soul = new_data
        elif config_type == "user":
            self.user = new_data
        elif config_type == "skill":
            self.skill = new_data
        elif config_type == "memory":
            self.memory_config = new_data

        # Save to disk
        self.config_manager.save(self.agent_id, config_type, new_data)
        return True

    def create_agent(self, config: Dict) -> Dict[str, Any]:
        """创建新Agent成员"""
        new_agent_id = config.get("agent_id", f"agent_{hash(config.get('name', ''))}")

        # Create default configs for new agent
        default_configs = self._generate_agent_configs(new_agent_id, config)

        # Save all configs
        for config_type, data in default_configs.items():
            self.config_manager.save(new_agent_id, config_type, data)

        return {
            "status": "success",
            "agent_id": new_agent_id,
            "message": f"Agent {new_agent_id} created successfully",
            "network_registered": True
        }

    def _generate_agent_configs(self, agent_id: str, config: Dict) -> Dict:
        """为新Agent生成默认配置"""
        return {
            "soul": {
                "version": "1.0",
                "name": agent_id,
                "description": f"Agent created by {self.agent_id}",
                "core_traits": {
                    "personality": config.get("personality", "Helpful assistant"),
                    "values": ["efficiency", "clarity"],
                    "goals": ["assist_user", "learn"]
                },
                "behavior_patterns": {
                    "decision_making": "collaborative",
                    "problem_solving": "step_by_step",
                    "communication": "clear"
                },
                "evolution_rules": {
                    "can_modify_self": False,
                    "modification_scope": [],
                    "snapshot_before_change": True,
                    "self_check_required": True
                },
                "constraints": {
                    "boundaries": ["no_harm"],
                    "forbidden_actions": []
                }
            },
            "user": {
                "version": "1.0",
                "agent_id": agent_id,
                "role": {
                    "type": config.get("role_type", "worker"),
                    "title": config.get("name", agent_id),
                    "responsibilities": ["task_execution"]
                },
                "capabilities": {
                    "max_team_size": 1,
                    "can_create_agent": False,
                    "can_modify_config": False,
                    "can_execute_tools": True
                },
                "tools": {
                    "enabled": ["bash"],
                    "bash": {
                        "enabled": True,
                        "timeout": 30,
                        "allowed_commands": ["ls", "pwd", "echo", "cat", "grep"],
                        "forbidden_commands": ["rm -rf", "sudo", "dd"]
                    }
                },
                "permissions": {
                    "file_read": ["*"],
                    "file_write": ["storage/memory/**"],
                    "network_access": True
                }
            },
            "skill": {
                "version": "1.0",
                "agent_id": agent_id,
                "skills": [],
                "skill_tree": {"root": None, "children": {}}
            },
            "memory": {
                "version": "1.0",
                "agent_id": agent_id,
                "memory_strategy": {
                    "short_term": {
                        "storage": "session",
                        "max_size": "1MB",
                        "auto_cleanup": True,
                        "ttl_seconds": 3600
                    },
                    "long_term": {
                        "storage": "file",
                        "path": f"storage/memory/long_term/{agent_id}",
                        "compression": False,
                        "auto_archive": True,
                        "archive_interval": "daily"
                    }
                },
                "handover": {
                    "required_fields": ["task_summary", "context", "next_steps"],
                    "format": "markdown",
                    "auto_generate": True
                },
                "retrieval": {
                    "default_limit": 10,
                    "relevance_threshold": 0.7,
                    "search_method": "keyword"
                }
            }
        }

    # ==================== Agent 网络协作方法 ====================

    def delegate_task(self, to_agent: str, task: Dict[str, Any],
                      callback_msg_id: Optional[str] = None) -> Dict[str, Any]:
        """委派任务给其他 Agent

        Args:
            to_agent: 接收方 Agent ID
            task: 任务详情，包含：
                - description: 任务描述
                - priority: 优先级 (1-10)
                - deadline: 截止时间（可选）
                - context: 相关上下文
            callback_msg_id: 回调消息 ID

        Returns:
            委派结果
        """
        msg_id = self.network.delegate_task(
            from_agent=self.agent_id,
            to_agent=to_agent,
            task=task,
            callback_msg_id=callback_msg_id
        )

        # 保存到记忆
        self.memory.write(
            memory_type="short_term",
            content={
                "action": "delegate_task",
                "to_agent": to_agent,
                "task": task,
                "message_id": msg_id
            }
        )

        return {
            "status": "success",
            "message_id": msg_id,
            "delegated_to": to_agent
        }

    def send_message(self, to_agent: str, content: Dict[str, Any],
                     msg_type: str = "task",
                     priority: int = 5,
                     expect_response: bool = False) -> Dict[str, Any]:
        """发送消息给其他 Agent

        Args:
            to_agent: 接收方 Agent ID
            content: 消息内容
            msg_type: 消息类型 (task/response/broadcast/handover)
            priority: 优先级 (1-10, 1 最高)
            expect_response: 是否期待响应

        Returns:
            发送结果
        """
        msg_type_map = {
            "task": MessageType.TASK,
            "response": MessageType.RESPONSE,
            "broadcast": MessageType.BROADCAST,
            "handover": MessageType.HANDOVER
        }

        msg_id = self.network.send(
            from_agent=self.agent_id,
            to_agent=to_agent,
            content=content,
            msg_type=msg_type_map.get(msg_type, MessageType.TASK),
            priority=priority,
            expect_response=expect_response
        )

        return {
            "status": "success",
            "message_id": msg_id,
            "sent_to": to_agent
        }

    def check_messages(self, limit: int = 10,
                       msg_type: Optional[str] = None) -> Dict[str, Any]:
        """检查收到的消息

        Args:
            limit: 最大返回数量
            msg_type: 消息类型过滤

        Returns:
            消息列表
        """
        msg_type_map = {
            "task": MessageType.TASK,
            "response": MessageType.RESPONSE,
            "broadcast": MessageType.BROADCAST,
            "handover": MessageType.HANDOVER
        }

        messages = self.network.receive(
            agent_id=self.agent_id,
            limit=limit,
            msg_type=msg_type_map.get(msg_type) if msg_type else None
        )

        return {
            "status": "success",
            "message_count": len(messages),
            "messages": [m.to_dict() for m in messages]
        }

    def process_message(self, message_id: str, success: bool = True,
                        error: Optional[str] = None) -> Dict[str, Any]:
        """处理消息

        Args:
            message_id: 消息 ID
            success: 是否成功处理
            error: 错误信息

        Returns:
            处理结果
        """
        result = self.network.mark_message_processed(
            message_id=message_id,
            agent_id=self.agent_id,
            success=success,
            error=error
        )

        return {
            "status": "success" if result else "failed",
            "message_id": message_id,
            "processed": result
        }

    def broadcast_message(self, content: Dict[str, Any],
                          exclude_agents: Optional[List[str]] = None) -> Dict[str, Any]:
        """广播消息给所有 Agent

        Args:
            content: 消息内容
            exclude_agents: 排除的 Agent ID 列表

        Returns:
            广播结果
        """
        msg_ids = self.network.broadcast(
            from_agent=self.agent_id,
            content=content,
            exclude_agents=exclude_agents
        )

        return {
            "status": "success",
            "broadcast_count": len(msg_ids),
            "message_ids": msg_ids
        }

    def get_network_stats(self) -> Dict[str, Any]:
        """获取 Agent 网络统计信息"""
        return self.network.get_network_stats()

    def find_specialist(self, task_type: str) -> Dict[str, Any]:
        """查找专业 Agent

        Args:
            task_type: 任务类型 (coding/security/testing/writing/research/planning)

        Returns:
            匹配的 Agent 信息
        """
        specialist_id = self.network.find_specialist(task_type)

        if specialist_id:
            agent_info = self.network.get_agent(specialist_id)
            return {
                "status": "success",
                "found": True,
                "agent_id": specialist_id,
                "agent_info": agent_info
            }

        return {
            "status": "success",
            "found": False,
            "message": f"No specialist found for task type: {task_type}"
        }

    def list_available_agents(self, only_active: bool = True) -> Dict[str, Any]:
        """列出可用的 Agent

        Args:
            only_active: 只列出活跃 Agent

        Returns:
            Agent 列表
        """
        agents = self.network.list_agents(
            status="active" if only_active else None
        )

        return {
            "status": "success",
            "agent_count": len(agents),
            "agents": agents
        }

    def create_handover(self, to_agent: str, handover_data: Dict[str, Any]) -> Dict[str, Any]:
        """创建交接给其他 Agent

        Args:
            to_agent: 接收方 Agent ID
            handover_data: 交接数据，包含：
                - task_summary: 任务摘要
                - context: 上下文
                - next_steps: 下一步行动
                - notes: 备注

        Returns:
            交接结果
        """
        msg_id = self.network.create_handover(
            from_agent=self.agent_id,
            to_agent=to_agent,
            handover_data=handover_data
        )

        return {
            "status": "success",
            "message_id": msg_id,
            "handed_over_to": to_agent
        }
