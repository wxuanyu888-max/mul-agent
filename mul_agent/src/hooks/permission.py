"""Permission Hook - 权限请求钩子

实现 Claude Code 风格的权限确认系统：
1. 危险操作前请求用户确认
2. 支持自动确认白名单
3. 支持"记住此选择"功能
"""

from typing import Any, Dict, List, Optional, Set
from pathlib import Path
import json
import hashlib

from mul_agent.hooks.base import BaseHook, HookContext, HookEvent, HookPriority


# ==================== 危险操作定义 ====================

class DangerLevel:
    """危险等级"""
    LOW = "low"           # 低风险（无需确认）
    MEDIUM = "medium"     # 中风险（建议确认）
    HIGH = "high"         # 高风险（必须确认）
    CRITICAL = "critical" # 严重风险（强烈建议确认）


# 危险命令模式
DANGEROUS_COMMANDS = {
    # 删除操作
    r"^\s*rm\s+.*": DangerLevel.HIGH,
    r"^\s*rm\s+-rf\s+.*": DangerLevel.CRITICAL,
    r"^\s*del\s+.*": DangerLevel.HIGH,

    # 格式化/清空操作
    r"^\s*mkfs\..*": DangerLevel.CRITICAL,
    r"^\s*dd\s+.*": DangerLevel.HIGH,
    r"^\s*>.*": DangerLevel.MEDIUM,  # 重定向清空

    # 权限修改
    r"^\s*chmod\s+.*": DangerLevel.MEDIUM,
    r"^\s*chown\s+.*": DangerLevel.MEDIUM,

    # 系统操作
    r"^\s*sudo\s+.*": DangerLevel.MEDIUM,
    r"^\s*kill\s+.*": DangerLevel.HIGH,
    r"^\s*pkill\s+.*": DangerLevel.HIGH,

    # 网络操作
    r"^\s*curl\s+.*\|\s*(ba)?sh": DangerLevel.HIGH,  # curl | bash
    r"^\s*wget\s+.*\|\s*(ba)?sh": DangerLevel.HIGH,

    # 包管理
    r"^\s*apt-get\s+remove.*": DangerLevel.MEDIUM,
    r"^\s*yum\s+remove.*": DangerLevel.MEDIUM,
    r"^\s*dnf\s+remove.*": DangerLevel.MEDIUM,

    # Git 危险操作
    r"^\s*git\s+push\s+.*--force": DangerLevel.HIGH,
    r"^\s*git\s+reset\s+--hard.*": DangerLevel.MEDIUM,
}

# 危险文件路径模式
DANGEROUS_PATHS = [
    "/etc/*",
    "/usr/*",
    "/bin/*",
    "/sbin/*",
    "/var/*",
    "/root/*",
    "/.ssh/*",
    "*.pem",
    "*.key",
    "*password*",
    "*secret*",
    "*.env",
    ".env*",
]


class PermissionRequest:
    """权限请求"""

    def __init__(
        self,
        action: str,
        description: str,
        danger_level: str,
        details: Dict[str, Any] = None,
        requires_confirmation: bool = True
    ):
        self.action = action
        self.description = description
        self.danger_level = danger_level
        self.details = details or {}
        self.requires_confirmation = requires_confirmation
        self.confirmed = False
        self.remember_choice = False

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "action": self.action,
            "description": self.description,
            "danger_level": self.danger_level,
            "details": self.details,
            "requires_confirmation": self.requires_confirmation,
            "confirmed": self.confirmed,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PermissionRequest":
        """从字典创建"""
        req = cls(
            action=data.get("action", ""),
            description=data.get("description", ""),
            danger_level=data.get("danger_level", "low"),
            details=data.get("details"),
            requires_confirmation=data.get("requires_confirmation", True)
        )
        req.confirmed = data.get("confirmed", False)
        req.remember_choice = data.get("remember_choice", False)
        return req


