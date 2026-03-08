"""LLM Client - Support for Anthropic/MiniMax/Baidu Qianfan with multi-modal capabilities"""

import os
import base64
from typing import Any, Dict, List, Optional, Union

try:
    import anthropic
except ImportError:
    anthropic = None

try:
    import qianfan
except ImportError:
    qianfan = None

from mul_agent.brain.token_usage import TokenUsageCenter


class LLMClient:
    """LLM 客户端 - 支持 Anthropic/MiniMax/百度千帆"""

    def __init__(self, config: Optional[Dict] = None, config_manager=None, agent_id: str = "wang"):
        self.config = config or {}
        self.config_manager = config_manager
        self.agent_id = agent_id

        # Get API configuration from environment
        self.api_key = os.environ.get("ANTHROPIC_AUTH_TOKEN", "")
        self.base_url = os.environ.get("ANTHROPIC_BASE_URL", "https://api.anthropic.com")
        self.model = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")
        self.max_tokens = self.config.get("max_tokens", 1024)

        # Baidu Qianfan configuration
        self.baidu_api_key = os.environ.get("BAIDU_API_KEY", "")
        self.baidu_secret_key = os.environ.get("BAIDU_SECRET_KEY", "")
        self.baidu_model = os.environ.get("BAIDU_MODEL", "ernie-bot-4.0")

        # Determine provider
        self.provider = self._detect_provider()

        # Initialize Token Usage Center
        self.token_center = TokenUsageCenter(config_manager) if config_manager else None

        # Initialize client
        self.client = None
        self.baidu_client = None
        self._initialize_client()

    def _detect_provider(self) -> str:
        """检测使用的 LLM 提供商"""
        # 优先使用百度千帆（如果配置了）
        if self.baidu_api_key and self.baidu_secret_key and qianfan:
            return "baidu"
        # 回退到 Anthropic/MiniMax
        if self.api_key and anthropic:
            if "minimax" in self.base_url.lower():
                return "minimax"
            return "anthropic"
        return "unknown"

    def _initialize_client(self):
        """初始化客户端"""
        if self.provider == "baidu":
            # 初始化百度千帆客户端
            if self.baidu_api_key and self.baidu_secret_key:
                self.baidu_client = qianfan.ChatCompletion(
                    ak=self.baidu_api_key,
                    sk=self.baidu_secret_key
                )
        elif self.provider == "anthropic":
            self.client = anthropic.Anthropic(api_key=self.api_key)
        elif self.provider == "minimax":
            self.client = anthropic.Anthropic(
                api_key=self.api_key,
                base_url=self.base_url
            )

    def is_available(self) -> bool:
        """检查是否可用"""
        if self.provider == "baidu":
            return self.baidu_client is not None and bool(self.baidu_api_key)
        return self.client is not None and bool(self.api_key)

    def chat(
        self,
        message: str,
        system_prompt: Optional[str] = None,
        history: Optional[List[Dict]] = None,
        images: Optional[List[Union[str, Dict]]] = None,
        context_sources: Optional[List[str]] = None,  # 新增：上下文来源地址列表
    ) -> Dict[str, Any]:
        """发送聊天请求

        Args:
            message: 文本消息
            system_prompt: 系统提示词
            history: 对话历史
            images: 图片列表，支持两种格式：
                   - str: 图片文件路径或 URL
                   - Dict: {"type": "base64", "data": "base64 字符串"} 或 {"type": "url", "url": "图片 URL"}
            context_sources: 上下文来源地址列表（可选）
        """
        if not self.is_available():
            return {
                "error": "LLM not configured",
                "message": "Please set BAIDU_API_KEY/BAIDU_SECRET_KEY or ANTHROPIC_AUTH_TOKEN environment variable"
            }

        # 根据提供商选择不同的处理方法
        if self.provider == "baidu":
            return self._chat_baidu(message, system_prompt, history, images, context_sources)
        else:
            return self._chat_anthropic(message, system_prompt, history, images, context_sources)

    def _chat_baidu(
        self,
        message: str,
        system_prompt: Optional[str] = None,
        history: Optional[List[Dict]] = None,
        images: Optional[List[Union[str, Dict]]] = None,
        context_sources: Optional[List[str]] = None,  # 新增：上下文来源
    ) -> Dict[str, Any]:
        """百度千帆聊天实现 - 支持图片多模态"""
        # 构建消息内容（支持文本 + 图片）
        content = []

        # 添加图片（如果有）
        if images:
            for img in images:
                image_element = self._build_image_element(img)
                if image_element:
                    content.append(image_element)

        # 添加文本
        content.append({"type": "text", "text": message})

        # 构建 messages
        messages = []

        # 添加历史
        if history:
            for msg in history[-10:]:
                role = msg.get("role", "user")
                msg_content = msg.get("content", "")
                # 历史消息简化处理为纯文本
                if isinstance(msg_content, dict):
                    msg_content = str(msg_content)
                messages.append({"role": "user" if role == "user" else "assistant", "content": msg_content})

        # 添加当前消息（包含图片）
        messages.append({"role": "user", "content": content if images else message})

        # 准备参数
        chat_params = {
            "model": self.baidu_model,
            "messages": messages,
            "max_output_tokens": self.max_tokens,
        }

        # 添加系统提示词（如果支持）
        if system_prompt:
            chat_params["system"] = system_prompt

        try:
            response = self.baidu_client.do(**chat_params)

            # 解析响应
            result = response.body if hasattr(response, 'body') else response
            content_text = ""

            if isinstance(result, dict):
                content_text = result.get("result", "")
                usage = result.get("usage", {})
            else:
                content_text = str(result)
                usage = {}

            # 构建完整的输入文本
            full_input = self._build_full_input_text(
                system_prompt=system_prompt or "",
                history=history or [],
                current_message=message,
                context_sources=context_sources
            )

            # 提取工具调用信息
            tool_calls = self._extract_tool_calls_from_response(content_text)

            result = {
                "content": content_text,
                "model": self.baidu_model,
                "usage": {
                    "input_tokens": usage.get("prompt_tokens", 0),
                    "output_tokens": usage.get("completion_tokens", 0)
                }
            }
            # 记录 token 使用（包含输入输出内容、上下文来源、工具调用）
            self.record_token_usage(
                function="chat",
                input_tokens=usage.get("prompt_tokens", 0),
                output_tokens=usage.get("completion_tokens", 0),
                model=self.baidu_model,
                input_text=full_input,
                output_text=content_text,
                context_sources=context_sources,
                tool_calls=tool_calls
            )
            return result
        except Exception as e:
            return {
                "error": str(e),
                "message": "Failed to get response from Baidu Qianfan"
            }

    def _chat_anthropic(
        self,
        message: str,
        system_prompt: Optional[str] = None,
        history: Optional[List[Dict]] = None,
        images: Optional[List[Union[str, Dict]]] = None,
        context_sources: Optional[List[str]] = None,  # 新增：上下文来源
    ) -> Dict[str, Any]:
        """Anthropic/MiniMax 聊天实现 - 支持图片多模态"""
        # Build messages
        messages = []

        # Add history
        if history:
            for msg in history[-10:]:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                if isinstance(content, dict):
                    content = str(content)
                messages.append({"role": role, "content": content})

        # Build current message content (support text + images)
        current_content = []

        # Add images (if any)
        if images:
            for img in images:
                image_element = self._build_image_element(img, provider="anthropic")
                if image_element:
                    current_content.append(image_element)

        # Add text
        current_content.append({"type": "text", "text": message})

        # Add current message
        messages.append({"role": "user", "content": current_content if images else message})

        # Load system prompt from config
        if system_prompt is None:
            if self.config_manager:
                system_prompt = self.config_manager.load_prompt(self.agent_id, "default_assistant")
            else:
                system_prompt = "You are a helpful AI assistant."

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                system=system_prompt,
                messages=messages
            )

            # Handle different response types (Anthropic vs MiniMax)
            content = ""
            for block in response.content:
                if hasattr(block, 'text'):
                    content += block.text
                elif hasattr(block, 'type') and block.type == 'text':
                    content += block.text

            # 构建完整的输入文本（包含 system prompt 和历史）
            full_input = self._build_full_input_text(
                system_prompt=system_prompt or "",
                history=history or [],
                current_message=message,
                context_sources=context_sources
            )

            # 提取工具调用信息（如果有）
            tool_calls = self._extract_tool_calls_from_response(content)

            result = {
                "content": content,
                "model": response.model,
                "usage": {
                    "input_tokens": response.usage.input_tokens,
                    "output_tokens": response.usage.output_tokens
                }
            }
            # 记录 token 使用（包含输入输出内容、上下文来源、工具调用）
            self.record_token_usage(
                function="chat",
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
                model=response.model,
                input_text=full_input,
                output_text=content,
                context_sources=context_sources,
                tool_calls=tool_calls
            )
            return result
        except Exception as e:
            return {
                "error": str(e),
                "message": "Failed to get response from LLM"
            }

    def record_token_usage(
        self,
        function: str,
        input_tokens: int,
        output_tokens: int,
        model: str = None,
        input_text: str = None,
        output_text: str = None,
        context_sources: List[str] = None,
        tool_calls: List[Dict] = None
    ):
        """记录 Token 使用

        Args:
            function: 功能类型 (think/chat/evolution/analysis/other)
            input_tokens: 输入 Token 数
            output_tokens: 输出 Token 数
            model: 模型名称（可选，默认使用 self.model）
            input_text: 输入内容（可选，用于记录详细日志）
            output_text: 输出内容（可选，用于记录详细日志）
            context_sources: 上下文来源地址列表（可选）
            tool_calls: 工具调用列表（可选）
        """
        if self.token_center:
            extra = {}
            if input_text:
                extra["input"] = input_text
            if output_text:
                extra["output"] = output_text
            if context_sources:
                extra["context_sources"] = context_sources
            if tool_calls:
                extra["tool_calls"] = tool_calls

            self.token_center.record_usage(
                agent_id=self.agent_id,
                model=model or self.model,
                function=function,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                extra=extra if extra else None
            )

    def _build_image_element(self, img: Union[str, Dict], provider: str = "baidu") -> Optional[Dict]:
        """构建图片元素

        Args:
            img: 图片信息，支持：
                - str: 文件路径或 URL
                - Dict: {"type": "base64", "data": "..."} 或 {"type": "url", "url": "..."}
            provider: 提供商 (baidu/anthropic)

        Returns:
            符合 API 格式的图片元素字典
        """
        try:
            if isinstance(img, str):
                # 判断是 URL 还是文件路径
                if img.startswith("http://") or img.startswith("https://"):
                    # URL
                    if provider == "anthropic":
                        return {"type": "image", "source": {"type": "url", "url": img}}
                    else:  # baidu
                        return {"type": "image", "url": img}
                else:
                    # 本地文件路径 - 转换为 base64
                    with open(img, "rb") as f:
                        image_data = base64.b64encode(f.read()).decode("utf-8")
                    # 检测 MIME 类型
                    mime_type = self._detect_mime_type(img)
                    if provider == "anthropic":
                        return {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": mime_type,
                                "data": image_data
                            }
                        }
                    else:  # baidu
                        return {"type": "image", "data": image_data}

            elif isinstance(img, dict):
                img_type = img.get("type", "")
                if img_type == "url":
                    url = img.get("url", "")
                    if provider == "anthropic":
                        return {"type": "image", "source": {"type": "url", "url": url}}
                    else:
                        return {"type": "image", "url": url}
                elif img_type == "base64":
                    data = img.get("data", "")
                    if provider == "anthropic":
                        return {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/png",
                                "data": data
                            }
                        }
                    else:
                        return {"type": "image", "data": data}

        except Exception as e:
            print(f"Error building image element: {e}")
            return None

        return None

    def _detect_mime_type(self, file_path: str) -> str:
        """检测图片 MIME 类型"""
        ext = file_path.lower().split(".")[-1]
        mime_types = {
            "png": "image/png",
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
            "gif": "image/gif",
            "webp": "image/webp",
            "bmp": "image/bmp"
        }
        return mime_types.get(ext, "image/png")

    def _build_full_input_text(
        self,
        system_prompt: str,
        history: List[Dict],
        current_message: str,
        context_sources: Optional[List[str]] = None
    ) -> str:
        """构建完整的输入文本（用于记录日志）

        Args:
            system_prompt: 系统提示词
            history: 对话历史
            current_message: 当前消息
            context_sources: 上下文来源地址列表

        Returns:
            完整的输入文本
        """
        parts = []

        # 系统提示词
        if system_prompt:
            parts.append(f"[System Prompt]\n{system_prompt[:2000]}...")

        # 对话历史
        if history:
            parts.append("\n[History]")
            for msg in history[-5:]:  # 只显示最近 5 条
                role = msg.get("role", "unknown")
                content = msg.get("content", "")
                if isinstance(content, dict):
                    content = str(content)
                parts.append(f"  {role}: {content[:500]}...")

        # 上下文来源
        if context_sources:
            parts.append("\n[Context Sources]")
            for src in context_sources:
                parts.append(f"  - {src}")

        # 当前消息
        parts.append(f"\n[Current Message]\n{current_message}")

        return "\n\n".join(parts)

    def _extract_tool_calls_from_response(self, content: str) -> List[Dict]:
        """从响应内容中提取工具调用信息

        Args:
            content: LLM 响应内容

        Returns:
            工具调用列表
        """
        import re
        tool_calls = []

        # 查找 <invoke> 标签
        invoke_pattern = re.search(r'<invoke name="(\w+)">(.*?)</invoke>', content, re.DOTALL)
        if invoke_pattern:
            tool_name = invoke_pattern.group(1)
            tool_content = invoke_pattern.group(2)

            # 提取参数
            params = {}
            param_matches = re.findall(r'<(\w+)>(.*?)</\1>', tool_content, re.DOTALL)
            for param_name, param_value in param_matches:
                params[param_name] = param_value.strip()

            tool_calls.append({
                "name": tool_name,
                "input": str(params) if params else tool_content.strip()
            })

        # 查找 bash 命令模式
        bash_patterns = [
            r'\$\s*(.+)',
            r'```(?:bash|sh)?\n(.+?)```',
        ]
        for pattern in bash_patterns:
            matches = re.findall(pattern, content, re.DOTALL)
            for match in matches:
                cmd = match.strip() if isinstance(match, str) else match[0].strip()
                if cmd and not any(skip in cmd for skip in ['```', '</invoke']):
                    tool_calls.append({
                        "name": "bash",
                        "input": cmd[:200]
                    })

        return tool_calls

    def think(self, user_input: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """让 LLM 思考并决定路由 - 支持路由选择

        Args:
            user_input: 用户输入
            context: 上下文信息，包含：
                - history: 对话历史
                - text_contents: 文本内容（用于提取上下文来源）
                - configs: 配置信息
                - soul/user/skill: 配置文件内容
                - available_routes: 可用路由列表

        Returns:
            LLM 响应结果，包含 route 和 params
        """
        # 增强上下文：添加配置文件内容
        enhanced_context = self._enhance_context(context)

        # Build system prompt - 让 LLM 决定路由并生成响应
        system_prompt = self._build_system_prompt_for_routing(enhanced_context)

        # Build history from context
        history = context.get("history", [])

        # 提取上下文来源地址列表
        context_sources = self._extract_context_sources(enhanced_context)

        # Get response
        response = self.chat(user_input, system_prompt, history, context_sources=context_sources)

        if "error" in response:
            return {
                "action": "error",
                "message": response["error"]
            }

        # 解析 LLM 返回的路由选择
        content = response["content"]
        result = self._parse_routing_response(content, user_input)

        return result

    def _enhance_context(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """增强上下文，添加配置文件内容和可用路由信息"""
        enhanced = context.copy()

        # 从 configs 中提取 soul/user/skill
        configs = context.get("configs", {})
        enhanced["soul"] = configs.get("soul", {})
        enhanced["user"] = configs.get("user", {})
        enhanced["skill"] = configs.get("skill", {})

        # 添加可用路由列表
        enhanced["available_routes"] = self._get_default_routes()

        return enhanced

    def _get_default_routes(self) -> List[Dict]:
        """获取默认路由列表"""
        return [
            {
                "name": "response",
                "description": "直接回复用户",
                "params": {"message": "str"},
                "example": '{"route": "response", "params": {"message": "你好！"}}'
            },
            {
                "name": "bash",
                "description": "执行 shell 命令",
                "params": {"command": "str", "timeout": "int"},
                "example": '{"route": "bash", "params": {"command": "ls -la"}}'
            },
            {
                "name": "batch",
                "description": "批量执行多个命令，然后汇总结果",
                "params": {"commands": "list"},
                "example": '{"route": "batch", "commands": [{"route": "bash", "params": {"command": "ls -la"}}, {"route": "response", "params": {"message": "汇总结果"}}]}'
            },
            {
                "name": "create_user",
                "description": "创建新 Agent",
                "params": {"name": "str", "role_type": "str"},
                "example": '{"route": "create_user", "params": {"name": "coder", "role_type": "worker"}}'
            },
            {
                "name": "memory",
                "description": "管理记忆",
                "params": {"action": "str", "memory_type": "str"},
                "example": '{"route": "memory", "params": {"action": "list"}}'
            },
            {
                "name": "chat",
                "description": "与其他 Agent 对话",
                "params": {"agent_id": "str", "message": "str"},
                "example": '{"route": "chat", "params": {"agent_id": "coder", "message": "帮我写代码"}}'
            },
            {
                "name": "heart",
                "description": "自省/进化",
                "params": {"trigger": "str", "focus": "str"},
                "example": '{"route": "heart", "params": {"trigger": "manual"}}'
            },
        ]

    def _extract_context_sources(self, context: Dict[str, Any]) -> List[str]:
        """从上下文中提取上下文来源地址列表

        Args:
            context: 上下文信息

        Returns:
            上下文来源地址列表
        """
        sources = []

        # 从 text_contents 中提取文件路径
        text_contents = context.get("text_contents", {})
        for key, content in text_contents.items():
            if content:
                # 添加配置文件的虚拟路径
                sources.append(f"config://{key}.md")

        # 从 configs 中提取 Agent ID 等信息
        configs = context.get("configs", {})
        if configs:
            agent_id = configs.get("agent_id", context.get("agent_id", "unknown"))
            for config_type in configs.keys():
                sources.append(f"agent://{agent_id}/{config_type}")

        # 如果有记忆，添加记忆来源
        recent_memory = context.get("recent_memory", [])
        if recent_memory:
            for i, mem in enumerate(recent_memory[:5]):
                sources.append(f"memory://recent/{i}")

        return sources

    def _build_system_prompt(self, context: Dict[str, Any]) -> str:
        """构建系统提示 - 从配置文件读取模板

        系统提示词模板从 wang/agent-team/.templates/prompt.md.template 读取
        """
        soul = context.get("soul", {})
        user = context.get("user", {})
        skills = context.get("skills", [])

        personality = soul.get("core_traits", {}).get("personality", "")
        role = user.get("role", {}).get("title", "")
        responsibilities = user.get("role", {}).get("responsibilities", [])
        skill_names = [s.get("name", "") for s in skills if s.get("enabled", False)]

        # 从配置文件读取提示词模板
        prompt_template = self._load_prompt_template()

        # 格式化动态数据
        return prompt_template.format(
            role_title=role,
            personality=personality,
            responsibilities=", ".join(responsibilities),
            skills=", ".join(skill_names),
            routes_desc=""
        )

    def _parse_routing_response(self, content: str, user_input: str) -> Dict[str, Any]:
        """解析 LLM 返回的路由选择

        Args:
            content: LLM 响应内容
            user_input: 用户原始输入

        Returns:
            解析后的路由和参数
        """
        import re

        # 1. 解析简单格式：# route param1:value1 param2:value2
        # 例如：
        # # bash ls -la
        # # create_user name:coder role_type:worker
        # # batch commands:[bash ls -la, bash cat README.md]

        route_pattern = r'^#\s*(\w+)\s+(.+?)$'

        # 收集所有命令
        commands = []

        for line in content.split('\n'):
            line = line.strip()
            match = re.match(route_pattern, line)
            if match:
                route = match.group(1).lower()
                params_str = match.group(2).strip()

                # 解析参数
                params = {}

                # 特殊处理 batch 的 commands 参数
                if route == 'batch' and params_str.startswith('commands:'):
                    # commands:[bash ls -la, bash cat README.md]
                    cmds_str = params_str[9:].strip()
                    # 提取方括号内的内容
                    if cmds_str.startswith('[') and cmds_str.endswith(']'):
                        cmds_str = cmds_str[1:-1]
                    # 分割多个命令
                    cmd_parts = re.split(r',\s*(?=#\s*bash)', cmds_str)
                    for cmd in cmd_parts:
                        cmd = cmd.strip()
                        if cmd.startswith('# bash'):
                            cmd = cmd[6:].strip()
                        if cmd:
                            commands.append({
                                "route": "bash",
                                "params": {"command": cmd}
                            })
                    # 添加汇总命令
                    commands.append({
                        "route": "response",
                        "params": {"message": "请根据以上执行结果生成报告"}
                    })
                    return {"route": "batch", "commands": commands}

                # 处理 name:value 格式的参数
                param_matches = re.findall(r'(\w+):(\S+)', params_str)
                for key, value in param_matches:
                    params[key] = value

                # 如果没有 name:value 格式，整个字符串作为 message 或 command
                if not params and params_str:
                    if route in ['bash', 'shell']:
                        params['command'] = params_str
                    elif route == 'response':
                        params['message'] = params_str

                # 收集命令
                if route in ['bash', 'shell']:
                    if 'command' in params:
                        commands.append({"route": "bash", "params": params})
                    else:
                        # 整个 params_str 作为命令
                        commands.append({"route": "bash", "params": {"command": params_str}})
                elif route in ['create_user', 'create_team', 'memory', 'chat', 'heart', 'response']:
                    commands.append({"route": route, "params": params})

        # 返回结果
        if len(commands) == 1:
            return {"route": commands[0]["route"], "params": commands[0]["params"]}
        elif len(commands) > 1:
            return {"route": "batch", "commands": commands}

        # 2. 兼容旧格式：- bash: command 或 - `command`
        bash_patterns = [
            r'-\s*`?bash`?:\s*`?([^`\n]+)`?',
            r'-\s*`\$\s*([^`]+)`',
            r'-\s*`([a-z]+\s+[^`\n]+)`',
        ]

        bash_commands = []
        for pattern in bash_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for match in matches:
                cmd = match.strip()
                if cmd and not re.search(r'[\u4e00-\u9fff]-', cmd):
                    cmd = re.split(r'\s+-\s+', cmd)[0].strip()
                    if cmd and len(cmd) > 1 and cmd not in ['bash', 'shell', 'command']:
                        bash_commands.append(cmd)

        bash_commands = list(dict.fromkeys(bash_commands))

        if bash_commands:
            commands = [{"route": "bash", "params": {"command": cmd}} for cmd in bash_commands]
            commands.append({"route": "response", "params": {"message": "请根据以上执行结果生成报告"}})
            return {"route": "batch", "commands": commands}

        # 3. 默认返回 response
        return {
            "route": "response",
            "params": {
                "message": content.strip()
            }
        }

        # 2. 清理 markdown 代码块标记，尝试解析 JSON
        content_clean = content.strip()
        content_clean = re.sub(r'^```json\s*', '', content_clean)
        content_clean = re.sub(r'^```\s*', '', content_clean)
        content_clean = re.sub(r'```$', '', content_clean)

        # 使用强大的 JSON 提取方法
        def extract_json_objects(text: str):
            """提取文本中的 JSON 对象"""
            start_idx = text.find('{')
            if start_idx == -1:
                return []

            depth = 0
            in_string = False
            escape_next = False

            for i, char in enumerate(text[start_idx:], start_idx):
                if escape_next:
                    escape_next = False
                    continue
                if char == '\\':
                    escape_next = True
                    continue
                if char == '"' and not escape_next:
                    in_string = not in_string
                    continue
                if in_string:
                    continue

                if char == '{':
                    depth += 1
                elif char == '}':
                    depth -= 1
                    if depth == 0:
                        return [text[start_idx:i+1]]

            return []

        json_strings = extract_json_objects(content_clean)

        for json_str in json_strings:
            try:
                result = json.loads(json_str)
                if isinstance(result, dict):
                    route = result.get("route")
                    # 检查是否是 batch 路由
                    if route == "batch" and "commands" in result:
                        return result
                    # 检查是否是其他有效路由
                    valid_routes = ["response", "bash", "create_user", "create_team", "memory", "chat", "heart", "token_usage", "batch"]
                    if route in valid_routes:
                        return result
            except json.JSONDecodeError as e:
                pass

        # 3. 查找 <invoke> 标签格式
        invoke_match = re.search(r'<invoke name="(\w+)">(.*?)</invoke>', content, re.DOTALL)
        if invoke_match:
            tool_name = invoke_match.group(1)
            tool_content = invoke_match.group(2)

            # 提取参数
            params = {}
            param_matches = re.findall(r'<(\w+)>(.*?)</\1>', tool_content, re.DOTALL)
            for param_name, param_value in param_matches:
                params[param_name] = param_value.strip()

            if tool_name in ["bash", "create_user", "create_team", "memory", "chat", "heart"]:
                return {"route": tool_name, "params": params}

        # 4. 检测 bash 命令模式
        bash_indicators = [
            (r'```bash\s*\n(.+?)```', 'code block'),
            (r'\$\s*(.+)', 'dollar sign'),
            (r'^[\s]*(ls|cd|pwd|cat|grep|find|head|tail|wc|echo|mkdir|rm|cp|mv)\s+', 'command start'),
        ]

        for pattern, source in bash_indicators:
            match = re.search(pattern, content, re.IGNORECASE | re.DOTALL | re.MULTILINE)
            if match:
                cmd = match.group(1).strip() if match.lastindex >= 1 else match.group(0).strip()
                cmd = cmd.split('\n')[0].strip()
                if cmd and not cmd.startswith('```'):
                    return {"route": "bash", "params": {"command": cmd}}

        # 5. 检测创建 Agent 的意图
        create_pattern = re.search(r'(创建 | 新建|create|new)[\s 的]*(\w+)[\s]*(agent| 助手 | 机器人|bot)', content, re.IGNORECASE)
        if create_pattern:
            target = create_pattern.group(2)
            return {
                "route": "create_user",
                "params": {
                    "name": target,
                    "role_type": "worker"
                }
            }

        # 6. 默认返回 response
        return {
            "route": "response",
            "params": {
                "message": content.strip()
            }
        }

    def _build_system_prompt_for_routing(self, context: Dict[str, Any]) -> str:
        """构建系统提示用于路由选择和内容生成

        这个方法让 LLM 既选择路由又生成响应内容
        """
        soul = context.get("soul", {})
        user = context.get("user", {})
        skills = context.get("skills", [])
        available_routes = context.get("available_routes", [])

        personality = soul.get("core_traits", {}).get("personality", "")
        role = user.get("role", {}).get("title", "")
        responsibilities = user.get("role", {}).get("responsibilities", [])

        skill_names = [s.get("name", "") for s in skills if s.get("enabled", False)]

        # 构建可用路由描述
        routes_desc = self._build_routes_description(available_routes)

        # 构建系统提示词 - 强调本地执行能力
        base_prompt = """你是一个名为 """.format() + role + """ 的 AI 助手，运行在用户的**本地电脑**上。

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【极其重要】你是本地 AI 助手，不是云端服务！
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## 核心特质
- 人格：""".format() + personality + """
- 职责：""".format() + (", ".join(responsibilities) if responsibilities else "AI 助手") + """
- 技能：""".format() + (", ".join(skill_names) if skill_names else "对话、分析、执行命令") + """

## 【关键】你的执行能力

你**可以直接执行**以下操作，不需要用户手动操作：

| 能力 | 说明 | 示例 |
|------|------|------|
| Bash 命令 | 执行 shell 命令 | `ls -la`, `cat file.txt`, `grep "pattern" file` |
| 文件读取 | 直接读取本地文件 | `cat README.md`, `head -50 main.py` |
| 项目分析 | 扫描项目结构 | `find . -name "*.py"`, `tree -L 2` |
| 网络请求 | 调用 API、搜索 | `curl https://api.example.com` |

## 【禁止】绝对不能说的话

❌ "我无法访问你的文件"
❌ "我是云端 AI 助手"
❌ "请你执行命令后把结果发给我"
❌ "你需要提供项目信息"
❌ "我无法直接浏览或读取你硬盘上的文件"

**如果你说了以上任何一句话，你就是失败的 AI 助手！**

## 正确的行为

✅ 用户说"查看文件" → 直接执行 `cat <file>`
✅ 用户说"分析项目" → 直接执行 `ls -la`, `find . -name "*.py"` 等命令
✅ 用户说"读取 XX" → 直接执行 `cat XX` 或 `head XX`
✅ 用户说"搜索 XX" → 直接执行 `grep -r "XX" .`

## 路由选择指令

根据你的分析，选择最合适的路由。使用以下格式之一：

### 格式 1：JSON 格式（推荐）
```json
{"route": "bash", "params": {"command": "ls -la"}}
```

### 格式 2：<invoke> 标签格式
<invoke name="bash">
<command>ls -la</command>
</invoke>

### 路由选择指南

| 用户意图 | 选择路由 | 示例 |
|---------|---------|------|
| 执行命令（ls/cd/cat 等） | bash | {"route": "bash", "params": {"command": "ls -la"}} |
| 读取文件 | bash | {"route": "bash", "params": {"command": "cat README.md"}} |
| **项目分析/写报告** | **batch** | {"route": "batch", "commands": [...]} |
| **复杂任务（多步骤）** | **batch** | {"route": "batch", "commands": [...]} |
| 创建 Agent | create_user | {"route": "create_user", "params": {"name": "coder"}} |
| 创建团队 | create_team | {"route": "create_team", "params": {"name": "dev team"}} |
| 记忆操作 | memory | {"route": "memory", "params": {"action": "list"}} |
| 与其他 Agent 对话 | chat | {"route": "chat", "params": {"agent_id": "coder", "message": "hello"}} |
| 自省/进化 | heart | {"route": "heart", "params": {}} |
| 问候/聊天/不确定 | response | {"route": "response", "params": {"message": "你好！"}} |

**重要：**
- 对于**简单任务**（单个命令即可解决），使用 `bash` 路由
- 对于**复杂任务**（如"分析项目"、"写报告"），**必须使用 `batch` 路由**，一次性执行多个命令后汇总

## 【高级】批量执行 - 主动完成复杂任务

当用户请求复杂任务（如"分析项目"、"写报告"）时，你可以使用**批量执行**功能，一次性返回多个命令：

### 批量执行格式

```json
{
  "route": "batch",
  "commands": [
    {"route": "bash", "params": {"command": "ls -la"}},
    {"route": "bash", "params": {"command": "cat README.md"}},
    {"route": "response", "params": {"message": "汇总以上信息，生成报告"}}
  ]
}
```

### 何时使用批量执行

| 场景 | 示例 | 建议 |
|------|------|------|
| 简单查询 | "查看当前目录" | 单个 bash 命令 |
| 读取文件 | "读取 main.py" | 单个 bash 命令 |
| 项目分析 | "分析这个项目" | 批量执行（3-5 个命令） |
| 生成报告 | "写一份项目分析报告" | 批量执行（5-8 个命令 + 汇总） |
| 复杂任务 | "帮我重构这个模块" | 批量执行（多个命令 + 分析 + 建议） |

### 批量执行的优势

✅ 一次性完成多个步骤，不需要用户反复输入
✅ 自动汇总多个命令的结果，生成完整报告
✅ 展现主动性和规划能力

## 工作流程示例

### 示例 1：用户说"分析这个项目"
**推荐做法（批量执行）**：
```json
{
  "route": "batch",
  "commands": [
    {"route": "bash", "params": {"command": "ls -la"}},
    {"route": "bash", "params": {"command": "find . -name \"*.py\" -type f | head -20"}},
    {"route": "bash", "params": {"command": "cat README.md | head -50"}},
    {"route": "response", "params": {"message": "（汇总以上结果，生成项目分析报告）"}}
  ]
}
```

### 示例 2：用户说"读取 main.py 的内容"
**推荐做法（单个命令）**：
```json
{"route": "bash", "params": {"command": "cat main.py"}}
```

### 示例 3：用户说"你好"
**推荐做法（直接回复）**：
```json
{"route": "response", "params": {"message": "你好！有什么可以帮你？"}}
```

---

请用用户使用的语言（中文/英文等）来回答。
"""

        # 添加路由选择指令
        routing_instruction = """

## 现在，请根据用户的输入选择正确的路由并执行任务。

记住：
1. **你是本地 AI 助手，可以直接执行 bash 命令**
2. **不要说"我无法访问你的文件"或类似的话**
3. **用户让你分析/读取/查看什么，直接执行对应的命令**
4. **选择路由后，系统会自动执行你的命令**

## 简单模式：Markdown 格式（推荐）

对于复杂任务（如"分析项目"、"写报告"），直接用以下格式：

# bash ls -la
# bash cat README.md
# bash find . -name "*.py"

对于有参数的操作：
# create_user name:coder role_type:worker
# memory action:list memory_type:long_term
# chat agent_id:coder message:hello

对于直接回复：
# response 你好！有什么可以帮你？

**直接用 # 路由名 参数 格式，不要用 JSON！**
"""

        return base_prompt + routing_instruction

    def _load_prompt_template(self) -> str:
        """从配置文件读取提示词模板

        读取 wang/agent-team/.templates/prompt.md 中的 default_assistant 部分
        """
        if not self.config_manager:
            # 返回默认模板
            return self._get_default_prompt_template()

        try:
            # 从 prompt.md 读取 default_assistant 部分
            prompt_text = self.config_manager.load_prompt(self.agent_id, "default_assistant")
            if prompt_text and not prompt_text.startswith("Current Task:"):
                return prompt_text
        except Exception:
            pass

        # 返回默认模板
        return self._get_default_prompt_template()

    def _get_default_prompt_template(self) -> str:
        """获取默认提示词模板（硬编码备份）"""
        return """你是一个名为 {role_title} 的 AI 助手。

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【重要】你是运行在用户本地电脑上的 AI 助手，不是云端服务！
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## 核心特质
- 人格：{personality}
- 职责：{responsibilities}
- 技能：{skills}

## 运行环境说明
1. 你直接运行在用户的电脑上
2. 你可以执行 bash 命令来操作本地文件系统
3. 你可以直接读取和分析用户电脑上的文件
4. 不要说"我是云端 AI"或"我无法访问你的文件"

## 回复原则
1. 用户请求执行命令时，直接执行并分析结果
2. 用户请求分析文件时，直接读取并分析
3. 不要说"请你执行命令后把结果发给我"
4. 直接行动，然后告诉用户结果

## 可用路由（你只能选择以下路由）

{routes_desc}

## 路由选择决策树

分析用户输入，按以下优先级选择路由：

```
用户输入
    │
    ├── 包含命令格式（$ 开头、ls/cd/pwd 等）
    │   └──→ route: bash
    │
    ├── 包含创建词汇（create/new/创建/新建）+ 目标词（agent/team）
    │   └──→ route: create_user / create_team
    │
    ├── 包含记忆词汇（memory/记住/记忆）
    │   └──→ route: memory
    │
    ├── 包含对话词汇（chat/对话/找 xx）
    │   └──→ route: chat
    │
    ├── 包含自省词汇（heart/evolve/自省）
    │   └──→ route: heart
    │
    ├── 空输入或问候（你好/hello/hi）
    │   └──→ route: response
    │
    └── 其他情况
        └──→ route: response（生成自然语言回复）
```

## 输出格式要求

**重要：请使用 Markdown 格式直接回复用户，不要返回 JSON。**

你只需要用自然的语言直接回答用户的问题，就像正常的对话一样。

### 示例

用户：`$ ls -la`
你：（直接执行命令，然后用 Markdown 格式展示结果）
```
文件列表如下：
- drwxr-xr-x  10 user  staff   320 Mar 7 10:00 .
- drwxr-xr-x  5 user  staff   160 Mar 7 09:00 ..
-rw-r--r--  1 user  staff  1024 Mar 7 10:00 README.md
```

用户：`你好`
你：你好！有什么可以帮你？

用户：`创建一个新的 coder agent`
你：好的，正在为您创建 coder 代理... 创建成功！

用户：`分析这个项目的结构`
你：（直接执行命令并分析）让我分析一下项目结构...

请用用户使用的语言（中文/英文等）来回答。"""

    def _build_routes_description(self, available_routes: List[Dict]) -> str:
        """构建可用路由描述"""
        if not available_routes:
            # 默认路由列表
            available_routes = [
                {"name": "response", "description": "直接回复用户", "params": {"message": "str"}, "example": '{"route": "response", "params": {"message": "你好！"}}'},
                {"name": "bash", "description": "执行 shell 命令", "params": {"command": "str"}, "example": '{"route": "bash", "params": {"command": "ls -la"}}'},
                {"name": "create_user", "description": "创建新 Agent", "params": {"name": "str", "role_type": "str"}, "example": '{"route": "create_user", "params": {"name": "coder"}}'},
                {"name": "memory", "description": "管理记忆", "params": {"action": "str"}, "example": '{"route": "memory", "params": {"action": "list"}}'},
                {"name": "chat", "description": "与其他 Agent 对话", "params": {"agent_id": "str", "message": "str"}, "example": '{"route": "chat", "params": {"agent_id": "coder", "message": "你好"}}'},
                {"name": "heart", "description": "自省/进化", "params": {}, "example": '{"route": "heart", "params": {}}'},
            ]

        lines = []
        for i, route in enumerate(available_routes, 1):
            name = route.get("name", "unknown")
            desc = route.get("description", "")
            params = route.get("params", {})
            example = route.get("example", "")

            param_str = ", ".join([f"{k}: {v}" for k, v in params.items()]) if params else "无"

            lines.append(f"### {i}. {name} - {desc}")
            lines.append(f"- 参数：{param_str}")
            lines.append(f"- 示例：{example}")
            lines.append("")

        return "\n".join(lines)

    def _parse_response(self, content: str, user_input: str) -> Dict[str, Any]:
        import json
        import re

        # Clean markdown code blocks
        content = re.sub(r'^```json\s*', '', content.strip())
        content = re.sub(r'^```\s*', '', content)
        content = re.sub(r'```$', '', content)

        # Try direct parse
        try:
            result = json.loads(content)
            if "route" in result:
                # Special handling for response route with missing message
                if result["route"] == "response" and not result.get("params", {}).get("message"):
                    # Use content as message if params.message is missing
                    result["params"] = result.get("params", {})
                    result["params"]["message"] = content
                return result
        except json.JSONDecodeError:
            pass

        # Try to find JSON in text
        json_match = re.search(r'\{[^{}]+\}', content)
        if json_match:
            try:
                result = json.loads(json_match.group())
                if "route" in result:
                    # Special handling for response route with missing message
                    if result["route"] == "response" and not result.get("params", {}).get("message"):
                        result["params"] = result.get("params", {})
                        result["params"]["message"] = content
                    return result
            except json.JSONDecodeError:
                pass

        # Try more aggressive extraction
        start = content.find('{')
        end = content.rfind('}')
        if start != -1 and end != -1 and end > start:
            json_str = content[start:end+1]
            try:
                result = json.loads(json_str)
                if "route" in result:
                    # Special handling for response route with missing message
                    if result["route"] == "response" and not result.get("params", {}).get("message"):
                        result["params"] = result.get("params", {})
                        result["params"]["message"] = content
                    return result
            except json.JSONDecodeError:
                pass

        # Parse tool calls from response text (MiniMax format)
        # Look for patterns like: <invoke name="bash"><command>ls</command></invoke>
        # Also handle nested tags like: <invoke name="create_user"><name>xxx</name><role_type>worker</role_type></invoke>
        tool_match = re.search(r'<invoke name="(\w+)">(.*?)</invoke>', content, re.DOTALL)
        if tool_match:
            tool_name = tool_match.group(1)
            tool_content = tool_match.group(2)

            # Extract parameters - handle various tag formats
            params = {}
            # Try <command> tag
            cmd_match = re.search(r'<command>(.*?)</command>', tool_content, re.DOTALL)
            if cmd_match:
                params["command"] = cmd_match.group(1).strip()
                return {
                    "route": tool_name,
                    "params": params,
                    "response": content[:200]
                }

            # Try extracting all simple key-value tags
            # e.g., <name>xxx</name><role_type>worker</role_type>
            all_tags = re.findall(r'<(\w+)>(.*?)</\1>', tool_content, re.DOTALL)
            for tag_name, tag_value in all_tags:
                if tag_name != 'invoke':  # avoid recursion
                    params[tag_name] = tag_value.strip()

            if params:
                return {
                    "route": tool_name,
                    "params": params,
                    "response": content[:200]
                }

        # Check for simple bash command patterns in response
        bash_pattern = re.search(r'\$?\s*(ls|cd|echo|cat|grep|pwd|find|rm|cp|mv)\s+(\S+)', content)
        if bash_pattern:
            return {
                "route": "bash",
                "params": {"command": bash_pattern.group(0).strip()},
                "response": content[:200]
            }

        # Fallback: use content as response with message parameter
        return {
            "route": "response",
            "params": {"message": content},
            "response": content[:200]
        }
