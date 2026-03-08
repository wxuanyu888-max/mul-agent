"""Router - Route dispatcher"""

from typing import Any, Dict, Callable

from mul_agent.brain.handlers import (
    CreateUserHandler,
    BashHandler,
    HeartHandler,
    MemoryHandler,
    ChatHandler,
    ResponseHandler,
    TokenUsageHandler,
    CreateTeamHandler,
    FileEditHandler,
    NetworkDelegateHandler,
    NetworkSendHandler,
    NetworkCheckHandler,
    NetworkBroadcastHandler,
    NetworkHandoverHandler,
)
from mul_agent.common.error_handler import (
    StandardErrorCodes,
    create_error_response,
    create_error_response_from_exception,
)
from mul_agent.common.response import create_success_response

# Skill/Command 支持
from mul_agent.skills.manager import SkillManager
from mul_agent.commands.manager import CommandManager

# 导入 memory 用于创建交接文档
from datetime import datetime


class Router:
    """路由分发器"""

    ROUTES: Dict[str, Callable] = {
        "create_user": CreateUserHandler,
        "bash": BashHandler,
        "heart": HeartHandler,
        "memory": MemoryHandler,
        "chat": ChatHandler,
        "response": ResponseHandler,
        "token_usage": TokenUsageHandler,
        "create_team": CreateTeamHandler,
        "file_edit": FileEditHandler,
        # Agent 网络相关路由
        "network_delegate": NetworkDelegateHandler,
        "network_send": NetworkSendHandler,
        "network_check": NetworkCheckHandler,
        "network_broadcast": NetworkBroadcastHandler,
        "network_handover": NetworkHandoverHandler,
    }

    def __init__(self, config_manager, agent_id: str = None):
        self.config_manager = config_manager
        self.agent_id = agent_id
        self.handlers = {
            name: handler(config_manager, agent_id)
            for name, handler in self.ROUTES.items()
        }

        # 初始化 Skill 和 Command 管理器
        self.skill_manager = SkillManager(config_manager, agent_id)
        self.command_manager = CommandManager(config_manager, agent_id)

        # 初始化 Memory（用于创建交接文档）
        from mul_agent.memory.memory import Memory
        self.memory_manager = Memory(config_manager, agent_id)

    def dispatch(self, route: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """根据路由名分发到对应处理器"""
        # 特殊路由：batch - 批量执行多个命令
        if route == "batch":
            # 支持两种格式：
            # 1. params = {"commands": [...]} - 标准格式
            # 2. params = {"route": "batch", "commands": [...]} - LLM 直接返回的格式
            commands = params.get("commands", [])
            if not commands:
                return create_error_response(
                    error_code=StandardErrorCodes.INVALID_PARAMS,
                    message="commands list is required for batch route",
                    route=route
                )

            # 分离不同类型的命令
            serial_cmds = []
            parallel_cmds = []
            async_cmds = []

            for cmd in commands:
                if cmd.get('async'):
                    async_cmds.append(cmd)
                elif cmd.get('parallel'):
                    parallel_cmds.append(cmd)
                else:
                    serial_cmds.append(cmd)

            # 创建交接文档（如果有 chat 或其他委派任务）
            for cmd in commands:
                if cmd.get('route') in ['chat', 'network_delegate']:
                    self._create_handover_for_task(cmd, params.get('user_input', ''))

            try:
                results = []

                # 1. 执行串行命令
                for cmd in serial_cmds:
                    cmd_route = cmd.get("route")
                    cmd_params = cmd.get("params", {})
                    result = self.dispatch(cmd_route, cmd_params)
                    results.append({
                        "route": cmd_route,
                        "result": result,
                        "type": "serial"
                    })

                # 2. 并行执行命令
                if parallel_cmds:
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future_to_cmd = {
                            executor.submit(self.dispatch, cmd.get("route"), cmd.get("params", {})): cmd
                            for cmd in parallel_cmds
                        }
                        for future in concurrent.futures.as_completed(future_to_cmd):
                            cmd = future_to_cmd[future]
                            try:
                                result = future.result()
                                results.append({
                                    "route": cmd.get("route"),
                                    "result": result,
                                    "type": "parallel"
                                })
                            except Exception as e:
                                results.append({
                                    "route": cmd.get("route"),
                                    "result": {"status": "error", "message": str(e)},
                                    "type": "parallel"
                                })

                # 3. 异步命令（后台执行，不等待）
                if async_cmds:
                    import threading
                    for cmd in async_cmds:
                        def run_async(cmd=cmd):
                            try:
                                self.dispatch(cmd.get("route"), cmd.get("params", {}))
                            except Exception as e:
                                print(f"Async command error: {e}")
                        thread = threading.Thread(target=run_async)
                        thread.start()
                        results.append({
                            "route": cmd.get("route"),
                            "result": {"status": "async", "message": "后台执行中"},
                            "type": "async"
                        })

                # 汇总所有结果
                return create_success_response(
                    data={
                        "batch_results": results,
                        "total_commands": len(commands),
                        "successful": len([r for r in results if r["result"].get("status") == "success"]),
                        "serial_count": len(serial_cmds),
                        "parallel_count": len(parallel_cmds),
                        "async_count": len(async_cmds)
                    },
                    route=route
                )
            except Exception as e:
                return create_error_response_from_exception(
                    exception=e,
                    default_error_code=StandardErrorCodes.HANDLER_ERROR,
                    route=route
                )

        # 特殊路由：skill - 执行技能
        if route == "skill":
            skill_id = params.get("skill_id")
            if not skill_id:
                return create_error_response(
                    error_code=StandardErrorCodes.INVALID_PARAMS,
                    message="skill_id is required",
                    route=route
                )
            try:
                # 移除 params 中的 skill_id，避免重复参数
                skill_params = {k: v for k, v in params.items() if k != "skill_id"}
                result = self.skill_manager.execute_skill(skill_id, **skill_params)
                return create_success_response(data=result, route=route)
            except Exception as e:
                return create_error_response_from_exception(
                    exception=e,
                    default_error_code=StandardErrorCodes.HANDLER_ERROR,
                    route=route
                )

        # 特殊路由：command - 执行命令
        if route == "command":
            command_name = params.get("command")
            args_str = params.get("args", "")
            if not command_name:
                return create_error_response(
                    error_code=StandardErrorCodes.INVALID_PARAMS,
                    message="command is required",
                    route=route
                )
            try:
                result = self.command_manager.execute(command_name, args_str)
                return create_success_response(data=result.to_dict(), route=route)
            except Exception as e:
                return create_error_response_from_exception(
                    exception=e,
                    default_error_code=StandardErrorCodes.HANDLER_ERROR,
                    route=route
                )

        # 标准路由处理
        if route not in self.handlers:
            return create_error_response(
                error_code=StandardErrorCodes.ROUTE_NOT_FOUND,
                message=f"Unknown route: {route}",
                route=route,
                details={"available_routes": list(self.ROUTES.keys()) + ["skill", "command"]}
            )

        handler = self.handlers[route]
        try:
            # Special handling for "response" route - allow empty params
            if route == "response" and not params:
                return {
                    "status": "success",
                    "message": "",
                    "type": "direct_response"
                }

            result = handler.handle(params)
            # 标准化响应格式
            if isinstance(result, dict):
                if result.get("status") == "error":
                    # Handler 已经返回错误，标准化格式
                    return create_error_response(
                        error_code=self._get_error_code(result.get("error_code", 1002)),
                        message=result.get("message", "Handler error"),
                        route=route,
                        details=result.get("details")
                    )
                # For "response" route, return the message directly without wrapping
                if route == "response":
                    return result
                return create_success_response(
                    data=result,
                    route=route
                )
            else:
                return create_success_response(
                    data={"output": result},
                    route=route
                )
        except Exception as e:
            return create_error_response_from_exception(
                exception=e,
                default_error_code=StandardErrorCodes.HANDLER_ERROR,
                route=route
            )

    def _get_error_code(self, code: int) -> StandardErrorCodes:
        """根据错误码获取标准错误码"""
        error_code_map = {
            1000: StandardErrorCodes.ROUTER_ERROR,
            1001: StandardErrorCodes.INVALID_PARAMS,
            1002: StandardErrorCodes.HANDLER_ERROR,
            1003: StandardErrorCodes.COMMAND_FORBIDDEN,
            1004: StandardErrorCodes.MISSING_PARAMS,
            1005: StandardErrorCodes.UNKNOWN_ACTION,
            1006: StandardErrorCodes.COMMAND_EXECUTION_FAILED,
            2000: StandardErrorCodes.CHAT_ERROR,
            2001: StandardErrorCodes.UNKNOWN_CHAT_ACTION,
            2002: StandardErrorCodes.AGENT_NOT_FOUND,
            2003: StandardErrorCodes.CONVERSATION_NOT_FOUND,
            3001: StandardErrorCodes.AGENT_ID_MISSING,
            3002: StandardErrorCodes.UNKNOWN_TOKEN_ACTION,
        }
        return error_code_map.get(code, StandardErrorCodes.UNKNOWN_ERROR)

    def list_routes(self) -> list:
        """列出所有可用路由"""
        return [
            {
                "name": name,
                "handler": handler.__class__.__name__
            }
            for name, handler in self.handlers.items()
        ]

    def _create_handover_for_task(self, cmd: Dict, user_input: str):
        """为委派任务创建交接文档

        命名规范：事情 - 人物-i 序号
        文档首页包含：description、有效期限、作用范围
        """
        from_agent = self.agent_id or 'core_brain'
        to_agent = cmd.get('params', {}).get('agent_id', 'unknown')
        task_type = cmd.get('route', 'task')

        # 生成任务序号
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        task_num = f"i{timestamp[-6:]}"

        # 任务名称：事情 - 人物-i 序号
        if task_type == 'chat':
            task_name = f"对话协作-{to_agent}-{task_num}"
        elif task_type == 'network_delegate':
            task_name = f"任务委派-{to_agent}-{task_num}"
        else:
            task_name = f"{task_type}-{to_agent}-{task_num}"

        # 构建交接内容
        content = {
            "task_name": task_name,
            "description": f"来自 {from_agent} 的协作请求：{user_input[:200]}",
            "deadline": "24 小时内",
            "scope": f"涉及 Agent: {to_agent}",
            "priority": "MEDIUM",
            "task_content": cmd.get('params', {}).get('message', '无具体内容')
        }

        # 调用 memory 创建交接文档
        try:
            self.memory_manager.create_handover(from_agent, to_agent, content)
        except Exception:
            # 如果 memory 不可用，不中断主流程
            pass
