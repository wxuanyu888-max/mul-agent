"""Autonomous Memory Decision System - 自主记忆决策系统

让 Agent 自主决定：
1. 是否记住某些内容（记忆重要性评估）
2. 记住到什么类型（short_term vs long_term vs handover）
3. 何时整理/归档旧记忆
4. 何时检索相关记忆
"""

import json
from typing import Any, Dict, List, Optional
from datetime import datetime


class MemoryDecisionSystem:
    """自主记忆决策系统"""

    def __init__(self, llm_client, memory, agent_id: str):
        self.llm = llm_client
        self.memory = memory
        self.agent_id = agent_id

        # 记忆配置
        self.config = {
            "max_short_term": 20,  # 短期记忆最大数量
            "max_long_term": 100,  # 长期记忆最大数量
            "consolidation_threshold": 15,  # 触发整理的阈值
            "importance_threshold": 0.6,  # 重要性阈值
        }

    def should_remember(self, user_input: str, result: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """判断是否应该记住这次交互

        使用 LLM 评估：
        1. 信息的重要性
        2. 是否有可复用的知识
        3. 是否有需要记住的上下文

        Returns:
            {
                "should_remember": bool,
                "importance_score": float,  # 0-1
                "memory_type": str,  # "short_term" | "long_term" | "handover"
                "content_to_save": Dict,  # 要保存的内容
                "reason": str  # 决策原因
            }
        """
        if not self.llm.is_available():
            # Fallback: 默认保存重要的交互
            return self._fallback_decision(user_input, result)

        # 构建评估 prompt
        prompt = f"""你是一个自主记忆系统。请评估以下交互是否需要被记住：

**用户输入**: {user_input[:500]}

**执行结果**: {json.dumps(result, ensure_ascii=False, default=str)[:1000]}

**当前上下文**:
- 作用域：{context.get("scope", "unknown")}
- 任务类型：{context.get("task_type", "unknown")}

请评估：
1. 这次交互是否包含重要信息需要记住？（0-1 评分）
2. 如果是，应该保存到哪种记忆类型？
   - short_term: 临时上下文，很快会过期
   - long_term: 持久知识，可复用
   - handover: 需要交接给其他 agent 的任务
3. 具体应该记住什么内容？

请以 JSON 格式回答：
```json
{{
    "should_remember": true/false,
    "importance_score": 0.0-1.0,
    "memory_type": "short_term|long_term|handover",
    "content_to_save": {{...}},
    "reason": "决策原因"
}}
```

如果 importance_score < 0.3，则 should_remember 应为 false。
"""

        try:
            llm_response = self.llm.think(prompt, {})
            decision = self._parse_json_response(llm_response)

            # 验证响应
            if not isinstance(decision, dict):
                return self._fallback_decision(user_input, result)

            decision.setdefault("should_remember", False)
            decision.setdefault("importance_score", 0.0)
            decision.setdefault("memory_type", "short_term")
            decision.setdefault("content_to_save", {"input": user_input, "result": result})
            decision.setdefault("reason", "")

            # 应用重要性阈值
            if decision.get("importance_score", 0) < self.config["importance_threshold"]:
                decision["should_remember"] = False

            return decision

        except Exception as e:
            print(f"Memory decision error: {e}")
            return self._fallback_decision(user_input, result)

    def _fallback_decision(self, user_input: str, result: Dict[str, Any]) -> Dict[str, Any]:
        """Fallback 决策逻辑（当 LLM 不可用时）"""
        # 简单规则：如果结果成功且包含有用信息，则记住
        is_success = result.get("status") == "success"
        has_data = bool(result.get("data") or result.get("result"))

        should_remember = is_success and has_data

        return {
            "should_remember": should_remember,
            "importance_score": 0.5 if should_remember else 0.2,
            "memory_type": "short_term",
            "content_to_save": {"input": user_input, "result": result},
            "reason": "Fallback decision based on success and data presence"
        }

    def _parse_json_response(self, llm_response: Dict[str, Any]) -> Any:
        """解析 LLM 的 JSON 响应"""
        try:
            # 尝试从响应中提取 JSON
            response_text = llm_response.get("params", {}).get("message", "")
            if not response_text:
                response_text = llm_response.get("content", "")

            # 查找 JSON 代码块
            import re
            json_match = re.search(r'```json\s*(.*?)\s*```', response_text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(1))

            # 尝试直接解析
            return json.loads(response_text)
        except:
            return None

    def needs_consolidation(self) -> Dict[str, Any]:
        """检查是否需要整理记忆

        整理策略：
        1. short_term 记忆数量超过阈值
        2. 定期整理（基于时间）
        3. 检测相似记忆并合并

        Returns:
            {
                "needs_consolidation": bool,
                "reason": str,
                "short_term_count": int,
                "action": "none" | "consolidate_to_long_term" | "cleanup_old"
            }
        """
        short_term_count = len(self.memory.list_memories("short_term", limit=100))

        if short_term_count > self.config["consolidation_threshold"]:
            return {
                "needs_consolidation": True,
                "reason": f"Short-term memory count ({short_term_count}) exceeds threshold ({self.config['consolidation_threshold']})",
                "short_term_count": short_term_count,
                "action": "consolidate_to_long_term"
            }

        return {
            "needs_consolidation": False,
            "reason": "Memory count within limits",
            "short_term_count": short_term_count,
            "action": "none"
        }

    def consolidate_memories(self, force: bool = False) -> Dict[str, Any]:
        """整理记忆：将 short_term 中有价值的内容转移到 long_term

        使用 LLM 评估每条 short_term 记忆：
        1. 是否具有持久价值
        2. 是否应该合并到现有 long_term 记忆
        3. 是否应该删除（临时信息已过时）
        """
        if not force:
            check = self.needs_consolidation()
            if not check["needs_consolidation"]:
                return {"status": "skipped", "reason": check["reason"]}

        # 获取所有 short_term 记忆
        short_term_memories = self.memory.list_memories("short_term", limit=50)

        if not short_term_memories:
            return {"status": "skipped", "reason": "No short-term memories to consolidate"}

        consolidated = []
        deleted = []
        kept = []

        for memory in short_term_memories:
            decision = self._evaluate_memory_for_consolidation(memory)

            if decision["action"] == "move_to_long_term":
                # 移动到 long_term
                self.memory.write("long_term", decision["content"])
                self.memory.delete(memory.get("id"))
                consolidated.append(memory.get("id"))

            elif decision["action"] == "delete":
                # 删除
                self.memory.delete(memory.get("id"))
                deleted.append(memory.get("id"))

            else:
                # 保留在 short_term
                kept.append(memory.get("id"))

        return {
            "status": "success",
            "consolidated_count": len(consolidated),
            "deleted_count": len(deleted),
            "kept_count": len(kept),
            "consolidated_ids": consolidated,
            "deleted_ids": deleted,
            "kept_ids": kept
        }

    def _evaluate_memory_for_consolidation(self, memory: Dict[str, Any]) -> Dict[str, Any]:
        """评估单条记忆是否应该被整理"""
        if not self.llm.is_available():
            # Fallback: 保留最近的，删除旧的
            timestamp = memory.get("timestamp", "")
            is_recent = timestamp > datetime.now().isoformat()[-10:]
            return {
                "action": "keep" if is_recent else "move_to_long_term",
                "content": memory.get("content", {})
            }

        prompt = f"""评估以下记忆是否应该被整理：

**记忆类型**: short_term
**记忆内容**: {json.dumps(memory.get("content", {}), ensure_ascii=False, default=str)[:1000]}
**创建时间**: {memory.get("timestamp", "unknown")}

请决定：
1. move_to_long_term: 有持久价值，应转入长期记忆
2. delete: 临时信息，已过时或无价值
3. keep: 仍然相关，保留在短期记忆

以 JSON 格式回答：
```json
{{
    "action": "move_to_long_term|delete|keep",
    "reason": "决策原因",
    "content": {{...}}  # 如果要移动，提供整理后的内容
}}
```
"""

        try:
            llm_response = self.llm.think(prompt, {})
            decision = self._parse_json_response(llm_response)
            if isinstance(decision, dict):
                decision.setdefault("action", "keep")
                decision.setdefault("content", memory.get("content", {}))
                return decision
        except Exception as e:
            print(f"Memory evaluation error: {e}")

        # Fallback: 保留
        return {"action": "keep", "content": memory.get("content", {})}

    def retrieve_relevant_memories(self, query: str, memory_type: Optional[str] = None, max_results: int = 10) -> List[Dict[str, Any]]:
        """检索与当前查询相关的记忆

        使用语义搜索而非简单的关键词匹配
        """
        # 首先尝试语义搜索
        if self.llm.is_available():
            relevant = self._semantic_search(query, memory_type, max_results)
            if relevant:
                return relevant

        # Fallback 到关键词搜索
        return self.memory.search(query, memory_type, max_results)

    def _semantic_search(self, query: str, memory_type: Optional[str], max_results: int) -> List[Dict[str, Any]]:
        """语义搜索：让 LLM 判断哪些记忆相关"""
        # 获取候选记忆
        memories = self.memory.list_memories(memory_type or "short_term", limit=50)

        if not memories:
            return []

        # 构建所有记忆的摘要
        memory_summaries = []
        for i, mem in enumerate(memories[:20]):  # 限制数量避免 token 溢出
            summary = {
                "index": i,
                "type": memory_type or "short_term",
                "content_preview": str(mem.get("content", {}))[:200],
                "timestamp": mem.get("timestamp", "")
            }
            memory_summaries.append(summary)

        prompt = f"""基于以下查询，从候选记忆中选择最相关的记忆：

**查询**: {query}

**候选记忆**:
{json.dumps(memory_summaries, ensure_ascii=False, default=str)}

请选择最相关的记忆索引（最多 {max_results} 个），以 JSON 格式回答：
```json
{{
    "relevant_indices": [0, 2, 5],
    "reasons": {{
        "0": "为什么这条记忆相关",
        "2": "为什么这条记忆相关"
    }}
}}
```
"""

        try:
            llm_response = self.llm.think(prompt, {})
            result = self._parse_json_response(llm_response)
            if isinstance(result, dict) and "relevant_indices" in result:
                indices = result["relevant_indices"]
                return [memories[i] for i in indices if i < len(memories)]
        except Exception as e:
            print(f"Semantic search error: {e}")

        return []

    def create_summary(self, memory_type: str = "short_term") -> Dict[str, Any]:
        """创建记忆摘要

        让 LLM 总结某一类型的所有记忆，提取关键信息
        """
        memories = self.memory.list_memories(memory_type, limit=50)

        if not memories:
            return {"status": "empty", "summary": f"No {memory_type} memories"}

        prompt = f"""总结以下{memory_type}记忆，提取关键信息：

**记忆列表**:
{json.dumps([m.get("content", {}) for m in memories], ensure_ascii=False, default=str)[:2000]}

请生成一份简洁的摘要，包括：
1. 主要主题/话题
2. 关键决策/结论
3. 待办事项/未完成的任务

以 JSON 格式回答：
```json
{{
    "main_topics": ["topic1", "topic2"],
    "key_decisions": ["decision1", "decision2"],
    "pending_tasks": ["task1", "task2"],
    "summary": "一段话总结"
}}
```
"""

        try:
            llm_response = self.llm.think(prompt, {})
            summary = self._parse_json_response(llm_response)
            return {
                "status": "success",
                "memory_count": len(memories),
                "summary": summary
            }
        except Exception as e:
            return {"status": "error", "error": str(e), "memory_count": len(memories)}
