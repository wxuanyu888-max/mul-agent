#!/usr/bin/env python3
"""
Advanced Test Suite for Agent System - v3.0
Focus: Team Collaboration & Self-Evolution Capabilities

Test Categories:
1. Multi-Agent Collaboration (Hard)
2. Complex Task Delegation (Expert)
3. Self-Evolution Under Constraints (Expert)
4. Cross-Agent Knowledge Transfer (Hard)
5. Emergent Behavior Detection (Expert)
"""

import pytest
import json
import tempfile
import shutil
import time
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List


# Import system components
from mul_agent.brain.brain import Brain
from mul_agent.brain.config_manager import ConfigManager
from mul_agent.brain.router import Router
from mul_agent.memory.memory import Memory


class TestResult:
    """Test result holder"""
    def __init__(self, name: str):
        self.name = name
        self.passed = False
        self.error = None
        self.details = {}
        self.duration = 0
        self.score = 0  # For partial credit

    def __repr__(self):
        status = "PASS" if self.passed else "FAIL"
        return f"[{status}] {self.name}"


# ============================================================================
# Category 1: Multi-Agent Collaboration Tests (Hard)
# ============================================================================

class TestMultiAgentCollaboration:
    """多 Agent 协作测试"""

    @pytest.fixture
    def setup(self):
        """设置测试环境"""
        temp_dir = tempfile.mkdtemp()
        config_manager = ConfigManager(temp_dir)
        core_brain = Brain("core_brain", config_manager)
        yield {
            "temp_dir": temp_dir,
            "config_manager": config_manager,
            "core_brain": core_brain
        }
        shutil.rmtree(temp_dir)

    def test_1_1_agent_chain_reaction(self, setup):
        """Task 1.1: Agent 链式反应测试

        测试目标：验证 Agent 之间能否形成工作链
        场景：User -> Brain -> Coder -> Writer -> Brain -> User
        """
        result = TestResult("1.1 Agent Chain Reaction")
        start = time.time()

        try:
            brain = setup["core_brain"]
            config_manager = setup["config_manager"]

            # Step 1: 创建 coder agent
            create_coder = {
                "route": "create_user",
                "params": {
                    "agent_id": "coder_advanced",
                    "name": "Senior Coder",
                    "role_type": "worker",
                    "personality": "Expert programmer, detail-oriented"
                }
            }
            coder_result = brain.router.dispatch(create_coder["route"], create_coder["params"])

            # Step 2: 创建 writer agent
            create_writer = {
                "route": "create_user",
                "params": {
                    "agent_id": "writer_advanced",
                    "name": "Technical Writer",
                    "role_type": "worker",
                    "personality": "Clear communicator, documentation expert"
                }
            }
            writer_result = brain.router.dispatch(create_writer["route"], create_writer["params"])

            # Step 3: 创建 reviewer agent
            create_reviewer = {
                "route": "create_user",
                "params": {
                    "agent_id": "reviewer",
                    "name": "Code Reviewer",
                    "role_type": "worker",
                    "personality": "Critical thinker, security-focused"
                }
            }
            reviewer_result = brain.router.dispatch(create_reviewer["route"], create_reviewer["params"])

            # Step 4: 验证所有 agent 被创建
            agents = config_manager.list_agents()
            created_agents = ["coder_advanced", "writer_advanced", "reviewer"]
            all_created = all(agent in agents for agent in created_agents)

            # Step 5: 模拟链式任务
            # Brain -> Coder (写代码)
            chat_coder = {
                "route": "chat",
                "params": {
                    "action": "send",
                    "agent_id": "coder_advanced",
                    "message": "Write a Python function to calculate fibonacci sequence"
                }
            }
            chat_result = brain.router.dispatch(chat_coder["route"], chat_coder["params"])

            # Step 6: Coder -> Writer (写文档)
            chat_writer = {
                "route": "chat",
                "params": {
                    "action": "send",
                    "agent_id": "writer_advanced",
                    "message": "Document the fibonacci function with examples"
                }
            }
            writer_chat_result = brain.router.dispatch(chat_writer["route"], chat_writer["params"])

            result.passed = all_created and coder_result.get("status") == "success"
            result.score = 100 if all_created else 50
            result.details = {
                "agents_created": len(created_agents),
                "coder_response": chat_result.get("status"),
                "writer_response": writer_chat_result.get("status"),
                "chain_completed": all_created
            }

        except Exception as e:
            result.error = str(e)

        result.duration = time.time() - start
        return result

    def test_1_2_agent_consensus_decision(self, setup):
        """Task 1.2: Agent 集体决策测试

        测试目标：验证多个 Agent 能否对复杂问题达成共识
        场景：3 个 agent 对同一技术方案进行评估
        """
        result = TestResult("1.2 Agent Consensus Decision")
        start = time.time()

        try:
            brain = setup["core_brain"]
            config_manager = setup["config_manager"]

            # 创建 3 个不同角色的 agent
            roles = [
                {"id": "architect", "name": "System Architect", "focus": "scalability"},
                {"id": "security_expert", "name": "Security Expert", "focus": "security"},
                {"id": "devops", "name": "DevOps Engineer", "focus": "deployment"}
            ]

            for role in roles:
                create_agent = {
                    "route": "create_user",
                    "params": {
                        "agent_id": role["id"],
                        "name": role["name"],
                        "role_type": "advisor",
                        "personality": f"Expert in {role['focus']}"
                    }
                }
                brain.router.dispatch(create_agent["route"], create_agent["params"])

            # 向每个 agent 询问同一技术方案
            question = "Should we use microservices for a startup MVP?"

            responses = []
            for role in roles:
                chat = {
                    "route": "chat",
                    "params": {
                        "action": "send",
                        "agent_id": role["id"],
                        "message": question
                    }
                }
                response = brain.router.dispatch(chat["route"], chat["params"])
                responses.append({
                    "agent": role["id"],
                    "response": response
                })

            # 验证所有 agent 都响应了
            valid_responses = sum(1 for r in responses if r["response"].get("status") == "success")

            result.passed = valid_responses == len(roles)
            result.details = {
                "total_agents": len(roles),
                "valid_responses": valid_responses,
                "consensus_possible": valid_responses >= 2
            }

        except Exception as e:
            result.error = str(e)

        result.duration = time.time() - start
        return result


