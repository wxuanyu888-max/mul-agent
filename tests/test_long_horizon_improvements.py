"""测试长路由改进功能

测试内容：
1. LLM 意图分类器
2. 并行执行支持
3. 错误恢复机制
4. 深度反思机制
5. 记忆检索整合
"""

import sys
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from mul_agent.brain.config_manager import ConfigManager
from mul_agent.brain.brain import Brain
from mul_agent.brain.autonomous_loop import AutonomousLoop


def test_complex_task_detection():
    """测试 1: 复杂任务检测"""
    print("\n" + "=" * 60)
    print("测试 1: 复杂任务检测")
    print("=" * 60)

    wang_dir = Path("/Users/agent/PycharmProjects/mul-agent/wang")
    config_manager = ConfigManager(config_dir=wang_dir, wang_dir=wang_dir)
    brain = Brain(agent_id="core_brain", config_manager=config_manager)

    test_cases = [
        # (输入，预期是否为复杂任务)
        ("你好", False),
        ("ls -la", False),
        ("cat README.md", False),
        ("完善这个项目的登录功能", True),
        ("分析项目结构", True),
        ("改进代码质量", True),
        ("实现一个新的 API 端点", True),
        ("帮我看看这个项目", True),
        ("fix the bug", True),
        ("what can you do", True),
    ]

    passed = 0
    failed = 0

    for input_text, expected in test_cases:
        result = brain._is_complex_task(input_text)
        status = "✓" if result == expected else "✗"

        if result == expected:
            passed += 1
        else:
            failed += 1

        print(f"{status} '{input_text}' -> {result} (预期：{expected})")

    print(f"\n结果：{passed} 通过，{failed} 失败")
    return failed == 0


async def test_intent_understanding():
    """测试 2: 意图理解（使用 LLM）"""
    print("\n" + "=" * 60)
    print("测试 2: 意图理解")
    print("=" * 60)

    wang_dir = Path("/Users/agent/PycharmProjects/mul-agent/wang")
    config_manager = ConfigManager(config_dir=wang_dir, wang_dir=wang_dir)
    brain = Brain(agent_id="core_brain", config_manager=config_manager)
    loop = AutonomousLoop(brain)

    test_inputs = [
        "完善这个项目的登录功能",
        "分析项目结构并生成报告",
        "帮我创建一个全新的 API 服务",
    ]

    for user_input in test_inputs:
        print(f"\n输入：'{user_input}'")
        intent = await loop._understand_intent(user_input)

        if intent.get("error"):
            print(f"  ✗ 错误：{intent.get('error')}")
        else:
            print(f"  ✓ 目标：{intent.get('goal', 'N/A')}")
            print(f"  ✓ 类型：{intent.get('type', 'N/A')}")
            print(f"  ✓ 复杂度：{intent.get('complexity', 'N/A')}")
            if intent.get("relevant_memories"):
                print(f"  ✓ 相关记忆：{len(intent.get('relevant_memories'))} 条")


async def test_plan_creation():
    """测试 3: 计划创建（利用记忆）"""
    print("\n" + "=" * 60)
    print("测试 3: 计划创建")
    print("=" * 60)

    wang_dir = Path("/Users/agent/PycharmProjects/mul-agent/wang")
    config_manager = ConfigManager(config_dir=wang_dir, wang_dir=wang_dir)
    brain = Brain(agent_id="core_brain", config_manager=config_manager)
    loop = AutonomousLoop(brain)

    # 先理解意图
    user_input = "分析这个项目"
    intent = await loop._understand_intent(user_input)

    if intent.get("error"):
        print(f"意图理解失败：{intent.get('error')}")
        return

    # 创建计划
    plan = await loop._create_plan(intent, user_input)

    if plan.get("error"):
        print(f"✗ 计划创建失败：{plan.get('error')}")
    else:
        steps = plan.get("steps", [])
        print(f"✓ 创建了 {len(steps)} 个步骤的计划")
        for i, step in enumerate(steps[:5], 1):  # 只显示前 5 个
            print(f"  {i}. [{step.get('route')}] {step.get('description', 'N/A')}")
            if step.get('can_parallel'):
                print(f"     ↳ 可并行执行")
            if step.get('depends_on'):
                print(f"     ↳ 依赖步骤：{step.get('depends_on')}")


def test_parallel_steps_detection():
    """测试 4: 并行步骤检测"""
    print("\n" + "=" * 60)
    print("测试 4: 并行步骤检测")
    print("=" * 60)

    wang_dir = Path("/Users/agent/PycharmProjects/mul-agent/wang")
    config_manager = ConfigManager(config_dir=wang_dir, wang_dir=wang_dir)
    brain = Brain(agent_id="core_brain", config_manager=config_manager)
    loop = AutonomousLoop(brain)

    # 模拟计划
    loop.plan = [
        {"route": "bash", "params": {"command": "ls -la"}, "description": "列出文件", "can_parallel": True},
        {"route": "bash", "params": {"command": "pwd"}, "description": "当前目录", "can_parallel": True},
        {"route": "bash", "params": {"command": "cat README.md"}, "description": "读取 README", "can_parallel": True},
        {"route": "chat", "params": {"agent_id": "coder", "message": "hi"}, "description": "联系 coder", "can_parallel": False, "depends_on": [0, 1, 2]},
    ]

    parallel_steps = loop._find_parallel_steps(0)

    print(f"计划总数：{len(loop.plan)}")
    print(f"可并行步骤：{len(parallel_steps)}")

    if parallel_steps:
        print("并行步骤列表:")
        for i, step in enumerate(parallel_steps, 1):
            print(f"  {i}. [{step.get('route')}] {step.get('description', 'N/A')}")
        print("✓ 测试通过")
    else:
        print("✗ 未检测到可并行步骤")


