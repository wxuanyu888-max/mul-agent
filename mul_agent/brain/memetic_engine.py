"""Memetic Engine - 模因引擎

从执行经验中提取可复用的知识模式，并应用到新情境
"""

import json
import time
import hashlib
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from pathlib import Path
from enum import Enum


class MemeType(Enum):
    """模因类型"""
    STRATEGY = "strategy"  # 策略模式
    WORKFLOW = "workflow"  # 工作流
    HEURISTIC = "heuristic"  # 启发式规则
    ANTI_PATTERN = "anti_pattern"  # 反面模式


class MemeStatus(Enum):
    """模因状态"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    EVOLVING = "evolving"


@dataclass
class Meme:
    """模因 - 可复用的知识单元"""
    id: str
    name: str
    meme_type: MemeType
    description: str
    status: MemeStatus = MemeStatus.ACTIVE

    # 情境匹配
    trigger_conditions: List[str] = field(default_factory=list)  # 触发条件关键词
    context_pattern: Dict = field(default_factory=dict)  # 情境模式

    # 核心内容
    content: Dict = field(default_factory=dict)  # 模因内容（计划、策略等）

    # 统计信息
    success_count: int = 0
    failure_count: int = 0
    last_used: Optional[float] = None
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    # 来源
    source_execution: Optional[str] = None  # 来源执行 ID
    evolved_from: Optional[str] = None  # 从哪个模因演化而来

    @property
    def confidence(self) -> float:
        """置信度"""
        total = self.success_count + self.failure_count
        if total == 0:
            return 0.5
        return self.success_count / total

    @property
    def usage_count(self) -> int:
        """使用次数"""
        return self.success_count + self.failure_count

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "type": self.meme_type.value,
            "description": self.description,
            "status": self.status.value,
            "trigger_conditions": self.trigger_conditions,
            "context_pattern": self.context_pattern,
            "content": self.content,
            "confidence": self.confidence,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "usage_count": self.usage_count,
            "last_used": self.last_used,
            "created_at": self.created_at
        }

    def record_success(self):
        """记录成功"""
        self.success_count += 1
        self.last_used = time.time()
        self.updated_at = time.time()

    def record_failure(self):
        """记录失败"""
        self.failure_count += 1
        self.last_used = time.time()
        self.updated_at = time.time()


@dataclass
class ExecutionTrace:
    """执行轨迹"""
    id: str
    goal: str
    plan: Dict = field(default_factory=dict)
    steps: List[Dict] = field(default_factory=list)
    results: List[Dict] = field(default_factory=list)
    outcome: str = ""  # success/failed/partial
    metadata: Dict = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "goal": self.goal,
            "plan": self.plan,
            "steps": self.steps,
            "results": self.results,
            "outcome": self.outcome,
            "metadata": self.metadata,
            "created_at": self.created_at
        }


class MemeticEngine:
    """模因引擎

    核心能力:
    1. 从执行轨迹中提取模因
    2. 情境匹配和检索
    3. 模因应用和执行
    4. 模因演化和淘汰
    """

    def __init__(self, storage_path: str = None):
        """初始化模因引擎

        Args:
            storage_path: 存储路径（可选）
        """
        self.memes: Dict[str, Meme] = {}
        self.traces: Dict[str, ExecutionTrace] = {}
        self.storage_path = Path(storage_path) if storage_path else None

        # 配置
        self.min_confidence_threshold = 0.6  # 最小置信度阈值
        self.max_meme_age_days = 30  # 最大模因年龄
        self.evolution_threshold = 5  # 演化触发次数

        # 加载已存储的模因
        if self.storage_path:
            self._load_memes()

    def extract_meme(self, trace: ExecutionTrace) -> Optional[Meme]:
        """从执行轨迹中提取模因

        Args:
            trace: 执行轨迹

        Returns:
            提取的模因，如果提取失败返回 None
        """
        self.traces[trace.id] = trace

        # 只有成功的执行才提取模因
        if trace.outcome != "success":
            return None

        # 分析轨迹，提取模式
        meme = self._analyze_and_extract(trace)

        if meme:
            self.memes[meme.id] = meme
            self._save_meme(meme)

        return meme

    def _analyze_and_extract(self, trace: ExecutionTrace) -> Optional[Meme]:
        """分析轨迹并提取模因"""
        steps = trace.steps
        results = trace.results

        if not steps or len(steps) < 2:
            return None  # 步骤太少，不值得提取

        # 分析执行模式
        route_sequence = [s.get("route") for s in steps]
        success_patterns = self._find_patterns(route_sequence, results)

        if not success_patterns:
            return None

        # 确定模因类型
        meme_type = self._determine_meme_type(steps)

        # 生成触发条件
        trigger_conditions = self._extract_trigger_conditions(trace)

        # 创建模因
        meme = Meme(
            id=self._generate_meme_id(trace.goal, route_sequence),
            name=self._generate_meme_name(trace.goal, meme_type),
            meme_type=meme_type,
            description=f"从{trace.goal}的执行中提取的模式",
            trigger_conditions=trigger_conditions,
            context_pattern={"route_sequence": route_sequence},
            content={
                "steps": steps,
                "success_patterns": success_patterns,
                "original_goal": trace.goal
            },
            source_execution=trace.id
        )

        meme.record_success()

        return meme

    def _find_patterns(self, route_sequence: List[str], results: List[Dict]) -> List[str]:
        """查找成功模式"""
        patterns = []

        # 分析哪些路由组合总是成功
        for i, (route, result) in enumerate(zip(route_sequence, results)):
            if result.get("status") == "success":
                patterns.append(f"{route} 成功")

        return patterns

    def _determine_meme_type(self, steps: List[Dict]) -> MemeType:
        """确定模因类型"""
        routes = [s.get("route") for s in steps]

        # 多步骤有序执行 → 工作流
        if len(routes) >= 3:
            return MemeType.WORKFLOW

        # 单一步骤的策略 → 策略模式
        if len(routes) == 1:
            return MemeType.STRATEGY

        # 启发式规则
        return MemeType.HEURISTIC

    def _extract_trigger_conditions(self, trace: ExecutionTrace) -> List[str]:
        """提取触发条件"""
        conditions = []

        # 从目标中提取关键词
        goal_words = trace.goal.lower().split()
        keywords = [w for w in goal_words if len(w) > 2]
        conditions.extend(keywords[:5])

        # 从元数据中提取
        if "keywords" in trace.metadata:
            conditions.extend(trace.metadata["keywords"])

        return list(set(conditions))

    def _generate_meme_id(self, goal: str, route_sequence: List[str]) -> str:
        """生成模因 ID"""
        content = f"{goal}:{','.join(route_sequence)}"
        return hashlib.md5(content.encode()).hexdigest()[:12]

    def _generate_meme_name(self, goal: str, meme_type: MemeType) -> str:
        """生成模因名称"""
        type_prefix = {
            MemeType.STRATEGY: "策略",
            MemeType.WORKFLOW: "流程",
            MemeType.HEURISTIC: "经验",
            MemeType.ANTI_PATTERN: "警示"
        }
        return f"{type_prefix.get(meme_type, '模式')}-{goal[:20]}"

    def retrieve(self, context: str, min_confidence: float = None) -> Optional[Meme]:
        """检索匹配的模因

        Args:
            context: 当前情境描述
            min_confidence: 最小置信度

        Returns:
            最匹配的模因
        """
        threshold = min_confidence or self.min_confidence_threshold

        candidates = []

        for meme in self.memes.values():
            if meme.status != MemeStatus.ACTIVE:
                continue
            if meme.confidence < threshold:
                continue

            # 计算匹配度
            score = self._calculate_match_score(meme, context)
            if score > 0:
                candidates.append((meme, score))

        if not candidates:
            return None

        # 返回得分最高的
        candidates.sort(key=lambda x: x[1], reverse=True)
        return candidates[0][0]

    def _calculate_match_score(self, meme: Meme, context: str) -> float:
        """计算匹配分数"""
        score = 0.0
        context_lower = context.lower()

        # 触发条件匹配
        for condition in meme.trigger_conditions:
            if condition.lower() in context_lower:
                score += 1.0

        # 情境模式匹配
        if meme.context_pattern:
            for key, pattern in meme.context_pattern.items():
                if isinstance(pattern, list):
                    for item in pattern:
                        if item.lower() in context_lower:
                            score += 0.5

        # 置信度加权
        score *= meme.confidence

        # 最近使用加权
        if meme.last_used:
            days_since_use = (time.time() - meme.last_used) / 86400
            if days_since_use < 7:
                score *= 1.2

        return score

    def apply(self, meme: Meme, context: Dict) -> Dict:
        """应用模因到当前情境

        Args:
            meme: 模因
            context: 当前上下文

        Returns:
            应用结果（计划、建议等）
        """
        if meme.meme_type == MemeType.WORKFLOW:
            return self._apply_workflow(meme, context)
        elif meme.meme_type == MemeType.STRATEGY:
            return self._apply_strategy(meme, context)
        elif meme.meme_type == MemeType.HEURISTIC:
            return self._apply_heuristic(meme, context)
        else:
            return {"status": "error", "message": "Unknown meme type"}

    def _apply_workflow(self, meme: Meme, context: Dict) -> Dict:
        """应用工作流模因"""
        content = meme.content
        steps = content.get("steps", [])

        # 生成可执行的计划步骤
        plan_steps = []
        for step in steps:
            plan_steps.append({
                "description": step.get("description", ""),
                "route": step.get("route", ""),
                "params": step.get("params", {}),
                "source_meme": meme.id
            })

        return {
            "status": "success",
            "type": "workflow",
            "meme_id": meme.id,
            "plan_steps": plan_steps,
            "confidence": meme.confidence
        }

    def _apply_strategy(self, meme: Meme, context: Dict) -> Dict:
        """应用策略模因"""
        return {
            "status": "success",
            "type": "strategy",
            "meme_id": meme.id,
            "recommendation": meme.content,
            "confidence": meme.confidence
        }

    def _apply_heuristic(self, meme: Meme, context: Dict) -> Dict:
        """应用启发式模因"""
        return {
            "status": "success",
            "type": "heuristic",
            "meme_id": meme.id,
            "rule": meme.description,
            "confidence": meme.confidence
        }

    def record_outcome(self, meme_id: str, success: bool):
        """记录模因应用结果"""
        meme = self.memes.get(meme_id)
        if not meme:
            return

        if success:
            meme.record_success()
        else:
            meme.record_failure()

        # 检查是否需要演化
        if meme.usage_count >= self.evolution_threshold:
            self._evaluate_evolution(meme)

        self._save_meme(meme)

    def _evaluate_evolution(self, meme: Meme):
        """评估是否需要演化"""
        if meme.confidence < 0.5:
            # 置信度太低，标记为不活跃
            meme.status = MemeStatus.INACTIVE
        elif meme.confidence > 0.8:
            # 高置信度，可以衍生新模因
            pass  # TODO: 实现演化逻辑

    def get_all_memes(self, active_only: bool = True) -> List[Dict]:
        """获取所有模因"""
        memes = self.memes.values()
        if active_only:
            memes = [m for m in memes if m.status == MemeStatus.ACTIVE]
        return [m.to_dict() for m in memes]

    def get_stats(self) -> Dict:
        """获取统计信息"""
        total = len(self.memes)
        active = sum(1 for m in self.memes.values() if m.status == MemeStatus.ACTIVE)
        avg_confidence = sum(m.confidence for m in self.memes.values()) / max(total, 1)

        return {
            "total_memes": total,
            "active_memes": active,
            "inactive_memes": total - active,
            "average_confidence": avg_confidence,
            "total_traces": len(self.traces)
        }

    def _save_meme(self, meme: Meme):
        """保存模因"""
        if not self.storage_path:
            return

        self.storage_path.mkdir(parents=True, exist_ok=True)
        meme_file = self.storage_path / f"{meme.id}.json"
        meme_file.write_text(json.dumps(meme.to_dict(), ensure_ascii=False, indent=2))

    def _load_memes(self):
        """加载模因"""
        if not self.storage_path or not self.storage_path.exists():
            return

        for meme_file in self.storage_path.glob("*.json"):
            try:
                data = json.loads(meme_file.read_text())
                meme = Meme(
                    id=data["id"],
                    name=data["name"],
                    meme_type=MemeType(data["type"]),
                    description=data["description"],
                    status=MemeStatus(data.get("status", "active")),
                    trigger_conditions=data.get("trigger_conditions", []),
                    context_pattern=data.get("context_pattern", {}),
                    content=data.get("content", {}),
                    success_count=data.get("success_count", 0),
                    failure_count=data.get("failure_count", 0),
                    last_used=data.get("last_used"),
                    created_at=data.get("created_at", time.time()),
                    updated_at=data.get("updated_at", time.time()),
                    source_execution=data.get("source_execution"),
                    evolved_from=data.get("evolved_from")
                )
                self.memes[meme.id] = meme
            except Exception as e:
                print(f"Error loading meme {meme_file}: {e}")


# 全局实例
memetic_engine = MemeticEngine()
