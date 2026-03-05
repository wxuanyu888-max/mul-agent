"""LLM Client - MiniMax (Anthropic-compatible) integration"""

import os
from typing import Any, Dict, List, Optional

try:
    import anthropic
except ImportError:
    anthropic = None


class LLMClient:
    """LLM 客户端 - 支持 Anthropic/MiniMax"""

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}

        # Get API configuration from environment
        self.api_key = os.environ.get("ANTHROPIC_AUTH_TOKEN", "")
        self.base_url = os.environ.get("ANTHROPIC_BASE_URL", "https://api.anthropic.com")
        self.model = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")
        self.max_tokens = self.config.get("max_tokens", 1024)

        # Initialize client
        self.client = None
        if self.api_key and anthropic:
            # For MiniMax (Anthropic-compatible API)
            if "minimax" in self.base_url.lower():
                self.client = anthropic.Anthropic(
                    api_key=self.api_key,
                    base_url=self.base_url
                )
            else:
                self.client = anthropic.Anthropic(
                    api_key=self.api_key
                )

    def is_available(self) -> bool:
        """检查是否可用"""
        return self.client is not None and bool(self.api_key)

    def chat(
        self,
        message: str,
        system_prompt: Optional[str] = None,
        history: Optional[List[Dict]] = None,
    ) -> Dict[str, Any]:
        """发送聊天请求"""
        if not self.is_available():
            return {
                "error": "LLM not configured",
                "message": "Please set ANTHROPIC_AUTH_TOKEN environment variable"
            }

        # Build messages
        messages = []

        # Add history
        if history:
            for msg in history[-10:]:  # Last 10 messages
                role = msg.get("role", "user")
                content = msg.get("content", "")
                if isinstance(content, dict):
                    content = str(content)
                messages.append({"role": role, "content": content})

        # Add current message
        messages.append({"role": "user", "content": message})

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                system=system_prompt or "You are a helpful AI assistant.",
                messages=messages
            )

            # Handle different response types (Anthropic vs MiniMax)
            content = ""
            for block in response.content:
                if hasattr(block, 'text'):
                    content += block.text
                elif hasattr(block, 'type') and block.type == 'text':
                    content += block.text

            return {
                "content": content,
                "model": response.model,
                "usage": {
                    "input_tokens": response.usage.input_tokens,
                    "output_tokens": response.usage.output_tokens
                }
            }
        except Exception as e:
            return {
                "error": str(e),
                "message": "Failed to get response from LLM"
            }

    def think(self, user_input: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """让 LLM 思考并决定行动"""
        # Build system prompt
        system_prompt = self._build_system_prompt(context)

        # Build history from context
        history = context.get("history", [])

        # Get response
        response = self.chat(user_input, system_prompt, history)

        if "error" in response:
            return {
                "action": "error",
                "message": response["error"]
            }

        # Parse response to determine action
        return self._parse_response(response["content"], user_input)

    def _build_system_prompt(self, context: Dict[str, Any]) -> str:
        """构建系统提示"""
        soul = context.get("soul", {})
        user = context.get("user", {})
        skills = context.get("skills", [])

        personality = soul.get("core_traits", {}).get("personality", "")
        role = user.get("role", {}).get("title", "")
        responsibilities = user.get("role", {}).get("responsibilities", [])

        skill_names = [s.get("name", "") for s in skills if s.get("enabled", False)]

        return f"""你是一个名为 {role} 的AI Agent。

核心特质: {personality}
职责: {", ".join(responsibilities)}
可用技能: {", ".join(skill_names)}

重要：你必须严格按照JSON格式返回，不能包含任何其他内容或格式！

可用动作:
- create_user: 创建新Agent，params: {{"name": "名称", "role_type": "worker/manager"}}
- bash: 执行shell命令，params: {{"command": "要执行的命令"}}
- memory: 管理记忆，params: {{"action": "list/read/write", "memory_type": "short_term/long_term"}}
- heart: 自省/进化，params: {{"focus": "status/all/skills"}}
- response: 直接回复用户，params: {{"message": "回复内容"}}

示例：
输入: "你好"
输出: {{"route": "response", "params": {{"message": "你好！有什么可以帮你的？"}}, "response": "你好！我是团队协调者..."}}

输入: "执行 ls -la"
输出: {{"route": "bash", "params": {{"command": "ls -la"}}, "response": "正在执行 ls -la 命令..."}}

请直接输出JSON，不要有其他文字！"""

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
