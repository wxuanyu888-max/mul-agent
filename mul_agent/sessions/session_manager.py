"""
Session Manager - 会话管理器 (Python 版本)

负责:
1. 创建和管理会话生命周期
2. 会话上下文存储与检索
3. 会话 Token 阈值管理
4. 会话压缩触发
"""

import json
import os
from pathlib import Path
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any, Dict, List, Optional, Literal
from uuid import uuid4
import re


# ============================================================================
# 类型定义
# ============================================================================

SessionRole = Literal["user", "assistant", "system"]


@dataclass
class SessionMessage:
    """会话消息"""
    id: str
    role: SessionRole
    content: str
    timestamp: float
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp,
            "metadata": self.metadata or {},
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SessionMessage":
        return cls(
            id=data.get("id", str(uuid4())),
            role=data.get("role", "user"),
            content=data.get("content", ""),
            timestamp=data.get("timestamp", datetime.now().timestamp()),
            metadata=data.get("metadata"),
        )


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
    id: str
    agent_id: str
    messages: List[SessionMessage] = field(default_factory=list)
    title: Optional[str] = None
    created_at: float = field(default_factory=lambda: datetime.now().timestamp())
    updated_at: float = field(default_factory=lambda: datetime.now().timestamp())
    token_count: int = 0
    bootstrap_token_count: int = 0
    needs_compression: bool = False
    compression_reason: str = ""
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class CompressionHint:
    """压缩提示"""
    needs_compression: bool
    compression_type: Optional[Literal["session", "bootstrap"]] = None
    current_tokens: Optional[Dict[str, int]] = None
    target_tokens: Optional[int] = None
    reason: Optional[str] = None
    prompt: Optional[str] = None


# ============================================================================
# Token 估算工具
# ============================================================================

def estimate_tokens(text: str) -> int:
    """估算文本的 token 数量

    使用简单的估算方法:
    - 英文：约 4 个字符 = 1 token
    - 中文：约 1.5 个字符 = 1 token
    """
    if not text:
        return 0

    # 检测中英文比例
    chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
    other_chars = len(text) - chinese_chars

    # 中文约 1.5 字符/token，英文约 4 字符/token
    return int(chinese_chars / 1.5 + other_chars / 4)


# ============================================================================
# SessionManager 类
# ============================================================================

