"""Tool Policy System - 工具策略系统

参考 OpenClaw 的工具策略设计：
1. Profile-based 策略 (minimal, coding, messaging, full)
2. Group-based 策略 (group:fs, group:runtime, group:sessions)
3. Allow/Deny 列表
4. Per-agent 策略覆盖

使用方式:
    from mul_agent.tools.policy import ToolPolicy

    # 创建策略
    policy = ToolPolicy.from_profile("coding")

    # 添加工具组
    policy.add_group("group:fs")

    # 检查工具是否允许
    if policy.is_allowed("read"):
        ...
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set
from enum import Enum


class ToolGroup(Enum):
    """工具组 - 工具类别的简写"""
    RUNTIME = "group:runtime"  # exec, bash, process
    FS = "group:fs"  # read, write, edit, apply_patch
    SESSIONS = "group:sessions"  # sessions_list, sessions_history, sessions_send
    MEMORY = "group:memory"  # memory_search, memory_get
    WEB = "group:web"  # web_search, web_fetch
    UI = "group:ui"  # browser, canvas
    AUTOMATION = "group:automation"  # cron, gateway
    MESSAGING = "group:messaging"  # message
    NODES = "group:nodes"  # nodes
    CODE = "group:code"  # glob, grep, search, git
    OPENCLAW = "group:openclaw"  # 所有内置工具


# 工具组到工具名的映射
GROUP_TOOLS: Dict[ToolGroup, List[str]] = {
    ToolGroup.RUNTIME: ["exec", "bash", "process", "kill", "bg"],
    ToolGroup.FS: ["read", "write", "edit", "apply_patch", "ls", "cat", "glob"],
    ToolGroup.SESSIONS: [
        "sessions_list", "sessions_history", "sessions_send",
        "sessions_spawn", "session_status"
    ],
    ToolGroup.MEMORY: ["memory_search", "memory_get", "memory_write"],
    ToolGroup.WEB: ["web_search", "web_fetch", "browse"],
    ToolGroup.UI: ["browser", "canvas", "screenshot"],
    ToolGroup.AUTOMATION: ["cron", "gateway", "schedule"],
    ToolGroup.MESSAGING: ["message", "send", "notify"],
    ToolGroup.NODES: ["nodes", "camera", "screen"],
    ToolGroup.CODE: ["glob", "grep", "search", "git", "git_diff", "git_status"],
    ToolGroup.OPENCLAW: [],  # 所有内置工具
}


@dataclass
class ToolPolicy:
    """工具策略

    参考 OpenClaw 设计：
    - profile: 基础工具配置
    - allow: 允许的工具列表
    - deny: 拒绝的工具列表
    - groups: 允许的工具组
    """
    profile: str = "full"  # minimal, coding, messaging, full
    allow: Set[str] = field(default_factory=set)
    deny: Set[str] = field(default_factory=set)
    groups: Set[str] = field(default_factory=set)
    also_allow: Set[str] = field(default_factory=set)  # 额外允许

    @classmethod
    def from_profile(cls, profile: str) -> "ToolPolicy":
        """从预设 profile 创建策略"""
        if profile == "minimal":
            return cls(
                profile=profile,
                allow={"session_status"},
            )
        elif profile == "coding":
            return cls(
                profile=profile,
                groups={
                    "group:fs",
                    "group:runtime",
                    "group:sessions",
                    "group:memory",
                    "group:code",
                },
                allow={"image", "glob", "grep", "search"},
            )
        elif profile == "messaging":
            return cls(
                profile=profile,
                groups={"group:messaging"},
                allow={
                    "sessions_list", "sessions_history", "sessions_send",
                    "session_status"
                },
            )
        elif profile == "full":
            return cls(profile=profile)
        else:
            raise ValueError(f"Unknown profile: {profile}")

    @classmethod
    def merge(cls, *policies: "ToolPolicy") -> "ToolPolicy":
        """合并多个策略（取并集）"""
        if not policies:
            return cls()

        result = cls(profile=policies[0].profile)
        for policy in policies:
            result.allow.update(policy.allow)
            result.deny.update(policy.deny)
            result.groups.update(policy.groups)
            result.also_allow.update(policy.also_allow)
        return result

    def add_group(self, group: str):
        """添加工具组"""
        self.groups.add(group)

    def remove_group(self, group: str):
        """移除工具组"""
        self.groups.discard(group)

    def allow_tool(self, name: str):
        """允许工具"""
        self.allow.add(name)

    def deny_tool(self, name: str):
        """拒绝工具"""
        self.deny.add(name)

    def is_allowed(self, tool_name: str) -> bool:
        """检查工具是否允许

        优先级：deny > allow > groups > profile
        """
        # deny 优先
        if tool_name in self.deny:
            return False

        # 检查是否在 also_allow 中
        if tool_name in self.also_allow:
            return True

        # 检查是否在 allow 中
        if tool_name in self.allow:
            return True

        # 检查是否在允许的组中
        for group_str in self.groups:
            try:
                group = ToolGroup(group_str)
                group_tools = GROUP_TOOLS.get(group, [])
                # 组内工具默认允许，除非被 deny
                if tool_name in group_tools:
                    return True
            except ValueError:
                # 未知的组，跳过
                continue

        # profile 为 full 时允许所有
        if self.profile == "full" and tool_name not in self.deny:
            return True

        return False

    def get_expanded_tools(self) -> Set[str]:
        """获取所有允许的工具名（展开组）"""
        tools = set(self.allow)
        tools.update(self.also_allow)

        for group_str in self.groups:
            try:
                group = ToolGroup(group_str)
                tools.update(GROUP_TOOLS.get(group, []))
            except ValueError:
                continue

        # 移除 deny 的工具
        tools -= self.deny

        return tools

    def to_dict(self) -> Dict:
        """转换为字典格式"""
        return {
            "profile": self.profile,
            "allow": sorted(self.allow),
            "deny": sorted(self.deny),
            "groups": sorted(self.groups),
            "also_allow": sorted(self.also_allow),
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "ToolPolicy":
        """从字典创建"""
        return cls(
            profile=data.get("profile", "full"),
            allow=set(data.get("allow", [])),
            deny=set(data.get("deny", [])),
            groups=set(data.get("groups", [])),
            also_allow=set(data.get("also_allow", [])),
        )


@dataclass
class AgentToolPolicy:
    """Per-Agent 工具策略

    支持：
    - 全局策略继承
    - per-agent 覆盖
    - provider-specific 策略
    """
    agent_id: str
    policy: ToolPolicy
    provider_policies: Dict[str, ToolPolicy] = field(default_factory=dict)
    sandbox_policy: Optional[ToolPolicy] = None

    def get_policy_for_provider(self, provider: str) -> ToolPolicy:
        """获取针对特定 provider 的策略"""
        if provider in self.provider_policies:
            # provider-specific 策略与基础策略合并
            return ToolPolicy.merge(self.policy, self.provider_policies[provider])
        return self.policy

    def is_allowed(self, tool_name: str, provider: str = None) -> bool:
        """检查工具是否允许"""
        if provider:
            policy = self.get_policy_for_provider(provider)
        else:
            policy = self.policy

        # sandbox 策略更严格
        if self.sandbox_policy:
            return policy.is_allowed(tool_name) and self.sandbox_policy.is_allowed(tool_name)

        return policy.is_allowed(tool_name)


def resolve_tool_groups(tools: List[str]) -> Set[str]:
    """将工具列表中的 group:* 展开为具体工具名"""
    result = set()
    for tool in tools:
        if tool.startswith("group:"):
            try:
                group = ToolGroup(tool)
                result.update(GROUP_TOOLS.get(group, []))
            except ValueError:
                continue
        else:
            result.add(tool)
    return result


def normalize_tool_name(name: str) -> str:
    """标准化工具名（小写，去除空格）"""
    return name.lower().strip().replace("-", "_")


def match_tool_pattern(tool_name: str, pattern: str) -> bool:
    """检查工具名是否匹配模式（支持通配符）"""
    if pattern == "*":
        return True
    if pattern.endswith("*"):
        return tool_name.startswith(pattern[:-1])
    if pattern.startswith("*"):
        return tool_name.endswith(pattern[1:])
    return tool_name == pattern