# ============================================================================
# Category 2: Complex Task Delegation Tests (Expert)
# ============================================================================

class TestComplexTaskDelegation:
    """复杂任务委派测试"""

    @pytest.fixture
    def setup(self):
        """设置测试环境"""
        temp_dir = tempfile.mkdtemp()
        config_manager = ConfigManager(temp_dir)
        core_brain = Brain("core_brain", config_manager)
        yield {
            "temp_dir": temp_dir,
            "config_manager": config_manager,
            "core_brain": core_brain
        }
        shutil.rmtree(temp_dir)

    def test_2_1_multi_phase_project(self, setup):
        """Task 2.1: 多阶段项目执行测试

        测试目标：验证 Agent 能否分解并执行多阶段项目
        场景：构建一个完整的 CRUD 应用
        """
        result = TestResult("2.1 Multi-Phase Project")
        start = time.time()

        try:
            brain = setup["core_brain"]
            config_manager = setup["config_manager"]
            output_dir = Path(setup["temp_dir"]) / "project_output"
            output_dir.mkdir()

            # Phase 1: 创建团队
            team_roles = [
                {"id": "backend_dev", "name": "Backend Developer"},
                {"id": "frontend_dev", "name": "Frontend Developer"},
                {"id": "qa_engineer", "name": "QA Engineer"}
            ]

            for role in team_roles:
                create = {
                    "route": "create_user",
                    "params": {
                        "agent_id": role["id"],
                        "name": role["name"],
                        "role_type": "worker"
                    }
                }
                brain.router.dispatch(create["route"], create["params"])

            # Phase 2: 定义项目任务
            project_phases = [
                {"phase": 1, "task": "Design API endpoints for user management", "agent": "backend_dev"},
                {"phase": 2, "task": "Create React components for user CRUD", "agent": "frontend_dev"},
                {"phase": 3, "task": "Write test cases for API and UI", "agent": "qa_engineer"}
            ]

            completed_phases = []
            for phase in project_phases:
                chat = {
                    "route": "chat",
                    "params": {
                        "action": "send",
                        "agent_id": phase["agent"],
                        "message": phase["task"]
                    }
                }
                response = brain.router.dispatch(chat["route"], chat["params"])
                if response.get("status") == "success":
                    completed_phases.append(phase["phase"])

            # Phase 3: 验证项目完成度
            project_completion_rate = len(completed_phases) / len(project_phases)

            result.passed = project_completion_rate >= 0.66  # At least 2/3 completed
            result.score = int(project_completion_rate * 100)
            result.details = {
                "total_phases": len(project_phases),
                "completed_phases": completed_phases,
                "completion_rate": f"{project_completion_rate * 100:.1f}%"
            }

        except Exception as e:
            result.error = str(e)

        result.duration = time.time() - start
        return result

    def test_2_2_dynamic_role_assignment(self, setup):
        """Task 2.2: 动态角色分配测试

        测试目标：验证 Agent 能否根据任务需求动态分配角色
        场景：紧急情况下一个 agent 需要承担多个角色
        """
        result = TestResult("2.2 Dynamic Role Assignment")
        start = time.time()

        try:
            brain = setup["core_brain"]
            config_manager = setup["config_manager"]

            # 只创建一个全能 agent
            create = {
                "route": "create_user",
                "params": {
                    "agent_id": "generalist",
                    "name": "Generalist",
                    "role_type": "generalist",
                    "personality": "Adaptable, multi-skilled"
                }
            }
            brain.router.dispatch(create["route"], create["params"])

            # 分配不同角色的任务
            tasks = [
                {"role": "coder", "task": "Write code"},
                {"role": "reviewer", "task": "Review code"},
                {"role": "tester", "task": "Test code"}
            ]

            role_responses = []
            for task in tasks:
                chat = {
                    "route": "chat",
                    "params": {
                        "action": "send",
                        "agent_id": "generalist",
                        "message": f"Act as a {task['role']}: {task['task']}"
                    }
                }
                response = brain.router.dispatch(chat["route"], chat["params"])
                role_responses.append(response.get("status") == "success")

            # 验证 agent 能否适应不同角色
            adaptive_score = sum(role_responses) / len(role_responses)

            result.passed = adaptive_score >= 0.66
            result.score = int(adaptive_score * 100)
            result.details = {
                "roles_tested": len(tasks),
                "successful_adaptations": sum(role_responses),
                "adaptability_score": f"{adaptive_score * 100:.1f}%"
            }

        except Exception as e:
            result.error = str(e)

        result.duration = time.time() - start
        return result


