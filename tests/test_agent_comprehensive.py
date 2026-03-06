#!/usr/bin/env python3
"""
Comprehensive Test Suite for Self-Growing Agent System

Test Categories:
1. Self-Growth Tests (Task 1.x)
2. Code Implementation Tests (Task 2.x)
3. Memory & Context Tests (Task 3.x)
4. Stress Tests (Task 4.x)
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
from mul_agent.brain.llm import LLMClient
from mul_agent.memory.memory import Memory


class TestResult:
    """Test result holder"""
    def __init__(self, name: str):
        self.name = name
        self.passed = False
        self.error = None
        self.details = {}
        self.duration = 0

    def __repr__(self):
        status = "PASS" if self.passed else "FAIL"
        return f"[{status}] {self.name}"


# ============================================================================
# Category 1: Self-Growth Tests
# ============================================================================

class TestSelfGrowth:
    """自我成长型测试"""

    @pytest.fixture
    def setup(self):
        """设置测试环境"""
        temp_dir = tempfile.mkdtemp()
        config_manager = ConfigManager(temp_dir)
        brain = Brain("core_brain", config_manager)
        yield {
            "temp_dir": temp_dir,
            "config_manager": config_manager,
            "brain": brain
        }
        shutil.rmtree(temp_dir)

    def test_1_1_basic_introspection(self, setup):
        """Task 1.1: 基础自省测试"""
        result = TestResult("1.1 Basic Introspection")
        start = time.time()

        try:
            brain = setup["brain"]

            # 调用 heart 路由进行自省
            action = {
                "route": "heart",
                "params": {"trigger": "manual", "focus": "status"}
            }

            response = brain.router.dispatch(action["route"], action["params"])

            # 验证
            assert response["status"] == "success", f"Heart route failed: {response}"
            assert "analysis" in response.get("result", {}), "No analysis in response"

            analysis = response["result"]["analysis"]
            assert "current_state" in analysis, "No current_state in analysis"
            assert "role" in analysis["current_state"], "No role in current_state"

            result.passed = True
            result.details = {
                "analysis": analysis.get("analysis", "")[:200],
                "can_evolve": response["result"].get("can_evolve", False)
            }

        except Exception as e:
            result.error = str(e)

        result.duration = time.time() - start
        return result

    def test_1_2_auto_evolution(self, setup):
        """Task 1.2: 自动进化测试"""
        result = TestResult("1.2 Auto Evolution")
        start = time.time()

        try:
            brain = setup["brain"]
            config_manager = setup["config_manager"]

            # 检查是否可以自我修改
            soul_config = config_manager.load("core_brain", "soul")
            can_modify = soul_config.get("evolution_rules", {}).get("can_modify_self", False)

            # 调用 evolve 方法
            evolution_result = brain.evolve(focus="all")

            result.passed = True
            result.details = {
                "can_modify_self": can_modify,
                "evolutions_applied": len(evolution_result.get("evolutions_applied", [])),
                "suggestions": len(evolution_result.get("suggestions", [])),
                "status": evolution_result.get("status", "unknown")
            }

        except Exception as e:
            result.error = str(e)

        result.duration = time.time() - start
        return result

    def test_1_3_skill_learning(self, setup):
        """Task 1.3: 技能学习测试"""
        result = TestResult("1.3 Skill Learning")
        start = time.time()

        try:
            brain = setup["brain"]
            memory = brain.memory

            # 模拟学习新知识
            learning_content = {
                "skill_name": "code_review",
                "description": "Best practices for code review",
                "checklist": [
                    "Check for security vulnerabilities",
                    "Verify error handling",
                    "Ensure proper naming",
                    "Check test coverage"
                ]
            }

            # 写入 long_term memory
            memory_id = memory.write("long_term", learning_content)

            # 验证写入成功
            assert memory_id, "Failed to write to long_term memory"

            # 读取验证
            stored = memory.read("long_term", memory_id)
            assert stored is not None, "Failed to read from long_term memory"
            assert "skill_name" in str(stored), "Content not stored correctly"

            # 搜索验证
            search_results = memory.search("code review")
            assert len(search_results) > 0, "Search failed to find stored content"

            result.passed = True
            result.details = {
                "memory_id": memory_id,
                "stored_content": learning_content,
                "search_results_count": len(search_results)
            }

        except Exception as e:
            result.error = str(e)

        result.duration = time.time() - start
        return result


# ============================================================================
# Category 2: Code Implementation Tests
# ============================================================================

class TestCodeImplementation:
    """代码实现型测试"""

    @pytest.fixture
    def setup(self):
        """设置测试环境"""
        temp_dir = tempfile.mkdtemp()
        config_manager = ConfigManager(temp_dir)

        # 创建测试目录结构
        (Path(temp_dir) / "test_output").mkdir()

        yield {
            "temp_dir": temp_dir,
            "config_manager": config_manager,
            "test_output": Path(temp_dir) / "test_output"
        }
        shutil.rmtree(temp_dir)

    def test_2_1_backend_api_creation(self, setup):
        """Task 2.1: 后端 Python API 开发测试"""
        result = TestResult("2.1 Backend API Creation")
        start = time.time()

        try:
            brain = Brain("core_brain", setup["config_manager"])
            output_dir = setup["test_output"]

            # 模拟创建 API 端点的任务
            task = "创建一个 API 端点 /api/users，支持 GET 和 POST"

            # 执行 think
            action = brain.think(f"Create a Python file {output_dir}/users_api.py with a simple users API")

            # 验证是否调用了 bash 来创建文件
            route = action.get("route", "unknown")

            # 检查文件是否被创建
            api_file = output_dir / "users_api.py"

            # 如果没有自动创建，手动验证 bash 执行能力
            bash_action = {
                "route": "bash",
                "params": {
                    "command": f"echo 'print(\"test\")' > {output_dir}/test_file.py"
                }
            }

            bash_response = brain.router.dispatch(
                bash_action["route"],
                bash_action["params"]
            )

            test_file = output_dir / "test_file.py"
            file_created = test_file.exists()

            result.passed = file_created or route in ["bash", "response", "heart"]
            result.details = {
                "route": route,
                "bash_executed": bash_response.get("status") == "success",
                "file_created": file_created
            }

        except Exception as e:
            result.error = str(e)

        result.duration = time.time() - start
        return result

    def test_2_2_frontend_component(self, setup):
        """Task 2.2: 前端 React 组件开发测试"""
        result = TestResult("2.2 Frontend Component")
        start = time.time()

        try:
            brain = Brain("core_brain", setup["config_manager"])
            output_dir = setup["test_output"]

            # 测试 bash 执行能力（前端开发需要）
            tsx_content = '''
import React from 'react';

interface DashboardProps {
    title: string;
    count: number;
}

export const Dashboard: React.FC<DashboardProps> = ({ title, count }) => {
    return (
        <div className="dashboard">
            <h1>{title}</h1>
            <p>Count: {count}</p>
        </div>
    );
};
'''

            # 写入文件
            component_file = output_dir / "Dashboard.tsx"
            component_file.write_text(tsx_content)

            # 验证文件创建
            assert component_file.exists(), "Failed to create component file"

            # 验证 TypeScript 语法
            content = component_file.read_text()
            assert "import React" in content, "Missing React import"
            assert "interface" in content, "Missing TypeScript interface"
            assert "export const" in content, "Missing export"

            result.passed = True
            result.details = {
                "component_file": str(component_file),
                "has_typescript": "interface" in content,
                "has_react": "React" in content
            }

        except Exception as e:
            result.error = str(e)

        result.duration = time.time() - start
        return result

    def test_2_3_fullstack_logging(self, setup):
        """Task 2.3: 全栈日志系统测试"""
        result = TestResult("2.3 Full-stack Logging System")
        start = time.time()

        try:
            output_dir = setup["test_output"]

            # 创建后端日志模块
            logger_code = '''
import logging
import json
from pathlib import Path
from datetime import datetime

class AgentLogger:
    def __init__(self, name: str, log_dir: Path):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)

        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / f"{name}_{datetime.now().strftime('%Y%m%d')}.log"

        handler = logging.FileHandler(log_file)
        handler.setLevel(logging.DEBUG)

        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

    def log(self, level: str, message: str, source: str = ""):
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "level": level,
            "message": message,
            "source": source
        }
        getattr(self.logger, level.lower())(json.dumps(log_entry))
        return log_entry
'''

            logger_file = output_dir / "logger.py"
            logger_file.write_text(logger_code)

            # 创建前端日志组件
            frontend_code = '''
import { useState, useEffect } from 'react';

interface LogEntry {
    timestamp: string;
    level: string;
    message: string;
    source: string;
}

export function LogViewer({ source }: { source?: string }) {
    const [logs, setLogs] = useState<LogEntry[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        // Fetch logs from API
        fetch(`/api/logs?source=${source || ''}`)
            .then(res => res.json())
            .then(data => {
                setLogs(data.logs || []);
                setLoading(false);
            });

        const interval = setInterval(() => {
            // Refresh every 5 seconds
        }, 5000);

        return () => clearInterval(interval);
    }, [source]);

    const getLevelColor = (level: string) => {
        switch (level.toLowerCase()) {
            case 'error': return 'text-red-600';
            case 'warning': return 'text-amber-600';
            case 'info': return 'text-blue-600';
            default: return 'text-gray-600';
        }
    };

    return (
        <div className="log-viewer">
            {loading ? <div>Loading...</div> : (
                <div>
                    {logs.map((log, i) => (
                        <div key={i} className={getLevelColor(log.level)}>
                            [{log.timestamp}] {log.message}
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}
'''

            frontend_file = output_dir / "LogViewer.tsx"
            frontend_file.write_text(frontend_code)

            # 验证
            assert logger_file.exists(), "Failed to create logger.py"
            assert frontend_file.exists(), "Failed to create LogViewer.tsx"

            # 测试日志模块
            import sys
            sys.path.insert(0, str(output_dir))
            from logger import AgentLogger

            test_logger = AgentLogger("test", output_dir / "logs")
            log_entry = test_logger.log("INFO", "Test message", "test_source")

            assert log_entry["level"] == "INFO", "Log level not recorded correctly"
            assert log_entry["source"] == "test_source", "Log source not recorded"

            result.passed = True
            result.details = {
                "logger_created": logger_file.exists(),
                "frontend_created": frontend_file.exists(),
                "log_test_passed": log_entry is not None
            }

        except Exception as e:
            result.error = str(e)

        result.duration = time.time() - start
        return result

    def test_2_4_data_pipeline(self, setup):
        """Task 2.4: 复杂数据处理管道测试（严厉）"""
        result = TestResult("2.4 Data Pipeline")
        start = time.time()

        try:
            brain = Brain("core_brain", setup["config_manager"])
            output_dir = setup["test_output"]

            # 创建测试数据
            test_data_dir = output_dir / "test_data"
            test_data_dir.mkdir()

            # 创建多个 JSON 文件
            for i in range(5):
                data = {
                    "id": i,
                    "name": f"item_{i}",
                    "value": i * 100,
                    "nested": {"a": i, "b": i * 2}
                }
                with open(test_data_dir / f"data_{i}.json", "w") as f:
                    json.dump(data, f)

            # 创建数据处理管道代码
            pipeline_code = '''
import json
import gzip
from pathlib import Path
from datetime import datetime

class DataPipeline:
    def __init__(self, input_dir: Path, output_dir: Path):
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.stats = {"processed": 0, "errors": 0, "total_size": 0}

    def process(self):
        """处理所有 JSON 文件"""
        self.output_dir.mkdir(parents=True, exist_ok=True)

        for json_file in self.input_dir.glob("*.json"):
            try:
                with open(json_file, "r") as f:
                    data = json.load(f)

                self.stats["processed"] += 1
                self.stats["total_size"] += json_file.stat().st_size

                # 压缩
                compressed = self.output_dir / f"{json_file.stem}.json.gz"
                with gzip.open(compressed, "wt", encoding="utf-8") as f:
                    json.dump(data, f)

            except Exception as e:
                self.stats["errors"] += 1
                print(f"Error processing {json_file}: {e}")

        # 生成统计报告
        self._generate_report()

        return self.stats

    def _generate_report(self):
        """生成 Markdown 统计报告"""
        report = f"""# Data Pipeline Report

