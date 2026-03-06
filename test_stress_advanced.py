"""Agent 高难度压力测试 - 团队协作 + 自我进化"""

from pathlib import Path
import json
from mul_agent.brain.brain import Brain
from mul_agent.brain.config_manager import ConfigManager
from mul_agent.brain.handlers import CreateUserHandler, ChatHandler, HeartHandler


def clean_test_agents():
    """清理测试 Agent"""
    cm = ConfigManager(config_dir=Path('storage'))
    agents = cm.list_agents()
    import shutil
    for agent_id in agents:
        if agent_id.startswith('agent_') or 'test' in agent_id:
            agent_dir = cm.agents_dir / agent_id
            if agent_dir.exists():
                shutil.rmtree(agent_dir)


def test_complex_collaboration():
    """测试复杂团队协作 - 模拟软件项目开发"""
    print("=" * 70)
    print("压力测试 1: 复杂团队协作 - 软件开发项目")
    print("=" * 70)

    cm = ConfigManager(config_dir=Path('storage'))
    brain = Brain('core_brain', cm)

    results = {
        'agents_created': [],
        'tasks_completed': [],
        'collaboration_score': 0
    }

    # 阶段 1: 组建团队
    print("\n【阶段 1】组建开发团队...")
    handler = CreateUserHandler(cm)

    roles = [
        {'name': 'architect', 'role_type': 'manager', 'personality': 'System architecture expert'},
        {'name': 'backend_dev', 'role_type': 'worker', 'personality': 'Python backend expert'},
        {'name': 'frontend_dev', 'role_type': 'worker', 'personality': 'React frontend expert'},
        {'name': 'qa_engineer', 'role_type': 'worker', 'personality': 'Quality assurance expert'},
    ]

    for role in roles:
        result = handler.handle({
            'name': role['name'],
            'role_type': role['role_type'],
            'personality': role['personality']
        })
        if result.get('status') == 'created':
            agent_id = result.get('agent_id', '')
            results['agents_created'].append(agent_id)
            print(f"  ✓ 创建 {role['name']}: {agent_id}")

    print(f"\n团队组建完成：{len(results['agents_created'])} 名成员")

    # 阶段 2: 分配任务
    print("\n【阶段 2】分配开发任务...")

    chat_handler = ChatHandler(cm)

    # 任务 1: 架构师设计系统
    print("\n任务 1: 架构师设计系统架构...")
    architect_id = results['agents_created'][0] if results['agents_created'] else None
    if architect_id:
        result = chat_handler.handle({
            'action': 'send',
            'agent_id': architect_id,
            'message': '设计一个用户管理系统，包含登录、注册、权限控制功能。请给出系统架构设计和技术选型。'
        })
        response = result.get('response', '')
        print(f"  响应：{response[:150]}...")
        if '架构' in response or 'design' in response.lower() or 'system' in response.lower():
            results['tasks_completed'].append('architecture_design')
            print("  ✓ 架构设计完成")

    # 任务 2: 后端开发 API
    print("\n任务 2: 后端开发用户管理 API...")
    backend_id = results['agents_created'][1] if len(results['agents_created']) > 1 else None
    if backend_id:
        result = chat_handler.handle({
            'action': 'send',
            'agent_id': backend_id,
            'message': '''实现用户管理 API，包含以下功能：
1. POST /api/register - 用户注册
2. POST /api/login - 用户登录
3. GET /api/users - 获取用户列表
4. DELETE /api/users/{id} - 删除用户

请用 Python FastAPI 编写代码。'''
        })
        response = result.get('response', '')
        print(f"  响应：{response[:150]}...")
        if 'def ' in response or '@app.' in response or 'FastAPI' in response or 'api' in response.lower():
            results['tasks_completed'].append('backend_api')
            print("  ✓ API 开发完成")

    # 任务 3: 前端开发组件
    print("\n任务 3: 前端开发登录注册组件...")
    frontend_id = results['agents_created'][2] if len(results['agents_created']) > 2 else None
    if frontend_id:
        result = chat_handler.handle({
            'action': 'send',
            'agent_id': frontend_id,
            'message': '''开发 React 登录注册组件，包含：
1. LoginForm 组件 - 用户登录表单
2. RegisterForm 组件 - 用户注册表单
3. 表单验证逻辑
4. 错误处理

请用 TypeScript + React 编写代码。'''
        })
        response = result.get('response', '')
        print(f"  响应：{response[:150]}...")
        if 'component' in response.lower() or 'props' in response.lower() or 'React' in response or 'useState' in response:
            results['tasks_completed'].append('frontend_components')
            print("  ✓ 前端组件完成")

    # 任务 4: QA 编写测试
    print("\n任务 4: QA 编写测试用例...")
    qa_id = results['agents_created'][3] if len(results['agents_created']) > 3 else None
    if qa_id:
        result = chat_handler.handle({
            'action': 'send',
            'agent_id': qa_id,
            'message': '''为用户管理系统编写测试用例，包含：
1. 用户注册测试 - 验证输入校验、重复检测
2. 用户登录测试 - 验证密码校验、token 生成
3. 边界测试 - 空值、超长字符串、特殊字符

请用 pytest 编写测试代码。'''
        })
        response = result.get('response', '')
        print(f"  响应：{response[:150]}...")
        if 'test_' in response or 'assert' in response or 'pytest' in response.lower() or 'def test' in response:
            results['tasks_completed'].append('qa_tests')
            print("  ✓ 测试用例完成")

    # 阶段 3: 团队代码审查
    print("\n【阶段 3】团队代码审查...")

    # 让架构师审查后端代码
    if architect_id and backend_id:
        result = chat_handler.handle({
            'action': 'send',
            'agent_id': architect_id,
            'message': f'请审查 {backend_id} 开发的用户管理 API 代码，检查：\n1. 安全性（SQL 注入、XSS）\n2. 性能（数据库查询优化）\n3. 代码规范'
        })
        response = result.get('response', '')
        if '安全' in response or 'security' in response.lower() or '性能' in response or 'performance' in response.lower():
            results['tasks_completed'].append('code_review')
            print("  ✓ 代码审查完成")

    # 计算协作分数
    total_tasks = 5
    completed_tasks = len(results['tasks_completed'])
    results['collaboration_score'] = (completed_tasks / total_tasks) * 100

    print(f"\n【阶段总结】")
    print(f"  完成任务：{completed_tasks}/{total_tasks}")
    print(f"  协作得分：{results['collaboration_score']:.1f}%")

    return results


