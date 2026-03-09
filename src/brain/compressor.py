"""Context Compressor - 上下文压缩器

提供 LLM 摘要压缩功能，支持 Agent 自我判断压缩时机。
"""

import json
import tiktoken
from typing import Any, Dict, List, Optional


class ContextCompressor:
    """上下文压缩器

    功能：
    - 使用 LLM 生成语义摘要
    - 支持 Agent 自我判断压缩时机
    - 智能分层压缩（早期/中期/近期）
    - Token 数量管理
    """

    # 默认配置
    DEFAULT_MAX_TOKENS = 8000
    DEFAULT_RECENT_COUNT = 10  # 保留最近 N 条消息
    DEFAULT_EARLY_SUMMARY_COUNT = 20  # 压缩早期 N 条消息

    def __init__(
        self,
        llm_client=None,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        recent_count: int = DEFAULT_RECENT_COUNT
    ):
        """初始化上下文压缩器

        Args:
            llm_client: LLM 客户端实例（用于生成摘要）
            max_tokens: 最大 token 数量
            recent_count: 保留最近消息数量
        """
        self.llm_client = llm_client
        self.max_tokens = max_tokens
        self.recent_count = recent_count
        self.encoding = None

        # 尝试加载 tiktoken 编码器
        try:
            self.encoding = tiktoken.get_encoding("cl100k_base")
        except Exception:
            pass

    def count_tokens(self, text: str) -> int:
        """计算 token 数量

        Args:
            text: 文本内容

        Returns:
            token 数量
        """
        if self.encoding:
            try:
                return len(self.encoding.encode(text))
            except Exception:
                pass

        # 回退：简单估算 (中文字符约 1.5 token，英文约 4 字符 1 token)
        chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
        other_chars = len(text) - chinese_chars
        return int(chinese_chars * 1.5 + other_chars * 0.25)

    def count_message_tokens(self, messages: List[Dict]) -> int:
        """计算消息列表的总 token 数量

        Args:
            messages: 消息列表

        Returns:
            总 token 数量
        """
        total = 0
        for msg in messages:
            content = msg.get("content", "")
            if isinstance(content, dict):
                content = json.dumps(content, ensure_ascii=False)
            total += self.count_tokens(content)
            # 加上角色前缀的 overhead
            total += 4
        # 加上消息格式 overhead
        total += 3
        return total

    def should_compress(self, messages: List[Dict], context: Optional[Dict] = None) -> bool:
        """判断是否需要压缩

        Agent 可以调用此方法自我判断是否需要压缩。

        Args:
            messages: 消息列表
            context: 额外上下文信息（可选）

        Returns:
            是否需要压缩
        """
        token_count = self.count_message_tokens(messages)

        # 检查是否超过 token 限制
        if token_count > self.max_tokens:
            return True

        # Agent 可以基于上下文自行判断
        if context:
            # 复杂任务可能需要更多上下文
            complexity = context.get("complexity", "normal")
            if complexity == "high" and token_count > self.max_tokens * 0.7:
                return True

            # Agent 明确请求压缩
            if context.get("request_compress", False):
                return True

        return False

    def compress(self, messages: List[Dict], summary: Optional[str] = None) -> List[Dict]:
        """压缩消息列表

        Args:
            messages: 原始消息列表
            summary: 已生成的摘要（可选，如果为 None 则调用 LLM 生成）

        Returns:
            压缩后的消息列表
        """
        if len(messages) <= self.recent_count:
            # 不需要压缩
            return messages

        # 分离消息
        early_messages = messages[:-self.recent_count]
        recent_messages = messages[-self.recent_count:]

        # 生成摘要
        if summary is None:
            summary = self.create_llm_summary(early_messages)

        # 构建压缩后的消息列表
        compressed_messages = [
            {
                "role": "system",
                "content": f"【对话历史摘要】以下是对之前对话的精简摘要：\n\n{summary}\n\n【注】如需查看完整历史，请查阅对话记录。",
                "timestamp": early_messages[0].get("timestamp", ""),
                "metadata": {"type": "summary", "original_count": len(early_messages)}
            }
        ]

        # 保留最近的消息
        compressed_messages.extend(recent_messages)

        return compressed_messages

    def create_llm_summary(self, messages: List[Dict]) -> str:
        """使用 LLM 生成摘要

        Args:
            messages: 消息列表

        Returns:
            摘要文本
        """
        if not self.llm_client:
            # 没有 LLM 客户端，使用规则提取
            return self._create_rule_based_summary(messages)

        # 构建 Prompt
        messages_text = self._format_messages_for_summary(messages)

        prompt = f"""请将以下对话历史压缩为精简摘要，保留：
1. 核心任务和目标
2. 关键决策和结论
3. 重要上下文和信息
4. 待完成的任务

对话历史：
{messages_text}

请以 Markdown 格式输出摘要："""

        try:
            # 调用 LLM
            response = self.llm_client.complete(prompt)
            if response and response.get("content"):
                return response["content"]
        except Exception:
            pass

        # 回退到规则提取
        return self._create_rule_based_summary(messages)

    def _format_messages_for_summary(self, messages: List[Dict]) -> str:
        """格式化消息列表用于摘要生成

        Args:
            messages: 消息列表

        Returns:
            格式化后的文本
        """
        lines = []
        for i, msg in enumerate(messages):
            role = msg.get("role", "unknown")
            content = msg.get("content", "")

            # 如果是 dict，转为字符串
            if isinstance(content, dict):
                content = json.dumps(content, ensure_ascii=False)

            # 截断过长内容
            if len(content) > 500:
                content = content[:500] + "..."

            timestamp = msg.get("timestamp", "")
            lines.append(f"[{i+1}] {role} ({timestamp[:19] if timestamp else ''}): {content}")

        return "\n\n".join(lines)

    def _create_rule_based_summary(self, messages: List[Dict]) -> str:
        """基于规则的摘要生成（无 LLM 时使用）

        Args:
            messages: 消息列表

        Returns:
            摘要文本
        """
        if not messages:
            return "无历史对话"

        # 提取关键信息
        user_messages = [m for m in messages if m.get("role") == "user"]
        assistant_messages = [m for m in messages if m.get("role") == "assistant"]

        lines = [
            f"## 对话摘要",
            f"",
            f"- 对话轮次: {len(messages)} (用户 {len(user_messages)} 次，助手 {len(assistant_messages)} 次)",
            f"",
        ]

        # 提取用户意图
        if user_messages:
            lines.append("### 用户意图")
            for msg in user_messages[-5:]:  # 最近5条
                content = msg.get("content", "")
                if isinstance(content, dict):
                    content = content.get("input", str(content))
                if len(content) > 100:
                    content = content[:100] + "..."
                lines.append(f"- {content}")
            lines.append("")

        # 提取助手响应摘要
        if assistant_messages:
            lines.append("### 助手响应")
            for msg in assistant_messages[-3:]:  # 最近3条
                content = msg.get("content", "")
                if isinstance(content, dict):
                    content = str(content)
                if len(content) > 100:
                    content = content[:100] + "..."
                lines.append(f"- {content}")

        return "\n".join(lines)

    def merge_compressed(
        self,
        messages: List[Dict],
        compressed_summary: str,
        recent_messages: List[Dict]
    ) -> List[Dict]:
        """合并压缩后的消息

        Args:
            messages: 原始消息列表
            compressed_summary: 压缩摘要
            recent_messages: 最近的消息列表

        Returns:
            合并后的消息列表
        """
        merged = [
            {
                "role": "system",
                "content": f"【对话历史摘要】\n\n{compressed_summary}\n\n【注】以下是对话的最新部分。",
                "metadata": {"type": "summary"}
            }
        ]

        merged.extend(recent_messages)
        return merged

    def analyze_context_complexity(
        self,
        messages: List[Dict],
        user_input: str
    ) -> Dict[str, Any]:
        """分析上下文复杂度（供 Agent 参考）

        Args:
            messages: 消息列表
            user_input: 当前用户输入

        Returns:
            复杂度分析结果
        """
        token_count = self.count_message_tokens(messages)

        # 计算消息数量
        msg_count = len(messages)

        # 估算复杂度
        complexity_factors = {
            "token_count": token_count,
            "message_count": msg_count,
            "input_length": len(user_input),
            "token_ratio": token_count / self.max_tokens if self.max_tokens > 0 else 0
        }

        # 判断复杂度等级
        if token_count > self.max_tokens:
            level = "critical"
            recommendation = "必须压缩，建议立即执行"
        elif token_count > self.max_tokens * 0.8:
            level = "high"
            recommendation = "建议压缩以留出空间"
        elif token_count > self.max_tokens * 0.5:
            level = "medium"
            recommendation = "可选择压缩，视任务需求而定"
        else:
            level = "low"
            recommendation = "当前上下文适中"

        return {
            "level": level,
            "recommendation": recommendation,
            "factors": complexity_factors,
            "should_compress": token_count > self.max_tokens
        }

    def create_compression_prompt(
        self,
        messages: List[Dict],
        target_tokens: Optional[int] = None
    ) -> str:
        """创建压缩用的 Prompt（供 Agent 调用）

        Args:
            messages: 消息列表
            target_tokens: 目标 token 数量

        Returns:
            压缩提示
        """
        target = target_tokens or (self.max_tokens // 2)

        return f"""请将以下对话历史压缩为约 {target} tokens 的摘要。

要求：
1. 保留核心任务和目标
2. 保留关键决策和结论
3. 保留重要上下文和信息
4. 标记待完成的任务

对话历史：
{self._format_messages_for_summary(messages)}

请以 Markdown 格式输出摘要："""


# 便捷函数
def create_compressor(llm_client=None, max_tokens: int = 8000) -> ContextCompressor:
    """创建 ContextCompressor 的便捷函数

    Args:
        llm_client: LLM 客户端实例
        max_tokens: 最大 token 数量

    Returns:
        ContextCompressor 实例
    """
    return ContextCompressor(llm_client=llm_client, max_tokens=max_tokens)
