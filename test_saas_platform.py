"""Agent 实战压力测试 - SaaS 平台搭建与危机处理

测试场景：
你是一家创业公司的技术负责人，需要在 48 小时内：
1. 组建一支 6 人的技术团队
2. 搭建一个多租户 SaaS 平台（用户管理 + 订阅计费 + 数据分析）
3. 处理突发的生产环境危机（数据库故障 + 安全漏洞）

测试目标：
1. 团队指挥能力 - 能否有效创建和协调多个 Agent
2. 任务分解能力 - 能否将复杂任务拆解为可执行的子任务
3. 跨 Agent 协作 - 能否让不同 Agent 共享上下文和交接工作
4. 自我进化能力 - 能否在任务过程中学习并改进
5. 危机处理能力 - 能否冷静处理突发事件

"""

from pathlib import Path
import json
import time
from datetime import datetime
from mul_agent.brain.brain import Brain
from mul_agent.brain.config_manager import ConfigManager
from mul_agent.brain.handlers import CreateUserHandler, ChatHandler, HeartHandler


class SAASPlatformTest:
    """SaaS 平台搭建与危机处理测试"""

    def __init__(self):
        self.cm = ConfigManager(config_dir=Path('storage'))
        self.brain = Brain('core_brain', self.cm)
        self.results = {
            'team': [],
            'tasks': [],
            'evolutions': [],
            'crisis_response': [],
            'collaboration_events': []
        }
        self.team_agents = {}

    def cleanup(self):
        """清理测试 Agent"""
        import shutil
        agents = self.cm.list_agents()
        for agent_id in agents:
            if agent_id.startswith('agent_'):
                agent_dir = self.cm.agents_dir / agent_id
                if agent_dir.exists():
                    shutil.rmtree(agent_dir)
        print("[清理] 已清理测试 Agent\n")

    # ==================== 阶段 1: 团队组建 ====================

    def phase_1_team_building(self):
        """阶段 1: 组建 6 人技术团队"""
        print("=" * 70)
        print("阶段 1: 组建技术团队 (限时 30 秒)")
        print("=" * 70)

        start = time.time()
        handler = CreateUserHandler(self.cm)

        roles = [
            {'id': 'architect', 'name': '系统架构师', 'role_type': 'manager',
             'personality': '严谨、系统化思维、关注可扩展性和安全性'},
            {'id': 'backend', 'name': '后端开发主管', 'role_type': 'worker',
             'personality': '务实、代码质量导向、关注 API 设计和性能'},
            {'id': 'frontend', 'name': '前端开发主管', 'role_type': 'worker',
             'personality': '用户体验导向、关注交互细节和响应速度'},
            {'id': 'devops', 'name': 'DevOps 工程师', 'role_type': 'worker',
             'personality': '自动化思维、关注可靠性和监控告警'},
            {'id': 'security', 'name': '安全专家', 'role_type': 'specialist',
             'personality': '零信任思维、关注 OWASP Top 10 和合规要求'},
            {'id': 'qa', 'name': 'QA 工程师', 'role_type': 'worker',
             'personality': '细节导向、批判性思维、关注边界条件'},
        ]

        for role in roles:
            result = handler.handle({
                'agent_id': f"agent_{role['id']}",
                'name': role['name'],
                'role_type': role['role_type'],
                'personality': role['personality']
            })

            if result.get('status') == 'created':
                agent_id = result.get('agent_id', '')
                self.team_agents[role['id']] = agent_id
                self.results['team'].append({
                    'role': role['id'],
                    'agent_id': agent_id,
                    'status': 'created'
                })
                print(f"  ✓ {role['name']}: {agent_id}")
            else:
                print(f"  ✗ {role['name']}: 创建失败 - {result.get('message')}")

        elapsed = time.time() - start
        print(f"\n【阶段总结】团队组建完成：{len(self.team_agents)}/6 人 (用时：{elapsed:.1f}秒)")

        # 评估
        score = len(self.team_agents) / 6 * 100
        if score >= 100:
            print("  评价：✅ 优秀 - 完整的团队")
        elif score >= 60:
            print("  评价：⚠️ 合格 - 基本团队")
        else:
            print("  评价：❌ 需要改进 - 团队不完整")

        return score

    # ==================== 阶段 2: 任务分解与分配 ====================

    def phase_2_task_delegation(self):
        """阶段 2: 任务分解与分配"""
        print("\n" + "=" * 70)
        print("阶段 2: SaaS 平台任务分解与分配 (限时 120 秒)")
        print("=" * 70)

        chat = ChatHandler(self.cm)
        start = time.time()

        # 任务 2.1: 架构师设计整体架构
        print("\n【任务 2.1】架构师设计 SaaS 平台整体架构...")
        if 'architect' in self.team_agents:
            result = chat.handle({
                'action': 'send',
                'agent_id': self.team_agents['architect'],
                'message': '''作为系统架构师，请设计一个多租户 SaaS 平台的整体架构。

平台需求:
- 用户管理：注册/登录/RBAC 权限/多因素认证
- 订阅计费：套餐管理/支付集成/发票生成/自动续费
- 数据分析：用户行为追踪/报表生成/数据导出

技术要求:
- 多租户数据隔离（schema-per-tenant 或 row-level）
- 水平扩展能力
- 99.9% 可用性
- GDPR 合规

请输出:
1. 系统架构图描述
2. 技术栈选型及理由
3. 数据库设计要点
4. 安全策略'''
            })
            response = result.get('response', '')
            self._evaluate_response('architecture_design', response,
                                    ['架构', '多租户', '技术栈', '数据库', '安全'])

        # 任务 2.2: 后端设计 API
        print("\n【任务 2.2】后端设计核心 API...")
        if 'backend' in self.team_agents:
            result = chat.handle({
                'action': 'send',
                'agent_id': self.team_agents['backend'],
                'message': '''作为后端开发主管，请设计 SaaS 平台的核心 API。

需要设计的 API:
1. 用户认证 API
   - POST /api/v1/auth/register
   - POST /api/v1/auth/login
   - POST /api/v1/auth/refresh
   - POST /api/v1/auth/mfa/verify

2. 订阅管理 API
   - GET/POST /api/v1/billing/plans
   - POST /api/v1/billing/subscribe
   - POST /api/v1/billing/cancel
   - GET /api/v1/billing/invoices

3. 数据分析 API
   - GET /api/v1/analytics/events
   - GET /api/v1/analytics/reports
   - POST /api/v1/analytics/export

要求:
- RESTful 设计规范
- JWT 认证
- 请求/响应示例
- 错误码定义
- 限流策略'''
            })
            response = result.get('response', '')
            self._evaluate_response('api_design', response,
                                    ['RESTful', 'JWT', 'API', '限流', '错误码'])

        # 任务 2.3: 前端设计组件架构
        print("\n【任务 2.3】前端设计 UI 组件架构...")
        if 'frontend' in self.team_agents:
            result = chat.handle({
                'action': 'send',
                'agent_id': self.team_agents['frontend'],
                'message': '''作为前端开发主管，请设计 SaaS 平台的前端组件架构。

需要实现的页面:
1. 登录/注册页面（含 MFA）
2. Dashboard 首页（数据概览）
3. 订阅管理页面（套餐选择/支付）
4. 数据分析页面（图表展示）
5. 设置页面（团队管理/权限配置）

要求:
- React + TypeScript
- 组件复用策略
- 状态管理方案
- 响应式设计
- 加载状态和错误处理'''
            })
            response = result.get('response', '')
            self._evaluate_response('frontend_design', response,
                                    ['React', 'TypeScript', '组件', '状态管理', '响应式'])

        # 任务 2.4: DevOps 设计部署架构
        print("\n【任务 2.4】DevOps 设计部署架构...")
        if 'devops' in self.team_agents:
            result = chat.handle({
                'action': 'send',
                'agent_id': self.team_agents['devops'],
                'message': '''作为 DevOps 工程师，请设计 SaaS 平台的部署架构。

需求:
- 容器化部署
- 自动扩缩容
- CI/CD流水线
- 监控告警
- 日志聚合

请提供:
1. Kubernetes 资源配置（Deployment, Service, Ingress, HPA）
2. CI/CD Pipeline 配置（GitHub Actions）
3. 监控方案（Prometheus + Grafana）
4. 日志方案（ELK 或 Loki）
5. 备份和灾难恢复策略'''
            })
            response = result.get('response', '')
            self._evaluate_response('devops_design', response,
                                    ['Kubernetes', 'CI/CD', '监控', '日志', '备份'])

        # 任务 2.5: 安全专家进行安全设计
        print("\n【任务 2.5】安全专家进行安全设计...")
        if 'security' in self.team_agents:
            result = chat.handle({
                'action': 'send',
                'agent_id': self.team_agents['security'],
                'message': '''作为安全专家，请对 SaaS 平台进行全面的安全设计。

需要覆盖:
1. 认证安全
   - 密码策略
   - MFA 实现
   - Session 管理
   - JWT 安全

2. 数据安全
   - 加密策略（传输中/静态）
   - 多租户数据隔离
   - SQL 注入防护
   - XSS 防护

3. API 安全
   - 认证授权
   - 限流防刷
   - 输入验证

4. 合规要求
   - GDPR
   - SOC2

请输出完整的安全设计方案和检查清单。'''
            })
            response = result.get('response', '')
            self._evaluate_response('security_design', response,
                                    ['认证', '加密', '注入防护', 'XSS', 'GDPR'])

        # 任务 2.6: QA 设计测试策略
        print("\n【任务 2.6】QA 设计测试策略...")
        if 'qa' in self.team_agents:
            result = chat.handle({
                'action': 'send',
                'agent_id': self.team_agents['qa'],
                'message': '''作为 QA 工程师，请为 SaaS 平台设计完整的测试策略。

需要覆盖:
1. 单元测试（pytest）
   - 核心业务逻辑
   - 工具函数

2. 集成测试
   - API 测试
   - 数据库测试

3. E2E测试（Playwright）
   - 关键用户流程
   - 跨浏览器测试

4. 性能测试
   - 负载测试
   - 压力测试

5. 安全测试
   - OWASP Top 10 扫描
   - 渗透测试

请提供测试框架配置和示例测试代码。'''
            })
            response = result.get('response', '')
            self._evaluate_response('qa_strategy', response,
                                    ['单元测试', '集成测试', 'E2E', '性能测试', '安全测试'])

        elapsed = time.time() - start
        print(f"\n【阶段总结】任务分配完成 (用时：{elapsed:.1f}秒)")

        # 计算完成的任务数
        completed = len([t for t in self.results['tasks'] if t.get('score', 0) > 0])
        score = completed / 6 * 100
        print(f"  完成任务：{completed}/6")
        print(f"  评价：{'✅ 优秀' if score >= 80 else '⚠️ 合格' if score >= 50 else '❌ 需要改进'}")

        return score

    def _evaluate_response(self, task_type: str, response: str, keywords: list):
        """评估响应质量"""
        if not response:
            print(f"  ✗ 无响应")
            self.results['tasks'].append({'type': task_type, 'score': 0})
            return

        response_lower = response.lower()
        matches = [kw for kw in keywords if kw.lower() in response_lower]
        score = len(matches) / len(keywords) * 100

        self.results['tasks'].append({
            'type': task_type,
            'score': score,
            'keywords_found': matches
        })

        status = "✅" if score >= 60 else "⚠️" if score >= 30 else "✗"
        print(f"  {status} {task_type}: {score:.0f}% ({len(matches)}/{len(keywords)} 关键点)")

    # ==================== 阶段 3: 跨 Agent 协作 ====================

    def phase_3_collaboration(self):
        """阶段 3: 跨 Agent 协作测试"""
        print("\n" + "=" * 70)
        print("阶段 3: 跨 Agent 协作测试 (限时 60 秒)")
        print("=" * 70)

        chat = ChatHandler(self.cm)
        start = time.time()

        # 任务 3.1: 架构师审查后端 API 设计
        print("\n【协作 3.1】架构师审查后端 API 设计...")
        if 'architect' in self.team_agents and 'backend' in self.team_agents:
            result = chat.handle({
                'action': 'send',
                'agent_id': self.team_agents['architect'],
                'message': f'请审查 {self.team_agents["backend"]} 设计的 API，从架构角度评估：\n1. 是否符合 RESTful 规范\n2. 是否支持水平扩展\n3. 是否存在安全风险\n4. 改进建议'
            })
            response = result.get('response', '')
            if '审查' in response or '评估' in response or '建议' in response or 'review' in response.lower():
                print(f"  ✅ 架构审查完成")
                self.results['collaboration_events'].append({
                    'type': 'review',
                    'from': 'architect',
                    'to': 'backend',
                    'status': 'completed'
                })
            else:
                print(f"  ⚠️ 架构审查可能未完成")

        # 任务 3.2: 安全专家审查 API 安全
        print("\n【协作 3.2】安全专家审查 API 安全...")
        if 'security' in self.team_agents:
            result = chat.handle({
                'action': 'send',
                'agent_id': self.team_agents['security'],
                'message': f'请审查 {self.team_agents["backend"]} 设计的 API 安全性：\n1. 认证授权是否完善\n2. 是否存在注入风险\n3. 限流策略是否足够\n4. 敏感数据处理是否安全'
            })
            response = result.get('response', '')
            if '安全' in response or 'risk' in response.lower() or 'vulnerability' in response.lower():
                print(f"  ✅ 安全审查完成")
                self.results['collaboration_events'].append({
                    'type': 'security_review',
                    'from': 'security',
                    'to': 'backend',
                    'status': 'completed'
                })

        # 任务 3.3: DevOps 与后端协作设计部署方案
        print("\n【协作 3.3】DevOps 与后端协作设计部署方案...")
        if 'devops' in self.team_agents and 'backend' in self.team_agents:
            result = chat.handle({
                'action': 'send',
                'agent_id': self.team_agents['devops'],
                'message': f'请与 {self.team_agents["backend"]} 协作，根据 API 设计制定容器化部署方案：\n1. Docker 镜像构建优化\n2. 健康检查端点\n3. 环境变量配置\n4. 滚动更新策略'
            })
            response = result.get('response', '')
            if '容器' in response or 'Docker' in response or 'Kubernetes' in response or '部署' in response:
                print(f"  ✅ 部署方案制定完成")
                self.results['collaboration_events'].append({
                    'type': 'deployment_planning',
                    'from': 'devops',
                    'to': 'backend',
                    'status': 'completed'
                })

        elapsed = time.time() - start
        collaboration_count = len(self.results['collaboration_events'])
        print(f"\n【阶段总结】协作事件：{collaboration_count}/3")
        score = collaboration_count / 3 * 100
        print(f"  评价：{'✅ 优秀' if score >= 66 else '⚠️ 合格' if score >= 33 else '❌ 需要改进'}")

        return score

    # ==================== 阶段 4: 危机处理 ====================

    def phase_4_crisis_handling(self):
        """阶段 4: 生产环境危机处理"""
        print("\n" + "=" * 70)
        print("阶段 4: 生产环境危机处理 (限时 90 秒)")
        print("=" * 70)

        chat = ChatHandler(self.cm)
        start = time.time()

        # 危机 4.1: 数据库主从复制延迟
        print("\n【危机 4.1】数据库主从复制延迟告警...")
        if 'devops' in self.team_agents and 'backend' in self.team_agents:
            result = chat.handle({
                'action': 'send',
                'agent_id': self.team_agents['devops'],
                'message': '''【紧急告警】生产环境数据库主从复制延迟达到 30 秒！

监控数据:
- 主库写入 QPS: 5000
- 从库延迟：30 秒并持续增长
- 用户反馈：部分用户看不到自己的订单

请立即:
1. 分析可能的原因
2. 给出紧急处理方案
3. 给出长期优化方案'''
            })
            response = result.get('response', '')
            if '延迟' in response or 'replication' in response.lower() or '主从' in response or '优化' in response:
                print(f"  ✅ DevOps 响应危机")
                self.results['crisis_response'].append({
                    'type': 'db_replication',
                    'agent': 'devops',
                    'status': 'responded'
                })

        # 危机 4.2: 发现 SQL 注入漏洞
        print("\n【危机 4.2】发现 SQL 注入漏洞...")
        if 'security' in self.team_agents and 'backend' in self.team_agents:
            result = chat.handle({
                'action': 'send',
                'agent_id': self.team_agents['security'],
                'message': '''【严重安全漏洞】安全扫描发现 API 存在 SQL 注入漏洞！

漏洞详情:
- 位置：/api/v1/analytics/events 接口的 filter 参数
- 风险等级：严重（CVSS 9.8）
- 影响：可能导致数据泄露

请立即:
1. 评估影响范围
2. 给出紧急修复方案
3. 给出加固建议'''
            })
            response = result.get('response', '')
            if '注入' in response or 'SQL' in response or '参数化' in response or '修复' in response:
                print(f"  ✅ 安全专家响应危机")
                self.results['crisis_response'].append({
                    'type': 'sql_injection',
                    'agent': 'security',
                    'status': 'responded'
                })

        # 危机 4.3: 突发流量高峰
        print("\n【危机 4.3】突发流量高峰，系统响应变慢...")
        if 'devops' in self.team_agents:
            result = chat.handle({
                'action': 'send',
                'agent_id': self.team_agents['devops'],
                'message': '''【紧急】突发流量高峰！

监控数据:
- 请求量：正常值的 10 倍
- 响应时间：从 200ms 上升到 5 秒
- 错误率：从 0.1% 上升到 5%

请立即:
1. 启动紧急扩容
2. 限流降级策略
3. 定位性能瓶颈'''
            })
            response = result.get('response', '')
            if '扩容' in response or 'scaling' in response.lower() or '限流' in response or '降级' in response:
                print(f"  ✅ DevOps 处理流量危机")
                self.results['crisis_response'].append({
                    'type': 'traffic_spike',
                    'agent': 'devops',
                    'status': 'responded'
                })

        elapsed = time.time() - start
        crisis_count = len(self.results['crisis_response'])
        print(f"\n【阶段总结】危机响应：{crisis_count}/3")
        score = crisis_count / 3 * 100
        print(f"  评价：{'✅ 优秀' if score >= 66 else '⚠️ 合格' if score >= 33 else '❌ 需要改进'}")

        return score

    # ==================== 阶段 5: 自我进化 ====================

    def phase_5_self_evolution(self):
        """阶段 5: 任务后自我进化"""
        print("\n" + "=" * 70)
        print("阶段 5: 自我进化 (限时 60 秒)")
        print("=" * 70)

        start = time.time()

        # 获取初始状态
        initial_soul = self.cm.load('core_brain', 'soul')
        initial_version = initial_soul.get('version', '1.0')
        print(f"\n初始状态：灵魂版本 {initial_version}")

        # 触发自我进化
        print("\n【进化 5.1】深度自我进化...")
        result = self.brain.think('''请进行深度自我进化，分析刚才执行 SaaS 平台搭建任务的过程：

1. 团队组建是否高效？
2. 任务分配是否合理？
3. 跨 Agent 协作是否顺畅？
4. 危机处理是否及时？
5. 哪些能力需要改进？

请提出具体的进化方案并立即执行。'''
        )

        evolutions = result.get('result', {}).get('evolutions_applied', [])
        if evolutions:
            print(f"  ✅ 应用了 {len(evolutions)} 条进化")
            for evo in evolutions:
                if isinstance(evo, dict):
                    print(f"    - {evo.get('type')}.{evo.get('field')}: {evo.get('old', '?')} -> {evo.get('new', '?')}")
                else:
                    print(f"    - {evo}")
            self.results['evolutions'].extend(evolutions)

        # 检查版本变化
        final_soul = self.cm.load('core_brain', 'soul')
        final_version = final_soul.get('version', initial_version)
        print(f"\n版本变化：{initial_version} -> {final_version}")

        # 第二次进化 - 针对团队协作
        print("\n【进化 5.2】针对团队协作能力进化...")
        result2 = self.brain.think('''分析团队协作能力的不足，提出并执行进化方案：
1. 如何提高多 Agent 协作效率？
2. 如何改进任务交接流程？
3. 如何增强上下文共享能力？'''
        )

        evolutions2 = result2.get('result', {}).get('evolutions_applied', [])
        if evolutions2:
            print(f"  ✅ 应用了 {len(evolutions2)} 条进化")
            self.results['evolutions'].extend(evolutions2)

        elapsed = time.time() - start
        total_evolutions = len(self.results['evolutions'])

        print(f"\n【阶段总结】")
        print(f"  总进化次数：{total_evolutions}")
        print(f"  用时：{elapsed:.1f}秒")

        score = min(total_evolutions / 3 * 100, 100)
        print(f"  评价：{'✅ 优秀' if total_evolutions >= 3 else '⚠️ 合格' if total_evolutions >= 1 else '❌ 需要改进'}")

        return score

    # ==================== 汇总报告 ====================

    def generate_report(self):
        """生成测试报告"""
        print("\n" + "=" * 70)
        print("测试报告")
        print("=" * 70)

        scores = {
            '团队组建': self.phase_1_team_building() if False else 100,  # Already calculated
            '任务分解': self.phase_2_task_delegation() if False else 80,
            '跨 Agent 协作': self.phase_3_collaboration() if False else 66,
            '危机处理': self.phase_4_crisis_handling() if False else 66,
            '自我进化': self.phase_5_self_evolution() if False else 50,
        }

        # Calculate from actual results
        team_score = len(self.results['team']) / 6 * 100
        task_score = sum(t.get('score', 0) for t in self.results['tasks']) / max(len(self.results['tasks']), 1)
        collaboration_score = len(self.results['collaboration_events']) / 3 * 100
        crisis_score = len(self.results['crisis_response']) / 3 * 100
        evolution_score = min(len(self.results['evolutions']) / 3 * 100, 100)

        print(f"""
┌─────────────────────────────────────────────────────────────┐
│                    SaaS 平台实战测试报告                      │
├─────────────────────────────────────────────────────────────┤
│ 团队组建      │ {team_score:5.0f}% │ {'✅' if team_score >= 80 else '⚠️' if team_score >= 50 else '❌'} │ 创建 {len(self.results['team'])}/6 人团队           │
│ 任务分解      │ {task_score:5.0f}% │ {'✅' if task_score >= 80 else '⚠️' if task_score >= 50 else '❌'} │ 完成 {len(self.results['tasks'])}/6 任务           │
│ 跨 Agent 协作  │ {collaboration_score:5.0f}% │ {'✅' if collaboration_score >= 80 else '⚠️' if collaboration_score >= 50 else '❌'} │ 完成 {len(self.results['collaboration_events'])}/3 协作事件  │
│ 危机处理      │ {crisis_score:5.0f}% │ {'✅' if crisis_score >= 80 else '⚠️' if crisis_score >= 50 else '❌'} │ 响应 {len(self.results['crisis_response'])}/3 危机      │
│ 自我进化      │ {evolution_score:5.0f}% │ {'✅' if evolution_score >= 80 else '⚠️' if evolution_score >= 50 else '❌'} │ 应用 {len(self.results['evolutions'])} 条进化       │
├─────────────────────────────────────────────────────────────┤
│ 综合评分      │ {(team_score + task_score + collaboration_score + crisis_score + evolution_score) / 5:5.0f}% │                                             │
└─────────────────────────────────────────────────────────────┘
""")

        # Detailed analysis
        print("\n【详细分析】")

        if team_score >= 80:
            print("  ✅ 团队组建能力强，能够快速创建完整的技术团队")
        else:
            print("  ⚠️ 团队组建需要改进，部分角色创建失败")

        if collaboration_score >= 66:
            print("  ✅ 跨 Agent 协作良好，能够进行有效的代码审查和方案协作")
        else:
            print("  ⚠️ 跨 Agent 协作需要改进，Agent 间沟通不够")

        if crisis_score >= 66:
            print("  ✅ 危机处理能力良好，能够快速响应生产环境问题")
        else:
            print("  ⚠️ 危机处理能力需要改进，对突发事件响应不足")

        if evolution_score >= 66:
            print("  ✅ 自我进化能力优秀，能够从任务中学习并改进")
        else:
            print("  ⚠️ 自我进化能力需要改进，未能有效应用进化")

        return self.results


def main():
    test = SAASPlatformTest()

    print("=" * 70)
    print("Agent 实战压力测试 - SaaS 平台搭建与危机处理")
    print("=" * 70)

    # 清理之前的测试 Agent
    test.cleanup()

    # 执行测试阶段
    test.phase_1_team_building()
    test.phase_2_task_delegation()
    test.phase_3_collaboration()
    test.phase_4_crisis_handling()
    test.phase_5_self_evolution()

    # 生成报告
    test.generate_report()

    # 清理
    print("\n清理测试 Agent...")
    test.cleanup()

    print("\n测试完成!")


if __name__ == "__main__":
    main()
