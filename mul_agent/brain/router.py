"""Router - Route dispatcher"""

from typing import Any, Dict, Callable

from mul_agent.brain.handlers import (
    CreateUserHandler,
    BashHandler,
    ChatHandler,
    CreateTeamHandler,
    FileEditHandler,
    HeartHandler,
    GlobHandler,
    GrepHandler,
    SubagentHandler,
    CodeUnderstandingHandler,
    ChainOfThoughtHandler,
    VisualizationHandler,
    PlannerHandler,
    MemeticHandler,
    GitDiffHandler,
    GitStatusHandler,
    GitCommitHandler,
    GitLogHandler,
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


class Router:
    """路由分发器

    核心路由:
    - bash: 执行 shell 命令
    - file_edit: 文件编辑
    - glob: 文件名模式匹配
    - grep: 文件内容搜索
    - code_understanding: 代码理解
    - cot: 推理链执行
    - visualization: 执行可视化
    - planner: 自主规划
    - memetic: 经验学习
    - chat: 与其他 Agent 对话
    - create: 创建 Agent 或团队
    """

    ROUTES: Dict[str, Callable] = {
        "bash": BashHandler,
        "file_edit": FileEditHandler,
        "glob": GlobHandler,
        "grep": GrepHandler,
        "code_understanding": CodeUnderstandingHandler,
        "cot": ChainOfThoughtHandler,
        "visualization": VisualizationHandler,
        "planner": PlannerHandler,
        "memetic": MemeticHandler,
        "chat": ChatHandler,
        "create_user": CreateUserHandler,
        "create_team": CreateTeamHandler,
        "heart": HeartHandler,
        "subagent": SubagentHandler,
        "git_diff": GitDiffHandler,
        "git_status": GitStatusHandler,
        "git_commit": GitCommitHandler,
        "git_log": GitLogHandler,
    }

    # 合并的 create 路由别名
    CREATE_ROUTES = {"create_user", "create_team"}

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

    def dispatch(self, route: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """根据路由名分发到对应处理器"""

        # 特殊路由：batch - 批量执行多个命令
        if route == "batch":
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
                details={"available_routes": list(self.ROUTES.keys()) + ["skill", "command", "batch"]}
            )

        handler = self.handlers[route]
        try:
            result = handler.handle(params)
            if isinstance(result, dict):
                if result.get("status") == "error":
                    return create_error_response(
                        error_code=self._get_error_code(result.get("error_code", 1002)),
                        message=result.get("message", "Handler error"),
                        route=route,
                        details=result.get("details")
                    )
                return create_success_response(data=result, route=route)
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
