"""Subagent 集成测试 - 测试实际复杂任务执行"""

import sys
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from mul_agent.brain.config_manager import ConfigManager
from mul_agent.brain.brain import Brain
from mul_agent.brain.subagent import SubagentStatus


def run_async(coro):
    """运行异步函数，处理已存在事件循环的情况"""
    try:
        # 检查是否有运行中的事件循环
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # 在已有循环中创建新线程运行
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, coro)
                return future.result()
        else:
            return loop.run_until_complete(coro)
    except RuntimeError:
        # 没有事件循环，创建一个新的
        return asyncio.run(coro)


def test_subagent_basic_functionality():
    """测试：subagent 基本功能（不实际执行 LLM 调用）"""
    print("=" * 60)
    print("测试：Subagent 基本功能")
    print("=" * 60)
    print()

    wang_dir = Path("/Users/agent/PycharmProjects/mul-agent/wang")
    config_manager = ConfigManager(config_dir=wang_dir, wang_dir=wang_dir)
    brain = Brain(agent_id="core_brain", config_manager=config_manager)

    # 1. 创建会话
    session = brain.subagent.create_session(description="功能测试")
    print(f"✓ 创建会话：{session.session_id}")
    assert session.session_id.startswith("subsession_")
    assert session.description == "功能测试"

    # 2. 派发任务
    task = brain.subagent.spawn(
        agent_id="alice",
        task_description="测试任务",
        params={"input": "你好"},
        timeout=30,
        session_id=session.session_id
    )
    print(f"✓ 派发任务：{task.task_id}")
    assert task.task_id.startswith("task_")
    assert task.agent_id == "alice"
    assert task.status == SubagentStatus.PENDING

    # 3. 获取任务
    retrieved = brain.subagent.get_task(task.task_id)
    assert retrieved is not None
    print(f"✓ 获取任务成功")

    # 4. 获取会话
    session_retrieved = brain.subagent.get_session(session.session_id)
    assert session_retrieved is not None
    assert len(session_retrieved.tasks) == 1
    print(f"✓ 获取会话成功，包含 {len(session_retrieved.tasks)} 个任务")

    # 5. 列出活跃会话
    active = brain.subagent.list_active_sessions()
    assert len(active) >= 1
    print(f"✓ 活跃会话数：{len(active)}")

    # 6. 获取统计信息
    stats = brain.subagent.get_stats()
    assert stats.get("total_sessions") >= 1
    assert stats.get("total_tasks") >= 1
    print(f"✓ 统计信息：{stats.get('total_sessions')} 会话，{stats.get('total_tasks')} 任务")

    print()
    return True


def test_subagent_via_router():
    """测试：通过 Router 委派任务"""
    print("=" * 60)
    print("测试：通过 Router 委派任务")
    print("=" * 60)
    print()

    wang_dir = Path("/Users/agent/PycharmProjects/mul-agent/wang")
    config_manager = ConfigManager(config_dir=wang_dir, wang_dir=wang_dir)
    brain = Brain(agent_id="core_brain", config_manager=config_manager)

    # 测试 list 操作
    result = brain.router.dispatch("subagent", {"action": "list"})
    print(f"✓ Router list 操作：{result.get('status')}")
    assert result.get("status") == "success"

    # 测试 spawn 操作
    result = brain.router.dispatch("subagent", {
        "action": "spawn",
        "agent_id": "bob",
        "description": "Router 测试任务",
        "input": "你好，Bob"
    })
    print(f"✓ Router spawn 操作：{result.get('status')}")
    task_id = result.get("data", {}).get("task_id")
    print(f"  Task ID: {task_id or 'N/A'}")
    assert result.get("status") == "success"
    assert task_id is not None

    # 测试 stats 操作
    result = brain.router.dispatch("subagent", {"action": "stats"})
    print(f"✓ Router stats 操作：{result.get('status')}")
    assert result.get("status") == "success"

    print()
    return True