class PermissionManager:
    """权限管理器"""

    def __init__(self, config_path: str = "storage/permissions/config.json"):
        self.config_path = Path(config_path)
        self.config_path.parent.mkdir(parents=True, exist_ok=True)

        # 白名单（自动批准）
        self.auto_approve_patterns: Set[str] = set()
        # 黑名单（自动拒绝）
        self.auto_deny_patterns: Set[str] = set()
        # 记住的选择
        self.remembered_choices: Dict[str, bool] = {}

        # 会话期间的临时确认
        self.session_confirmations: Set[str] = set()

        self._load_config()

    def _load_config(self) -> None:
        """加载配置"""
        if self.config_path.exists():
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    config = json.load(f)
                self.auto_approve_patterns = set(config.get("auto_approve", []))
                self.auto_deny_patterns = set(config.get("auto_deny", []))
                self.remembered_choices = config.get("remembered_choices", {})
            except Exception:
                pass

    def _save_config(self) -> None:
        """保存配置"""
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump({
                    "auto_approve": list(self.auto_approve_patterns),
                    "auto_deny": list(self.auto_deny_patterns),
                    "remembered_choices": self.remembered_choices,
                }, f, indent=2)
        except Exception as e:
            print(f"Failed to save permission config: {e}")

    def _hash_action(self, action: str, details: Dict[str, Any]) -> str:
        """生成动作的唯一哈希（用于记住选择）"""
        content = f"{action}:{json.dumps(details, sort_keys=True)}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def should_auto_approve(self, action: str, details: Dict[str, Any]) -> Optional[bool]:
        """检查是否应该自动批准/拒绝

        Returns:
            True: 自动批准
            False: 自动拒绝
            None: 需要用户确认
        """
        action_hash = self._hash_action(action, details)

        # 检查记住的选择
        if action_hash in self.remembered_choices:
            return self.remembered_choices[action_hash]

        # 检查会话期间的确认
        if action_hash in self.session_confirmations:
            return True

        # 检查白名单
        for pattern in self.auto_approve_patterns:
            if pattern in action:
                return True

        # 检查黑名单
        for pattern in self.auto_deny_patterns:
            if pattern in action:
                return False

        return None

    def approve(self, action: str, details: Dict[str, Any], remember: bool = False) -> None:
        """批准权限"""
        action_hash = self._hash_action(action, details)
        self.session_confirmations.add(action_hash)

        if remember:
            self.remembered_choices[action_hash] = True
            self._save_config()

    def deny(self, action: str, details: Dict[str, Any], remember: bool = False) -> None:
        """拒绝权限"""
        action_hash = self._hash_action(action, details)

        if remember:
            self.auto_deny_patterns.add(action)
            self._save_config()

    def clear_session_confirmations(self) -> None:
        """清除会话期间的确认"""
        self.session_confirmations.clear()

    def add_auto_approve(self, pattern: str) -> None:
        """添加到白名单"""
        self.auto_approve_patterns.add(pattern)
        self._save_config()

    def add_auto_deny(self, pattern: str) -> None:
        """添加到黑名单"""
        self.auto_deny_patterns.add(pattern)
        self._save_config()

    def get_config(self) -> Dict[str, Any]:
        """获取配置"""
        return {
            "auto_approve": list(self.auto_approve_patterns),
            "auto_deny": list(self.auto_deny_patterns),
            "remembered_choices": self.remembered_choices,
            "session_confirmations_count": len(self.session_confirmations),
        }


