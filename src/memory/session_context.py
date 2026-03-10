"""Session Context Manager - 会话上下文管理器

负责：
1. 加载会话对话历史
2. Token 计数与阈值检测
3. 触发压缩提示
"""

import os
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime


# Token 估算函数（简单版本：按字符数估算）
def estimate_tokens(text: str) -> int:
    """估算文本的 token 数量

    使用简单的估算方法：
    - 英文：约 4 个字符 = 1 token
    - 中文：约 1.5 个字符 = 1 token
    """
    if not text:
        return 0

    # 检测中英文比例
    chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
    other_chars = len(text) - chinese_chars

    # 中文约 1.5 字符/token，英文约 4 字符/token
    return int(chinese_chars / 1.5 + other_chars / 4)


@dataclass
class TokenThreshold:
    """Token 阈值配置"""
    session_warning: int = 8000      # Session 警告阈值
    session_max: int = 16000         # Session 最大阈值
    bootstrap_warning: int = 4000    # Bootstrap 警告阈值
    bootstrap_max: int = 8000        # Bootstrap 最大阈值
    compression_target: int = 3000   # 压缩后目标 token 数


@dataclass
class SessionContext:
    """会话上下文"""
    agent_id: str
    session_id: str
    messages: List[Dict[str, Any]] = field(default_factory=list)
    bootstrap_content: Dict[str, Any] = field(default_factory=dict)
    token_count: int = 0
    bootstrap_token_count: int = 0
    needs_compression: bool = False
    compression_reason: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())


