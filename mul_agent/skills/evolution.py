"""Skill Evolution System - 技能自进化系统

参考 Claude Code 的学习模式设计：
1. 从执行历史中提取成功模式
2. 自动生成新技能
3. 技能评估和筛选
4. 技能库持续进化
"""

import json
import hashlib
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
import threading


class SkillSource(Enum):
    """技能来源"""
    MANUAL = "manual"  # 手动创建
    LEARNED = "learned"  # 从历史学习
    EVOLVED = "evolved"  # 进化而来
    EXTRACTED = "extracted"  # 从成功执行中提取


class SkillConfidence(Enum):
    """技能置信度"""
    LOW = 0.3
    MEDIUM = 0.6
    HIGH = 0.9


@dataclass
class SkillPattern:
    """技能模式"""
    name: str
    description: str
    trigger_keywords: List[str] = field(default_factory=list)
    route: str = ""
    params_template: Dict[str, Any] = field(default_factory=dict)
    success_conditions: List[str] = field(default_factory=list)
    source: SkillSource = SkillSource.MANUAL
    confidence: float = 0.5
    usage_count: int = 0
    success_rate: float = 0.0
    created_at: float = field(default_factory=time.time)
    last_used_at: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "trigger_keywords": self.trigger_keywords,
            "route": self.route,
            "params_template": self.params_template,
            "success_conditions": self.success_conditions,
            "source": self.source.value,
            "confidence": self.confidence,
            "usage_count": self.usage_count,
            "success_rate": self.success_rate,
            "created_at": self.created_at,
            "last_used_at": self.last_used_at
        }

    def to_skill_definition(self) -> Dict[str, Any]:
        """转换为技能定义格式"""
        return {
            "id": f"learned_{self.name}",
            "name": self.name,
            "description": self.description,
            "type": "learned_skill",
            "pattern": {
                "route": self.route,
                "params_template": self.params_template
            },
            "metadata": {
                "source": self.source.value,
                "confidence": self.confidence,
                "success_rate": self.success_rate
            }
        }


@dataclass
class ExecutionRecord:
    """执行记录"""
    id: str
    user_input: str
    route: str
    params: Dict[str, Any]
    result: Dict[str, Any]
    success: bool
    timestamp: float = field(default_factory=time.time)
    context: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "user_input": self.user_input,
            "route": self.route,
            "params": self.params,
            "result": self.result,
            "success": self.success,
            "timestamp": self.timestamp,
            "context": self.context
        }