class SessionManager:
    """会话上下文管理器"""

    def __init__(
        self,
        storage_path: str = "storage/sessions",
        thresholds: Optional[TokenThreshold] = None,
        default_agent_id: Optional[str] = None
    ):
        """初始化会话上下文管理器

        Args:
            storage_path: 存储路径
            thresholds: Token 阈值配置
            default_agent_id: 默认 Agent ID
        """
        # 展开 ~ 路径
        if storage_path.startswith("~"):
            home = os.path.expanduser("~")
            storage_path = os.path.join(home, storage_path[1:])
        elif not os.path.isabs(storage_path):
            storage_path = os.path.abspath(storage_path)

        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)

        self.thresholds = thresholds or TokenThreshold()
        self.context_cache: Dict[str, SessionContext] = {}
        self.default_agent_id = default_agent_id

        # 事件回调
        self._on_session_created_callbacks = []
        self._on_session_deleted_callbacks = []

    def on_session_created(self, callback):
        """注册 session:created 事件回调"""
        self._on_session_created_callbacks.append(callback)

    def on_session_deleted(self, callback):
        """注册 session:deleted 事件回调"""
        self._on_session_deleted_callbacks.append(callback)

    def _emit(self, event_name: str, *args, **kwargs):
        """触发事件"""
        if event_name == "session:created":
            for callback in self._on_session_created_callbacks:
                try:
                    callback(*args, **kwargs)
                except Exception:
                    pass
        elif event_name == "session:deleted":
            for callback in self._on_session_deleted_callbacks:
                try:
                    callback(*args, **kwargs)
                except Exception:
                    pass

    def get_session_path(self, agent_id: str, session_id: str) -> Path:
        """获取会话存储路径"""
        path = self.storage_path / agent_id / session_id
        path.mkdir(parents=True, exist_ok=True)
        return path

    def load_session(
        self,
        session_id: str,
        agent_id: Optional[str] = None,
        max_messages: Optional[int] = None
    ) -> SessionContext:
        """加载会话上下文

        Args:
            session_id: 会话 ID
            agent_id: Agent ID
            max_messages: 最大加载消息数 (用于分页加载)

        Returns:
            SessionContext 实例
        """
        effective_agent_id = agent_id or self.default_agent_id or "default"
        cache_key = f"{effective_agent_id}:{session_id}"

        # 检查缓存
        if cache_key in self.context_cache:
            ctx = self.context_cache[cache_key]
            if max_messages and len(ctx.messages) > max_messages:
                ctx.messages = ctx.messages[-max_messages:]
            return ctx

        # 从文件系统加载
        session_path = self.get_session_path(effective_agent_id, session_id)
        context = SessionContext(
            id=session_id,
            agent_id=effective_agent_id,
            messages=[],
            created_at=datetime.now().timestamp(),
            updated_at=datetime.now().timestamp(),
        )

        # 加载对话历史
        history_file = session_path / "history.jsonl"
        if history_file.exists():
            messages = []
            with open(history_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            msg_data = json.loads(line)
                            messages.append(SessionMessage.from_dict(msg_data))
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
                context.metadata = {"bootstrap": json.load(f)}

        # 加载元数据
        meta_file = session_path / "context_meta.json"
        if meta_file.exists():
            with open(meta_file, "r", encoding="utf-8") as f:
                meta = json.load(f)
                context.title = meta.get("title")
                context.created_at = meta.get("created_at", context.created_at)
                context.updated_at = meta.get("updated_at", context.updated_at)

        # 计算 token 数
        self._update_token_counts(context)

        # 检查是否需要压缩
        self._check_compression_needed(context)

        # 缓存
        self.context_cache[cache_key] = context

        return context

    def create_session(
        self,
        session_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        title: Optional[str] = None,
        initial_messages: Optional[List[SessionMessage]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> SessionContext:
        """创建新会话

        Args:
            session_id: 会话 ID (可选，自动生成)
            agent_id: Agent ID
            title: 会话标题
            initial_messages: 初始消息列表
            metadata: 附加元数据

        Returns:
            SessionContext 实例
        """
        session_id = session_id or str(uuid4())
        effective_agent_id = agent_id or self.default_agent_id or "default"
        cache_key = f"{effective_agent_id}:{session_id}"

        context = SessionContext(
            id=session_id,
            agent_id=effective_agent_id,
            title=title,
            messages=initial_messages or [],
            metadata=metadata,
            created_at=datetime.now().timestamp(),
            updated_at=datetime.now().timestamp(),
        )

        # 计算初始 token 数
        self._update_token_counts(context)

        # 持久化
        self._save_session(context)

        # 缓存
        self.context_cache[cache_key] = context

        # 触发事件
        self._emit("session:created", context)

        return context

    def add_message(
        self,
        session_id: str,
        role: SessionRole,
        content: str,
        agent_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> SessionContext:
        """添加消息到会话

        Args:
            session_id: 会话 ID
            role: 角色 (user/assistant/system)
            content: 消息内容
            agent_id: Agent ID
            metadata: 附加元数据

        Returns:
            更新后的 SessionContext
        """
        effective_agent_id = agent_id or self.default_agent_id or "default"
        context = self.load_session(session_id, effective_agent_id)

        # 添加消息
        message = SessionMessage(
            id=str(uuid4()),
            role=role,
            content=content,
            timestamp=datetime.now().timestamp(),
            metadata=metadata or {}
        )
        context.messages.append(message)
        context.updated_at = datetime.now().timestamp()

        # 更新 token 计数
        self._update_token_counts(context)

        # 检查是否需要压缩
        self._check_compression_needed(context)

        # 持久化
        self._save_session(context)

        return context

    def update_session_metadata(
        self,
        session_id: str,
        title: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        agent_id: Optional[str] = None
    ) -> SessionContext:
        """更新会话元数据

        Args:
            session_id: 会话 ID
            title: 会话标题
            metadata: 附加元数据
            agent_id: Agent ID

        Returns:
            更新后的 SessionContext
        """
        effective_agent_id = agent_id or self.default_agent_id or "default"
        context = self.load_session(session_id, effective_agent_id)

        if title is not None:
            context.title = title
        if metadata is not None:
            if context.metadata is None:
                context.metadata = {}
            context.metadata.update(metadata)

        context.updated_at = datetime.now().timestamp()
        self._save_session(context)
        return context

    def delete_session(self, session_id: str, agent_id: Optional[str] = None) -> None:
        """删除会话

        Args:
            session_id: 会话 ID
            agent_id: Agent ID
        """
        effective_agent_id = agent_id or self.default_agent_id or "default"
        cache_key = f"{effective_agent_id}:{session_id}"
        session_path = self.get_session_path(effective_agent_id, session_id)

        # 删除目录
        import shutil
        if session_path.exists():
            shutil.rmtree(session_path, ignore_errors=True)

        # 清除缓存
        if cache_key in self.context_cache:
            del self.context_cache[cache_key]

        # 触发事件
        self._emit("session:deleted", session_id=session_id, agent_id=effective_agent_id)

    def list_sessions(self, agent_id: Optional[str] = None) -> List[SessionContext]:
        """列出所有会话

        Args:
            agent_id: Agent ID

        Returns:
            SessionContext 列表，按更新时间倒序
        """
        effective_agent_id = agent_id or self.default_agent_id or "default"
        agent_path = self.storage_path / effective_agent_id
        sessions = []

        if agent_path.exists():
            for entry in agent_path.iterdir():
                if entry.is_dir():
                    try:
                        context = self.load_session(entry.name, effective_agent_id)
                        sessions.append(context)
                    except Exception:
                        # 跳过无法加载的会话
                        pass

        # 按更新时间排序
        sessions.sort(key=lambda s: s.updated_at, reverse=True)
        return sessions

    def get_compression_hint(self, context: SessionContext) -> CompressionHint:
        """获取压缩提示

        Returns:
            CompressionHint 实例
        """
        if not context.needs_compression:
            return CompressionHint(needs_compression=False)

        # 判断压缩类型
        compression_type: Literal["session", "bootstrap"] = "session"
        if context.bootstrap_token_count >= self.thresholds.bootstrap_warning:
            compression_type = "bootstrap"

        return CompressionHint(
            needs_compression=True,
            compression_type=compression_type,
            current_tokens={
                "session": context.token_count,
                "bootstrap": context.bootstrap_token_count,
            },
            target_tokens=self.thresholds.compression_target,
            reason=context.compression_reason,
            prompt=self._build_compression_prompt(context, compression_type),
        )

    # ========================================================================
    # 私有方法
    # ========================================================================

    def _update_token_counts(self, context: SessionContext) -> None:
        """更新 Token 计数"""
        # 计算 session token
        session_tokens = sum(estimate_tokens(msg.content) for msg in context.messages)
        context.token_count = session_tokens

        # 计算 bootstrap token
        if context.metadata and "bootstrap" in context.metadata:
            bootstrap_text = json.dumps(context.metadata["bootstrap"], ensure_ascii=False)
            context.bootstrap_token_count = estimate_tokens(bootstrap_text)
        else:
            context.bootstrap_token_count = 0

    def _check_compression_needed(self, context: SessionContext) -> None:
        """检查是否需要压缩"""
        needs_compression = False
        reasons = []

        # 检查 session token
        if context.token_count >= self.thresholds.session_max:
            needs_compression = True
            reasons.append(
                f"Session tokens ({context.token_count}) exceed max ({self.thresholds.session_max})"
            )
        elif context.token_count >= self.thresholds.session_warning:
            context.needs_compression = True
            context.compression_reason = f"Session tokens ({context.token_count}) approaching max"
            return

        # 检查 bootstrap token
        if context.bootstrap_token_count >= self.thresholds.bootstrap_max:
            needs_compression = True
            reasons.append(
                f"Bootstrap tokens ({context.bootstrap_token_count}) exceed max "
                f"({self.thresholds.bootstrap_max})"
            )
        elif context.bootstrap_token_count >= self.thresholds.bootstrap_warning:
            needs_compression = True
            reasons.append(
                f"Bootstrap tokens ({context.bootstrap_token_count}) approaching max"
            )

        context.needs_compression = needs_compression
        if reasons:
            context.compression_reason = "; ".join(reasons)

    def _save_session(self, context: SessionContext) -> None:
        """保存会话到磁盘"""
        session_path = self.get_session_path(context.agent_id, context.id)

        # 保存对话历史 (JSONL 格式)
        history_file = session_path / "history.jsonl"
        with open(history_file, "w", encoding="utf-8") as f:
            for msg in context.messages:
                f.write(json.dumps(msg.to_dict(), ensure_ascii=False) + "\n")

        # 保存 bootstrap 内容
        if context.metadata and "bootstrap" in context.metadata:
            bootstrap_file = session_path / "bootstrap.json"
            with open(bootstrap_file, "w", encoding="utf-8") as f:
                json.dump(
                    context.metadata["bootstrap"],
                    f,
                    ensure_ascii=False,
                    indent=2
                )

        # 保存元数据
        meta_file = session_path / "context_meta.json"
        meta = {
            "title": context.title,
            "agent_id": context.agent_id,
            "session_id": context.id,
            "token_count": context.token_count,
            "bootstrap_token_count": context.bootstrap_token_count,
            "needs_compression": context.needs_compression,
            "compression_reason": context.compression_reason,
            "created_at": context.created_at,
            "updated_at": context.updated_at,
            "message_count": len(context.messages),
        }
        with open(meta_file, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)

        # 更新缓存
        cache_key = f"{context.agent_id}:{context.id}"
        self.context_cache[cache_key] = context

    def _build_compression_prompt(
        self,
        context: SessionContext,
        compression_type: Literal["session", "bootstrap"]
    ) -> str:
        """构建压缩提示词"""
        if compression_type == "bootstrap":
            bootstrap_content = context.metadata.get("bootstrap", {}) if context.metadata else {}
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
{json.dumps(bootstrap_content, ensure_ascii=False)[:500]}...
"""
        else:
            # Session 压缩
            recent_messages = context.messages[-10:] if len(context.messages) > 10 else context.messages
            early_messages = context.messages[:-10] if len(context.messages) > 10 else []

            recent_preview = "\n".join([
                f"- [{msg.role}] {msg.content[:100]}..."
                for msg in recent_messages[:5]
            ])

            return f"""【压缩请求】会话内容接近 token 上限

当前 Session Token 数：{context.token_count}
最大允许：{self.thresholds.session_max}
警告阈值：{self.thresholds.session_warning}

请压缩早期对话历史，保留最近消息完整。

压缩要求：
1. 将早期对话 (前 {len(early_messages)} 条) 压缩为摘要
2. 保留最近 {len(recent_messages)} 条消息完整
3. 将压缩摘要存档到 memory 系统
4. 压缩后目标 token 数：{self.thresholds.compression_target}

最近消息预览：
{recent_preview}
"""