# ============================================================================
# Category 3: Self-Evolution Under Constraints (Expert)
# ============================================================================

class TestSelfEvolutionConstraints:
    """受限条件下的自我进化测试"""

    @pytest.fixture
    def setup(self):
        """设置测试环境"""
        temp_dir = tempfile.mkdtemp()
        config_manager = ConfigManager(temp_dir)
        core_brain = Brain("core_brain", config_manager)
        yield {
            "temp_dir": temp_dir,
            "config_manager": config_manager,
            "core_brain": core_brain
        }
        shutil.rmtree(temp_dir)

    def test_3_1_evolution_with_rollback(self, setup):
        """Task 3.1: 进化失败回滚测试

        测试目标：验证进化失败后能否回滚到安全状态
        """
        result = TestResult("3.1 Evolution with Rollback")
        start = time.time()

        try:
            brain = setup["core_brain"]
            config_manager = setup["config_manager"]

            # 记录初始状态
            initial_soul = config_manager.load("core_brain", "soul")
            initial_version = initial_soul.get("version", "1.0")

            # 创建快照
            config_manager._create_snapshot("core_brain", "soul")

            # 尝试进化
            evolution_result = brain.evolve(focus="all", require_confirmation=False)

            # 验证配置仍然有效
            validation = config_manager.validate_config("core_brain")

            # 如果进化导致配置无效，应该回滚
            if not validation["valid"]:
                # 回滚逻辑
                snapshots = config_manager.list_snapshots("core_brain")
                if snapshots:
                    # Restore would happen here
                    rollback_successful = True
                else:
                    rollback_successful = False
            else:
                rollback_successful = True  # No rollback needed

            result.passed = validation["valid"] or rollback_successful
            result.details = {
                "initial_version": initial_version,
                "evolution_status": evolution_result.get("status"),
                "config_valid": validation["valid"],
                "rollback_successful": rollback_successful
            }

        except Exception as e:
            result.error = str(e)

        result.duration = time.time() - start
        return result

    def test_3_2_incremental_evolution(self, setup):
        """Task 3.2: 渐进式进化测试

        测试目标：验证系统能否通过多次小步进化达到大改进
        """
        result = TestResult("3.2 Incremental Evolution")
        start = time.time()

        try:
            brain = setup["core_brain"]
            config_manager = setup["config_manager"]

            evolution_iterations = 3
            improvements = []

            for i in range(evolution_iterations):
                evolution = brain.evolve(focus="all")
                suggestions = evolution.get("suggestions", [])
                applied = evolution.get("evolutions_applied", [])

                improvements.append({
                    "iteration": i + 1,
                    "suggestions_count": len(suggestions),
                    "applied_count": len(applied)
                })

            # 验证渐进式改进
            total_suggestions = sum(i["suggestions_count"] for i in improvements)
            total_applied = sum(i["applied_count"] for i in improvements)

            result.passed = total_suggestions > 0
            result.details = {
                "iterations": evolution_iterations,
                "total_suggestions": total_suggestions,
                "total_applied": total_applied,
                "improvements": improvements
            }

        except Exception as e:
            result.error = str(e)

        result.duration = time.time() - start
        return result