class SkillEvolutionSystem:
    """技能进化系统"""

    def __init__(self, storage_dir: str = "storage/skill_evolution"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        self._patterns: Dict[str, SkillPattern] = {}
        self._execution_history: List[ExecutionRecord] = []
        self._lock = threading.Lock()

        # 加载已保存的模式
        self._load_patterns()

        # 配置
        self.max_history_size = 1000
        self.min_success_rate_for_learning = 0.8
        self.min_usage_count_for_learning = 3
        self.confidence_decay_rate = 0.01

    def _load_patterns(self):
        """加载已保存的模式"""
        patterns_file = self.storage_dir / "patterns.json"
        if patterns_file.exists():
            try:
                with open(patterns_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for name, pattern_data in data.items():
                        self._patterns[name] = SkillPattern(**pattern_data)
            except Exception as e:
                print(f"Error loading patterns: {e}")

    def _save_patterns(self):
        """保存模式到文件"""
        patterns_file = self.storage_dir / "patterns.json"
        with open(patterns_file, "w", encoding="utf-8") as f:
            data = {name: pattern.to_dict() for name, pattern in self._patterns.items()}
            json.dump(data, f, ensure_ascii=False, indent=2)

    def record_execution(self, user_input: str, route: str, params: Dict[str, Any],
                         result: Dict[str, Any], success: bool, context: Dict[str, Any] = None):
        """记录一次执行

        Args:
            user_input: 用户输入
            route: 执行的路由
            params: 执行参数
            result: 执行结果
            success: 是否成功
            context: 上下文信息
        """
        record = ExecutionRecord(
            id=hashlib.md5(f"{user_input}{time.time()}".encode()).hexdigest()[:12],
            user_input=user_input,
            route=route,
            params=params,
            result=result,
            success=success,
            context=context or {}
        )

        with self._lock:
            self._execution_history.append(record)

            # 限制历史记录大小
            if len(self._execution_history) > self.max_history_size:
                self._execution_history = self._execution_history[-self.max_history_size:]

            # 尝试从成功执行中学习
            if success:
                self._try_learn_from_execution(record)

    def _try_learn_from_execution(self, record: ExecutionRecord):
        """尝试从成功执行中学习"""
        # 查找相似的用户输入模式
        similar_records = self._find_similar_executions(record.user_input)

        if len(similar_records) >= self.min_usage_count_for_learning - 1:  # 减去当前这条
            # 计算成功率
            success_count = sum(1 for r in similar_records if r.success) + 1  # +1 是当前这条
            success_rate = success_count / (len(similar_records) + 1)

            if success_rate >= self.min_success_rate_for_learning:
                # 可以学习为新技能
                self._extract_pattern(record, similar_records, success_rate)

    def _find_similar_executions(self, user_input: str, similarity_threshold: float = 0.6) -> List[ExecutionRecord]:
        """查找相似的执行记录"""
        similar = []

        # 简单的关键词匹配
        input_words = set(user_input.lower().split())

        for record in self._execution_history[:-1]:  # 排除最新这条
            record_words = set(record.user_input.lower().split())

            # Jaccard 相似度
            intersection = len(input_words & record_words)
            union = len(input_words | record_words)

            if union > 0:
                similarity = intersection / union
                if similarity >= similarity_threshold:
                    similar.append(record)

        return similar

    def _extract_pattern(self, record: ExecutionRecord, similar_records: List[ExecutionRecord],
                         success_rate: float):
        """从成功执行中提取模式"""
        # 生成模式名称
        pattern_name = f"pattern_{record.route}_{hashlib.md5(record.user_input.encode()).hexdigest()[:8]}"

        # 检查是否已存在
        if pattern_name in self._patterns:
            # 更新现有模式
            pattern = self._patterns[pattern_name]
            pattern.usage_count += 1
            pattern.success_rate = success_rate
            pattern.last_used_at = time.time()
        else:
            # 提取关键词作为触发器
            trigger_keywords = self._extract_keywords(record.user_input)

            # 创建新模式
            pattern = SkillPattern(
                name=pattern_name,
                description=f"从成功执行中学习的模式：{record.user_input[:50]}...",
                trigger_keywords=trigger_keywords,
                route=record.route,
                params_template=self._extract_params_template(record.params),
                success_conditions=["status == 'success'"],
                source=SkillSource.EXTRACTED,
                confidence=SkillConfidence.LOW.value,
                usage_count=1,
                success_rate=success_rate
            )

            with self._lock:
                self._patterns[pattern_name] = pattern
                self._save_patterns()

    def _extract_keywords(self, text: str, max_keywords: int = 5) -> List[str]:
        """从文本中提取关键词"""
        # 简单的关键词提取：去除停用词
        stopwords = {'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been',
                     'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
                     'would', 'could', 'should', 'may', 'might', 'must', 'shall',
                     'can', 'need', 'dare', 'ought', 'used', 'to', 'of', 'in',
                     'for', 'on', 'with', 'at', 'by', 'from', 'as', 'into',
                     'through', 'during', 'before', 'after', 'above', 'below',
                     '我', '的', '了', '在', '是', '就', '和', '都', '而', '及',
                     '与', '着', '或', '一个', '没有', '我们', '你们', '他们'}

        words = text.lower().split()
        keywords = [w for w in words if w not in stopwords and len(w) > 1]

        return keywords[:max_keywords]

    def _extract_params_template(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """从参数中提取模板"""
        template = {}
        for key, value in params.items():
            if isinstance(value, str):
                # 字符串参数，保留模式
                template[key] = value
            elif isinstance(value, (int, float)):
                # 数字，保留为占位符
                template[key] = f"<{key}>"
            elif isinstance(value, dict):
                # 字典，递归处理
                template[key] = self._extract_params_template(value)
            else:
                # 其他类型，转为字符串
                template[key] = str(value)

        return template

    def get_pattern_for_input(self, user_input: str) -> Optional[SkillPattern]:
        """根据用户输入获取匹配的模式"""
        input_words = set(user_input.lower().split())

        best_match = None
        best_score = 0

        for pattern in self._patterns.values():
            # 计算与触发关键词的匹配度
            match_count = sum(1 for kw in pattern.trigger_keywords
                              if kw.lower() in input_words)

            if match_count > 0:
                score = match_count / len(pattern.trigger_keywords)

                # 考虑置信度和成功率
                score *= pattern.confidence
                score *= pattern.success_rate

                if score > best_score and score >= 0.3:  # 最低匹配阈值
                    best_score = score
                    best_match = pattern

        return best_match

    def promote_pattern_to_skill(self, pattern_name: str, skill_manager) -> bool:
        """将模式提升为正式技能"""
        pattern = self._patterns.get(pattern_name)
        if not pattern:
            return False

        # 提高置信度
        pattern.confidence = SkillConfidence.HIGH.value

        # 创建技能定义
        skill_def = pattern.to_skill_definition()

        # TODO: 注册到技能管理器
        # skill_manager.register_skill(...)

        pattern.source = SkillSource.LEARNED
        self._save_patterns()

        return True

    def decay_confidence(self):
        """衰减长时间未使用模式的置信度"""
        current_time = time.time()
        thirty_days = 30 * 24 * 60 * 60

        with self._lock:
            for pattern in self._patterns.values():
                if pattern.last_used_at:
                    days_since_use = (current_time - pattern.last_used_at) / (24 * 60 * 60)
                    if days_since_use > 7:  # 7 天未使用
                        pattern.confidence *= (1 - self.confidence_decay_rate * days_since_use)
                        pattern.confidence = max(0.1, pattern.confidence)

            self._save_patterns()

    def list_patterns(self, min_confidence: float = 0) -> List[Dict[str, Any]]:
        """列出所有模式"""
        return [
            pattern.to_dict()
            for pattern in self._patterns.values()
            if pattern.confidence >= min_confidence
        ]

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        total_patterns = len(self._patterns)
        learned_patterns = sum(1 for p in self._patterns.values()
                               if p.source == SkillSource.LEARNED)
        extracted_patterns = sum(1 for p in self._patterns.values()
                                  if p.source == SkillSource.EXTRACTED)

        avg_confidence = sum(p.confidence for p in self._patterns.values()) / max(1, total_patterns)
        avg_success_rate = sum(p.success_rate for p in self._patterns.values()) / max(1, total_patterns)

        return {
            "total_patterns": total_patterns,
            "learned_patterns": learned_patterns,
            "extracted_patterns": extracted_patterns,
            "avg_confidence": round(avg_confidence, 3),
            "avg_success_rate": round(avg_success_rate, 3),
            "execution_history_size": len(self._execution_history)
        }

    def export_patterns(self, filepath: str):
        """导出模式到文件"""
        data = {name: pattern.to_dict() for name, pattern in self._patterns.items()}
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def import_patterns(self, filepath: str):
        """从文件导入模式"""
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
            for name, pattern_data in data.items():
                self._patterns[name] = SkillPattern(**pattern_data)
        self._save_patterns()


# 全局实例
_skill_evolution_system: Optional[SkillEvolutionSystem] = None


def get_skill_evolution_system() -> SkillEvolutionSystem:
    """获取技能进化系统单例"""
    global _skill_evolution_system
    if _skill_evolution_system is None:
        _skill_evolution_system = SkillEvolutionSystem()
    return _skill_evolution_system


# 便捷函数
def record_execution(user_input: str, route: str, params: Dict, result: Dict,
                     success: bool, context: Dict = None):
    """记录执行"""
    system = get_skill_evolution_system()
    system.record_execution(user_input, route, params, result, success, context)


def get_matching_pattern(user_input: str) -> Optional[Dict[str, Any]]:
    """获取匹配的模式"""
    system = get_skill_evolution_system()
    pattern = system.get_pattern_for_input(user_input)
    return pattern.to_dict() if pattern else None


def list_learned_skills() -> List[Dict[str, Any]]:
    """列出所有学习到的技能"""
    system = get_skill_evolution_system()
    return system.list_patterns(min_confidence=0.5)
