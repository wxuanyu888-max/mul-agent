"""测试自主执行模式"""

import sys
from pathlib import Path
sys.path.insert(0, '/Users/agent/PycharmProjects/mul-agent')

from mul_agent.brain.config_manager import ConfigManager
from mul_agent.brain.brain import Brain

# 创建配置管理器
wang_dir = Path("/Users/agent/PycharmProjects/mul-agent/wang")
config_manager = ConfigManager(config_dir=wang_dir, wang_dir=wang_dir)

# 创建 Core Brain 实例
brain = Brain(agent_id="core_brain", config_manager=config_manager)

# 测试复杂任务检测
test_inputs = [
    ("你好", False),
    ("完善这个项目的登录功能", True),
    ("ls -la", False),
    ("分析这个项目", True),
    ("改进代码结构", True),
    ("创建新 agent", True),
]

print("=== 测试复杂任务检测 ===\n")
for input_text, expected in test_inputs:
    result = brain._is_complex_task(input_text)
    status = "✓" if result == expected else "✗"
    print(f"{status} '{input_text}' -> {result} (expected: {expected})")

# 测试意图理解
print("\n=== 测试意图理解 ===\n")

# 创建一个简单的测试
async def test_intent():
    from mul_agent.brain.autonomous_loop import AutonomousLoop

    loop = AutonomousLoop(brain)
    intent = await loop._understand_intent("完善这个项目的登录功能")
    print(f"意图：{intent}")
    return intent

import asyncio
try:
    intent_result = asyncio.run(test_intent())
    print(f"意图理解结果：{intent_result}")
except Exception as e:
    print(f"意图理解测试跳过（LLM 可能未配置）: {e}")

print("\n=== 测试完成 ===")