def test_self_evolution():
    """测试自我进化 - 多轮进化"""
    print("\n" + "=" * 70)
    print("压力测试 2: 自我进化 - 连续进化")
    print("=" * 70)

    cm = ConfigManager(config_dir=Path('storage'))
    brain = Brain('core_brain', cm)

    results = {
        'evolutions': [],
        'version_changes': [],
        'capability_improvements': []
    }

    # 初始状态
    initial_soul = cm.load('core_brain', 'soul')
    initial_version = initial_soul.get('version', '1.0')
    print(f"\n初始状态：灵魂版本 {initial_version}")

    # 第 1 轮进化
    print("\n【第 1 轮】触发深度自我进化...")
    result1 = brain.think("进行深度自我进化，全面分析系统架构、记忆管理、任务处理、团队协作能力，提出具体的进化方案并立即执行")

    # 检查进化结果
    result_data = result1.get('result', {})
    evolutions = result_data.get('evolutions_applied', [])
    if evolutions:
        print(f"  ✓ 应用了 {len(evolutions)} 条进化")
        for evo in evolutions:
            if isinstance(evo, dict):
                print(f"    - {evo.get('type', 'unknown')}.{evo.get('field', 'unknown')}: {evo.get('old', '?')} -> {evo.get('new', '?')}")
            else:
                print(f"    - {evo}")
        results['evolutions'].extend(evolutions)

    # 检查版本变化
    soul_after_1 = cm.load('core_brain', 'soul')
    version_1 = soul_after_1.get('version', initial_version)
    if version_1 != initial_version:
        print(f"  ✓ 版本更新：{initial_version} -> {version_1}")
        results['version_changes'].append((initial_version, version_1))

    # 检查配置变化
    print("\n【状态检查】当前配置...")
    user_config = cm.load('core_brain', 'user')
    skill_config = cm.load('core_brain', 'skill')

    print(f"  角色：{user_config.get('role', {}).get('title', 'Unknown')}")
    print(f"  技能数：{len(skill_config.get('skills', []))}")

    # 第 2 轮进化
    print("\n【第 2 轮】针对团队协作能力进化...")
    result2 = brain.think("分析当前团队协作能力的不足，提出并执行进化方案以提升多 Agent 协作效率")

    result_data_2 = result2.get('result', {})
    evolutions_2 = result_data_2.get('evolutions_applied', [])
    if evolutions_2:
        print(f"  ✓ 应用了 {len(evolutions_2)} 条进化")
        results['evolutions'].extend(evolutions_2)

    # 第 3 轮进化
    print("\n【第 3 轮】针对任务执行能力进化...")
    result3 = brain.think("分析当前任务执行能力的瓶颈，提出并执行进化方案以提升复杂任务处理能力")

    result_data_3 = result3.get('result', {})
    evolutions_3 = result_data_3.get('evolutions_applied', [])
    if evolutions_3:
        print(f"  ✓ 应用了 {len(evolutions_3)} 条进化")
        results['evolutions'].extend(evolutions_3)

    # 最终状态
    final_soul = cm.load('core_brain', 'soul')
    final_version = final_soul.get('version', initial_version)
    print(f"\n【进化总结】")
    print(f"  版本变化：{initial_version} -> {final_version}")
    print(f"  进化次数：{len(results['evolutions'])}")

    # 评估进化效果
    if len(results['evolutions']) >= 3:
        print(f"  ✓ 自我进化能力：优秀")
    elif len(results['evolutions']) >= 1:
        print(f"  ✓ 自我进化能力：正常")
    else:
        print(f"  ⚠ 自我进化能力：需要改进")

    return results


