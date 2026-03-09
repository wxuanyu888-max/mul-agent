"""Multi-Agent Parallel Executor - 多 Agent 并行执行器

参考 Claude Code 的多角色子代理设计：
1. 并行执行多个独立任务
2. 多视角分析（安全、性能、可维护性）
3. 结果聚合和综合
"""

import asyncio
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass
from enum import Enum
import time


class AgentRole(Enum):
    """Agent 角色"""
    SECURITY = "security"  # 安全专家
    PERFORMANCE = "performance"  # 性能专家
    MAINTAINABILITY = "maintainability"  # 可维护性专家
    ARCHITECT = "architect"  # 架构师
    DEVELOPER = "developer"  # 开发者
    TESTER = "tester"  # 测试专家
    REVIEWER = "reviewer"  # 代码审查员


@dataclass
class AgentTask:
    """Agent 任务"""
    task_id: str
    role: AgentRole
    description: str
    input_data: Dict[str, Any]
    timeout: int = 300  # 超时时间（秒）


@dataclass
class AgentResult:
    """Agent 执行结果"""
    task_id: str
    role: AgentRole
    status: str  # success, error, timeout
    result: Any
    error: Optional[str] = None
    execution_time: float = 0.0


class MultiAgentParallelExecutor:
    """多 Agent 并行执行器"""

    def __init__(self, brain=None):
        """初始化多 Agent 并行执行器

        Args:
            brain: Brain 实例，用于与其他 Agent 通信
        """
        self.brain = brain
        self._active_tasks: Dict[str, asyncio.Task] = {}
        self._results: Dict[str, AgentResult] = {}

    async def execute_multi_perspective(
        self,
        task: str,
        perspectives: List[AgentRole] = None,
        timeout: int = 60
    ) -> Dict[str, Any]:
        """多视角分析

        Args:
            task: 任务描述
            perspectives: 视角列表，默认 [SECURITY, PERFORMANCE, MAINTAINABILITY]
            timeout: 超时时间（秒）

        Returns:
            Dict: 聚合结果
        """
        if perspectives is None:
            perspectives = [
                AgentRole.SECURITY,
                AgentRole.PERFORMANCE,
                AgentRole.MAINTAINABILITY
            ]

        # 创建任务
        tasks = []
        for role in perspectives:
            agent_task = AgentTask(
                task_id=f"{task}_{role.value}_{int(time.time())}",
                role=role,
                description=self._build_perspective_prompt(role, task),
                input_data={"task": task},
                timeout=timeout
            )
            tasks.append(agent_task)

        # 并行执行
        results = await self._execute_parallel(tasks, timeout=timeout)

        # 聚合结果
        return self._synthesize_perspectives(results, task)

    def _build_perspective_prompt(self, role: AgentRole, task: str) -> str:
        """构建视角提示词"""
        prompts = {
            AgentRole.SECURITY: f"""从安全角度分析以下任务：
{task}

请检查：
1. 是否存在安全漏洞（SQL 注入、XSS、CSRF 等）
2. 是否有敏感数据泄露风险
3. 认证和授权是否充分
4. 输入验证是否到位

以 JSON 格式返回分析结果。""",

            AgentRole.PERFORMANCE: f"""从性能角度分析以下任务：
{task}

请检查：
1. 时间复杂度是否合理
2. 是否有内存泄漏风险
3. 数据库查询是否优化
4. 是否有缓存优化空间

以 JSON 格式返回分析结果。""",

            AgentRole.MAINTAINABILITY: f"""从可维护性角度分析以下任务：
{task}

请检查：
1. 代码结构是否清晰
2. 命名是否规范
3. 是否有充分的文档和注释
4. 是否易于测试和扩展

以 JSON 格式返回分析结果。""",

            AgentRole.ARCHITECT: f"""从架构角度分析以下任务：
{task}

请检查：
1. 系统分层是否合理
2. 模块解耦是否充分
3. 扩展性设计是否到位
4. 技术选型是否合适

以 JSON 格式返回分析结果。""",

            AgentRole.DEVELOPER: f"""从开发者角度实现以下任务：
{task}

请提供：
1. 具体实现方案
2. 关键代码示例
3. 依赖和注意事项

以 JSON 格式返回。""",

            AgentRole.TESTER: f"""从测试角度分析以下任务：
{task}

请提供：
1. 测试策略
2. 关键测试用例
3. 边界条件检查
4. 回归测试建议

以 JSON 格式返回。""",

            AgentRole.REVIEWER: f"""从代码审查角度分析以下任务：
{task}

请检查：
1. 代码规范遵循
2. 潜在 bug
3. 改进建议
4. 最佳实践

以 JSON 格式返回。"""
        }
        return prompts.get(role, f"分析任务：{task}")

    async def _execute_parallel(
        self,
        tasks: List[AgentTask],
        timeout: int = 60
    ) -> List[AgentResult]:
        """并行执行任务

        Args:
            tasks: 任务列表
            timeout: 超时时间

        Returns:
            List[AgentResult]: 执行结果列表
        """
        async def execute_single(task: AgentTask) -> AgentResult:
            """执行单个任务"""
            start_time = time.time()

            try:
                # 如果有 Brain 实例，使用 LLM 执行
                if self.brain and hasattr(self.brain, 'llm') and self.brain.llm.is_available():
                    result = await asyncio.wait_for(
                        asyncio.get_event_loop().run_in_executor(
                            None,
                            lambda: self.brain.llm.chat(task.description)
                        ),
                        timeout=task.timeout
                    )
                    return AgentResult(
                        task_id=task.task_id,
                        role=task.role,
                        status="success",
                        result=result,
                        execution_time=time.time() - start_time
                    )
                else:
                    # 模拟执行（用于测试）
                    await asyncio.sleep(0.1)
                    return AgentResult(
                        task_id=task.task_id,
                        role=task.role,
                        status="success",
                        result={"perspective": task.role.value, "analysis": "分析完成"},
                        execution_time=time.time() - start_time
                    )

            except asyncio.TimeoutError:
                return AgentResult(
                    task_id=task.task_id,
                    role=task.role,
                    status="timeout",
                    result=None,
                    error=f"执行超时（{task.timeout}秒）",
                    execution_time=time.time() - start_time
                )
            except Exception as e:
                return AgentResult(
                    task_id=task.task_id,
                    role=task.role,
                    status="error",
                    result=None,
                    error=str(e),
                    execution_time=time.time() - start_time
                )

        # 并发执行所有任务
        exec_tasks = [execute_single(task) for task in tasks]
        results = await asyncio.gather(*exec_tasks, return_exceptions=True)

        # 处理异常
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append(AgentResult(
                    task_id=tasks[i].task_id,
                    role=tasks[i].role,
                    status="error",
                    result=None,
                    error=str(result)
                ))
            else:
                processed_results.append(result)

        return processed_results

    def _synthesize_perspectives(
        self,
        results: List[AgentResult],
        original_task: str
    ) -> Dict[str, Any]:
        """综合多视角结果

        Args:
            results: 执行结果列表
            original_task: 原始任务

        Returns:
            Dict: 综合结果
        """
        synthesis = {
            "task": original_task,
            "perspectives": {},
            "summary": [],
            "recommendations": [],
            "risks": [],
            "execution_stats": {
                "total_tasks": len(results),
                "successful": sum(1 for r in results if r.status == "success"),
                "failed": sum(1 for r in results if r.status != "success"),
                "total_time": sum(r.execution_time for r in results)
            }
        }

        # 整理各视角结果
        for result in results:
            perspective_name = result.role.value
            synthesis["perspectives"][perspective_name] = {
                "status": result.status,
                "result": result.result,
                "error": result.error,
                "execution_time": result.execution_time
            }

            if result.status == "success" and result.result:
                # 提取关键点
                if isinstance(result.result, dict):
                    content = result.result.get("content", str(result.result))
                else:
                    content = str(result.result)

                synthesis["summary"].append(
                    f"**{perspective_name}**: 分析完成"
                )

        # 生成综合建议
        synthesis["recommendations"] = self._generate_recommendations(results)
        synthesis["risks"] = self._identify_risks(results)

        return synthesis

    def _generate_recommendations(self, results: List[AgentResult]) -> List[str]:
        """生成综合建议"""
        recommendations = []

        for result in results:
            if result.status != "success":
                continue

            role = result.role
            if role == AgentRole.SECURITY:
                recommendations.append("建议进行安全审计和渗透测试")
            elif role == AgentRole.PERFORMANCE:
                recommendations.append("建议进行性能基准测试和优化")
            elif role == AgentRole.MAINTAINABILITY:
                recommendations.append("建议添加文档和单元测试")

        return recommendations

    def _identify_risks(self, results: List[AgentResult]) -> List[str]:
        """识别风险"""
        risks = []

        for result in results:
            if result.status == "error":
                risks.append(f"{result.role.value}分析失败：{result.error}")
            elif result.status == "timeout":
                risks.append(f"{result.role.value}分析超时")

        return risks

    async def delegate_to_agents(
        self,
        tasks: List[Dict[str, Any]],
        callback: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """委派任务给多个 Agent

        Args:
            tasks: 任务列表，每个任务包含 target_agent 和 task_content
            callback: 进度回调函数

        Returns:
            Dict: 聚合结果
        """
        async def execute_delegation(task_info: Dict[str, Any]) -> Dict[str, Any]:
            target_agent = task_info.get("target_agent")
            task_content = task_info.get("task_content")

            if not target_agent or not task_content:
                return {"status": "error", "error": "Missing target_agent or task_content"}

            # 如果有 Brain 实例，使用网络委派
            if self.brain and hasattr(self.brain, 'network'):
                try:
                    result = self.brain.delegate_task(
                        to_agent=target_agent,
                        task={"content": task_content}
                    )
                    return {"status": "success", "target": target_agent, "result": result}
                except Exception as e:
                    return {"status": "error", "target": target_agent, "error": str(e)}
            else:
                # 模拟执行
                await asyncio.sleep(0.1)
                return {"status": "success", "target": target_agent, "result": {"mock": True}}

        # 并行执行所有委派
        exec_tasks = [execute_delegation(task) for task in tasks]
        results = await asyncio.gather(*exec_tasks, return_exceptions=True)

        # 处理结果
        processed = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed.append({
                    "status": "error",
                    "target": tasks[i].get("target_agent", "unknown"),
                    "error": str(result)
                })
            else:
                processed.append(result)

            # 回调
            if callback:
                await callback(processed[-1])

        return {
            "total": len(tasks),
            "successful": sum(1 for r in processed if r.get("status") == "success"),
            "failed": sum(1 for r in processed if r.get("status") != "success"),
            "results": processed
        }


# 便捷函数
async def multi_perspective_analysis(brain, task: str, perspectives: List[str] = None) -> Dict[str, Any]:
    """便捷函数：多视角分析"""
    executor = MultiAgentParallelExecutor(brain)

    # 转换字符串视角为 AgentRole
    if perspectives:
        role_map = {
            "security": AgentRole.SECURITY,
            "performance": AgentRole.PERFORMANCE,
            "maintainability": AgentRole.MAINTAINABILITY,
            "architect": AgentRole.ARCHITECT,
            "developer": AgentRole.DEVELOPER,
            "tester": AgentRole.TESTER,
            "reviewer": AgentRole.REVIEWER,
        }
        roles = [role_map.get(p.lower(), AgentRole.DEVELOPER) for p in perspectives]
    else:
        roles = None

    return await executor.execute_multi_perspective(task, perspectives=roles)


async def parallel_delegate(brain, tasks: List[Dict], callback=None) -> Dict[str, Any]:
    """便捷函数：并行委派任务"""
    executor = MultiAgentParallelExecutor(brain)
    return await executor.delegate_to_agents(tasks, callback=callback)
