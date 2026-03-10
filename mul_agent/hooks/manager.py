"""Hook Manager - 钩子管理器"""

import importlib
import inspect
from pathlib import Path
from typing import Any, Dict, List, Optional, Type

from .base import BaseHook, HookEvent, HookMetadata


class HookManager:
    """钩子管理器

    负责注册、管理和触发钩子
    """

    def __init__(self, config_manager=None, agent_id: str = None):
        """初始化钩子管理器

        Args:
            config_manager: 配置管理器
            agent_id: Agent ID
        """
        self.config_manager = config_manager
        self.agent_id = agent_id or "default"
        self._hooks: Dict[str, BaseHook] = {}  # hook_id -> hook instance
        self._event_handlers: Dict[HookEvent, List[str]] = {  # event -> [hook_ids]
            event: [] for event in HookEvent
        }
        self._load_builtin_hooks()

    def _load_builtin_hooks(self) -> None:
        """加载内置钩子"""
        try:
            from . import builtin
            # 自动注册 builtin 模块中的所有 Hook 类
            for name, obj in inspect.getmembers(builtin):
                if (inspect.isclass(obj) and
                    issubclass(obj, BaseHook) and
                    obj != BaseHook and
                    hasattr(obj, 'hook_id')):
                    self.register_hook(obj)
        except ImportError:
            pass  # builtin 模块可能不存在

    def register_hook(self, hook_class: Type[BaseHook], instance: Optional[BaseHook] = None) -> Optional[str]:
        """注册钩子

        Args:
            hook_class: 钩子类
            instance: 可选的钩子实例，如果不提供则创建新实例

        Returns:
            Optional[str]: 钩子 ID，如果注册失败返回 None
        """
        try:
            # 创建或使用了提供的实例
            hook_instance = instance if instance is not None else hook_class(
                config_manager=self.config_manager,
                agent_id=self.agent_id
            )

            # 初始化钩子
            if not hook_instance.initialize():
                print(f"Failed to initialize hook: {hook_class.hook_id}")
                return None

            # 检查是否已存在
            if hook_instance.hook_id in self._hooks:
                print(f"Hook already registered: {hook_instance.hook_id}")
                return hook_instance.hook_id

            # 注册钩子实例
            self._hooks[hook_instance.hook_id] = hook_instance

            # 注册事件处理器
            self._register_event_handlers(hook_instance)

            return hook_instance.hook_id

        except Exception as e:
            print(f"Error registering hook {hook_class.hook_id}: {e}")
            return None

    def _register_event_handlers(self, hook: BaseHook) -> None:
        """为钩子注册事件处理器

        Args:
            hook: 钩子实例
        """
        # 检查钩子是否覆盖了各个事件方法
        hook_class = hook.__class__

        # 为每个事件类型检查是否有自定义实现
        event_methods = {
            HookEvent.PRE_TOOL_USE: 'pre_tool_use',
            HookEvent.POST_TOOL_USE: 'post_tool_use',
            HookEvent.SESSION_START: 'session_start',
            HookEvent.SESSION_END: 'session_end',
            HookEvent.PRE_MESSAGE: 'pre_message',
            HookEvent.POST_MESSAGE: 'post_message',
            HookEvent.PRE_COMMAND: 'pre_command',
            HookEvent.POST_COMMAND: 'post_command',
        }

        for event, method_name in event_methods.items():
            # 检查是否覆盖了该方法
            if getattr(hook_class, method_name) is not getattr(BaseHook, method_name):
                self._event_handlers[event].append(hook.hook_id)

    def unregister_hook(self, hook_id: str) -> bool:
        """注销钩子

        Args:
            hook_id: 钩子 ID

        Returns:
            bool: 是否注销成功
        """
        if hook_id not in self._hooks:
            return False

        # 从所有事件处理器中移除
        hook = self._hooks[hook_id]
        for event in self._event_handlers:
            if hook_id in self._event_handlers[event]:
                self._event_handlers[event].remove(hook_id)

        # 删除钩子实例
        del self._hooks[hook_id]
        return True

    def get_hook(self, hook_id: str) -> Optional[BaseHook]:
        """获取钩子

        Args:
            hook_id: 钩子 ID

        Returns:
            Optional[BaseHook]: 钩子实例，如果不存在返回 None
        """
        return self._hooks.get(hook_id)

    def list_hooks(self) -> List[Dict[str, Any]]:
        """列出所有已注册的钩子

        Returns:
            List[Dict]: 钩子元数据列表
        """
        return [hook.get_metadata().__dict__ for hook in self._hooks.values()]

    def get_hooks_by_event(self, event: HookEvent) -> List[BaseHook]:
        """根据事件获取相关的钩子

        Args:
            event: 钩子事件

        Returns:
            List[BaseHook]: 钩子实例列表
        """
        hook_ids = self._event_handlers.get(event, [])
        return [self._hooks[hook_id] for hook_id in hook_ids if hook_id in self._hooks]

    def get_hooks_by_tag(self, tag: str) -> List[BaseHook]:
        """根据标签获取钩子

        Args:
            tag: 钩子标签

        Returns:
            List[BaseHook]: 钩子实例列表
        """
        return [
            hook for hook in self._hooks.values()
            if tag in hook.hook_tags
        ]

    # =========================================================================
    # 触发钩子
    # =========================================================================

    def trigger_hooks(self, event: HookEvent, *args, **kwargs) -> Any:
        """触发指定事件的钩子

        Args:
            event: 钩子事件
            *args: 事件参数
            **kwargs: 事件关键字参数

        Returns:
            Any: 最后一个钩子的返回值，如果没有钩子则返回 None 或初始值
        """
        hooks = self.get_hooks_by_event(event)
        if not hooks:
            return kwargs.get('context', kwargs.get('result', kwargs.get('params', {})))

        result = kwargs.get('context', kwargs.get('result', kwargs.get('params', {})))

        for hook in hooks:
            if not hook.enabled:
                continue

            try:
                method_name = {
                    HookEvent.PRE_TOOL_USE: 'pre_tool_use',
                    HookEvent.POST_TOOL_USE: 'post_tool_use',
                    HookEvent.SESSION_START: 'session_start',
                    HookEvent.SESSION_END: 'session_end',
                    HookEvent.PRE_MESSAGE: 'pre_message',
                    HookEvent.POST_MESSAGE: 'post_message',
                    HookEvent.PRE_COMMAND: 'pre_command',
                    HookEvent.POST_COMMAND: 'post_command',
                }.get(event)

                if method_name:
                    method = getattr(hook, method_name)
                    result = method(*args, **kwargs)
            except Exception as e:
                print(f"Error executing hook {hook.hook_id}.{method_name}: {e}")

        return result

    def trigger_pre_tool_use(self, route: str, params: dict) -> dict:
        """触发工具使用前钩子

        Args:
            route: 工具路由
            params: 工具参数

        Returns:
            dict: 修改后的参数
        """
        return self.trigger_hooks(
            HookEvent.PRE_TOOL_USE,
            route=route,
            params=params
        )

    def trigger_post_tool_use(self, route: str, params: dict, result: dict) -> dict:
        """触发工具使用后钩子

        Args:
            route: 工具路由
            params: 工具参数
            result: 工具执行结果

        Returns:
            dict: 修改后的结果
        """
        return self.trigger_hooks(
            HookEvent.POST_TOOL_USE,
            route=route,
            params=params,
            result=result
        )

    def trigger_session_start(self, context: Optional[dict] = None) -> dict:
        """触发会话开始钩子

        Args:
            context: 会话上下文

        Returns:
            dict: 修改后的上下文
        """
        if context is None:
            context = {}
        return self.trigger_hooks(HookEvent.SESSION_START, context=context)

    def trigger_session_end(self, context: Optional[dict] = None) -> dict:
        """触发会话结束钩子

        Args:
            context: 会话上下文

        Returns:
            dict: 修改后的上下文
        """
        if context is None:
            context = {}
        return self.trigger_hooks(HookEvent.SESSION_END, context=context)

    def trigger_pre_message(self, context: dict) -> dict:
        """触发消息处理前钩子

        Args:
            context: 消息上下文

        Returns:
            dict: 修改后的上下文
        """
        return self.trigger_hooks(HookEvent.PRE_MESSAGE, context=context)

    def trigger_post_message(self, context: dict, response: dict) -> dict:
        """触发消息处理后钩子

        Args:
            context: 消息上下文
            response: 响应内容

        Returns:
            dict: 修改后的响应
        """
        return self.trigger_hooks(
            HookEvent.POST_MESSAGE,
            context=context,
            response=response
        )

    def trigger_pre_command(self, command: str, args: str) -> tuple:
        """触发命令执行前钩子

        Args:
            command: 命令名称
            args: 命令参数

        Returns:
            tuple: (command, args) 修改后的命令和参数
        """
        result = self.trigger_hooks(
            HookEvent.PRE_COMMAND,
            command=command,
            args=args
        )
        return result if isinstance(result, tuple) else (command, args)

    def trigger_post_command(self, command: str, args: str, result: dict) -> dict:
        """触发命令执行后钩子

        Args:
            command: 命令名称
            args: 命令参数
            result: 命令执行结果

        Returns:
            dict: 修改后的结果
        """
        return self.trigger_hooks(
            HookEvent.POST_COMMAND,
            command=command,
            args=args,
            result=result
        )

    # =========================================================================
    # 管理方法
    # =========================================================================

    def enable_hook(self, hook_id: str) -> bool:
        """启用钩子

        Args:
            hook_id: 钩子 ID

        Returns:
            bool: 是否成功启用
        """
        hook = self.get_hook(hook_id)
        if hook:
            hook.enabled = True
            return True
        return False

    def disable_hook(self, hook_id: str) -> bool:
        """禁用钩子

        Args:
            hook_id: 钩子 ID

        Returns:
            bool: 是否成功禁用
        """
        hook = self.get_hook(hook_id)
        if hook:
            hook.enabled = False
            return True
        return False

    def reload_all(self) -> None:
        """重新加载所有钩子"""
        # 保存当前钩子配置
        hook_ids = list(self._hooks.keys())

        # 清空所有钩子
        self._hooks.clear()
        for event in self._event_handlers:
            self._event_handlers[event] = []

        # 重新加载内置钩子
        self._load_builtin_hooks()

    def to_dict(self) -> Dict[str, Any]:
        """将钩子管理器转换为字典

        Returns:
            Dict: 钩子管理器字典
        """
        return {
            "agent_id": self.agent_id,
            "hooks_count": len(self._hooks),
            "hooks": self.list_hooks(),
            "event_handlers": {
                event.value: hook_ids
                for event, hook_ids in self._event_handlers.items()
            }
        }

    def __str__(self) -> str:
        """字符串表示"""
        return f"HookManager(agent_id={self.agent_id}, hooks={len(self._hooks)})"

    def __repr__(self) -> str:
        """详细字符串表示"""
        return f"<HookManager(agent_id='{self.agent_id}', hooks={len(self._hooks)})>"