class SessionContextManager:
    """会话上下文管理器"""

    def __init__(
        self,
        storage_path: str = "storage/sessions",
        thresholds: Optional[TokenThreshold] = None
    ):
        """初始化会话上下文管理器

        Args:
            storage_path: 存储路径
            thresholds: Token 阈值配置
        """
        self.storage_path = Path(__file__).parent.parent.parent / storage_path
        self.storage_path.mkdir(parents=True, exist_ok=True)

        self.thresholds = thresholds or TokenThreshold()
        self.context_cache: Dict[str, SessionContext] = {}

    def get_session_path(self, agent_id: str, session_id: str) -> Path:
        """获取会话存储路径"""
        path = self.storage_path / agent_id / session_id
        path.mkdir(parents=True, exist_ok=True)
        return path

    def load_session(
        self,
        agent_id: str,
        session_id: str,
        max_messages: Optional[int] = None
    ) -> SessionContext:
        """加载会话上下文

        Args:
            agent_id: Agent ID
            session_id: 会话 ID
            max_messages: 最大加载消息数（用于分页加载）

        Returns:
            SessionContext 实例
        """
        cache_key = f"{agent_id}:{session_id}"

        # 检查缓存
        if cache_key in self.context_cache:
            return self.context_cache[cache_key]

        # 从文件系统加载
        session_path = self.get_session_path(agent_id, session_id)
        context = SessionContext(agent_id=agent_id, session_id=session_id)

        # 加载对话历史
        history_file = session_path / "history.jsonl"
        if history_file.exists():
            messages = []
            with open(history_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            msg = json.loads(line)
                            messages.append(msg)
                        except json.JSONDecodeError:
                            continue

            # 应用消息数量限制
            if max_messages and len(messages) > max_messages:
                messages = messages[-max_messages:]

            context.messages = messages

        # 加载 bootstrap 内容
        bootstrap_file = session_path / "bootstrap.json"
        if bootstrap_file.exists():
            with open(bootstrap_file, "r", encoding="utf-8") as f:
                context.bootstrap_content = json.load(f)

        # 计算 token 数
        self._update_token_counts(context)

        # 检查是否需要压缩
        self._check_compression_needed(context)

        # 缓存
        self.context_cache[cache_key] = context

        return context

    def add_message(
        self,
        agent_id: str,
        session_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> SessionContext:
        """添加消息到会话

        Args:
            agent_id: Agent ID
            session_id: 会话 ID
            role: 角色 (user/assistant/system)
            content: 消息内容
            metadata: 附加元数据

        Returns:
            更新后的 SessionContext
        """
        context = self.load_session(agent_id, session_id)

        # 添加消息
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {}
        }
        context.messages.append(message)
        context.updated_at = datetime.now().isoformat()

        # 更新 token 计数
        self._update_token_counts(context)

        # 检查是否需要压缩
        self._check_compression_needed(context)

        # 持久化
        self._save_session(context)

        return context

    def update_bootstrap(
        self,
        agent_id: str,
        session_id: str,
        content: Dict[str, Any]
    ) -> SessionContext:
        """更新 bootstrap 内容

        Args:
            agent_id: Agent ID
            session_id: 会话 ID
            content: bootstrap 内容

        Returns:
            更新后的 SessionContext
        """
        context = self.load_session(agent_id, session_id)
        context.bootstrap_content = content
        context.updated_at = datetime.now().isoformat()

        # 更新 token 计数
        self._update_token_counts(context)

        # 检查是否需要压缩
        self._check_compression_needed(context)

        # 持久化
        self._save_session(context)

        return context

    def _update_token_counts(self, context: SessionContext) -> None:
        """更新 Token 计数"""
        # 计算 session token
        session_tokens = 0
        for msg in context.messages:
            content = msg.get("content", "")
            session_tokens += estimate_tokens(content)
        context.token_count = session_tokens

        # 计算 bootstrap token
        bootstrap_text = json.dumps(context.bootstrap_content, ensure_ascii=False)
        context.bootstrap_token_count = estimate_tokens(bootstrap_text)

    def _check_compression_needed(self, context: SessionContext) -> None:
        """检查是否需要压缩"""
        needs_compression = False
        reasons = []

        # 检查 session token
        if context.token_count >= self.thresholds.session_max:
            needs_compression = True
            reasons.append(f"Session tokens ({context.token_count}) exceed max ({self.thresholds.session_max})")
        elif context.token_count >= self.thresholds.session_warning:
            # 警告阈值，提示 agent 准备压缩
            context.needs_compression = True
            context.compression_reason = f"Session tokens ({context.token_count}) approaching max"
            return

        # 检查 bootstrap token
        if context.bootstrap_token_count >= self.thresholds.bootstrap_max:
            needs_compression = True
            reasons.append(f"Bootstrap tokens ({context.bootstrap_token_count}) exceed max ({self.thresholds.bootstrap_max})")
        elif context.bootstrap_token_count >= self.thresholds.bootstrap_warning:
            needs_compression = True
            reasons.append(f"Bootstrap tokens ({context.bootstrap_token_count}) approaching max")

        context.needs_compression = needs_compression
        context.compression_reason = "; ".join(reasons) if reasons else ""

    def _save_session(self, context: SessionContext) -> None:
        """保存会话到磁盘"""
        session_path = self.get_session_path(context.agent_id, context.session_id)

        # 保存对话历史
        history_file = session_path / "history.jsonl"
        with open(history_file, "w", encoding="utf-8") as f:
            for msg in context.messages:
                f.write(json.dumps(msg, ensure_ascii=False) + "\n")

        # 保存 bootstrap 内容
        bootstrap_file = session_path / "bootstrap.json"
        with open(bootstrap_file, "w", encoding="utf-8") as f:
            json.dump(context.bootstrap_content, f, ensure_ascii=False, indent=2)

        # 保存上下文元数据
        meta_file = session_path / "context_meta.json"
        meta = {
            "agent_id": context.agent_id,
            "session_id": context.session_id,
            "token_count": context.token_count,
            "bootstrap_token_count": context.bootstrap_token_count,
            "needs_compression": context.needs_compression,
            "compression_reason": context.compression_reason,
            "created_at": context.created_at,
            "updated_at": context.updated_at,
            "message_count": len(context.messages)
        }
        with open(meta_file, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)

        # 更新缓存
        cache_key = f"{context.agent_id}:{context.session_id}"
        self.context_cache[cache_key] = context

    def get_compression_hint(self, context: SessionContext) -> Dict[str, Any]:
        """获取压缩提示词

        当需要压缩时，生成提示词告诉 Agent 如何压缩

        Returns:
            压缩提示词字典
        """
        if not context.needs_compression:
            return {
                "needs_compression": False,
                "hint": None
            }

        # 判断压缩类型
        compression_type = "session"
        target_tokens = self.thresholds.compression_target

        if context.bootstrap_token_count >= self.thresholds.bootstrap_warning:
            compression_type = "bootstrap"

        # 构建提示词
        hint = {
            "needs_compression": True,
            "type": compression_type,
            "current_tokens": {
                "session": context.token_count,
                "bootstrap": context.bootstrap_token_count
            },
            "target_tokens": target_tokens,
            "reason": context.compression_reason,
            "prompt": self._build_compression_prompt(context, compression_type)
        }

        return hint

    def _build_compression_prompt(
        self,
        context: SessionContext,
        compression_type: str
    ) -> str:
        """构建压缩提示词

        Args:
            context: 会话上下文
            compression_type: 压缩类型 (session/bootstrap)

        Returns:
            压缩提示词
        """
        if compression_type == "bootstrap":
            return f"""【压缩请求】Bootstrap 内容接近 token 上限

当前 Bootstrap Token 数：{context.bootstrap_token_count}
最大允许：{self.thresholds.bootstrap_max}
警告阈值：{self.thresholds.bootstrap_warning}

请将旧的 bootstrap 内容压缩存档到 memory 系统，并更新 bootstrap 为精简版本。

压缩要求：
1. 保留最关键的上下文信息
2. 将详细信息存档到 memory
3. 压缩后目标 token 数：{self.thresholds.compression_target}

当前 bootstrap 内容摘要：
{json.dumps(context.bootstrap_content, ensure_ascii=False)[:500]}...
"""
        else:
            # Session 压缩
            recent_messages = context.messages[-10:] if len(context.messages) > 10 else context.messages
            early_messages = context.messages[:-10] if len(context.messages) > 10 else []

            early_summary_needed = len(early_messages) > 0

            return f"""【压缩请求】会话内容接近 token 上限

当前 Session Token 数：{context.token_count}
最大允许：{self.thresholds.session_max}
警告阈值：{self.thresholds.session_warning}

请压缩早期对话历史，保留最近消息完整。

压缩要求：
1. 将早期对话（前 {len(early_messages)} 条）压缩为摘要
2. 保留最近 {len(recent_messages)} 条消息完整
3. 将压缩摘要存档到 memory 系统
4. 压缩后目标 token 数：{self.thresholds.compression_target}

最近消息预览：
""" + "\n".join([
    f"- [{m['role']}] {m['content'][:100]}..."
    for m in recent_messages[:5]
])
