"""Hook Manager - 钩子管理器"""

import importlib
from pathlib import Path
from typing import Any, Dict, List, Optional, Type, Callable
import json

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

from mul_agent.hooks.base import BaseHook, HookEvent, HookContext, HookPriority


class HookManager:
    """钩子管理器

    负责：
    - 注册钩子
    - 触发钩子
    - 钩子生命周期管理
    - 从配置文件加载钩子
    """

    def __init__(self, config_manager=None, agent_id: str = None):
        """初始化钩子管理器

        Args:
            config_manager: 配置管理器
            agent_id: Agent ID
        """
        self.config_manager = config_manager
        self.agent_id = agent_id or "wangyue"

        # 已注册的钩子实例，按事件分组
        self._hooks: Dict[HookEvent, List[BaseHook]] = {
            event: [] for event in HookEvent
        }

        # 钩子元数据缓存
        self._hook_metadata: Dict[str, Dict[str, Any]] = {}

        # 加载内置钩子和配置文件钩子
        self._load_builtin_hooks()
        self._load_hook_configs()

    def _load_builtin_hooks(self) -> None:
        """加载内置钩子"""
        builtin_hooks = [
            "mul_agent.hooks.builtin.LogInvocationHook",
            "mul_agent.hooks.builtin.FormatOutputHook",
        ]

        for hook_path in builtin_hooks:
            try:
                module_path, class_name = hook_path.rsplit(".", 1)
                module = importlib.import_module(module_path)
                hook_class = getattr(module, class_name)
                self.register_hook(hook_class)
            except Exception as e:
                print(f"Error loading builtin hook {hook_path}: {e}")

    def _load_hook_configs(self) -> None:
        """从配置加载钩子"""
        try:
            # 从 soul.md 或 user.md 中加载钩子配置
            soul_config = self.config_manager.load(self.agent_id, "soul")
            hooks_config = soul_config.get("hooks", [])

            for hook_data in hooks_config:
                hook_id = hook_data.get("id")
                enabled = hook_data.get("enabled", True)

                if not enabled:
                    continue

                # 尝试加载动态钩子
                module_path = hook_data.get("module_path")
                if module_path:
                    try:
                        module = importlib.import_module(module_path)
                        class_name = hook_data.get("class_name", "DynamicHook")
                        hook_class = getattr(module, class_name)
                        self.register_hook(hook_class)
                    except Exception as e:
                        print(f"Error loading dynamic hook {module_path}: {e}")
        except Exception as e:
            print(f"Error loading hook configs: {e}")

    def register_hook(self, hook_class: Type[BaseHook], instance: BaseHook = None) -> str:
        """注册钩子

        Args:
            hook_class: 钩子类
            instance: 钩子实例（如果为 None 则自动创建）

        Returns:
            str: 钩子 ID
        """
        if instance is None:
            instance = hook_class(
                config_manager=self.config_manager,
                agent_id=self.agent_id
            )

        # 初始化钩子
        if not instance.initialize():
            raise ValueError(f"Failed to initialize hook {instance.hook_id}")

        # 注册到对应的事件
        for event in instance.events:
            if event in self._hooks:
                # 按优先级插入（优先级高的在前）
                hooks_list = self._hooks[event]
                insert_index = 0
                for i, existing_hook in enumerate(hooks_list):
                    if existing_hook.priority.value > instance.priority.value:
                        insert_index = i
                        break
                    insert_index = i + 1
                hooks_list.insert(insert_index, instance)

        # 记录元数据
        self._hook_metadata[instance.hook_id] = instance.get_metadata()

        return instance.hook_id

    def unregister_hook(self, hook_id: str) -> bool:
        """注销钩子"""
        removed = False
        for event, hooks in self._hooks.items():
            for i, hook in enumerate(hooks):
                if hook.hook_id == hook_id:
                    hooks.pop(i)
                    removed = True
                    break

        if hook_id in self._hook_metadata:
            del self._hook_metadata[hook_id]

        return removed

    def trigger_hooks(self, event: HookEvent, data: Dict[str, Any] = None) -> Dict[str, Any]:
        """触发钩子

        Args:
            event: 事件类型
            data: 事件数据

        Returns:
            Dict: 处理后的数据（可能被钩子修改）
        """
        if event not in self._hooks:
            return data or {}

        context = HookContext(
            event=event,
            agent_id=self.agent_id,
            data=data or {}
        )

        for hook in self._hooks[event]:
            if not hook.enabled:
                continue

            try:
                result = hook.execute(context)
                # 钩子可以修改 context.data
                if result:
                    context.data.update(result)
            except Exception as e:
                print(f"Error executing hook {hook.hook_id}: {e}")
                # 继续执行其他钩子

        return context.data

    def trigger_pre_tool_use(self, tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """触发 PreToolUse 钩子

        Args:
            tool_name: 工具名称
            params: 工具参数

        Returns:
            Dict: 可能修改后的参数
        """
        data = {"tool_name": tool_name, "params": params}
        return self.trigger_hooks(HookEvent.PRE_TOOL_USE, data)

    def trigger_post_tool_use(
        self,
        tool_name: str,
        params: Dict[str, Any],
        result: Any
    ) -> Dict[str, Any]:
        """触发 PostToolUse 钩子

        Args:
            tool_name: 工具名称
            params: 工具参数
            result: 执行结果

        Returns:
            Dict: 可能修改后的结果
        """
        data = {"tool_name": tool_name, "params": params, "result": result}
        return self.trigger_hooks(HookEvent.POST_TOOL_USE, data)

    def trigger_session_start(self) -> Dict[str, Any]:
        """触发 SessionStart 钩子"""
        return self.trigger_hooks(HookEvent.SESSION_START, {})

    def trigger_session_end(self, session_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """触发 SessionEnd 钩子"""
        return self.trigger_hooks(HookEvent.SESSION_END, session_data or {})

    def list_hooks(self, event: HookEvent = None) -> List[Dict[str, Any]]:
        """列出所有钩子

        Args:
            event: 可选，只列出某个事件的钩子

        Returns:
            List[Dict]: 钩子元数据列表
        """
        if event:
            return [hook.get_metadata() for hook in self._hooks.get(event, [])]
        return list(self._hook_metadata.values())

    def enable_hook(self, hook_id: str) -> bool:
        """启用钩子"""
        for event, hooks in self._hooks.items():
            for hook in hooks:
                if hook.hook_id == hook_id:
                    hook.enabled = True
                    self._hook_metadata[hook_id]["enabled"] = True
                    return True
        return False

    def disable_hook(self, hook_id: str) -> bool:
        """禁用钩子"""
        for event, hooks in self._hooks.items():
            for hook in hooks:
                if hook.hook_id == hook_id:
                    hook.enabled = False
                    self._hook_metadata[hook_id]["enabled"] = False
                    return True
        return False

    def add_hook_function(
        self,
        event: HookEvent,
        callback: Callable[[HookContext], Optional[Dict[str, Any]]],
        priority: HookPriority = HookPriority.NORMAL,
        hook_id: str = None
    ) -> str:
        """添加函数钩子

        Args:
            event: 事件类型
            callback: 回调函数
            priority: 优先级
            hook_id: 钩子 ID（可选）

        Returns:
            str: 钩子 ID
        """
        from mul_agent.hooks.base import BaseHook

        # 创建动态钩子类
        class FunctionHook(BaseHook):
            def __init__(self, callback, events, priority, hook_id):
                self.callback = callback
                self._hook_id = hook_id
                self.events = events
                self.priority = priority
                super().__init__()

            @property
            def hook_id(self):
                return self._hook_id or f"function_hook_{id(self.callback)}"

            def _initialize(self):
                pass

            def execute(self, context):
                return self.callback(context)

        hook_instance = FunctionHook(
            callback=callback,
            events=[event],
            priority=priority,
            hook_id=hook_id
        )

        return self.register_hook(FunctionHook, hook_instance)

    def to_dict(self) -> Dict[str, Any]:
        """将钩子管理器状态转换为字典"""
        return {
            "agent_id": self.agent_id,
            "hooks_count": len(self._hook_metadata),
            "hooks_by_event": {
                event.value: [h.get_metadata() for h in hooks]
                for event, hooks in self._hooks.items()
                if hooks
            }
        }
