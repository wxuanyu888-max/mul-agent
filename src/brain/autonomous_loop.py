"""Autonomous Loop - 自主执行循环

让 Agent 能够：
1. 理解用户意图
2. 分解任务成步骤
3. 自主执行循环（观察→决策→行动→反思）
4. 任务完成后自动反思（Heart）
"""

import json
import re
import asyncio
from typing import Any, Dict, List, Optional
from mul_agent.brain.llm import LLMClient


class AutonomousLoop:
    """自主执行循环 - 让 Agent 真正能独立完成任务"""

    def __init__(self, brain, progress_callback=None):
        self.brain = brain
        self.llm = brain.llm
        self.max_iterations = 15  # 防止无限循环
        self.task_count = 0  # 任务计数器，用于触发 heart
        self.progress_callback = progress_callback  # 进度回调函数
        self.step_cache = {}  # 步骤结果缓存

    async def run(self, user_input: str) -> Dict[str, Any]:
        """
        自主执行任务

        流程:
        1. 理解意图 - 用户到底想要什么
        2. 初始规划 - 分解成步骤
        3. 执行循环:
           - 观察当前状态
           - 决定下一步
           - 执行
           - 反思结果
           - 更新计划
        4. 任务完成后反思（Heart）
        """
        self.brain._update_state("autonomous_start", "启动自主执行模式")

        # 1. 理解意图
        intent = await self._understand_intent(user_input)

        if intent.get("error"):
            return {
                "status": "error",
                "message": f"意图理解失败：{intent.get('error')}"
            }

        self.brain._update_state("intent_understood", f"理解意图：{intent.get('goal')}")
        await self._notify_progress("intent_understood", {"goal": intent.get("goal"), "type": intent.get("type")})

        # 2. 初始规划
        plan = await self._create_plan(intent, user_input)

        if plan.get("error"):
            return {
                "status": "error",
                "message": f"任务规划失败：{plan.get('error')}"
            }

        self.brain._update_state("plan_created", f"创建计划：{len(plan.get('steps', []))}个步骤")
        await self._notify_progress("plan_created", {"steps_count": len(plan.get("steps", []))})

        # 保存到上下文
        self.plan = plan.get("steps", [])
        self.intent = intent
        self.results = []
        self.iteration = 0

        # 3. 执行循环
        while not self._is_plan_complete() and self.iteration < self.max_iterations:
            self.iteration += 1

            self.brain._update_state("iteration", f"执行迭代 {self.iteration}/{self.max_iterations}")

            # 观察
            observation = self._observe()

            # 检查是否有可并行执行的步骤
            completed_count = len([r for r in self.results if r.get("status") != "pending"])
            parallel_steps = self._find_parallel_steps(completed_count)

            if parallel_steps:
                # 并行执行
                results = await self._execute_steps_parallel(parallel_steps)
                self.results.extend(results)

                # 对每个结果进行条件反思
                for i, (step, result) in enumerate(zip(parallel_steps, results)):
                    if self._should_reflect(step, result):
                        plan_progress = (completed_count + i + 1) / len(self.plan) if self.plan else 1.0
                        reflection = await self._deep_reflect(step, result, plan_progress)
                        if reflection.get("need_adjustment"):
                            self.plan = await self._adjust_plan(reflection)
                    else:
                        # 简单成功，跳过反思
                        pass
            else:
                # 串行执行
                next_step = await self._decide_next_step(observation)

                if next_step is None:
                    self.brain._update_state("no_more_steps", "没有更多步骤可执行")
                    break

                # 执行（带重试）
                result = await self._execute_with_retry(next_step)
                self.results.append(result)

                # 条件反射：只在需要时才调用 LLM
                if self._should_reflect(next_step, result):
                    plan_progress = (len(self.results)) / len(self.plan) if self.plan else 1.0
                    reflection = await self._deep_reflect(next_step, result, plan_progress)
                else:
                    # 简单成功，使用轻量级反思
                    reflection = {
                        "meets_expectations": True,
                        "need_adjustment": False,
                        "analysis": "步骤执行成功，无需调整",
                        "lesson_learned": None
                    }

                # 更新计划
                if reflection.get("need_adjustment"):
                    # 先尝试动态调整
                    adjusted = await self._adjust_plan_dynamically(reflection)
                    if not adjusted:
                        self.plan = await self._adjust_plan(reflection)

        # 4. 任务完成后反思（Heart）
        await self._post_task_reflection(user_input)

        # 5. 合成最终结果
        final_result = self._synthesize_result(user_input)

        self.brain._update_state("autonomous_completed", "自主执行完成")

        return final_result

    async def _understand_intent(self, user_input: str) -> Dict[str, Any]:
        """理解用户意图 - 增强版（动态记忆检索）"""
        # 先快速分类任务类型
        task_type = self._quick_classify_task(user_input)

        # 根据任务类型决定检索策略
        memory_config = {
            "implementation": {"max_results": 5, "type": "long_term"},
            "exploration": {"max_results": 3, "type": "short_term"},
            "fix": {"max_results": 5, "type": "long_term"},
            "analysis": {"max_results": 4, "type": "long_term"},
            "simple": {"max_results": 0, "type": None}
        }

        config = memory_config.get(task_type, {"max_results": 2, "type": "short_term"})

        # 检索相关记忆
        relevant_memories = []
        if config["max_results"] > 0:
            if hasattr(self.brain, 'memory_decision') and self.brain.memory_decision:
                try:
                    relevant_memories = self.brain.memory_decision.retrieve_relevant_memories(
                        query=user_input,
                        memory_type=config["type"],
                        max_results=config["max_results"]
                    )
                    if relevant_memories:
                        await self._notify_progress("memories_found", {
                            "count": len(relevant_memories),
                            "type": config["type"]
                        })
                except Exception as e:
                    print(f"Memory retrieval error: {e}")

        # 获取工作区信息
        workspace_info = ""
        if hasattr(self.brain, 'workspace') and self.brain.workspace:
            workspace_info = self.brain.workspace.get_context_prompt()

        prompt = f"""分析用户的真实意图：

用户输入：{user_input}

**工作区信息**:
{workspace_info}

{f'**相关历史记忆**: {str(relevant_memories)[:500]}' if relevant_memories else ''}

请分析：
1. 用户想要什么？（goal）
2. 涉及什么项目/文件？（scope，参考工作区信息）
3. 是什么类型的任务？（type: exploration/implementation/fix/optimization/analysis）
4. 怎么算完成？（success_criteria）
5. 任务复杂度如何？（simple/medium/complex）

以 JSON 格式返回：
{{
    "goal": "用户的核心目标",
    "scope": "涉及的范围",
    "type": "任务类型",
    "success_criteria": "完成的标准",
    "complexity": "simple/medium/complex",
    "relevant_memories_count": {len(relevant_memories)}
}}
"""
        try:
            result = self.llm.chat(prompt)
            content = result.get("content", "")

            # 尝试提取 JSON
            import re
            json_match = re.search(r'\{[\s\S]*\}', content)
            if json_match:
                intent = json.loads(json_match.group())
                # 添加记忆到意图中
                if relevant_memories:
                    intent["relevant_memories"] = [m.get("content") for m in relevant_memories]
                return intent

            # Fallback
            return {
                "goal": user_input,
                "scope": "",
                "type": "exploration",
                "success_criteria": "用户满意"
            }
        except Exception as e:
            return {"error": str(e), "goal": user_input}

    async def _create_plan(self, intent: Dict[str, Any], user_input: str) -> Dict[str, Any]:
        """创建执行计划 - 增强版（利用记忆 + 工作区信息）"""
        # 构建记忆上下文
        memory_context = ""
        if intent.get("relevant_memories"):
            memory_context = "\n**.related_memories**\n" + "\n".join(
                f"- {str(m)[:200]}" for m in intent.get("relevant_memories", [])
            )

        # 获取工作区信息
        workspace_info = ""
        if hasattr(self.brain, 'workspace') and self.brain.workspace:
            workspace_info = self.brain.workspace.get_context_prompt()

        prompt = f"""
**任务目标**: {intent.get('goal')}
**任务类型**: {intent.get('type')}
**成功标准**: {intent.get('success_criteria')}
**复杂度**: {intent.get('complexity', 'medium')}

**工作区信息**:
{workspace_info}

{memory_context}

请将该任务分解成具体的执行步骤。

**可用工具/路由**:
- bash: 执行 shell 命令
- file_edit: 读取/修改文件
- chat: 与其他 Agent 对话（alice-代码，bob-规划，wangyue-日常）
- memory: 写入/读取记忆
- response: 直接回复用户

**要求**:
1. 每个步骤必须是可执行的原子操作
2. 指定每个步骤的路由类型
3. 标记哪些步骤可以并行（无依赖关系的独立操作）
4. 对于需要专业知识的任务（写代码、修 bug），委派给 alice
5. 参考相关记忆，避免重复工作
6. 利用工作区信息，了解项目结构和依赖

以 JSON 数组格式返回：
[
    {{
        "step": 1,
        "route": "bash/file_edit/chat/memory/response",
        "params": {{"command": "..."}},
        "description": "这一步做什么",
        "executor": "self/alice/bob/wangyue",
        "can_parallel": false,
        "depends_on": []  // 依赖的步骤索引
    }},
    ...
]
"""
        try:
            result = self.llm.chat(prompt)
            content = result.get("content", "")

            import re
            json_match = re.search(r'\[[\s\S]*\]', content)
            if json_match:
                steps = json.loads(json_match.group())
                return {"steps": steps}

            return {"error": "无法解析计划"}
        except Exception as e:
            return {"error": str(e)}

    def _is_plan_complete(self) -> bool:
        """检查计划是否完成"""
        if not self.plan:
            return len(self.results) > 0

        # 检查是否还有未完成的步骤
        completed_steps = [r for r in self.results if r.get("status") != "pending"]
        return len(completed_steps) >= len(self.plan)

    def _quick_classify_task(self, user_input: str) -> str:
        """快速任务分类（不使用 LLM，节省 token）

        Returns:
            "implementation" | "exploration" | "fix" | "analysis" | "simple"
        """
        input_lower = user_input.lower()

        # 简单任务关键词
        simple_keywords = ["你好", "hello", "hi", "谢谢", "what can you do"]
        if any(kw in input_lower for kw in simple_keywords):
            return "simple"

        # 实现类任务
        impl_keywords = ["实现", "创建", "开发", "搭建", "implement", "create", "develop", "build"]
        if any(kw in input_lower for kw in impl_keywords):
            return "implementation"

        # 修复类任务
        fix_keywords = ["修复", "debug", "fix", "错误", "bug", "问题"]
        if any(kw in input_lower for kw in fix_keywords):
            return "fix"

        # 分析类任务
        analysis_keywords = ["分析", "analyze", "查看", "检查", "explore"]
        if any(kw in input_lower for kw in analysis_keywords):
            return "analysis"

        # 默认探索类
        return "exploration"

    async def _notify_progress(self, event: str, data: Dict[str, Any] = None):
        """通知进度 - 流式输出"""
        if self.progress_callback:
            try:
                if hasattr(self.progress_callback, '__await__'):
                    await self.progress_callback(event, data or {})
                else:
                    self.progress_callback(event, data or {})
            except Exception as e:
                print(f"[进度通知] 错误：{e}")

    def _extract_capabilities(self) -> list:
        """从配置提取能力列表（用于计划动态调整）"""
        return []

    def _should_reflect(self, step: Dict[str, Any], result: Dict[str, Any]) -> bool:
        """轻量级判断：是否需要深度反思

        规则：
        1. 失败/错误 → 必须反思
        2. 成功 + 简单操作 → 跳过反思
        3. 关键步骤 → 必须反思

        Returns:
            True: 需要深度反思
            False: 可以跳过
        """
        # 规则 1: 失败必须反思
        if result.get("status") != "success":
            return True

        # 规则 2: 关键步骤必须反思（涉及数据修改）
        critical_routes = ["file_edit", "create_user", "create_team", "memory"]
        if step.get("route") in critical_routes:
            return True

        # 规则 3: 简单操作且成功 → 跳过
        simple_routes = ["bash", "response"]
        if step.get("route") in simple_routes:
            # 检查结果大小，输出小则跳过
            result_size = len(str(result))
            if result_size < 300:
                return False

        # 规则 4: chat 操作看重要性
        if step.get("route") == "chat":
            # 检查是否是关键 Agent
            agent_id = step.get("params", {}).get("agent_id", "")
            if agent_id in ["coder", "alice", "bob"]:  # 关键 Agent
                return True
            return False

        # 默认：需要反思
        return True

    def _find_parallel_steps(self, current_idx: int) -> List[Dict[str, Any]]:
        """查找可以并行执行的步骤 - 增强版（智能依赖分析）"""
        if not self.plan or current_idx >= len(self.plan):
            return []

        # 分析依赖关系
        dependencies = self._analyze_step_dependencies(current_idx)

        parallel_steps = []
        max_parallel = 3

        for i in range(current_idx, min(current_idx + max_parallel, len(self.plan))):
            step = self.plan[i]

            # 检查是否在依赖列表中
            has_dependency = i in dependencies.get("blocked", [])

            # 基础检查
            can_parallel = (
                step.get("route") in ["bash", "file_edit", "chat"] and
                not step.get("depends_on") and
                step.get("can_parallel", True) and
                not has_dependency
            )

            if can_parallel:
                parallel_steps.append(step)
            elif has_dependency:
                # 有依赖关系，停止
                break

        return parallel_steps if len(parallel_steps) > 1 else []

    async def _check_plan_validity(self) -> Dict[str, Any]:
        """检查当前计划是否仍然有效"""
        if not self.results:
            return {"needs_replan": False, "reason": "无执行结果"}

        # 计算成功率
        failed_count = len([r for r in self.results if r.get("status") == "error"])
        success_rate = (len(self.results) - failed_count) / max(len(self.results), 1)

        # 规则 1: 成功率低于 50% 需要重新规划
        if success_rate < 0.5:
            await self._notify_progress("plan_warning", {
                "reason": "成功率过低",
                "success_rate": success_rate,
                "failed_count": failed_count
            })
            return {
                "needs_replan": True,
                "reason": f"成功率过低 ({success_rate:.0%})",
                "success_rate": success_rate
            }

        # 规则 2: 连续失败 3 次需要调整
        consecutive_failures = 0
        for r in reversed(self.results):
            if r.get("status") == "error":
                consecutive_failures += 1
            else:
                break

        if consecutive_failures >= 3:
            await self._notify_progress("plan_warning", {
                "reason": "连续失败",
                "consecutive_failures": consecutive_failures
            })
            return {
                "needs_replan": True,
                "reason": f"连续失败{consecutive_failures}次",
                "consecutive_failures": consecutive_failures
            }

        # 规则 3: 检查迭代次数
        if self.iteration >= self.max_iterations * 0.8:
            await self._notify_progress("plan_warning", {
                "reason": "接近最大迭代次数",
                "iteration": self.iteration,
                "max_iterations": self.max_iterations
            })
            return {
                "needs_replan": True,
                "reason": "接近最大迭代次数",
                "iteration": self.iteration
            }

        return {"needs_replan": False, "success_rate": success_rate}

    async def _adjust_plan_dynamically(self, reflection: Dict[str, Any]):
        """动态调整计划"""
        # 检查计划有效性
        validity = await self._check_plan_validity()

        if validity.get("needs_replan"):
            replan_prompt = f"""
当前计划执行遇到困难：
- 原因：{validity.get('reason')}

请调整后续计划。返回 JSON 数组格式。
"""
            try:
                result = self.llm.chat(replan_prompt)
                import re
                json_match = re.search(r'\[[\s\S]*\]', result.get("content", ""))
                if json_match:
                    new_plan = json.loads(json_match.group())
                    completed_count = len([r for r in self.results if r.get("status") != "pending"])
                    self.plan = self.plan[:completed_count] + new_plan
                    await self._notify_progress("plan_replanned", {"new_steps": len(new_plan)})
                    return True
            except Exception as e:
                print(f"[动态调整] 错误：{e}")

        return False

    def _extract_capabilities(self) -> list:
        """从配置提取能力列表"""
        return []

    def _analyze_step_dependencies(self, start_idx: int) -> Dict[str, List[int]]:
        """智能分析步骤间的依赖关系

        Args:
            start_idx: 起始步骤索引

        Returns:
            {"blocked": [需要等待的步骤索引], "safe": [可以并行的步骤索引]}
        """
        blocked = []
        safe = []

        # 分析从 start_idx 开始的步骤
        modified_paths = set()  # 记录被修改的路径

        for i in range(start_idx, min(start_idx + 3, len(self.plan))):
            step = self.plan[i]
            route = step.get("route")
            params = step.get("params", {})

            # 检查文件操作
            if route == "file_edit":
                path = params.get("path", "")
                if path:
                    # 写操作：后续步骤不能使用
                    modified_paths.add(path)
                    # 检查是否依赖前面的修改
                    for prev_path in modified_paths:
                        if path.startswith(prev_path) or prev_path.startswith(path):
                            blocked.append(i)
                            break
                    else:
                        safe.append(i)

            elif route == "bash":
                cmd = params.get("command", "")
                # 检查管道和重定向
                if "|" in cmd or ">>" in cmd or ">" in cmd:
                    # 可能依赖前面的输出
                    blocked.append(i)
                else:
                    safe.append(i)

            else:
                safe.append(i)

        return {"blocked": blocked, "safe": safe}

    def _observe(self) -> Dict[str, Any]:
        """观察当前状态"""
        return {
            "plan": self.plan,
            "total_steps": len(self.plan) if self.plan else 0,
            "completed": len([r for r in self.results if r.get("status") == "success"]),
            "failed": len([r for r in self.results if r.get("status") == "error"]),
            "pending": len([r for r in self.results if r.get("status") == "pending"]),
            "last_result": self.results[-1] if self.results else None,
            "iteration": self.iteration
        }

    async def _decide_next_step(self, observation: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """决定下一步做什么"""
        # 简单实现：返回下一个未完成的步骤
        if not self.plan:
            return None

        completed_count = len([r for r in self.results if r.get("status") != "pending"])

        if completed_count >= len(self.plan):
            return None

        # 获取下一个步骤
        next_idx = completed_count
        if next_idx < len(self.plan):
            step = self.plan[next_idx].copy()
            step["index"] = next_idx
            return step

        return None

    def _get_cache_key(self, step: Dict[str, Any]) -> str:
        """生成步骤缓存键"""
        import hashlib
        key_data = f"{step.get('route')}:{json.dumps(step.get('params'), sort_keys=True)}"
        return hashlib.md5(key_data.encode()).hexdigest()

    async def _execute_step(self, step: Dict[str, Any]) -> Dict[str, Any]:
        """执行步骤 - 支持缓存和并行执行"""
        route = step.get("route")
        params = step.get("params", {})

        # 检查缓存（只缓存只读操作）
        cacheable_routes = ["bash", "glob", "grep"]
        if route in cacheable_routes:
            cache_key = self._get_cache_key(step)
            if cache_key in self.step_cache:
                await self._notify_progress("step_cached", {
                    "step": step.get("index", 0),
                    "description": step.get("description", "")
                })
                return self.step_cache[cache_key]

        self.brain._update_state(
            "executing_step",
            f"执行步骤 {step.get('index', 0) + 1}: {step.get('description', route)}"
        )

        try:
            # 标记为进行中
            step["status"] = "executing"

            result = self.brain.router.dispatch(route, params)

            step["status"] = "completed"
            step["result"] = result

            result_data = {
                "status": "success",
                "step": step,
                "result": result
            }

            # 缓存结果（只读操作）
            if route in cacheable_routes:
                cache_key = self._get_cache_key(step)
                self.step_cache[cache_key] = result_data

            return result_data

        except Exception as e:
            step["status"] = "failed"
            return {
                "status": "error",
                "step": step,
                "error": str(e)
            }

    async def _execute_steps_parallel(self, steps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """并行执行多个步骤"""
        import asyncio

        self.brain._update_state(
            "executing_parallel",
            f"并行执行 {len(steps)} 个步骤"
        )

        async def execute_single(step: Dict[str, Any]) -> Dict[str, Any]:
            return await self._execute_with_retry(step)

        # 并行执行
        tasks = [execute_single(step) for step in steps]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 处理结果
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append({
                    "status": "error",
                    "step": steps[i],
                    "error": str(result)
                })
            else:
                processed_results.append(result)

        return processed_results


    async def _execute_with_retry(self, step: Dict[str, Any]) -> Dict[str, Any]:
        """执行步骤带智能重试机制 - 增强版

        根据错误类型动态决定重试策略：
        - timeout: 重试 2 次，指数退避
        - permission: 不重试，直接寻找替代方案
        - not_found: 重试 1 次 + 寻找替代
        - rate_limit: 重试 3 次，长退避
        """
        # 错误类型配置
        retry_config = {
            "timeout": {"max_retries": 2, "delay": 1, "action": "retry"},
            "permission": {"max_retries": 0, "delay": 0, "action": "alternative"},
            "not_found": {"max_retries": 1, "delay": 0, "action": "alternative"},
            "rate_limit": {"max_retries": 3, "delay": 3, "action": "retry"},
            "default": {"max_retries": 2, "delay": 1, "action": "retry"}
        }

        last_error = None
        error_type = "default"

        for attempt in range(5):  # 最大保护次数
            try:
                result = await self._execute_step(step)

                if result.get("status") == "success":
                    if attempt > 0:
                        result["retry_info"] = {"attempt": attempt + 1}
                    return result

                # 失败：分析错误类型
                last_error = result.get("error", "Unknown error")
                error_type = self._classify_error(last_error)
                config = retry_config.get(error_type, retry_config["default"])

                await self._notify_progress("step_error", {
                    "error": last_error[:200],
                    "error_type": error_type,
                    "attempt": attempt + 1
                })

                # 根据配置决定行动
                if config["action"] == "alternative":
                    alternative = await self._find_alternative_approach(step, last_error)
                    if alternative:
                        step = alternative
                        continue
                    elif error_type == "permission":
                        # 权限错误无法替代，直接失败
                        break

                if attempt >= config["max_retries"]:
                    break

                # 延迟重试
                if config["delay"] > 0:
                    import asyncio
                    await asyncio.sleep(config["delay"] * (attempt + 1))

            except Exception as e:
                last_error = str(e)
                error_type = self._classify_error(last_error)
                config = retry_config.get(error_type, retry_config["default"])

                if attempt >= config["max_retries"]:
                    break

        # 所有重试都失败
        await self._notify_progress("step_failed", {
            "step": step.get("description", ""),
            "error": last_error[:200] if last_error else "Unknown",
            "error_type": error_type
        })
        return {
            "status": "error",
            "step": step,
            "error": f"执行失败 ({error_type}): {last_error}",
            "retries_exhausted": True
        }

    def _classify_error(self, error: str) -> str:
        """错误分类"""
        error_lower = error.lower() if error else ""

        if any(kw in error_lower for kw in ["timeout", "超时", "timed out"]):
            return "timeout"
        if any(kw in error_lower for kw in ["permission", "denied", "权限", "unauthorized"]):
            return "permission"
        if any(kw in error_lower for kw in ["not found", "不存在", "no such file", "404"]):
            return "not_found"
        if any(kw in error_lower for kw in ["rate limit", "too many", "frequency"]):
            return "rate_limit"

        return "default"

    async def _find_alternative_approach(self, step: Dict[str, Any], error: str) -> Optional[Dict[str, Any]]:
        """寻找替代执行方案

        Args:
            step: 原始步骤
            error: 错误信息

        Returns:
            替代步骤，如果没有则返回 None
        """
        if not self.llm.is_available():
            return None

        prompt = f"""执行步骤时遇到错误，请提供替代方案：

**原始步骤**: {step.get('description', step.get('route'))}
**路由类型**: {step.get('route')}
**参数**: {step.get('params', {})}
**错误信息**: {error[:500]}

请分析：
1. 为什么这个步骤会失败？
2. 有什么替代方法可以达到相同目的？
3. 如果无法替代，建议跳过还是调整计划？

以 JSON 格式返回：
```json
{{
    "has_alternative": true/false,
    "alternative_step": {{
        "route": "bash/file_edit/chat/...",
        "params": {{...}},
        "description": "替代方案说明"
    }},
    "reason": "分析原因",
    "suggest_skip": true/false
}}
```
"""
        try:
            result = self.llm.chat(prompt)
            content = result.get("content", "")

            json_match = re.search(r'\{[\s\S]*\}', content)
            if json_match:
                decision = json.loads(json_match.group())

                if decision.get("has_alternative") and decision.get("alternative_step"):
                    alt_step = decision["alternative_step"]
                    alt_step["is_alternative"] = True
                    alt_step["original_error"] = error
                    alt_step["alternative_reason"] = decision.get("reason", "")
                    return alt_step

        except Exception as e:
            print(f"[替代方案] 错误：{e}")

        return None

    async def _handle_step_failure(self, step: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
        """处理步骤失败，决定后续行动

        Args:
            step: 失败的步骤
            result: 失败结果

        Returns:
            处理决策
        """
        prompt = f"""步骤执行失败，请决定后续行动：

**失败步骤**: {step.get('description', step.get('route'))}
**路由类型**: {step.get('route')}
**错误信息**: {result.get('error', 'Unknown')[:500]}

请决定：
1. 这个步骤重要吗？必须执行吗？
2. 应该重试、调整参数、还是跳过？
3. 是否需要调整后续计划？

以 JSON 格式返回：
```json
{{
    "action": "retry|adjust|skip|abort",
    "reason": "决策原因",
    "retry_params": {{...}},  // 如果 action=retry，提供调整后的参数
    "adjust_plan": true/false,  // 是否需要调整后续计划
    "error_severity": "low/medium/high"
}}
```
"""
        try:
            result_decision = self.llm.chat(prompt)
            content = result_decision.get("content", "")

            json_match = re.search(r'\{[\s\S]*\}', content)
            if json_match:
                return json.loads(json_match.group())

        except Exception as e:
            print(f"[失败处理] 错误：{e}")

        # Fallback：默认跳过
        return {
            "action": "skip",
            "reason": "无法获取决策，默认跳过",
            "error_severity": "medium"
        }


    async def _deep_reflect(self, step: Dict[str, Any], result: Dict[str, Any],
                          plan_progress: float) -> Dict[str, Any]:
        """深度反思 - 无论成功失败都进行反思

        Args:
            step: 当前执行的步骤
            result: 执行结果
            plan_progress: 计划完成进度 (0.0-1.0)
        """
        prompt = f"""
反思这次执行：

**步骤**: {step.get('description', step.get('route'))}
**执行结果**: {str(result)[:800]}
**计划进度**: {plan_progress:.0%}

请分析：
1. 结果是否符合预期？为什么？
2. 有没有更好的执行方式？
3. 基于当前结果，后续计划需要调整吗？
4. 有什么经验可以记录下来？

以 JSON 格式返回：
{{
    "meets_expectations": true/false,
    "analysis": "结果分析",
    "alternative_approach": "更好的方式（如果有）",
    "need_adjustment": true/false,
    "adjustment_suggestion": "调整建议",
    "lesson_learned": "学到的经验",
    "confidence_update": 0.0-1.0
}}
"""
        try:
            reflection_result = self.llm.chat(prompt)
            content = reflection_result.get("content", "")

            import re
            json_match = re.search(r'\{[\s\S]*\}', content)
            if json_match:
                return json.loads(json_match.group())
        except Exception as e:
            print(f"Deep reflection error: {e}")

        # Fallback
        return {
            "meets_expectations": result.get("status") == "success",
            "need_adjustment": result.get("status") != "success",
            "analysis": "反思失败，使用默认判断"
        }

    async def _reflect(self, step: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
        """反思执行结果"""
        # 如果是简单成功，不需要反思
        if result.get("status") == "success":
            return {"success": True, "need_adjustment": False}

        # 失败时需要反思
        prompt = f"""
步骤：{step.get('description', step.get('route'))}
结果：{result}

请反思：
1. 为什么会失败？
2. 需要调整后续计划吗？
3. 有什么替代方案？

以 JSON 格式返回：
{{
    "success": false,
    "reason": "失败原因",
    "need_adjustment": true/false,
    "adjustment_suggestion": "调整建议",
    "alternative_approach": "替代方案"
}}
"""
        try:
            result_reflect = self.llm.chat(prompt)
            content = result_reflect.get("content", "")

            import re
            json_match = re.search(r'\{[\s\S]*\}', content)
            if json_match:
                return json.loads(json_match.group())
        except Exception:
            pass

        return {"success": False, "need_adjustment": False}

    async def _adjust_plan(self, reflection: Dict[str, Any]) -> List[Dict[str, Any]]:
        """调整计划"""
        prompt = f"""
当前计划：{json.dumps(self.plan, ensure_ascii=False)}

执行反思：
- 失败原因：{reflection.get('reason')}
- 调整建议：{reflection.get('adjustment_suggestion')}

请调整后续计划。返回调整后的完整计划（JSON 数组格式）。
"""
        try:
            result = self.llm.chat(prompt)
            content = result.get("content", "")

            import re
            json_match = re.search(r'\[[\s\S]*\]', content)
            if json_match:
                return json.loads(json_match.group())
        except Exception:
            pass

        return self.plan

    async def _post_task_reflection(self, user_input: str) -> None:
        """任务完成后的反思（Heart）"""
        self.task_count += 1

        # 检查是否需要触发 heart
        need_heart = (
            self.task_count >= 3 or  # 每 3 个任务触发一次
            len([r for r in self.results if r.get("status") == "error"]) > 0  # 有失败
        )

        if not need_heart:
            return

        self.brain._update_state("heart_reflection", "执行任务后反思")

        prompt = f"""
任务：{user_input}
执行结果：{json.dumps(self.results, ensure_ascii=False, default=str)}

请反思：
1. 任务完成得怎么样？（1-10 分）
2. 有没有可以改进的地方？
3. 团队成员（alice/bob）的表现如何？需要优化他们的提示词吗？
4. 学到了什么可以记录下来的？

以 JSON 格式返回：
{{
    "score": 8,
    "what_went_well": "...",
    "what_to_improve": "...",
    "team_feedback": "...",
    "lessons_learned": "..."
}}
"""
        try:
            reflection = self.llm.chat(prompt)

            # 将反思写入记忆
            self.brain.memory.write(
                memory_type="long_term",
                content={
                    "type": "task_reflection",
                    "task": user_input[:200],
                    "reflection": reflection.get("content", "")
                }
            )

            # 重置计数器
            if self.task_count >= 3:
                self.task_count = 0

        except Exception as e:
            print(f"Heart reflection error: {e}")

    def _synthesize_result(self, user_input: str) -> Dict[str, Any]:
        """合成最终结果"""
        # 让 LLM 生成最终报告
        prompt = f"""
任务：{user_input}

执行历史：
{json.dumps(self.results, ensure_ascii=False, default=str)[:3000]}

请生成一份完整的任务完成报告，包括：
1. 任务目标
2. 执行了哪些步骤
3. 最终结果
4. 后续建议（如果有）

用 Markdown 格式返回。
"""
        try:
            result = self.llm.chat(prompt)
            return {
                "status": "completed",
                "task": user_input,
                "steps_executed": len(self.results),
                "iterations": self.iteration,
                "report": result.get("content", "任务已完成"),
                "details": self.results
            }
        except Exception as e:
            return {
                "status": "completed",
                "task": user_input,
                "steps_executed": len(self.results),
                "report": f"任务执行完成，但生成报告失败：{e}"
            }

    def _is_complex_task(self, user_input: str) -> bool:
        """检测是否是复杂任务"""
        complex_keywords = [
            '完善', '改进', '优化', '实现', '开发',
            'improve', 'enhance', 'implement', 'develop',
            '分析', 'analyze', 'explore', '探索',
            '重构', 'refactor', '设计', 'design',
            '创建', 'create', '构建', 'build'
        ]

        input_lower = user_input.lower()
        return any(kw in input_lower for kw in complex_keywords)
