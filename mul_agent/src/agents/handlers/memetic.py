"""Memetic Handler - 模因处理器"""

from typing import Any, Dict

from .base import BaseHandler
from mul_agent.brain.memetic_engine import memetic_engine, ExecutionTrace, MemeType


class MemeticHandler(BaseHandler):
    """模因处理器

    使用场景:
    - 从成功执行中提取经验
    - 检索历史经验辅助决策
    - 查看已学习的模式
    """

    def handle(self, params: Dict[str, Any]) -> Dict[str, Any]:
        if not params:
            return {"status": "error", "error_code": 1004, "message": "Missing params"}

        action = params.get("action", "list")

        if action == "extract":
            return self._extract(params)
        elif action == "retrieve":
            return self._retrieve(params)
        elif action == "apply":
            return self._apply(params)
        elif action == "record":
            return self._record(params)
        elif action == "list":
            return self._list(params)
        elif action == "get":
            return self._get(params)
        elif action == "stats":
            return self._stats(params)
        else:
            return {"status": "error", "error_code": 1005, "message": f"Unknown action: {action}"}

    def _extract(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """从执行轨迹中提取模因"""
        trace_data = params.get("trace")

        if not trace_data:
            return {"status": "error", "error_code": 1004, "message": "Missing: trace"}

        # 创建 ExecutionTrace
        trace = ExecutionTrace(
            id=trace_data.get("id", ""),
            goal=trace_data.get("goal", ""),
            plan=trace_data.get("plan", {}),
            steps=trace_data.get("steps", []),
            results=trace_data.get("results", []),
            outcome=trace_data.get("outcome", "success"),
            metadata=trace_data.get("metadata", {})
        )

        meme = memetic_engine.extract_meme(trace)

        if meme:
            return {
                "status": "success",
                "meme": meme.to_dict(),
                "message": f"成功提取模因：{meme.name}"
            }

        return {
            "status": "success",
            "message": "未能提取模因（可能执行不成功或步骤太少）"
        }

    def _retrieve(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """检索匹配的模因"""
        context = params.get("context", "")
        min_confidence = params.get("min_confidence", 0.6)

        meme = memetic_engine.retrieve(context, min_confidence)

        if meme:
            return {
                "status": "success",
                "meme": meme.to_dict(),
                "matched": True
            }

        return {
            "status": "success",
            "matched": False,
            "message": "未找到匹配的模因"
        }

    def _apply(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """应用模因"""
        meme_id = params.get("meme_id")
        context = params.get("context", {})

        if not meme_id:
            return {"status": "error", "error_code": 1004, "message": "Missing: meme_id"}

        meme = memetic_engine.memes.get(meme_id)
        if not meme:
            return {"status": "error", "message": f"Meme {meme_id} not found"}

        result = memetic_engine.apply(meme, context)
        return result

    def _record(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """记录模因应用结果"""
        meme_id = params.get("meme_id")
        success = params.get("success", True)

        if not meme_id:
            return {"status": "error", "error_code": 1004, "message": "Missing: meme_id"}

        memetic_engine.record_outcome(meme_id, success)

        meme = memetic_engine.memes.get(meme_id)
        return {
            "status": "success",
            "meme_id": meme_id,
            "confidence": meme.confidence if meme else None,
            "usage_count": meme.usage_count if meme else None
        }

    def _list(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """列出所有模因"""
        active_only = params.get("active_only", True)
        memes = memetic_engine.get_all_memes(active_only)

        return {
            "status": "success",
            "memes": memes,
            "count": len(memes)
        }

    def _get(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """获取单个模因详情"""
        meme_id = params.get("meme_id")

        if not meme_id:
            return {"status": "error", "error_code": 1004, "message": "Missing: meme_id"}

        meme = memetic_engine.memes.get(meme_id)
        if not meme:
            return {"status": "error", "message": f"Meme {meme_id} not found"}

        return {
            "status": "success",
            "meme": meme.to_dict()
        }

    def _stats(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """获取统计信息"""
        stats = memetic_engine.get_stats()
        return {
            "status": "success",
            **stats
        }