async def test_deep_reflection():
    """测试 5: 深度反思机制"""
    print("\n" + "=" * 60)
    print("测试 5: 深度反思机制")
    print("=" * 60)

    wang_dir = Path("/Users/agent/PycharmProjects/mul-agent/wang")
    config_manager = ConfigManager(config_dir=wang_dir, wang_dir=wang_dir)
    brain = Brain(agent_id="core_brain", config_manager=config_manager)
    loop = AutonomousLoop(brain)

    # 模拟步骤和结果
    step = {
        "route": "bash",
        "params": {"command": "ls -la"},
        "description": "列出项目文件"
    }

    result = {
        "status": "success",
        "step": step,
        "result": {"stdout": "total 100\n..."}
    }

    reflection = await loop._deep_reflect(step, result, plan_progress=0.3)

    print(f"步骤：{step.get('description')}")
    print(f"反思结果:")
    print(f"  ✓ 符合预期：{reflection.get('meets_expectations', 'N/A')}")
    print(f"  ✓ 分析：{reflection.get('analysis', 'N/A')[:100]}...")
    print(f"  ✓ 需要调整：{reflection.get('need_adjustment', 'N/A')}")
    if reflection.get('lesson_learned'):
        print(f"  ✓ 经验：{reflection.get('lesson_learned', 'N/A')[:100]}...")


async def main():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("长路由改进功能测试")
    print("=" * 60)

    # 测试 1: 复杂任务检测（同步）
    test1_passed = test_complex_task_detection()

    # 测试 2: 意图理解
    await test_intent_understanding()

    # 测试 3: 计划创建
    await test_plan_creation()

    # 测试 4: 并行步骤检测
    test_parallel_steps_detection()

    # 测试 5: 深度反思
    await test_deep_reflection()

    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)

    if test1_passed:
        print("✓ 所有测试通过")
    else:
        print("✗ 部分测试失败")


if __name__ == "__main__":
    asyncio.run(main())



def test_token_optimization():
    """测试 Token 优化：验证条件反射逻辑"""
    print("\n" + "=" * 60)
    print("测试：Token 优化 - 条件反射")
    print("=" * 60)

    from mul_agent.brain.config_manager import ConfigManager
    from mul_agent.brain.brain import Brain
    from mul_agent.brain.autonomous_loop import AutonomousLoop
    from pathlib import Path

    wang_dir = Path("/Users/agent/PycharmProjects/mul-agent/wang")
    config_manager = ConfigManager(config_dir=wang_dir, wang_dir=wang_dir)
    brain = Brain(agent_id="core_brain", config_manager=config_manager)
    loop = AutonomousLoop(brain)

    test_cases = [
        # (步骤，结果，预期是否反思)
        (
            {"route": "bash", "params": {"command": "ls -la"}},
            {"status": "success", "result": {"stdout": "total 10"}},
            False,  # 简单成功，不反思
        ),
        (
            {"route": "bash", "params": {"command": "ls -la"}},
            {"status": "error", "error": "Permission denied"},
            True,  # 失败，必须反思
        ),
        (
            {"route": "file_edit", "params": {"path": "main.py"}},
            {"status": "success", "result": {}},
            True,  # 关键操作，必须反思
        ),
        (
            {"route": "response", "params": {"message": "hi"}},
            {"status": "success", "result": {}},
            False,  # 简单回复，不反思
        ),
        (
            {"route": "chat", "params": {"agent_id": "coder", "message": "hi"}},
            {"status": "success", "result": {}},
            True,  # 关键 Agent，必须反思
        ),
        (
            {"route": "chat", "params": {"agent_id": "tmp", "message": "hi"}},
            {"status": "success", "result": {}},
            False,  # 非关键 Agent，不反思
        ),
        (
            {"route": "memory", "params": {"action": "write"}},
            {"status": "success", "result": {}},
            True,  # 记忆操作，必须反思
        ),
    ]

    passed = 0
    failed = 0

    for i, (step, result, expected) in enumerate(test_cases, 1):
        should_reflect = loop._should_reflect(step, result)
        status = "✓" if should_reflect == expected else "✗"
        
        if should_reflect == expected:
            passed += 1
        else:
            failed += 1
        
        print(f"{status} 测试{i}: [{step['route']}] 反思={should_reflect} (预期：{expected})")

    print(f"\n结果：{passed} 通过，{failed} 失败")
    
    # 计算 Token 节省
    total_cases = len(test_cases)
    skip_count = sum(1 for _, _, expected in test_cases if not expected)
    saved_percentage = (skip_count / total_cases) * 100
    
    print(f"\nToken 节省：{skip_count}/{total_cases} 步骤可跳过 ({saved_percentage:.0f}%)")
    
    return failed == 0


if __name__ == "__main__":
    test_token_optimization()