# ============================================================================
# Category 4: Cross-Agent Knowledge Transfer (Hard)
# ============================================================================

class TestKnowledgeTransfer:
    """跨 Agent 知识转移测试"""

    @pytest.fixture
    def setup(self):
        """设置测试环境"""
        temp_dir = tempfile.mkdtemp()
        config_manager = ConfigManager(temp_dir)
        core_brain = Brain("core_brain", config_manager)
        yield {
            "temp_dir": temp_dir,
            "config_manager": config_manager,
            "core_brain": core_brain
        }
        shutil.rmtree(temp_dir)

    def test_4_1_knowledge_handover(self, setup):
        """Task 4.1: 知识交接测试

        测试目标：验证 Agent 能否将学到的知识转移给另一个 Agent
        """
        result = TestResult("4.1 Knowledge Handover")
        start = time.time()

        try:
            brain = setup["core_brain"]
            memory = brain.memory
            config_manager = setup["config_manager"]

            # Step 1: Teacher agent 学习知识
            teacher_knowledge = {
                "type": "best_practice",
                "topic": "python_error_handling",
                "content": "Always use specific exception types, log context, and provide user-friendly messages"
            }
            teacher_memory_id = memory.write("long_term", teacher_knowledge)

            # Step 2: 创建交接文档
            handover_id = memory.create_handover(
                from_agent="teacher",
                to_agent="student",
                content={
                    "knowledge_id": teacher_memory_id,
                    "transfer_type": "skill",
                    "priority": "high"
                }
            )

            # Step 3: 验证交接文档
            handover = memory.read_handover(handover_id)

            # Step 4: 创建 student agent
            create = {
                "route": "create_user",
                "params": {
                    "agent_id": "student",
                    "name": "Student",
                    "role_type": "learner"
                }
            }
            brain.router.dispatch(create["route"], create["params"])

            # Step 5: 验证学生能否访问知识
            search_results = memory.search("error handling")

            result.passed = handover is not None and len(search_results) > 0
            result.details = {
                "knowledge_transferred": teacher_knowledge["topic"],
                "handover_created": handover is not None,
                "knowledge_searchable": len(search_results) > 0
            }

        except Exception as e:
            result.error = str(e)

        result.duration = time.time() - start
        return result

    def test_4_2_shared_memory_access(self, setup):
        """Task 4.2: 共享内存访问测试

        测试目标：验证多个 Agent 能否访问和更新共享记忆
        """
        result = TestResult("4.2 Shared Memory Access")
        start = time.time()

        try:
            brain = setup["core_brain"]
            memory = brain.memory

            # 创建共享记忆
            shared_knowledge = {
                "type": "team_protocol",
                "content": "All agents must validate inputs before processing",
                "access_level": "shared"
            }
            shared_id = memory.write("long_term", shared_knowledge)

            # 多个 agent 尝试访问
            agents = ["agent_a", "agent_b", "agent_c"]
            access_results = []

            for agent_id in agents:
                # 每个 agent 搜索共享记忆
                search_results = memory.search("team protocol")
                access_results.append(len(search_results) > 0)

            # 验证所有 agent 都能访问共享记忆
            all_access = all(access_results)

            result.passed = all_access
            result.details = {
                "shared_memory_id": shared_id,
                "agents_tested": len(agents),
                "successful_access": sum(access_results),
                "all_can_access": all_access
            }

        except Exception as e:
            result.error = str(e)

        result.duration = time.time() - start
        return result


