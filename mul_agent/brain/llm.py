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

    def __init__(self, config: Optional[Dict] = None, config_manager=None, agent_id: str = "core_brain"):
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
    ) -> Dict[str, Any]:
        """发送聊天请求

        Args:
            message: 文本消息
            system_prompt: 系统提示词
            history: 对话历史
            images: 图片列表，支持两种格式：
                   - str: 图片文件路径或 URL
                   - Dict: {"type": "base64", "data": "base64 字符串"} 或 {"type": "url", "url": "图片 URL"}
        """
        if not self.is_available():
            return {
                "error": "LLM not configured",
                "message": "Please set BAIDU_API_KEY/BAIDU_SECRET_KEY or ANTHROPIC_AUTH_TOKEN environment variable"
            }

        # 根据提供商选择不同的处理方法
        if self.provider == "baidu":
            return self._chat_baidu(message, system_prompt, history, images)
        else:
            return self._chat_anthropic(message, system_prompt, history, images)

    def _chat_baidu(
        self,
        message: str,
        system_prompt: Optional[str] = None,
        history: Optional[List[Dict]] = None,
        images: Optional[List[Union[str, Dict]]] = None,
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

            result = {
                "content": content_text,
                "model": self.baidu_model,
                "usage": {
                    "input_tokens": usage.get("prompt_tokens", 0),
                    "output_tokens": usage.get("completion_tokens", 0)
                }
            }
            # 记录 token 使用
            self.record_token_usage(
                function="chat",
                input_tokens=usage.get("prompt_tokens", 0),
                output_tokens=usage.get("completion_tokens", 0),
                model=self.baidu_model
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

            result = {
                "content": content,
                "model": response.model,
                "usage": {
                    "input_tokens": response.usage.input_tokens,
                    "output_tokens": response.usage.output_tokens
                }
            }
            # 记录 token 使用
            self.record_token_usage(
                function="chat",
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
                model=response.model
            )
            return result
        except Exception as e:
            return {
                "error": str(e),
                "message": "Failed to get response from LLM"
            }

    def record_token_usage(self, function: str, input_tokens: int, output_tokens: int, model: str = None):
        """记录 Token 使用

        Args:
            function: 功能类型 (think/chat/evolution/analysis/other)
            input_tokens: 输入 Token 数
            output_tokens: 输出 Token 数
            model: 模型名称（可选，默认使用 self.model）
        """
        if self.token_center:
            self.token_center.record_usage(
                agent_id=self.agent_id,
                model=model or self.model,
                function=function,
                input_tokens=input_tokens,
                output_tokens=output_tokens
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

    def think(self, user_input: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """让 LLM 思考并决定行动 - 自动记录 token 使用到 think 类别"""
        # Build system prompt
        system_prompt = self._build_system_prompt(context)

        # Build history from context
        history = context.get("history", [])

        # Get response - chat method already records token usage
        response = self.chat(user_input, system_prompt, history)

        if "error" in response:
            return {
                "action": "error",
                "message": response["error"]
            }

        # Parse response to determine action
        result = self._parse_response(response["content"], user_input)

        # 添加 token 使用信息到结果
        if "usage" in response:
            result["usage"] = response["usage"]

        return result

    def _build_system_prompt(self, context: Dict[str, Any]) -> str:
        """构建系统提示 - 系统固定模板 + 动态角色数据

        系统提示词模板是硬编码的（系统协议），但角色数据从配置文件读取。
        """
        soul = context.get("soul", {})
        user = context.get("user", {})
        skills = context.get("skills", [])

        personality = soul.get("core_traits", {}).get("personality", "")
        role = user.get("role", {}).get("title", "")
        responsibilities = user.get("role", {}).get("responsibilities", [])

        skill_names = [s.get("name", "") for s in skills if s.get("enabled", False)]

        # 系统固定模板（协议层，不可配置）
        system_template = """你是一个名为 {role_title} 的 AI Agent。

核心特质：{personality}
职责：{responsibilities}
可用技能：{skills}

重要：你必须严格按照 JSON 格式返回，不能包含任何其他内容或格式！

可用动作:
- create_user: 创建新 Agent
- bash: 执行 shell 命令
- memory: 管理记忆
- heart: 自省/进化
- response: 直接回复用户
- chat: 与其他 Agent 对话

示例:
输入："你好"
输出：JSON 格式，包含 route="response" 和 message 参数

输入："执行 ls -la"
输出：JSON 格式，包含 route="bash" 和 command 参数

请直接输出 JSON，不要有其他文字！"""

        # 格式化动态数据（从 soul.md 和 user.md 读取）
        return system_template.format(
            role_title=role,
            personality=personality,
            responsibilities=", ".join(responsibilities),
            skills=", ".join(skill_names)
        )

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
                return result
        except json.JSONDecodeError:
            pass

        # Try to find JSON in text
        json_match = re.search(r'\{[^{}]+\}', content)
        if json_match:
            try:
                result = json.loads(json_match.group())
                if "route" in result:
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

        # Fallback: use content as response
        return {
            "route": "heart",
            "params": {"trigger": "manual", "focus": "status"},
            "response": content[:200]
        }
