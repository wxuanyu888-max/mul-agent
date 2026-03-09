#!/usr/bin/env python3
"""测试 V2 版本与原版的对比"""

import sys
import json
from pathlib import Path

# 添加路径
sys.path.insert(0, str(Path(__file__).parent))

from mul_agent.brain.config_manager import ConfigManager
from mul_agent.brain.brain import Brain
from mul_agent.brain.brain_v2 import BrainV2

# 配置路径
CONFIG_DIR = Path("storage")

def print_separator(title=""):
    print("\n" + "=" * 60)
    if title:
        print(f"  {title}")
        print("=" * 60)

def format_result(result: dict, label: str):
    """格式化显示结果"""
    print(f"\n【{label}】")
    route = result.get("route", "unknown")
    print(f"  路由：{route}")

    if route == "batch":
        commands = result.get("commands", [])
        print(f"  批量命令数：{len(commands)}")
        for i, cmd in enumerate(commands[:3], 1):  # 只显示前 3 个
            print(f"    {i}. {cmd.get('route')}: {cmd.get('params', {})}")
        if len(commands) > 3:
            print(f"    ... 还有 {len(commands) - 3} 个命令")
    elif route == "bash":
        print(f"  命令：{result.get('params', {}).get('command', 'N/A')}")
    elif route == "response":
        message = result.get("data", {}).get("message", "")
        if message:
            print(f"  回复：{message[:200]}..." if len(message) > 200 else f"  回复：{message}")
    else:
        print(f"  参数：{result.get('params', {})}")

def test_simple_command():
    """测试 1：简单命令 - ls"""
    print_separator("测试 1: 简单命令 'ls -la'")

    config_manager = ConfigManager(CONFIG_DIR)

    # V2
    brain_v2 = BrainV2("wangyue", config_manager)
    result_v2 = brain_v2.think_v2("ls -la")
    format_result(result_v2, "V2")
    return result_v2

def test_exploration():
    """测试 2: 探索请求 - '看看项目结构'"""
    print_separator("测试 2: 探索请求 '看看项目结构'")

    config_manager = ConfigManager(CONFIG_DIR)

    # V2
    brain_v2 = BrainV2("wangyue", config_manager)
    result_v2 = brain_v2.think_v2("看看项目结构")
    format_result(result_v2, "V2")
    return result_v2

def test_complex_task():
    """测试 3: 复杂任务 - '完善登录功能'"""
    print_separator("测试 3: 复杂任务 '完善登录功能'")

    config_manager = ConfigManager(CONFIG_DIR)

    # V2
    brain_v2 = BrainV2("wangyue", config_manager)
    result_v2 = brain_v2.think_v2("完善登录功能")
    format_result(result_v2, "V2")
    return result_v2

def test_greeting():
    """测试 4: 问候 - '你好'"""
    print_separator("测试 4: 问候 '你好'")

    config_manager = ConfigManager(CONFIG_DIR)

    # V2
    brain_v2 = BrainV2("wangyue", config_manager)
    result_v2 = brain_v2.think_v2("你好")
    format_result(result_v2, "V2")
    return result_v2

def test_chat_agent():
    """测试 5: 与其他 Agent 对话 - '找 alice 帮我写代码'"""
    print_separator("测试 5: 与其他 Agent 对话 '找 alice 帮我写代码'")

    config_manager = ConfigManager(CONFIG_DIR)

    # V2
    brain_v2 = BrainV2("wangyue", config_manager)
    result_v2 = brain_v2.think_v2("找 alice 帮我写代码")
    format_result(result_v2, "V2")
    return result_v2

def run_all_tests():
    """运行所有测试"""
    print("""
╔═══════════════════════════════════════════════════════════╗
║           Brain V2 测试                                     ║
╠═══════════════════════════════════════════════════════════╣
║  测试场景：                                                ║
║  1. 简单命令 (ls -la)                                     ║
║  2. 探索请求 (看看项目结构)                                ║
║  3. 复杂任务 (完善登录功能)                                ║
║  4. 问候 (你好)                                            ║
║  5. Agent 对话 (找 alice 帮我写代码)                        ║
╚═══════════════════════════════════════════════════════════╝
    """)

    tests = [
        ("简单命令：ls -la", test_simple_command),
        ("探索请求：看看项目结构", test_exploration),
        ("复杂任务：完善登录功能", test_complex_task),
        ("问候：你好", test_greeting),
        ("Agent 对话：找 alice 帮我写代码", test_chat_agent),
    ]

    results = []
    for name, test in tests:
        print(f"\n\n>>> 开始测试：{name}")
        try:
            result = test()
            results.append((name, "成功", None))
        except Exception as e:
            results.append((name, "失败", str(e)))
            print(f"\n【测试失败】{name}: {e}")
            import traceback
            traceback.print_exc()

    # 汇总结果
    print_separator("测试结果汇总")
    for name, status, error in results:
        icon = "✓" if status == "成功" else "✗"
        print(f"  {icon} {name}: {status}")
        if error:
            print(f"    错误：{error[:100]}")

    print("\n\n关键观察点:")
    print("  1. V2 是否返回了正确的路由？")
    print("  2. V2 是否直接行动？")
    print("  3. V2 的提示词是否更简洁清晰？")

if __name__ == "__main__":
    run_all_tests()