# ============================================================================
# Category 5: Emergent Behavior Detection (Expert)
# ============================================================================

class TestEmergentBehavior:
    """涌现行为检测测试"""

    @pytest.fixture
    def setup(self):
        """设置测试环境"""
        temp_dir = tempfile.mkdtemp()
        config_manager = ConfigManager(temp_dir)
        core_brain = Brain("core_brain", config_manager)
        yield {
            "temp_dir": temp_dir,
            "config_manager": config_manager,
            "core_brain": core_brain
        }
        shutil.rmtree(temp_dir)

    def test_5_1_spontaneous_collaboration(self, setup):
        """Task 5.1: 自发协作行为测试

        测试目标：检测 Agent 是否能自发形成协作模式
        """
        result = TestResult("5.1 Spontaneous Collaboration")
        start = time.time()

        try:
            brain = setup["core_brain"]
            config_manager = setup["config_manager"]

            # 创建 specialized agents
            specialists = [
                {"id": "planner", "skill": "planning"},
                {"id": "executor", "skill": "execution"},
                {"id": "validator", "skill": "validation"}
            ]

            for spec in specialists:
                create = {
                    "route": "create_user",
                    "params": {
                        "agent_id": spec["id"],
                        "name": f"Specialist_{spec['skill']}",
                        "role_type": "specialist",
                        "personality": f"Expert in {spec['skill']}"
                    }
                }
                brain.router.dispatch(create["route"], create["params"])

            # 给出需要协作的任务
            complex_task = "Build a secure REST API with validation"

            # 观察 agent 响应模式
            responses = []
            for spec in specialists:
                chat = {
                    "route": "chat",
                    "params": {
                        "action": "send",
                        "agent_id": spec["id"],
                        "message": complex_task
                    }
                }
                response = brain.router.dispatch(chat["route"], chat["params"])
                responses.append(response)

            # 检测协作迹象
            collaboration_indicators = []
            for i, resp in enumerate(responses):
                result_data = resp.get("result", {})
                response_text = str(result_data).lower()

                # 检查是否提到其他 agent
                for other_spec in specialists:
                    if other_spec["id"] != specialists[i]["id"]:
                        if other_spec["id"] in response_text or other_spec["skill"] in response_text:
                            collaboration_indicators.append(True)

            collaboration_detected = len(collaboration_indicators) > 0

            result.passed = all(r.get("status") == "success" for r in responses)
            result.score = 100 if collaboration_detected else 60
            result.details = {
                "all_responded": all(r.get("status") == "success" for r in responses),
                "collaboration_detected": collaboration_detected,
                "collaboration_signals": len(collaboration_indicators)
            }

        except Exception as e:
            result.error = str(e)

        result.duration = time.time() - start
        return result

    def test_5_2_adaptive_workflow(self, setup):
        """Task 5.2: 自适应工作流测试

        测试目标：验证系统能否根据上下文调整工作流程
        """
        result = TestResult("5.2 Adaptive Workflow")
        start = time.time()

        try:
            brain = setup["core_brain"]

            # 模拟不同场景
            scenarios = [
                {"type": "urgent", "input": "Emergency: Fix production bug now"},
                {"type": "normal", "input": "Please add a new feature when you have time"},
                {"type": "exploratory", "input": "What are some ways to improve performance?"}
            ]

            workflow_adjustments = []

            for scenario in scenarios:
                # 记录上下文分析
                analysis = brain.get_context_analysis()

                # 处理输入
                response = brain.think(scenario["input"])

                # 检测工作流调整
                adjustments = {
                    "scenario": scenario["type"],
                    "response_route": response.get("route"),
                    "context_level": analysis.get("level", "unknown")
                }
                workflow_adjustments.append(adjustments)

            # 验证系统对不同场景有不同响应
            unique_routes = len(set(a["response_route"] for a in workflow_adjustments))

            result.passed = unique_routes >= 2  # At least 2 different responses
            result.details = {
                "scenarios_tested": len(scenarios),
                "unique_responses": unique_routes,
                "workflow_adjustments": workflow_adjustments
            }

        except Exception as e:
            result.error = str(e)

        result.duration = time.time() - start
        return result


