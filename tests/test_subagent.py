"""测试 Subagent 功能"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from mul_agent.brain.config_manager import ConfigManager
from mul_agent.brain.brain import Brain
from mul_agent.brain.subagent import SubagentManager, SubagentStatus, SubagentTask, SubagentSession


def test_subagent_manager_initialization():
    """测试 SubagentManager 初始化"""
    print("=== 测试 SubagentManager 初始化 ===\n")

    wang_dir = Path("/Users/agent/PycharmProjects/mul-agent/wang")
    config_manager = ConfigManager(config_dir=wang_dir, wang_dir=wang_dir)
    brain = Brain(agent_id="core_brain", config_manager=config_manager)

    # 检查 subagent 属性是否存在
    assert hasattr(brain, 'subagent'), "Brain 应该具有 subagent 属性"
    assert isinstance(brain.subagent, SubagentManager), "subagent 应该是 SubagentManager 实例"

    print("✓ SubagentManager 初始化成功")
    print(f"  - 最大并发数：{brain.subagent.max_concurrent}")
    print(f"  - 默认超时：{brain.subagent.default_timeout}s")
    print()


def test_create_session():
    """测试创建子代理会话"""
    print("=== 测试创建子代理会话 ===\n")

    wang_dir = Path("/Users/agent/PycharmProjects/mul-agent/wang")
    config_manager = ConfigManager(config_dir=wang_dir, wang_dir=wang_dir)
    brain = Brain(agent_id="core_brain", config_manager=config_manager)

    # 创建会话
    session = brain.subagent.create_session(description="测试会话")

    assert session is not None, "应该成功创建会话"
    assert session.session_id.startswith("subsession_"), "会话 ID 应该以 subsession_ 开头"
    assert session.parent_agent_id == "core_brain", "父代理 ID 应该正确"
    assert session.description == "测试会话", "会话描述应该正确"
    assert len(session.tasks) == 0, "新会话应该没有任务"

    print(f"✓ 会话创建成功")
    print(f"  - Session ID: {session.session_id}")
    print(f"  - Parent Agent: {session.parent_agent_id}")
    print(f"  - Description: {session.description}")
    print()


def test_spawn_task():
    """测试派发生子代理任务"""
    print("=== 测试派发生子代理任务 ===\n")

    wang_dir = Path("/Users/agent/PycharmProjects/mul-agent/wang")
    config_manager = ConfigManager(config_dir=wang_dir, wang_dir=wang_dir)
    brain = Brain(agent_id="core_brain", config_manager=config_manager)

    # 创建任务
    task = brain.subagent.spawn(
        agent_id="alice",
        task_description="测试任务：代码审查",
        params={"input": "请审查这个项目的代码结构"},
        timeout=60
    )

    assert task is not None, "应该成功创建任务"
    assert task.task_id.startswith("task_"), "任务 ID 应该以 task_ 开头"
    assert task.agent_id == "alice", "代理 ID 应该正确"
    assert task.description == "测试任务：代码审查", "任务描述应该正确"
    assert task.status == SubagentStatus.PENDING, "新任务状态应该是 PENDING"
    assert task.timeout == 60, "超时时间应该正确"

    print(f"✓ 任务派发成功")
    print(f"  - Task ID: {task.task_id}")
    print(f"  - Agent ID: {task.agent_id}")
    print(f"  - Description: {task.description}")
    print(f"  - Status: {task.status.value}")
    print(f"  - Timeout: {task.timeout}s")
    print()

    return task.task_id


def test_get_task():
    """测试获取任务"""
    print("=== 测试获取任务 ===\n")

    wang_dir = Path("/Users/agent/PycharmProjects/mul-agent/wang")
    config_manager = ConfigManager(config_dir=wang_dir, wang_dir=wang_dir)
    brain = Brain(agent_id="core_brain", config_manager=config_manager)

    # 先创建任务
    task = brain.subagent.spawn(
        agent_id="bob",
        task_description="测试获取任务",
        params={"input": "test"}
    )

    # 获取任务
    retrieved = brain.subagent.get_task(task.task_id)

    assert retrieved is not None, "应该能够获取任务"
    assert retrieved.task_id == task.task_id, "任务 ID 应该匹配"
    assert retrieved.agent_id == "bob", "代理 ID 应该匹配"

    print(f"✓ 任务获取成功")
    print(f"  - Task ID: {retrieved.task_id}")
    print(f"  - Agent ID: {retrieved.agent_id}")
    print()


def test_get_session():
    """测试获取会话"""
    print("=== 测试获取会话 ===\n")

    wang_dir = Path("/Users/agent/PycharmProjects/mul-agent/wang")
    config_manager = ConfigManager(config_dir=wang_dir, wang_dir=wang_dir)
    brain = Brain(agent_id="core_brain", config_manager=config_manager)

    # 创建会话并添加任务
    session = brain.subagent.create_session(description="测试获取会话")
    task = brain.subagent.spawn(
        agent_id="wangyue",
        task_description="会话中的任务",
        params={"input": "test"},
        session_id=session.session_id
    )

    # 获取会话
    retrieved = brain.subagent.get_session(session.session_id)

    assert retrieved is not None, "应该能够获取会话"
    assert retrieved.session_id == session.session_id, "会话 ID 应该匹配"
    assert len(retrieved.tasks) == 1, "会话应该包含 1 个任务"

    print(f"✓ 会话获取成功")
    print(f"  - Session ID: {retrieved.session_id}")
    print(f"  - Task Count: {len(retrieved.tasks)}")
    print()


def test_list_active_sessions():
    """测试列出活跃会话"""
    print("=== 测试列出活跃会话 ===\n")

    wang_dir = Path("/Users/agent/PycharmProjects/mul-agent/wang")
    config_manager = ConfigManager(config_dir=wang_dir, wang_dir=wang_dir)
    brain = Brain(agent_id="core_brain", config_manager=config_manager)

    # 创建几个会话
    brain.subagent.create_session(description="会话 1")
    brain.subagent.create_session(description="会话 2")

    # 列出活跃会话
    active = brain.subagent.list_active_sessions()

    assert isinstance(active, list), "应该返回列表"
    assert len(active) >= 2, "应该至少有 2 个活跃会话"

    print(f"✓ 活跃会话列表获取成功")
    print(f"  - Active Sessions: {len(active)}")
    for session in active[-2:]:  # 显示最后创建的两个
        print(f"    - {session['session_id']}: {session.get('description', 'N/A')}")
    print()


def test_subagent_stats():
    """测试获取统计信息"""
    print("=== 测试获取统计信息 ===\n")

    wang_dir = Path("/Users/agent/PycharmProjects/mul-agent/wang")
    config_manager = ConfigManager(config_dir=wang_dir, wang_dir=wang_dir)
    brain = Brain(agent_id="core_brain", config_manager=config_manager)

    # 创建一些任务
    brain.subagent.create_session(description="统计测试会话")
    brain.subagent.spawn(
        agent_id="alice",
        task_description="统计测试任务 1",
        params={"input": "test"}
    )
    brain.subagent.spawn(
        agent_id="bob",
        task_description="统计测试任务 2",
        params={"input": "test"}
    )

    # 获取统计信息
    stats = brain.subagent.get_stats()

    assert isinstance(stats, dict), "统计信息应该是字典"
    assert "total_sessions" in stats, "应该包含 total_sessions"
    assert "total_tasks" in stats, "应该包含 total_tasks"
    assert "completed_tasks" in stats, "应该包含 completed_tasks"
    assert "success_rate" in stats, "应该包含 success_rate"

    print(f"✓ 统计信息获取成功")
    print(f"  - Total Sessions: {stats['total_sessions']}")
    print(f"  - Total Tasks: {stats['total_tasks']}")
    print(f"  - Completed Tasks: {stats['completed_tasks']}")
    print(f"  - Success Rate: {stats['success_rate']:.2%}")
    print()


def test_subagent_router_dispatch():
    """测试通过 Router 派发 subagent 请求"""
    print("=== 测试 Router 派发 subagent 请求 ===\n")

    wang_dir = Path("/Users/agent/PycharmProjects/mul-agent/wang")
    config_manager = ConfigManager(config_dir=wang_dir, wang_dir=wang_dir)
    brain = Brain(agent_id="core_brain", config_manager=config_manager)

    # 测试 list 操作
    result = brain.router.dispatch("subagent", {"action": "list"})

    assert result.get("status") == "success", "请求应该成功"
    assert "data" in result, "应该包含 data"
    assert "active_sessions" in result["data"], "应该包含 active_sessions"

    print(f"✓ Router 派发成功")
    print(f"  - Action: list")
    print(f"  - Active Sessions: {result['data']['total_count']}")
    print()

    # 测试 spawn 操作
    result = brain.router.dispatch("subagent", {
        "action": "spawn",
        "agent_id": "alice",
        "description": "Router 测试任务",
        "input": "你好，Alice"
    })

    assert result.get("status") == "success", "spawn 请求应该成功"
    assert "task_id" in result.get("data", {}), "应该返回 task_id"

    print(f"✓ Spawn 操作成功")
    print(f"  - Task ID: {result['data'].get('task_id')}")
    print()


def test_subagent_router_stats():
    """测试通过 Router 获取统计信息"""
    print("=== 测试 Router 获取统计信息 ===\n")

    wang_dir = Path("/Users/agent/PycharmProjects/mul-agent/wang")
    config_manager = ConfigManager(config_dir=wang_dir, wang_dir=wang_dir)
    brain = Brain(agent_id="core_brain", config_manager=config_manager)

    result = brain.router.dispatch("subagent", {"action": "stats"})

    assert result.get("status") == "success", "请求应该成功"
    stats = result.get("data", {})

    print(f"✓ 统计信息获取成功")
    print(f"  - Total Sessions: {stats.get('total_sessions', 0)}")
    print(f"  - Total Tasks: {stats.get('total_tasks', 0)}")
    print(f"  - Success Rate: {stats.get('success_rate', 0):.2%}")
    print()


def test_tools_module():
    """测试 tools 模块的 subagent 工具函数"""
    print("=== 测试 Tools 模块工具函数 ===\n")

    from mul_agent.tools.subagent_tools import (
        spawn_subagent,
        create_subagent_session,
        get_subagent_stats,
        delegate_to_coder,
        delegate_to_planner,
    )

    wang_dir = Path("/Users/agent/PycharmProjects/mul-agent/wang")
    config_manager = ConfigManager(config_dir=wang_dir, wang_dir=wang_dir)
    brain = Brain(agent_id="core_brain", config_manager=config_manager)

    # 测试 create_subagent_session
    session_id = create_subagent_session(brain, "工具函数测试")
    assert session_id is not None, "应该成功创建会话"
    print(f"✓ create_subagent_session 成功：{session_id}")

    # 测试 spawn_subagent
    result = spawn_subagent(
        brain=brain,
        agent_id="wangyue",
        task_description="工具函数测试任务",
        task_input="你好"
    )
    assert result.get("task_id") is not None, "应该成功创建任务"
    print(f"✓ spawn_subagent 成功：{result.get('task_id')}")

    # 测试 get_subagent_stats
    stats_result = get_subagent_stats(brain)
    assert stats_result.get("status") == "success", "应该成功获取统计"
    print(f"✓ get_subagent_stats 成功")

    # 测试 delegate_to_coder
    coder_result = delegate_to_coder(
        brain=brain,
        task_description="代码审查",
        task_input="请审查项目代码"
    )
    assert coder_result.get("task_id") is not None, "应该成功委派给 coder"
    print(f"✓ delegate_to_coder 成功：{coder_result.get('task_id')}")

    # 测试 delegate_to_planner
    planner_result = delegate_to_planner(
        brain=brain,
        task_description="架构设计",
        task_input="请设计项目架构"
    )
    assert planner_result.get("task_id") is not None, "应该成功委派给 planner"
    print(f"✓ delegate_to_planner 成功：{planner_result.get('task_id')}")

    print()


def run_all_tests():
    """运行所有测试"""
    print("=" * 60)
    print("Subagent 功能测试")
    print("=" * 60)
    print()

    tests = [
        test_subagent_manager_initialization,
        test_create_session,
        test_spawn_task,
        test_get_task,
        test_get_session,
        test_list_active_sessions,
        test_subagent_stats,
        test_subagent_router_dispatch,
        test_subagent_router_stats,
        test_tools_module,
    ]

    passed = 0
    failed = 0
    errors = []

    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            failed += 1
            errors.append((test.__name__, str(e)))
            print(f"✗ {test.__name__} 失败：{e}\n")
        except Exception as e:
            failed += 1
            errors.append((test.__name__, str(e)))
            print(f"✗ {test.__name__} 错误：{e}\n")

    print("=" * 60)
    print(f"测试结果：{passed} 通过，{failed} 失败")
    print("=" * 60)

    if errors:
        print("\n错误详情:")
        for name, error in errors:
            print(f"  - {name}: {error}")

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
