"""测试 Commander 模式 - 核心大脑任务委派

运行方式：
```bash
python -m tests.test_commander
```
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from mul_agent.brain.brain import Brain
from mul_agent.brain.config_manager import ConfigManager
from mul_agent.brain.commander import Commander, get_commander, TaskType


def test_commander_creation():
    """测试 Commander 创建"""
    print("=" * 60)
    print("测试 1: Commander 创建")
    print("=" * 60)

    config_manager = ConfigManager("storage")
    brain = Brain("core_brain", config_manager)

    if brain.commander:
        print("✅ Commander 创建成功")
        print(f"   - Agent ID: {brain.agent_id}")
        print(f"   - LLM 可用：{brain.use_llm}")
    else:
        print("❌ Commander 创建失败")
        print("   可能原因：LLM 不可用或 agent_id 不是 core_brain")

    return brain


def test_commander_delegation(brain: Brain):
    """测试 Commander 任务委派"""
    print("\n" + "=" * 60)
    print("测试 2: Commander 任务委派")
    print("=" * 60)

    test_cases = [
        # (任务描述，预期委派给哪个 Agent)
        ("实现用户登录功能", "alice"),
        ("设计一个微服务架构", "bob"),
        ("帮我看看项目结构", "wangyue"),
        ("修复这个 bug", "alice"),
        ("完善文档", "wangyue"),
    ]

    for task_desc, expected_agent in test_cases:
        print(f"\n📝 任务：{task_desc}")
        print(f"   预期委派给：{expected_agent}")

        # 判断是否需要委派
        if brain.commander:
            needs_delegation = brain.commander._is_team_delegation_task(task_desc)
            print(f"   需要委派：{needs_delegation}")

            # 分析任务类型
            analysis = brain.commander._analyze_task(task_desc)
            if not analysis.get("error"):
                task_type = analysis.get("type")
                complexity = analysis.get("complexity")
                required_agent = analysis.get("required_agent")
                print(f"   任务类型：{task_type}")
                print(f"   复杂度：{complexity}")
                print(f"   需要 Agent: {required_agent}")
            else:
                print(f"   分析失败：{analysis.get('error')}")
        else:
            print("   Commander 不可用")

    print("\n✅ 任务分析测试完成")


def test_commander_keywords():
    """测试 Commander 关键词识别"""
    print("\n" + "=" * 60)
    print("测试 3: Commander 关键词识别")
    print("=" * 60)

    from mul_agent.commander import Commander, DELEGATION_KEYWORDS

    print(f"委派关键词列表：{DELEGATION_KEYWORDS}")
    print(f"关键词数量：{len(DELEGATION_KEYWORDS)}")

    # 测试关键词匹配
    test_inputs = [
        ("实现一个功能", True),  # 包含"实现"
        ("开发新功能", True),  # 包含"开发"
        ("设计架构", True),  # 包含"设计"
        ("你好", False),  # 简单问候
        ("谢谢", False),  # 简单感谢
        ("修复 bug", True),  # 包含"修复"和"bug"
    ]

    commander = Commander.__new__(Commander)
    commander.DELEGATION_KEYWORDS = DELEGATION_KEYWORDS

    for text, expected in test_inputs:
        # 简单关键词匹配测试
        has_keyword = any(kw in text.lower() for kw in DELEGATION_KEYWORDS)
        status = "✅" if has_keyword == expected else "⚠️"
        print(f"{status} '{text}': 有关键词={has_keyword}, 预期={expected}")


def test_task_type_mapping():
    """测试任务类型到 Agent 的映射"""
    print("\n" + "=" * 60)
    print("测试 4: 任务类型到 Agent 的映射")
    print("=" * 60)

    from mul_agent.commander import TASK_AGENT_MAP, TaskType, AgentRole

    print("任务类型 → Agent 映射:")
    for task_type, agent in TASK_AGENT_MAP.items():
        agent_name = agent.value if agent else "需要分解"
        print(f"  {task_type.value} → {agent_name}")


def main():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("🧠 Commander 模式测试")
    print("=" * 60)
    print("测试核心大脑的任务委派能力\n")

    # 测试 1: Commander 创建
    brain = test_commander_creation()

    # 测试 2: 任务委派分析
    test_commander_delegation(brain)

    # 测试 3: 关键词识别
    test_commander_keywords()

    # 测试 4: 任务类型映射
    test_task_type_mapping()

    print("\n" + "=" * 60)
    print("✅ 所有测试完成")
    print("=" * 60)
    print("\n下一步：")
    print("1. 启动 core_brain: python -m mul_agent.main")
    print("2. 输入复杂任务，如：'实现用户登录功能'")
    print("3. 观察是否自动委派给 alice/bob/wangyue")


if __name__ == "__main__":
    main()