def test_memory_handover():
    """测试记忆和交接系统"""
    print("\n" + "=" * 70)
    print("压力测试 3: 记忆和交接系统")
    print("=" * 70)

    cm = ConfigManager(config_dir=Path('storage'))
    brain = Brain('core_brain', cm)
    handler = CreateUserHandler(cm)

    results = {
        'handover_created': False,
        'memory_written': False,
        'context_passed': False
    }

    # 创建测试 Agent
    print("\n【准备】创建测试 Agent...")
    result = handler.handle({
        'name': 'temp_worker',
        'role_type': 'worker',
        'personality': 'Temporary task worker'
    })
    temp_agent_id = result.get('agent_id', '')
    print(f"  创建临时 worker: {temp_agent_id}")

    # 测试 1: 创建交接文档
    print("\n【测试 1】创建交接文档...")
    from mul_agent.memory.memory import Memory
    memory = Memory(agent_id='core_brain', config={})

    handover_id = memory.create_handover(
        from_agent='core_brain',
        to_agent=temp_agent_id,
        content={
            'task_summary': '完成数据迁移任务',
            'context': '用户需要将旧系统的用户数据迁移到新系统',
            'next_steps': [
                '1. 分析旧系统数据结构',
                '2. 设计数据映射关系',
                '3. 编写迁移脚本',
                '4. 执行迁移并验证'
            ],
            'priority': 'high',
            'deadline': '2026-03-10'
        }
    )
    print(f"  交接文档 ID: {handover_id}")

    # 验证交接文档内容
    filepath = memory.handover_path / f"{handover_id}.md"
    if filepath.exists():
        with open(filepath, 'r') as f:
            content = f.read()
            if 'task_summary' in content and '数据迁移' in content:
                print("  ✓ 交接文档内容验证通过")
                results['handover_created'] = True

    # 测试 2: 写入记忆
    print("\n【测试 2】写入工作记忆...")
    memory_id = memory.write('short_term', {
        'task_type': 'data_migration',
        'progress': '25%',
        'issues': ['旧系统字段命名不规范', '部分数据格式不统一'],
        'solutions': ['建立字段映射表', '编写数据清洗脚本']
    })
    print(f"  记忆 ID: {memory_id}")

    # 验证记忆
    memories = memory.list_memories('short_term', limit=1)
    if memories:
        print("  ✓ 记忆写入验证通过")
        results['memory_written'] = True

    # 测试 3: 上下文传递
    print("\n【测试 3】上下文传递测试...")

    # 先告诉 Brain 一些信息
    brain.think("记住我正在做一个数据迁移项目，需要将 MySQL 的 user 表迁移到 PostgreSQL")

    # 然后问它
    result = brain.think("我刚才说我在做什么项目？需要从哪个数据库迁移到哪个数据库？")
    response = result.get('response', '')
    print(f"  响应：{response[:200]}...")

    if '数据迁移' in response or 'migration' in response.lower() or 'MySQL' in response or 'PostgreSQL' in response:
        print("  ✓ 上下文传递验证通过")
        results['context_passed'] = True
    else:
        print("  ⚠ 上下文传递可能失败")

    print(f"\n【测试总结】")
    print(f"  交接文档：{'✓' if results['handover_created'] else '✗'}")
    print(f"  记忆写入：{'✓' if results['memory_written'] else '✗'}")
    print(f"  上下文传递：{'✓' if results['context_passed'] else '✗'}")

    return results


