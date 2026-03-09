"""Subagent Tools - 子代理工具函数

提供给 handlers 和其他模块使用的子代理工具函数
"""

import asyncio
from typing import Any, Dict, List, Optional


def spawn_subagent(
    brain,
    agent_id: str,
    task_description: str,
    task_input: str = "",
    timeout: int = 300
) -> Dict[str, Any]:
    """派发生子代理任务

    Args:
        brain: Brain 实例
        agent_id: 子代理 ID
        task_description: 任务描述
        task_input: 任务输入
        timeout: 超时时间（秒）

    Returns:
        任务结果
    """
    task = brain.subagent.spawn(
        agent_id=agent_id,
        task_description=task_description,
        params={"input": task_input},
        timeout=timeout
    )

    return {
        "task_id": task.task_id,
        "agent_id": agent_id,
        "status": task.status.value,
        "message": f"Subagent task spawned: {task_description}"
    }


async def execute_subagent_task(
    brain,
    agent_id: str,
    task_input: str,
    timeout: int = 300
) -> Dict[str, Any]:
    """执行子代理任务并等待结果

    Args:
        brain: Brain 实例
        agent_id: 子代理 ID
        task_input: 任务输入
        timeout: 超时时间（秒）

    Returns:
        执行结果
    """
    from mul_agent.brain.brain import Brain

    # 创建子代理实例
    subagent = Brain(
        agent_id=agent_id,
        config_manager=brain.config_manager
    )

    try:
        # 在超时时间内执行
        result = await asyncio.wait_for(
            asyncio.to_thread(subagent.think, task_input),
            timeout=timeout
        )
        return {
            "status": "success",
            "agent_id": agent_id,
            "result": result
        }
    except asyncio.TimeoutError:
        return {
            "status": "error",
            "error": f"Subagent execution timed out after {timeout}s"
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }


async def delegate_to_multiple_agents(
    brain,
    delegations: List[Dict[str, Any]],
    max_concurrent: int = 5
) -> Dict[str, Any]:
    """委派任务给多个子代理并并行执行

    Args:
        brain: Brain 实例
        delegations: 委派列表，每个元素包含：
            - agent_id: 子代理 ID
            - task_input: 任务输入
            - timeout: 超时时间（可选）
        max_concurrent: 最大并发数

    Returns:
        聚合结果
    """
    semaphore = asyncio.Semaphore(max_concurrent)

    async def execute_single(delegation: Dict[str, Any]) -> Dict[str, Any]:
        async with semaphore:
            return await execute_subagent_task(
                brain=brain,
                agent_id=delegation.get("agent_id"),
                task_input=delegation.get("task_input", ""),
                timeout=delegation.get("timeout", 300)
            )

    tasks = [execute_single(d) for d in delegations]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # 处理结果
    processed = []
    successful = 0
    failed = 0

    for i, result in enumerate(results):
        if isinstance(result, Exception):
            processed.append({
                "agent_id": delegations[i].get("agent_id"),
                "status": "error",
                "error": str(result)
            })
            failed += 1
        elif result.get("status") == "success":
            processed.append(result)
            successful += 1
        else:
            processed.append(result)
            failed += 1

    return {
        "status": "success" if failed == 0 else "partial_success" if successful > 0 else "error",
        "total": len(delegations),
        "successful": successful,
        "failed": failed,
        "results": processed
    }


def create_subagent_session(brain, description: str = "") -> str:
    """创建子代理会话

    Args:
        brain: Brain 实例
        description: 会话描述

    Returns:
        会话 ID
    """
    session = brain.subagent.create_session(description=description)
    return session.session_id


def get_subagent_result(brain, task_id: str = None, session_id: str = None) -> Dict[str, Any]:
    """获取子代理结果

    Args:
        brain: Brain 实例
        task_id: 任务 ID
        session_id: 会话 ID

    Returns:
        结果数据
    """
    if task_id:
        task = brain.subagent.get_task(task_id)
        if not task:
            return {"status": "error", "message": f"Task not found: {task_id}"}

        return {
            "status": "success",
            "task_id": task.task_id,
            "agent_id": task.agent_id,
            "description": task.description,
            "result": task.result,
            "error": task.error,
            "execution_time": (task.completed_at - task.started_at) if task.completed_at and task.started_at else None
        }

    elif session_id:
        session = brain.subagent.get_session(session_id)
        if not session:
            return {"status": "error", "message": f"Session not found: {session_id}"}

        results = [
            {
                "task_id": t.task_id,
                "agent_id": t.agent_id,
                "status": t.status.value,
                "result": t.result,
                "error": t.error
            }
            for t in session.tasks
        ]

        return {
            "status": "success",
            "session_id": session.session_id,
            "results": results
        }

    else:
        return {"status": "error", "message": "task_id or session_id is required"}


def list_active_subagent_sessions(brain) -> Dict[str, Any]:
    """列出活跃的子代理会话

    Args:
        brain: Brain 实例

    Returns:
        活跃会话列表
    """
    sessions = brain.subagent.list_active_sessions()
    return {
        "status": "success",
        "sessions": sessions,
        "total": len(sessions)
    }


def get_subagent_stats(brain) -> Dict[str, Any]:
    """获取子代理统计信息

    Args:
        brain: Brain 实例

    Returns:
        统计信息
    """
    stats = brain.subagent.get_stats()
    return {
        "status": "success",
        "stats": stats
    }


# 便捷函数：委派给特定类型的 Agent

def delegate_to_coder(brain, task_description: str, task_input: str = "") -> Dict[str, Any]:
    """委派任务给代码工程师（alice）"""
    return spawn_subagent(
        brain=brain,
        agent_id="alice",
        task_description=task_description,
        task_input=task_input
    )


def delegate_to_planner(brain, task_description: str, task_input: str = "") -> Dict[str, Any]:
    """委派任务给规划师（bob）"""
    return spawn_subagent(
        brain=brain,
        agent_id="bob",
        task_description=task_description,
        task_input=task_input
    )


def delegate_to_assistant(brain, task_description: str, task_input: str = "") -> Dict[str, Any]:
    """委派任务给助理（wangyue）"""
    return spawn_subagent(
        brain=brain,
        agent_id="wangyue",
        task_description=task_description,
        task_input=task_input
    )