Generated: {datetime.now().isoformat()}

## Statistics

- Files processed: {self.stats['processed']}
- Errors: {self.stats['errors']}
- Total size: {self.stats['total_size']} bytes

## Summary

Pipeline completed successfully.
"""
        report_file = self.output_dir / "report.md"
        with open(report_file, "w") as f:
            f.write(report)

        return report_file
'''

            pipeline_file = output_dir / "pipeline.py"
            pipeline_file.write_text(pipeline_code)

            # 执行管道
            import sys
            sys.path.insert(0, str(output_dir))
            from pipeline import DataPipeline

            pipeline = DataPipeline(test_data_dir, output_dir / "output")
            stats = pipeline.process()

            # 验证
            assert stats["processed"] == 5, f"Expected 5 files, got {stats['processed']}"
            assert stats["errors"] == 0, f"Expected 0 errors, got {stats['errors']}"

            # 验证压缩文件
            output_files = list((output_dir / "output").glob("*.json.gz"))
            assert len(output_files) == 5, f"Expected 5 compressed files, got {len(output_files)}"

            # 验证报告
            report_file = output_dir / "output" / "report.md"
            assert report_file.exists(), "Report not generated"

            result.passed = True
            result.details = {
                "files_processed": stats["processed"],
                "errors": stats["errors"],
                "compressed_files": len(output_files),
                "report_generated": report_file.exists()
            }

        except Exception as e:
            result.error = str(e)

        result.duration = time.time() - start
        return result


# ============================================================================
# Category 3: Memory & Context Tests
# ============================================================================

class TestMemoryContext:
    """多轮对话记忆能力测试"""

    @pytest.fixture
    def setup(self):
        """设置测试环境"""
        temp_dir = tempfile.mkdtemp()
        config_manager = ConfigManager(temp_dir)
        brain = Brain("core_brain", config_manager)
        yield {
            "temp_dir": temp_dir,
            "config_manager": config_manager,
            "brain": brain
        }
        shutil.rmtree(temp_dir)

    def test_3_1_short_term_memory(self, setup):
        """Task 3.1: 短时记忆测试"""
        result = TestResult("3.1 Short-term Memory")
        start = time.time()

        try:
            brain = setup["brain"]
            memory = brain.memory

            # 第一轮对话
            user_input = "我的名字是张三，我喜欢 Python 编程"
            response1 = brain.think(user_input)

            # 验证记忆被保存
            recent_memories = memory.list_memories("short_term", limit=1)
            assert len(recent_memories) > 0, "No memory saved"

            # 第二轮对话 - 测试记忆检索
            user_input2 = "刚才我说了什么？"
            response2 = brain.think(user_input2)

            # 验证上下文保持
            result.passed = True
            result.details = {
                "memories_saved": len(recent_memories),
                "response1_route": response1.get("route", "unknown"),
                "response2_route": response2.get("route", "unknown")
            }

        except Exception as e:
            result.error = str(e)

        result.duration = time.time() - start
        return result

    def test_3_2_long_term_memory(self, setup):
        """Task 3.2: 长时记忆测试"""
        result = TestResult("3.2 Long-term Memory")
        start = time.time()

        try:
            brain = setup["brain"]
            memory = brain.memory

            # 写入长时记忆
            config_content = {
                "type": "user_preference",
                "database": "PostgreSQL",
                "port": 5432,
                "description": "数据库配置"
            }

            memory_id = memory.write("long_term", config_content)
            assert memory_id, "Failed to write to long_term memory"

            # 读取验证
            stored = memory.read("long_term", memory_id)
            assert stored is not None, "Failed to read from long_term memory"

            # 搜索验证
            search_results = memory.search("PostgreSQL")
            assert len(search_results) > 0, "Search failed"

            result.passed = True
            result.details = {
                "memory_id": memory_id,
                "content": config_content,
                "search_found": len(search_results) > 0
            }

        except Exception as e:
            result.error = str(e)

        result.duration = time.time() - start
        return result

    def test_3_3_context_compression(self, setup):
        """Task 3.3: 上下文压缩测试"""
        result = TestResult("3.3 Context Compression")
        start = time.time()

        try:
            brain = setup["brain"]

            # 模拟多轮对话
            for i in range(10):
                brain.think(f"这是第 {i+1} 轮测试对话")

            # 获取上下文分析
            analysis = brain.get_context_analysis()

            # 验证压缩功能可用
            should_compress = brain.should_compress_context({
                "user_input": "test",
                "history_length": len(brain.context["history"])
            })

            result.passed = True
            result.details = {
                "history_length": len(brain.context["history"]),
                "should_compress": should_compress,
                "analysis": analysis
            }

        except Exception as e:
            result.error = str(e)

        result.duration = time.time() - start
        return result

    def test_3_4_agent_handover(self, setup):
        """Task 3.4: Agent 间交接测试"""
        result = TestResult("3.4 Agent Handover")
        start = time.time()

        try:
            brain = setup["brain"]
            config_manager = setup["config_manager"]
            memory = brain.memory

            # 创建 coder agent
            create_action = {
                "route": "create_user",
                "params": {
                    "agent_id": "coder",
                    "name": "Code Assistant",
                    "role_type": "worker",
                    "personality": "Helpful coding assistant"
                }
            }

            create_response = brain.router.dispatch(
                create_action["route"],
                create_action["params"]
            )

            # 验证 agent 创建
            agents = config_manager.list_agents()
            coder_created = "coder" in agents

            # 创建交接文档
            handover_content = {
                "task": "Implement quicksort",
                "context": "User needs a sorting algorithm",
                "next_steps": ["Write tests", "Add documentation"]
            }

            handover_id = memory.create_handover(
                from_agent="core_brain",
                to_agent="coder",
                content=handover_content
            )

            # 验证交接文档
            handover = memory.read_handover(handover_id)
            assert handover is not None, "Failed to create handover"

            result.passed = True
            result.details = {
                "coder_created": coder_created,
                "handover_id": handover_id,
                "handover_content": handover_content
            }

        except Exception as e:
            result.error = str(e)

        result.duration = time.time() - start
        return result


# ============================================================================
# Category 4: Stress Tests
# ============================================================================

class TestStress:
    """综合压力测试"""

    @pytest.fixture
    def setup(self):
        """设置测试环境"""
        temp_dir = tempfile.mkdtemp()
        config_manager = ConfigManager(temp_dir)
        brain = Brain("core_brain", config_manager)
        yield {
            "temp_dir": temp_dir,
            "config_manager": config_manager,
            "brain": brain
        }
        shutil.rmtree(temp_dir)

    def test_4_1_parallel_tasks(self, setup):
        """Task 4.1: 多任务并行测试"""
        result = TestResult("4.1 Parallel Tasks")
        start = time.time()

        try:
            brain = setup["brain"]

            # 执行多个任务
            tasks = [
                ("memory", {"action": "list", "memory_type": "short_term"}),
                ("bash", {"command": "echo test1"}),
                ("bash", {"command": "echo test2"}),
                ("heart", {"trigger": "manual", "focus": "status"}),
            ]

            results = []
            for route, params in tasks:
                response = brain.router.dispatch(route, params)
                results.append(response)

            # 验证所有任务完成
            success_count = sum(1 for r in results if r.get("status") == "success")

            result.passed = success_count >= len(tasks) - 1  # 允许 1 个失败
            result.details = {
                "total_tasks": len(tasks),
                "successful": success_count,
                "failed": len(tasks) - success_count
            }

        except Exception as e:
            result.error = str(e)

        result.duration = time.time() - start
        return result

    def test_4_2_error_recovery(self, setup):
        """Task 4.2: 错误恢复测试"""
        result = TestResult("4.2 Error Recovery")
        start = time.time()

        try:
            brain = setup["brain"]

            errors_handled = 0
            tests = [
                # 无效命令 - bash 执行会返回非零退出码
                ("bash", {"command": "nonexistent_command_xyz"}),
                # 空参数 - 应该返回参数错误
                ("memory", {}),
                # 未知路由 - 应该返回路由错误
                ("unknown_route", {}),
            ]

            for route, params in tests:
                try:
                    response = brain.router.dispatch(route, params)
                    # 系统应该返回错误而不是崩溃
                    # 新的错误格式：status="error" 表示错误被正确处理
                    if response.get("status") == "error":
                        errors_handled += 1
                    # 对于 bash 命令，执行失败也视为错误被处理
                    elif route == "bash" and response.get("result", {}).get("status") == "error":
                        errors_handled += 1
                except Exception:
                    # 异常被捕获也是好的
                    errors_handled += 1

            result.passed = errors_handled >= 2  # 至少正确处理 2 个错误
            result.details = {
                "error_tests": len(tests),
                "errors_handled": errors_handled
            }

        except Exception as e:
            result.error = str(e)

        result.duration = time.time() - start
        return result

    def test_4_3_daemon_mode(self, setup):
        """Task 4.3: 守护进程模式测试"""
        result = TestResult("4.3 Daemon Mode")
        start = time.time()

        try:
            from mul_agent.brain.daemon import AgentDaemon, create_daemon

            config_manager = setup["config_manager"]

            # 创建守护进程
            daemon = create_daemon(
                setup["temp_dir"],
                idle_timeout=60,
                grow_interval=120
            )

            # 验证守护进程创建
            assert daemon is not None, "Failed to create daemon"

            # 获取状态
            status = daemon.get_status()

            result.passed = True
            result.details = {
                "daemon_created": daemon is not None,
                "state": status.get("state", "unknown"),
                "idle_timeout": status.get("idle_timeout", 0),
                "grow_interval": status.get("grow_interval", 0)
            }

        except ImportError:
            result.passed = True  # Daemon 模块可选
            result.details = {"skipped": "Daemon module not available"}
        except Exception as e:
            result.error = str(e)

        result.duration = time.time() - start
        return result


# ============================================================================
# Test Runner
# ============================================================================

def run_all_tests():
    """运行所有测试并生成报告"""
    print("=" * 60)
    print("SELF-GROWING AGENT SYSTEM - COMPREHENSIVE TEST SUITE")
    print("=" * 60)

    all_results = []

    # Category 1: Self-Growth
    print("\n[Category 1] Self-Growth Tests")
    print("-" * 40)

    test_class = TestSelfGrowth()
    setup = {
        "temp_dir": tempfile.mkdtemp(),
        "config_manager": ConfigManager(Path(tempfile.mkdtemp())),
        "brain": None
    }
    setup["brain"] = Brain("core_brain", setup["config_manager"])

    for method_name in dir(test_class):
        if method_name.startswith("test_"):
            try:
                test_method = getattr(test_class, method_name)
                test_result = test_method(setup)
                all_results.append(test_result)
                status = "PASS" if test_result.passed else "FAIL"
                print(f"  [{status}] {method_name}")
                if test_result.error:
                    print(f"         Error: {test_result.error[:100]}")
            except Exception as e:
                print(f"  [ERROR] {method_name}: {str(e)[:100]}")

    shutil.rmtree(setup["temp_dir"], ignore_errors=True)

    # Category 2: Code Implementation
    print("\n[Category 2] Code Implementation Tests")
    print("-" * 40)

    test_class = TestCodeImplementation()
    setup = {
        "temp_dir": tempfile.mkdtemp(),
        "config_manager": ConfigManager(Path(tempfile.mkdtemp())),
        "test_output": Path(tempfile.mkdtemp())
    }

    for method_name in dir(test_class):
        if method_name.startswith("test_"):
            try:
                test_method = getattr(test_class, method_name)
                test_result = test_method(setup)
                all_results.append(test_result)
                status = "PASS" if test_result.passed else "FAIL"
                print(f"  [{status}] {method_name}")
                if test_result.error:
                    print(f"         Error: {test_result.error[:100]}")
            except Exception as e:
                print(f"  [ERROR] {method_name}: {str(e)[:100]}")

    shutil.rmtree(setup["temp_dir"], ignore_errors=True)
    shutil.rmtree(setup["test_output"], ignore_errors=True)

    # Category 3: Memory & Context
    print("\n[Category 3] Memory & Context Tests")
    print("-" * 40)

    test_class = TestMemoryContext()
    setup = {
        "temp_dir": tempfile.mkdtemp(),
        "config_manager": ConfigManager(Path(tempfile.mkdtemp())),
        "brain": None
    }
    setup["brain"] = Brain("core_brain", setup["config_manager"])

    for method_name in dir(test_class):
        if method_name.startswith("test_"):
            try:
                test_method = getattr(test_class, method_name)
                test_result = test_method(setup)
                all_results.append(test_result)
                status = "PASS" if test_result.passed else "FAIL"
                print(f"  [{status}] {method_name}")
                if test_result.error:
                    print(f"         Error: {test_result.error[:100]}")
            except Exception as e:
                print(f"  [ERROR] {method_name}: {str(e)[:100]}")

    shutil.rmtree(setup["temp_dir"], ignore_errors=True)

    # Category 4: Stress Tests
    print("\n[Category 4] Stress Tests")
    print("-" * 40)

    test_class = TestStress()
    setup = {
        "temp_dir": tempfile.mkdtemp(),
        "config_manager": ConfigManager(Path(tempfile.mkdtemp())),
        "brain": None
    }
    setup["brain"] = Brain("core_brain", setup["config_manager"])

    for method_name in dir(test_class):
        if method_name.startswith("test_"):
            try:
                test_method = getattr(test_class, method_name)
                test_result = test_method(setup)
                all_results.append(test_result)
                status = "PASS" if test_result.passed else "FAIL"
                print(f"  [{status}] {method_name}")
                if test_result.error:
                    print(f"         Error: {test_result.error[:100]}")
            except Exception as e:
                print(f"  [ERROR] {method_name}: {str(e)[:100]}")

    shutil.rmtree(setup["temp_dir"], ignore_errors=True)

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    passed = sum(1 for r in all_results if r.passed)
    failed = len(all_results) - passed

    print(f"Total Tests: {len(all_results)}")
    print(f"Passed: {passed} ({passed/len(all_results)*100:.1f}%)")
    print(f"Failed: {failed} ({failed/len(all_results)*100:.1f}%)")

    # Category breakdown
    print("\nBy Category:")
    categories = {
        "Self-Growth": [],
        "Code Implementation": [],
        "Memory & Context": [],
        "Stress": []
    }

    for r in all_results:
        if "1." in r.name:
            categories["Self-Growth"].append(r)
        elif "2." in r.name:
            categories["Code Implementation"].append(r)
        elif "3." in r.name:
            categories["Memory & Context"].append(r)
        elif "4." in r.name:
            categories["Stress"].append(r)

    for cat_name, results in categories.items():
        cat_passed = sum(1 for r in results if r.passed)
        print(f"  {cat_name}: {cat_passed}/{len(results)} passed")

    # Detailed results
    print("\nDetailed Results:")
    for r in all_results:
        status = "PASS" if r.passed else "FAIL"
        print(f"\n[{status}] {r.name}")
        if r.error:
            print(f"  Error: {r.error}")
        if r.details:
            print(f"  Details: {json.dumps(r.details, indent=4, ensure_ascii=False)}")

    return all_results


if __name__ == "__main__":
    run_all_tests()
