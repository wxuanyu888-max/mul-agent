"""Route Handlers"""

from typing import Any, Dict

from mul_agent.tools.bash_executor import BashExecutor
from mul_agent.tools.mcp_tools import GrepTool
from mul_agent.memory.memory import Memory


class BaseHandler:
    """基础处理器"""

    def __init__(self, config_manager):
        self.config_manager = config_manager


class ResponseHandler(BaseHandler):
    """直接响应处理器 - 用于LLM直接返回响应的情况"""

    def handle(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """直接返回响应"""
        message = params.get("message", "")
        return {
            "message": message,
            "type": "direct_response"
        }


class CreateUserHandler(BaseHandler):
    """创建新Agent处理器"""

    def handle(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """创建新Agent"""
        agent_id = params.get("agent_id")
        name = params.get("name", agent_id)
        role_type = params.get("role_type", "worker")
        personality = params.get("personality", "Helpful assistant")

        if not agent_id:
            # Generate agent_id if not provided
            import uuid
            agent_id = f"agent_{uuid.uuid4().hex[:8]}"

        # Create config for new agent
        config = {
            "agent_id": agent_id,
            "name": name,
            "role_type": role_type,
            "personality": personality
        }

        # Actually create the agent using config_manager
        try:
            # Get the config manager from the handler
            from mul_agent.brain.brain import Brain

            # Use core_brain's config_manager to create the agent
            # We need to get the config_manager from somewhere - use a workaround
            # For now, we'll create configs directly

            # Create all required config files
            agent_configs = self._generate_agent_configs(agent_id, config)

            # Save each config
            for config_type, data in agent_configs.items():
                self.config_manager.save(agent_id, config_type, data)

            return {
                "agent_id": agent_id,
                "name": name,
                "role_type": role_type,
                "status": "created",
                "message": f"Agent {agent_id} created successfully!"
            }
        except Exception as e:
            return {
                "agent_id": agent_id,
                "name": name,
                "role_type": role_type,
                "status": "error",
                "message": f"Failed to create agent: {str(e)}"
            }

    def _generate_agent_configs(self, agent_id: str, config: Dict) -> Dict:
        """Generate default configs for new agent"""
        return {
            "soul": {
                "version": "1.0",
                "name": agent_id,
                "description": f"Agent created by core_brain",
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
                        "allowed_commands": ["ls", "pwd", "echo", "cat", "grep", "find", "head", "tail", "wc"],
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


class BashHandler(BaseHandler):
    """Bash命令执行处理器"""

    def handle(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """执行bash命令"""
        command = params.get("command", "")
        timeout = params.get("timeout", 30)
        cwd = params.get("cwd")

        if not command:
            return {
                "status": "error",
                "error_code": 1004,
                "message": "No command provided"
            }

        executor = BashExecutor(timeout=timeout, cwd=cwd)

        # Get allowed commands from config
        agent_config = self.config_manager.load("core_brain", "user")
        allowed = agent_config.get("tools", {}).get("bash", {}).get("allowed_commands", ["*"])
        forbidden = agent_config.get("tools", {}).get("bash", {}).get("forbidden_commands", [])

        # Check if command is allowed
        if not executor.is_safe(command, allowed, forbidden):
            return {
                "status": "error",
                "error_code": 1003,
                "message": f"Command not allowed: {command}"
            }

        result = executor.execute(command)

        return {
            "stdout": result.get("stdout", ""),
            "stderr": result.get("stderr", ""),
            "exit_code": result.get("exit_code", -1),
            "duration": result.get("duration", 0)
        }


class HeartHandler(BaseHandler):
    """自省/进化处理器"""

    def handle(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """触发自省和进化"""
        trigger = params.get("trigger", "manual")
        focus = params.get("focus", "all")

        # Load configurations
        soul = self.config_manager.load("core_brain", "soul")
        user = self.config_manager.load("core_brain", "user")
        skill = self.config_manager.load("core_brain", "skill")

        # Get LLM to analyze
        from mul_agent.brain.llm import LLMClient
        llm = LLMClient({})

        current_state = {
            "role": user.get("role", {}).get("title", "未知"),
            "skills_count": len(skill.get("skills", [])),
            "soul_version": soul.get("version"),
            "can_modify_self": soul.get("evolution_rules", {}).get("can_modify_self", False)
        }

        suggestions = []
        analysis_text = ""
        evolutions_applied = []

        # 如果允许自我修改，获取进化建议并执行
        if current_state["can_modify_self"] and llm.is_available():
            prompt = f"""你是一个AI系统的自我进化分析器。请分析当前状态并提出具体的改进方案。

当前状态:
- 角色: {current_state['role']}
- 技能数: {current_state['skills_count']}
- 灵魂版本: {current_state['soul_version']}
- 可自我修改: {current_state['can_modify_self']}

请分析并以JSON格式返回具体的修改方案。如果不需要修改则返回空的suggestions:
{{"suggestions": [
  {{"type": "soul/user/skill/memory", "field": "具体字段", "old_value": "旧值", "new_value": "新值", "reason": "修改原因"}}
], "analysis": "简短分析"}}
"""

            result = llm.chat(prompt)
            content = result.get("content", "")
            import re, json
            match = re.search(r'\{.*\}', content, re.DOTALL)
            if match:
                try:
                    data = json.loads(match.group())
                    suggestions = data.get("suggestions", [])
                    analysis_text = data.get("analysis", "")

                    # 执行进化 - 实际保存配置
                    for suggestion in suggestions:
                        suggestion_type = suggestion.get("type", "")
                        field = suggestion.get("field", "")
                        new_value = suggestion.get("new_value", "")

                        if suggestion_type == "soul" and field:
                            # 更新soul配置
                            keys = field.split(".")
                            current = soul
                            for k in keys[:-1]:
                                current = current.get(k, {})
                            current[keys[-1]] = new_value
                            self.config_manager.save("core_brain", "soul", soul)
                            evolutions_applied.append(f"更新soul.{field} = {new_value}")

                        elif suggestion_type == "user" and field:
                            # 更新user配置
                            keys = field.split(".")
                            current = user
                            for k in keys[:-1]:
                                current = current.get(k, {})
                            current[keys[-1]] = new_value
                            self.config_manager.save("core_brain", "user", user)
                            evolutions_applied.append(f"更新user.{field} = {new_value}")

                except Exception as e:
                    analysis_text = f"解析出错: {str(e)}"

        return {
            "analysis": {
                "trigger": trigger,
                "focus": focus,
                "current_state": current_state,
                "issues_found": suggestions,
                "analysis": analysis_text
            },
            "can_evolve": current_state["can_modify_self"],
            "evolutions_applied": evolutions_applied,
            "status": "success"
        }


class MemoryHandler(BaseHandler):
    """记忆管理处理器"""

    def handle(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """管理记忆"""
        action = params.get("action", "read")
        memory_type = params.get("memory_type", "long_term")
        agent_id = params.get("agent_id", "core_brain")
        content = params.get("content", {})

        # Initialize memory
        memory_config = self.config_manager.load(agent_id, "memory")
        memory = Memory(agent_id=agent_id, config=memory_config)

        if action == "write":
            memory_id = memory.write(memory_type, content)
            return {
                "action": "write",
                "memory_id": memory_id,
                "status": "success"
            }

        elif action == "read":
            memory_id = params.get("memory_id")
            result = memory.read(memory_type, memory_id)
            return {
                "action": "read",
                "memory": result,
                "status": "success"
            }

        elif action == "list":
            memories = memory.list_memories(memory_type)
            return {
                "action": "list",
                "count": len(memories),
                "memories": memories,
                "status": "success"
            }

        elif action == "search":
            query = params.get("query", "")
            results = memory.search(query)
            return {
                "action": "search",
                "query": query,
                "results": results,
                "status": "success"
            }

        else:
            return {
                "status": "error",
                "error_code": 1005,
                "message": f"Unknown action: {action}"
            }


class ChatHandler(BaseHandler):
    """Chat对话处理器 - 与指定Agent对话"""

    # 内存中的对话历史
    conversations: dict = {}

    def handle(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """处理对话请求"""
        action = params.get("action", "send")  # send / switch / list / clear
        agent_id = params.get("agent_id", "core_brain")
        message = params.get("message", "")
        conversation_id = params.get("conversation_id")

        if action == "send":
            return self._handle_send(agent_id, message, conversation_id)
        elif action == "switch":
            return self._handle_switch(agent_id, conversation_id)
        elif action == "list":
            return self._handle_list(agent_id)
        elif action == "clear":
            return self._handle_clear(conversation_id)
        else:
            return {
                "status": "error",
                "error_code": 2001,
                "message": f"Unknown action: {action}"
            }

    def _handle_send(self, agent_id: str, message: str, conversation_id: str = None) -> Dict[str, Any]:
        """发送消息给指定Agent"""
        if not conversation_id:
            conversation_id = f"{agent_id}_001"

        if conversation_id not in self.conversations:
            self.conversations[conversation_id] = []

        # 获取Agent配置
        try:
            agent_config = self.config_manager.load(agent_id, "user")
            soul_config = self.config_manager.load(agent_id, "soul")
        except Exception as e:
            return {
                "status": "error",
                "error_code": 2002,
                "message": f"Agent not found: {agent_id}",
                "details": str(e)
            }

        personality = soul_config.get("core_traits", {}).get("personality", "Helpful assistant")
        role_title = agent_config.get("role", {}).get("title", "Assistant")
        system_prompt = f"You are {role_title}. Your personality: {personality}"

        self.conversations[conversation_id].append({
            "role": "user",
            "content": message
        })

        response = self._generate_response(
            agent_id=agent_id,
            message=message,
            history=self.conversations[conversation_id],
            system_prompt=system_prompt
        )

        self.conversations[conversation_id].append({
            "role": "assistant",
            "content": response["content"]
        })

        return {
            "status": "success",
            "action": "send",
            "conversation_id": conversation_id,
            "agent_id": agent_id,
            "response": response["content"],
            "history_count": len(self.conversations[conversation_id])
        }

    def _handle_switch(self, agent_id: str, conversation_id: str = None) -> Dict[str, Any]:
        """切换到另一个Agent"""
        try:
            agent_config = self.config_manager.load(agent_id, "user")
        except Exception:
            return {
                "status": "error",
                "error_code": 2002,
                "message": f"Agent not found: {agent_id}"
            }

        new_conversation_id = f"{agent_id}_001"
        if new_conversation_id not in self.conversations:
            self.conversations[new_conversation_id] = []

        return {
            "status": "success",
            "action": "switch",
            "agent_id": agent_id,
            "conversation_id": new_conversation_id,
            "role": agent_config.get("role", {}).get("title"),
            "message": f"已切换到 Agent: {agent_id}"
        }

    def _handle_list(self, agent_id: str = None) -> Dict[str, Any]:
        """列出可用Agent或会话"""
        if agent_id:
            convs = [
                {"conversation_id": k, "messages": len(v)}
                for k, v in self.conversations.items()
                if k.startswith(agent_id)
            ]
            return {
                "status": "success",
                "agent_id": agent_id,
                "conversations": convs
            }
        else:
            agents = self.config_manager.list_agents()
            return {
                "status": "success",
                "available_agents": agents,
                "active_conversations": list(self.conversations.keys())
            }

    def _handle_clear(self, conversation_id: str = None) -> Dict[str, Any]:
        """清除对话历史"""
        if conversation_id:
            if conversation_id in self.conversations:
                del self.conversations[conversation_id]
                return {
                    "status": "success",
                    "message": f"Conversation {conversation_id} cleared"
                }
            return {
                "status": "error",
                "error_code": 2003,
                "message": f"Conversation not found: {conversation_id}"
            }
        else:
            self.conversations.clear()
            return {
                "status": "success",
                "message": "All conversations cleared"
            }

    def _generate_response(self, agent_id: str, message: str, history: list, system_prompt: str) -> Dict[str, Any]:
        """生成响应"""
        # 检查是否有LLM可用
        from mul_agent.brain.llm import LLMClient
        llm = LLMClient()

        if llm.is_available():
            response = llm.chat(
                message=message,
                system_prompt=system_prompt,
                history=history[:-1]
            )
            return {
                "content": response.get("content", "..."),
                "source": "llm"
            }

        # 简化版：基于关键词生成响应
        message_lower = message.lower()

        if "coder" in agent_id.lower() or "developer" in agent_id.lower():
            return self._coder_response(message_lower)
        elif "writer" in agent_id.lower():
            return self._writer_response(message_lower)
        else:
            return self._default_response(message_lower)

    def _coder_response(self, message: str) -> Dict[str, Any]:
        """Coder Agent 响应风格"""
        if "hello" in message or "hi" in message or "你好" in message:
            content = "你好！我是你的编码助手。有什么编程问题我可以帮你解答的吗？"
        elif "write" in message or "code" in message or "写" in message:
            content = "我可以帮你编写代码。请告诉我你需要什么功能的代码？"
        elif "bug" in message or "error" in message or "错误" in message:
            content = "遇到bug了吗？请分享错误信息，我可以帮你调试。"
        else:
            content = "明白了。让我帮你分析一下这个问题。"
        return {"content": content, "source": "rule"}

    def _writer_response(self, message: str) -> Dict[str, Any]:
        """Writer Agent 响应风格"""
        if "hello" in message or "hi" in message or "你好" in message:
            content = "你好！我是你的写作助手。有什么文章或内容需要我帮你创作吗？"
        elif "write" in message or "文章" in message:
            content = "好的，请告诉我你想要什么主题的文章？"
        else:
            content = "我明白了。让我帮你继续这个创作。"
        return {"content": content, "source": "rule"}

    def _default_response(self, message: str) -> Dict[str, Any]:
        """默认响应"""
        import random
        if "hello" in message or "hi" in message or "你好" in message:
            responses = [
                "你好！有什么我可以帮你的吗？",
                "你好！我是你的AI助手，很高兴为你服务。",
                "你好！请问有什么需要？"
            ]
            content = random.choice(responses)
        elif "help" in message or "帮助" in message:
            content = "我可以帮你完成各种任务，比如编写代码、回答问题、分析数据等。请告诉我你的需求。"
        elif "who" in message and "you" in message:
            content = "我是一个AI Agent，可以根据你的需求扮演不同的角色来帮助你。"
        else:
            content = "我明白了。请告诉我更多细节，这样我可以更好地帮助你。"
        return {"content": content, "source": "rule"}