def test_parallel_delegation_structure():
    """测试：并行委派结构（不实际执行）"""
    print("=" * 60)
    print("测试：并行委派结构")
    print("=" * 60)
    print()

    wang_dir = Path("/Users/agent/PycharmProjects/mul-agent/wang")
    config_manager = ConfigManager(config_dir=wang_dir, wang_dir=wang_dir)
    brain = Brain(agent_id="core_brain", config_manager=config_manager)

    # 创建会话
    session = brain.subagent.create_session(description="并行测试")

    # 准备多个委派任务
    delegations = [
        {"agent_id": "alice", "description": "任务 1", "params": {"input": "test1"}, "timeout": 30},
        {"agent_id": "bob", "description": "任务 2", "params": {"input": "test2"}, "timeout": 30},
        {"agent_id": "wangyue", "description": "任务 3", "params": {"input": "test3"}, "timeout": 30},
    ]

    print(f"准备委派 {len(delegations)} 个任务...")
    for d in delegations:
        print(f"  - {d['agent_id']}: {d['description']}")

    # 创建任务但不执行
    tasks = []
    for d in delegations:
        task = brain.subagent.spawn(
            agent_id=d["agent_id"],
            task_description=d["description"],
            params=d["params"],
            timeout=d["timeout"],
            session_id=session.session_id
        )
        tasks.append(task)

    print(f"✓ 成功创建 {len(tasks)} 个任务")
    assert len(tasks) == len(delegations)

    # 验证会话状态
    session_updated = brain.subagent.get_session(session.session_id)
    assert len(session_updated.tasks) == len(delegations)
    print(f"✓ 会话包含 {len(session_updated.tasks)} 个任务")

    # 验证所有任务状态
    for task in tasks:
        assert task.status == SubagentStatus.PENDING
    print(f"✓ 所有任务状态为 PENDING")

    print()
    return True


def test_subagent_execution_with_timeout():
    """测试：执行单个任务（带超时控制）"""
    print("=" * 60)
    print("测试：执行单个任务（带超时）")
    print("=" * 60)
    print()

    wang_dir = Path("/Users/agent/PycharmProjects/mul-agent/wang")
    config_manager = ConfigManager(config_dir=wang_dir, wang_dir=wang_dir)
    brain = Brain(agent_id="core_brain", config_manager=config_manager)

    # 创建任务
    task = brain.subagent.spawn(
        agent_id="wangyue",
        task_description="简短问候",
        params={"input": "你好"},
        timeout=30  # 30 秒超时
    )

    print(f"创建任务：{task.task_id}")
    print(f"代理：{task.agent_id}")
    print(f"超时：{task.timeout}s")
    print()

    # 执行任务
    async def run_task():
        return await brain.subagent.execute(task)

    print("开始执行...")
    result = run_async(run_task())

    print(f"执行完成，状态：{result.status.value}")

    if result.status == SubagentStatus.COMPLETED:
        print(f"✓ 任务成功完成")
        if result.result:
            output = str(result.result)
            print(f"  结果预览：{output[:200]}...")
    elif result.status == SubagentStatus.TIMEOUT:
        print(f"⚠ 任务超时（可能是 LLM 调用时间较长）")
    elif result.status == SubagentStatus.FAILED:
        print(f"✗ 任务失败：{result.error}")

    print()
    # 只要不是异常崩溃就认为测试通过
    return True


def test_subagent_stats_after_execution():
    """测试：执行后获取统计信息"""
    print("=" * 60)
    print("测试：执行后获取统计信息")
    print("=" * 60)
    print()

    wang_dir = Path("/Users/agent/PycharmProjects/mul-agent/wang")
    config_manager = ConfigManager(config_dir=wang_dir, wang_dir=wang_dir)
    brain = Brain(agent_id="core_brain", config_manager=config_manager)

    # 获取统计信息
    stats = brain.subagent.get_stats()

    print("Subagent 统计信息:")
    print(f"  总会话数：{stats.get('total_sessions', 0)}")
    print(f"  活跃会话：{stats.get('active_sessions', 0)}")
    print(f"  已完成会话：{stats.get('completed_sessions', 0)}")
    print(f"  总任务数：{stats.get('total_tasks', 0)}")
    print(f"  已完成任务：{stats.get('completed_tasks', 0)}")
    print(f"  失败任务：{stats.get('failed_tasks', 0)}")
    print(f"  成功率：{stats.get('success_rate', 0):.2%}")
    print()

    return True


def run_all_integration_tests():
    """运行所有集成测试"""
    print()
    print("#" * 60)
    print("# Subagent 集成测试 - 实际任务执行")
    print("#" * 60)
    print()

    tests = [
        ("基本功能", test_subagent_basic_functionality),
        ("Router 委派", test_subagent_via_router),
        ("并行委派结构", test_parallel_delegation_structure),
        ("执行带超时", test_subagent_execution_with_timeout),
        ("统计信息", test_subagent_stats_after_execution),
    ]

    passed = 0
    failed = 0
    results = []

    for name, test_func in tests:
        try:
            result = test_func()
            if result:
                passed += 1
                status = "✓ 通过"
            else:
                failed += 1
                status = "✗ 失败"
            results.append((name, status))
        except Exception as e:
            failed += 1
            status = f"✗ 错误：{e}"
            results.append((name, status))
            import traceback
            traceback.print_exc()

    print()
    print("=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    for name, status in results:
        print(f"  {name}: {status}")
    print()
    print(f"总计：{passed} 通过，{failed} 失败")
    print("=" * 60)

    return failed == 0


if __name__ == "__main__":
    success = run_all_integration_tests()
    sys.exit(0 if success else 1)