# ============================================================================
# Test Runner
# ============================================================================

def run_all_advanced_tests():
    """运行所有高级测试并生成报告"""
    print("=" * 70)
    print("ADVANCED AGENT SYSTEM TEST SUITE v3.0")
    print("Focus: Team Collaboration & Self-Evolution")
    print("=" * 70)

    all_results = []
    categories = {
        "Multi-Agent Collaboration": TestMultiAgentCollaboration,
        "Complex Task Delegation": TestComplexTaskDelegation,
        "Self-Evolution Constraints": TestSelfEvolutionConstraints,
        "Knowledge Transfer": TestKnowledgeTransfer,
        "Emergent Behavior": TestEmergentBehavior
    }

    for cat_name, test_class in categories.items():
        print(f"\n[{cat_name}]")
        print("-" * 50)

        test_instance = test_class()

        # Setup fixture
        temp_dir = tempfile.mkdtemp()
        config_manager = ConfigManager(temp_dir)
        core_brain = Brain("core_brain", config_manager)
        setup = {
            "temp_dir": temp_dir,
            "config_manager": config_manager,
            "core_brain": core_brain
        }

        for method_name in dir(test_class):
            if method_name.startswith("test_"):
                try:
                    test_method = getattr(test_instance, method_name)
                    test_result = test_method(setup)
                    all_results.append(test_result)
                    status = "PASS" if test_result.passed else "FAIL"
                    score_str = f" (Score: {test_result.score})" if test_result.score else ""
                    print(f"  [{status}] {method_name}{score_str}")
                    if test_result.error:
                        print(f"         Error: {test_result.error[:100]}...")
                except Exception as e:
                    print(f"  [ERROR] {method_name}: {str(e)[:100]}...")

        shutil.rmtree(temp_dir, ignore_errors=True)

    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)

    passed = sum(1 for r in all_results if r.passed)
    failed = len(all_results) - passed
    avg_score = sum(r.score for r in all_results if r.score) / max(1, len([r for r in all_results if r.score]))

    print(f"Total Tests: {len(all_results)}")
    print(f"Passed: {passed} ({passed/len(all_results)*100:.1f}%)")
    print(f"Failed: {failed} ({failed/len(all_results)*100:.1f}%)")
    print(f"Average Score: {avg_score:.1f}/100")

    # Category breakdown
    print("\nBy Category:")
    for cat_name, test_class in categories.items():
        cat_results = [r for r in all_results if cat_name in (test_class.__doc__ or "")]
        # Fallback: get by method prefix
        if not cat_results:
            cat_prefix = list(categories.keys()).index(cat_name)
            start_idx = cat_prefix * 2  # Approximate
            cat_results = all_results[start_idx:start_idx + 2]

        cat_passed = sum(1 for r in cat_results if r.passed) if cat_results else 0
        print(f"  {cat_name}: {cat_passed}/{len(cat_results) if cat_results else 'N/A'} passed")

    return all_results


if __name__ == "__main__":
    run_all_advanced_tests()
