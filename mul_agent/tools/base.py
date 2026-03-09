"""Base Tool Classes - 工具基类

提供统一的工具接口和结果类型

参考 OpenClaw 架构设计：
1. 统一的工具接口 (SyncTool/AsyncTool)
2. 工具元数据包含 gating 信息
3. 工具结果支持结构化输出和媒体内容
4. 内置安全检查和权限控制
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Callable, TypeVar, Generic
from dataclasses import dataclass, asdict, field
import json


@dataclass
class ToolGate:
    """工具门控条件 - 决定工具何时可用

    参考 OpenClaw 的 metadata.openclaw.requires:
    - bins: 需要的二进制文件
    - env: 需要的环境变量
    - config: 需要的配置项
    - os: 支持的操作系统
    """
    bins: List[str] = field(default_factory=list)
    any_bins: List[str] = field(default_factory=list)  # 至少有一个
    env: List[str] = field(default_factory=list)
    config: List[str] = field(default_factory=list)
    os: List[str] = field(default_factory=list)  # darwin, linux, win32
    always: bool = False  # 总是启用，跳过其他检查


@dataclass
class ToolMetadata:
    """工具元数据

    参考 OpenClaw SKILL.md frontmatter 设计
    """
    name: str
    description: str
    input_schema: Dict[str, Any]
    examples: Optional[List[Dict[str, Any]]] = None
    gate: Optional[ToolGate] = None
    owner_only: bool = False  # 仅所有者可用
    sandbox_safe: bool = True  # 沙箱中是否安全
    tags: List[str] = field(default_factory=list)  # 工具标签/分类


@dataclass
class ToolResult:
    """工具执行结果

    参考 OpenClaw AgentToolResult 设计：
    - content: 用于展示给用户的内容（支持文本、图片等）
    - details: 结构化数据，供后续工具使用
    """
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    message: Optional[str] = None
    content: List[Dict[str, Any]] = field(default_factory=list)  # 展示内容
    details: Optional[Dict[str, Any]] = None  # 结构化详情

    @classmethod
    def success(cls, data: Any = None, message: str = None, details: Dict = None):
        result = cls(success=True, data=data, message=message)
        if details:
            result.details = details
        return result

    @classmethod
    def error(cls, error: str, data: Any = None, status: int = None):
        result = cls(success=False, error=error, data=data)
        if status:
            result.details = {"status": status}
        return result

    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        # 清理 None 值
        return {k: v for k, v in result.items() if v is not None}

    def to_content(self) -> List[Dict[str, Any]]:
        """转换为可展示的内容格式"""
        if self.content:
            return self.content

        content = []
        if self.message:
            content.append({"type": "text", "text": self.message})
        if self.data is not None:
            if isinstance(self.data, str):
                content.append({"type": "text", "text": self.data})
            else:
                content.append({
                    "type": "text",
                    "text": json.dumps(self.data, indent=2, ensure_ascii=False)
                })
        if self.error:
            content.append({"type": "error", "text": self.error})
        return content


# 工具输入验证器类型
T = TypeVar('T')


class ToolInputError(Exception):
    """工具输入错误"""
    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.status = status


class ToolAuthorizationError(ToolInputError):
    """工具授权错误"""
    def __init__(self, message: str):
        super().__init__(message, status=403)


class SyncTool(ABC):
    """同步工具基类

    参考 OpenClaw 设计：
    1. 统一的 execute 入口
    2. 内置参数验证
    3. 支持工具门控检查
    """

    metadata: ToolMetadata

    def __init__(self, context: Optional[Dict[str, Any]] = None):
        """初始化工具

        Args:
            context: 工具执行上下文，包含：
                - agent_id: Agent ID
                - session_id: 会话 ID
                - workspace_dir: 工作目录
                - config: 配置对象
                - sender_is_owner: 发送者是否为所有者
        """
        self.context = context or {}

    @abstractmethod
    def execute_sync(self, **kwargs) -> ToolResult:
        """执行工具（同步）

        Args:
            **kwargs: 工具参数

        Returns:
            ToolResult: 执行结果
        """
        pass

    def execute(self, **kwargs) -> ToolResult:
        """执行工具的入口方法 - 包含预处理和后处理"""
        # 前置检查
        self._before_execute(**kwargs)

        # 执行
        result = self.execute_sync(**kwargs)

        # 后置处理
        self._after_execute(result)

        return result

    def _before_execute(self, **kwargs):
        """执行前钩子 - 用于验证和预处理"""
        # 检查 owner_only 工具
        if self.metadata.owner_only and not self.context.get("sender_is_owner"):
            raise ToolAuthorizationError(
                f"Tool '{self.metadata.name}' requires owner privileges"
            )

    def _after_execute(self, result: ToolResult):
        """执行后钩子 - 用于清理和日志"""
        pass

    def check_gate(self) -> bool:
        """检查工具门控条件

        Returns:
            bool: 工具是否可用
        """
        if not self.metadata.gate:
            return True

        gate = self.metadata.gate

        # always 门控
        if gate.always:
            return True

        import os
        import platform

        # OS 检查
        if gate.os:
            current_os = platform.system().lower()
            os_map = {"darwin": "darwin", "linux": "linux", "win32": "windows"}
            if current_os not in [os_map.get(o, o) for o in gate.os]:
                return False

        # 二进制文件检查
        if gate.bins:
            for binary in gate.bins:
                if not self._find_binary(binary):
                    return False

        # 任何二进制文件检查
        if gate.any_bins:
            found = False
            for binary in gate.any_bins:
                if self._find_binary(binary):
                    found = True
                    break
            if not found:
                return False

        # 环境变量检查
        if gate.env:
            for env_var in gate.env:
                if env_var not in os.environ:
                    return False

        # 配置检查
        if gate.config:
            config = self.context.get("config", {})
            for config_key in gate.config:
                if not self._get_config_value(config, config_key):
                    return False

        return True

    def _find_binary(self, name: str) -> bool:
        """检查二进制文件是否在 PATH 中"""
        import shutil
        return shutil.which(name) is not None

    def _get_config_value(self, config: Dict, key: str) -> Any:
        """从配置中获取值（支持点分隔的路径）"""
        value = config
        for part in key.split("."):
            if isinstance(value, dict):
                value = value.get(part)
            else:
                return None
        return value is not None and value is not False

    def to_registry_definition(self) -> Dict[str, Any]:
        """转换为工具注册表定义格式"""
        return {
            "name": self.metadata.name,
            "description": self.metadata.description,
            "input_schema": self.metadata.input_schema,
            "examples": self.metadata.examples or [],
            "tags": self.metadata.tags or [],
            "owner_only": self.metadata.owner_only,
        }


class AsyncTool(ABC):
    """异步工具基类"""

    metadata: ToolMetadata

    def __init__(self, context: Optional[Dict[str, Any]] = None):
        self.context = context or {}

    @abstractmethod
    async def execute_async(self, **kwargs) -> ToolResult:
        """执行工具（异步）"""
        pass

    async def execute(self, **kwargs) -> ToolResult:
        """执行工具的入口方法"""
        self._before_execute(**kwargs)
        result = await self.execute_async(**kwargs)
        self._after_execute(result)
        return result

    def _before_execute(self, **kwargs):
        if self.metadata.owner_only and not self.context.get("sender_is_owner"):
            raise ToolAuthorizationError(
                f"Tool '{self.metadata.name}' requires owner privileges"
            )

    def _after_execute(self, result: ToolResult):
        pass

    def check_gate(self) -> bool:
        """检查工具门控条件（同 SyncTool）"""
        if not self.metadata.gate:
            return True

        gate = self.metadata.gate

        if gate.always:
            return True

        import os
        import platform

        if gate.os:
            current_os = platform.system().lower()
            os_map = {"darwin": "darwin", "linux": "linux", "win32": "windows"}
            if current_os not in [os_map.get(o, o) for o in gate.os]:
                return False

        if gate.bins:
            for binary in gate.bins:
                if not self._find_binary(binary):
                    return False

        if gate.any_bins:
            found = False
            for binary in gate.any_bins:
                if self._find_binary(binary):
                    found = True
                    break
            if not found:
                return False

        if gate.env:
            for env_var in gate.env:
                if env_var not in os.environ:
                    return False

        if gate.config:
            config = self.context.get("config", {})
            for config_key in gate.config:
                if not self._get_config_value(config, config_key):
                    return False

        return True

    def _find_binary(self, name: str) -> bool:
        import shutil
        return shutil.which(name) is not None

    def _get_config_value(self, config: Dict, key: str) -> Any:
        value = config
        for part in key.split("."):
            if isinstance(value, dict):
                value = value.get(part)
            else:
                return None
        return value is not None and value is not False

    def to_registry_definition(self) -> Dict[str, Any]:
        return {
            "name": self.metadata.name,
            "description": self.metadata.description,
            "input_schema": self.metadata.input_schema,
            "examples": self.metadata.examples or [],
            "tags": self.metadata.tags or [],
            "owner_only": self.metadata.owner_only,
        }


# 便捷类型
AnyTool = SyncTool | AsyncTool
ToolResultCallback = Callable[[ToolResult], None]