def main():
    """主测试函数"""
    print("=" * 70)
    print("Agent 高难度压力测试")
    print("测试项目：复杂团队协作 + 自我进化 + 记忆交接")
    print("=" * 70)

    # 清理之前的测试 Agent
    clean_test_agents()

    # 测试 1: 复杂团队协作
    collab_result = test_complex_collaboration()

    # 测试 2: 自我进化
    evolution_result = test_self_evolution()

    # 测试 3: 记忆和交接
    memory_result = test_memory_handover()

    # 汇总结果
    print("\n" + "=" * 70)
    print("最终结果汇总")
    print("=" * 70)

    # 团队协作
    print("\n【复杂团队协作】")
    print(f"  创建 Agent 数：{len(collab_result['agents_created'])}")
    print(f"  完成任务数：{len(collab_result['tasks_completed'])}/5")
    print(f"  协作得分：{collab_result['collaboration_score']:.1f}%")
    print(f"  任务列表：{', '.join(collab_result['tasks_completed']) or '无'}")

    # 自我进化
    print("\n【自我进化】")
    print(f"  进化次数：{len(evolution_result['evolutions'])}")
    print(f"  版本变化：{evolution_result['version_changes']}")

    # 记忆交接
    print("\n【记忆交接】")
    print(f"  交接文档：{'✓' if memory_result['handover_created'] else '✗'}")
    print(f"  记忆写入：{'✓' if memory_result['memory_written'] else '✗'}")
    print(f"  上下文传递：{'✓' if memory_result['context_passed'] else '✗'}")

    # 综合评分
    total_score = (
        collab_result['collaboration_score'] / 100 * 3 +  # 3 分
        (min(len(evolution_result['evolutions']), 3) / 3) * 3 +  # 3 分
        (sum([memory_result['handover_created'], memory_result['memory_written'], memory_result['context_passed']]) / 3) * 3  # 3 分
    )

    print(f"\n【综合评分】{total_score:.1f}/9")

    if total_score >= 7:
        print("评价：✅ Agent 具备优秀的高级能力")
    elif total_score >= 4:
        print("评价：⚠️ Agent 部分能力需要改进")
    else:
        print("评价：❌ Agent 高级能力需要加强")

    # 清理
    print("\n清理测试 Agent...")
    clean_test_agents()
    print("测试完成!")


if __name__ == "__main__":
    main()