class PermissionHook(BaseHook):
    """权限请求钩子"""

    hook_id = "permission"
    hook_name = "Permission Request"
    hook_version = "1.0.0"
    hook_description = "请求用户确认危险操作"

    events = [HookEvent.PRE_TOOL_USE, HookEvent.PRE_ROUTE]
    priority = HookPriority.HIGH  # 高优先级，最先执行

    # 需要确认的路由
    REQUIRES_CONFIRMATION_ROUTES = {
        "bash": DangerLevel.MEDIUM,
        "file_edit": DangerLevel.LOW,
        "file_delete": DangerLevel.HIGH,
        "glob": DangerLevel.LOW,
        "grep": DangerLevel.LOW,
    }

    def _initialize(self) -> None:
        """初始化钩子"""
        self.permission_manager = PermissionManager()
        self.pending_request: Optional[PermissionRequest] = None

    def execute(self, context: HookContext) -> Optional[Dict[str, Any]]:
        """执行权限检查"""
        event = context.event

        if event == HookEvent.PRE_TOOL_USE:
            return self._check_tool_permission(context)
        elif event == HookEvent.PRE_ROUTE:
            return self._check_route_permission(context)

        return None

    def _check_tool_permission(self, context: HookContext) -> Optional[Dict[str, Any]]:
        """检查工具使用权限"""
        tool_name = context.get("tool_name", "")
        params = context.get("params", {})

        # 检查是否是危险工具
        danger_level = self._get_tool_danger_level(tool_name, params)

        if danger_level == DangerLevel.LOW:
            return None  # 无需确认

        # 检查是否需要确认
        auto_decision = self.permission_manager.should_auto_approve(tool_name, params)

        if auto_decision is True:
            return None  # 自动批准
        elif auto_decision is False:
            return {"blocked": True, "error": "此操作已被自动拒绝"}

        # 需要用户确认
        request = PermissionRequest(
            action=tool_name,
            description=self._get_tool_description(tool_name, params),
            danger_level=danger_level,
            details=params
        )

        self.pending_request = request

        # 返回确认请求
        return {
            "requires_confirmation": True,
            "permission_request": request.to_dict(),
            "message": self._format_confirmation_message(request)
        }

    def _check_route_permission(self, context: HookContext) -> Optional[Dict[str, Any]]:
        """检查路由权限"""
        route = context.get("route", "")
        params = context.get("params", {})

        # 检查是否是危险路由
        if route not in self.REQUIRES_CONFIRMATION_ROUTES:
            return None

        danger_level = self.REQUIRES_CONFIRMATION_ROUTES[route]

        # 特殊处理 bash 路由 - 检查危险命令
        if route == "bash":
            command = params.get("command", "")
            cmd_danger_level = self._get_command_danger_level(command)
            if cmd_danger_level == DangerLevel.CRITICAL:
                danger_level = DangerLevel.CRITICAL
            elif cmd_danger_level == DangerLevel.HIGH and danger_level != DangerLevel.CRITICAL:
                danger_level = DangerLevel.HIGH

        if danger_level == DangerLevel.LOW:
            return None

        # 检查是否需要确认
        auto_decision = self.permission_manager.should_auto_approve(route, params)

        if auto_decision is True:
            return None
        elif auto_decision is False:
            return {"blocked": True, "error": "此操作已被自动拒绝"}

        # 需要用户确认
        request = PermissionRequest(
            action=route,
            description=self._get_route_description(route, params),
            danger_level=danger_level,
            details=params
        )

        self.pending_request = request

        return {
            "requires_confirmation": True,
            "permission_request": request.to_dict(),
            "message": self._format_confirmation_message(request)
        }

    def _get_tool_danger_level(self, tool_name: str, params: Dict[str, Any]) -> str:
        """获取工具的危险等级"""
        # 文件编辑工具
        if tool_name == "file_edit":
            path = params.get("path", "")
            if self._is_dangerous_path(path):
                return DangerLevel.HIGH
            return DangerLevel.LOW

        # Bash 工具
        if tool_name == "bash":
            command = params.get("command", "")
            return self._get_command_danger_level(command)

        return DangerLevel.LOW

    def _get_command_danger_level(self, command: str) -> str:
        """获取命令的危险等级"""
        import re

        max_level = DangerLevel.LOW
        level_order = {
            DangerLevel.LOW: 0,
            DangerLevel.MEDIUM: 1,
            DangerLevel.HIGH: 2,
            DangerLevel.CRITICAL: 3,
        }

        for pattern, level in DANGEROUS_COMMANDS.items():
            if re.match(pattern, command, re.IGNORECASE):
                if level_order.get(level, 0) > level_order.get(max_level, 0):
                    max_level = level

        return max_level

    def _is_dangerous_path(self, path: str) -> bool:
        """检查是否是危险路径"""
        import fnmatch

        for pattern in DANGEROUS_PATHS:
            if fnmatch.fnmatch(path, pattern):
                return True

        return False

    def _get_tool_description(self, tool_name: str, params: Dict[str, Any]) -> str:
        """获取工具描述"""
        if tool_name == "file_edit":
            path = params.get("path", "")
            return f"编辑文件：{path}"
        elif tool_name == "bash":
            cmd = params.get("command", "")[:100]
            return f"执行命令：{cmd}"
        return f"执行操作：{tool_name}"

    def _get_route_description(self, route: str, params: Dict[str, Any]) -> str:
        """获取路由描述"""
        if route == "bash":
            cmd = params.get("command", "")[:100]
            return f"执行命令：{cmd}"
        elif route == "file_edit":
            path = params.get("path", "")
            return f"编辑文件：{path}"
        elif route == "glob":
            pattern = params.get("pattern", "")
            return f"查找文件：{pattern}"
        elif route == "grep":
            pattern = params.get("pattern", "")
            return f"搜索内容：{pattern}"
        return f"执行路由：{route}"

    def _format_confirmation_message(self, request: PermissionRequest) -> str:
        """格式化确认消息"""
        icons = {
            DangerLevel.LOW: " ",
            DangerLevel.MEDIUM: "⚠️",
            DangerLevel.HIGH: "🛑",
            DangerLevel.CRITICAL: "🚫",
        }

        icon = icons.get(request.danger_level, "⚠️")

        message = f"""{icon} **{request.danger_level.upper()} 风险操作**

{request.description}

请确认是否继续执行此操作。
- 回复 **确认** 或 **yes** 批准
- 回复 **拒绝** 或 **no** 拒绝
- 回复 **记住此选择** 将选择保存到配置"""

        return message

    def confirm_pending_request(
        self,
        confirmed: bool,
        remember: bool = False
    ) -> Optional[PermissionRequest]:
        """确认待处理的请求

        Args:
            confirmed: 是否确认
            remember: 是否记住选择

        Returns:
            PermissionRequest: 已确认的请求，如果没有待处理请求则返回 None
        """
        if not self.pending_request:
            return None

        request = self.pending_request
        request.confirmed = confirmed
        request.remember_choice = remember

        if confirmed:
            self.permission_manager.approve(
                request.action,
                request.details,
                remember
            )
        else:
            self.permission_manager.deny(
                request.action,
                request.details,
                remember
            )

        self.pending_request = None
        return request

    def get_permission_config(self) -> Dict[str, Any]:
        """获取权限配置"""
        return self.permission_manager.get_config()

    def add_auto_approve_pattern(self, pattern: str) -> None:
        """添加自动批准模式"""
        self.permission_manager.add_auto_approve(pattern)

    def add_auto_deny_pattern(self, pattern: str) -> None:
        """添加自动拒绝模式"""
        self.permission_manager.add_auto_deny(pattern)


# 全局权限管理器实例
_global_permission_manager: Optional[PermissionManager] = None


def get_permission_manager() -> PermissionManager:
    """获取全局权限管理器"""
    global _global_permission_manager
    if _global_permission_manager is None:
        _global_permission_manager = PermissionManager()
    return _global_permission_manager


def check_permission(
    action: str,
    details: Dict[str, Any] = None
) -> Optional[PermissionRequest]:
    """检查权限（便捷函数）

    Args:
        action: 动作名称
        details: 动作详情

    Returns:
        PermissionRequest: 如果需要确认则返回请求，否则返回 None
    """
    manager = get_permission_manager()
    auto_decision = manager.should_auto_approve(action, details or {})

    if auto_decision is True:
        return None
    elif auto_decision is False:
        return PermissionRequest(
            action=action,
            description=action,
            danger_level=DangerLevel.HIGH,
            details=details or {},
            requires_confirmation=True
        )

    # 默认需要确认
    return PermissionRequest(
        action=action,
        description=action,
        danger_level=DangerLevel.MEDIUM,
        details=details or {},
        requires_confirmation=True
    )
