"""Hybrid Search - 混合搜索

基于 openclaw 的 hybrid.ts 设计
实现向量搜索和全文搜索的结果合并与重新排序

核心功能:
1. FTS5 查询构建 - 将原始查询转换为 FTS5 语法
2. BM25 排名转换 - 将 BM25 排名转换为归一化分数
3. 混合结果合并 - 支持可配置权重、MMR 重新排序、时间衰减
"""

import re
import time
from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from pathlib import Path

from .mmr import (
    mmr_rerank,
    apply_mmr_to_hybrid_results,
    MMRConfig,
    DEFAULT_MMR_CONFIG,
    temporal_decay_factor,
    apply_temporal_decay,
)


# ============================================================================
# 类型定义
# ============================================================================

HybridSource = str  # "memory" | "sessions" | 其他来源


@dataclass
class HybridVectorResult:
    """向量搜索结果"""
    id: str
    path: str
    start_line: int
    end_line: int
    source: HybridSource
    snippet: str
    vector_score: float


@dataclass
class HybridKeywordResult:
    """全文搜索结果 (FTS)"""
    id: str
    path: str
    start_line: int
    end_line: int
    source: HybridSource
    snippet: str
    text_score: float


@dataclass
class HybridResult:
    """混合搜索结果"""
    path: str
    start_line: int
    end_line: int
    score: float
    snippet: str
    source: HybridSource


@dataclass
class TemporalDecayConfig:
    """时间衰减配置

    Attributes:
        enabled: 是否启用时间衰减
        half_life_days: 半衰期 (天)，默认 30 天
    """
    enabled: bool = False
    half_life_days: float = 30.0


DEFAULT_TEMPORAL_DECAY_CONFIG = TemporalDecayConfig(enabled=False, half_life_days=30.0)


# ============================================================================
# FTS5 查询构建
# ============================================================================

def build_fts_query(raw: str) -> Optional[str]:
    """构建 FTS5 查询字符串

    将原始查询字符串转换为 FTS5 语法，使用 AND 连接所有标记。
    标记提取规则：匹配 Unicode 字母、数字和下划线。

    Args:
        raw: 原始查询字符串

    Returns:
        FTS5 查询字符串，如果无有效标记则返回 None

    Example:
        >>> build_fts_query("如何部署应用")
        '"如何部署应用"'

        >>> build_fts_query("Python 异步编程")
        '"Python" AND "异步编程"'

        >>> build_fts_query("   ")
        None
    """
    # 使用 Unicode 感知的标记提取
    # 匹配字母、数字、下划线和中文字符
    tokens = re.findall(r'[\\u4e00-\\u9fa5\\w]+', raw)

    # 清理空标记
    cleaned_tokens = [t.strip() for t in tokens if t.strip()]

    if not cleaned_tokens:
        return None

    # 将每个标记用双引号包裹 (精确匹配)
    # 并移除标记内部的双引号以避免语法错误
    quoted_tokens = [f'"{t.replace(chr(34), "")}"' for t in cleaned_tokens]

    # 使用 AND 连接所有标记
    return " AND ".join(quoted_tokens)


# ============================================================================
# BM25 排名转换
# ============================================================================

def bm25_rank_to_score(rank: float) -> float:
    """将 BM25 排名转换为归一化分数

    BM25 排名值越小表示越相关 (越小越好)。
    此函数将排名转换为 [0, 1] 范围的分数 (越大越好)。

    转换公式:
    - 对于负排名 (SQLite FTS5 BM25 通常返回负值): score = relevance / (1 + relevance)
      其中 relevance = -rank
    - 对于非负排名：score = 1 / (1 + rank)

    Args:
        rank: BM25 排名值 (通常来自 SQLite FTS5 的 bm25() 函数)

    Returns:
        归一化分数 [0, 1]，越大表示越相关

    Example:
        >>> bm25_rank_to_score(-10)  # 高相关性
        0.909...

        >>> bm25_rank_to_score(0)  # 中等
        1.0

        >>> bm25_rank_to_score(999)  # 低相关性
        0.001...
    """
    # 处理非有限数值
    if not (rank == rank):  # NaN 检查
        return 1 / (1 + 999)

    if rank < 0:
        # 负排名：转换为正的相关性分数
        relevance = -rank
        return relevance / (1 + relevance)

    # 非负排名：直接转换
    return 1 / (1 + rank)


# ============================================================================
# 混合结果合并
# ============================================================================

def merge_hybrid_results(
    vector: List[HybridVectorResult],
    keyword: List[HybridKeywordResult],
    vector_weight: float = 0.7,
    text_weight: float = 0.3,
    workspace_dir: Optional[str] = None,
    mmr: Optional[MMRConfig] = None,
    temporal_decay: Optional[TemporalDecayConfig] = None,
    now_ms: Optional[float] = None,
) -> List[HybridResult]:
    """合并向量和全文搜索结果

    合并策略:
    1. 通过唯一 ID (path:start_line:end_line) 合并相同结果
    2. 使用可配置权重计算加权分数
    3. 可选应用时间衰减
    4. 可选应用 MMR 重新排序以增加多样性

    Args:
        vector: 向量搜索结果列表
        keyword: 全文搜索结果列表
        vector_weight: 向量分数权重，默认 0.7
        text_weight: 文本分数权重，默认 0.3
        workspace_dir: 工作目录路径，用于时间衰减计算文件修改时间
        mmr: MMR 配置，用于多样性重新排序
        temporal_decay: 时间衰减配置
        now_ms: 当前时间戳 (毫秒)，用于测试

    Returns:
        合并后的混合搜索结果列表，按分数降序排列

    Example:
        >>> vector_results = [
        ...     HybridVectorResult("id1", "file.py", 1, 10, "memory", "snippet", 0.9)
        ... ]
        >>> keyword_results = [
        ...     HybridKeywordResult("id1", "file.py", 1, 10, "memory", "snippet", 0.8)
        ... ]
        >>> merged = merge_hybrid_results(
        ...     vector_results, keyword_results,
        ...     vector_weight=0.6, text_weight=0.4
        ... )
    """
    # 用于合并结果的字典
    by_id: Dict[str, Dict[str, Any]] = {}

    # 添加向量搜索结果
    for r in vector:
        by_id[r.id] = {
            "id": r.id,
            "path": r.path,
            "start_line": r.start_line,
            "end_line": r.end_line,
            "source": r.source,
            "snippet": r.snippet,
            "vector_score": r.vector_score,
            "text_score": 0.0,
        }

    # 添加全文搜索结果并更新已有结果
    for r in keyword:
        existing = by_id.get(r.id)
        if existing:
            existing["text_score"] = r.text_score
            # 如果全文搜索提供了更好的片段，则更新
            if r.snippet and len(r.snippet) > 0:
                existing["snippet"] = r.snippet
        else:
            by_id[r.id] = {
                "id": r.id,
                "path": r.path,
                "start_line": r.start_line,
                "end_line": r.end_line,
                "source": r.source,
                "snippet": r.snippet,
                "vector_score": 0.0,
                "text_score": r.text_score,
            }

    # 创建混合结果并计算加权分数
    merged: List[HybridResult] = []
    for entry in by_id.values():
        score = vector_weight * entry["vector_score"] + text_weight * entry["text_score"]
        merged.append(HybridResult(
            path=entry["path"],
            start_line=entry["start_line"],
            end_line=entry["end_line"],
            score=score,
            snippet=entry["snippet"],
            source=entry["source"],
        ))

    # 应用时间衰减
    decay_config = temporal_decay or DEFAULT_TEMPORAL_DECAY_CONFIG
    if decay_config.enabled and workspace_dir:
        merged = _apply_temporal_decay_to_hybrid_results(
            results=merged,
            workspace_dir=workspace_dir,
            half_life_days=decay_config.half_life_days,
            now_ms=now_ms,
        )

    # 按分数降序排序
    merged.sort(key=lambda x: x.score, reverse=True)

    # 应用 MMR 重新排序 (如果启用)
    mmr_config = mmr or DEFAULT_MMR_CONFIG
    if mmr_config.enabled:
        return apply_mmr_to_hybrid_results(merged, mmr_config)

    return merged


def _apply_temporal_decay_to_hybrid_results(
    results: List[HybridResult],
    workspace_dir: str,
    half_life_days: float,
    now_ms: Optional[float] = None,
) -> List[HybridResult]:
    """对混合搜索结果应用时间衰减

    使用指数衰减模型：factor = 0.5 ^ (days_elapsed / half_life_days)

    Args:
        results: 混合搜索结果列表
        workspace_dir: 工作目录路径
        half_life_days: 半衰期 (天)
        now_ms: 当前时间戳 (毫秒)

    Returns:
        应用时间衰减后的结果列表
    """
    if not results:
        return results

    now = now_ms if now_ms is not None else time.time() * 1000

    # 缓存文件时间戳以避免重复读取
    timestamp_cache: Dict[str, float] = {}

    decayed_results: List[HybridResult] = []

    for result in results:
        # 尝试从路径提取日期或使用文件修改时间
        timestamp = _extract_timestamp_from_path(
            path=result.path,
            workspace_dir=workspace_dir,
            cache=timestamp_cache,
        )

        if timestamp is None:
            # 无法确定时间，不应用衰减
            decayed_results.append(result)
            continue

        # 计算经过的天数
        age_ms = max(0, now - timestamp)
        age_days = age_ms / (1000 * 60 * 60 * 24)  # 毫秒转天

        # 计算衰减因子
        decay_factor = temporal_decay_factor(
            timestamp=timestamp / 1000,  # 转换为秒
            half_life_days=half_life_days,
            current_time=now / 1000,
        )

        # 应用衰减到分数
        decayed_result = HybridResult(
            path=result.path,
            start_line=result.start_line,
            end_line=result.end_line,
            score=result.score * decay_factor,
            snippet=result.snippet,
            source=result.source,
        )
        decayed_results.append(decayed_result)

    # 按衰减后的分数重新排序
    decayed_results.sort(key=lambda x: x.score, reverse=True)

    return decayed_results


def _extract_timestamp_from_path(
    path: str,
    workspace_dir: str,
    cache: Dict[str, float],
) -> Optional[float]:
    """从路径提取时间戳

    尝试以下方法:
    1. 从路径中的日期模式提取 (如 memory/2024-01-15.md)
    2. 使用文件修改时间 (mtime)

    Args:
        path: 文件路径
        workspace_dir: 工作目录
        cache: 时间戳缓存

    Returns:
        时间戳 (毫秒)，如果无法提取则返回 None
    """
    cache_key = path

    # 检查缓存
    if cache_key in cache:
        return cache[cache_key]

    # 尝试从路径中的日期模式提取
    # 匹配模式：memory/YYYY-MM-DD.md
    date_pattern = r'(?:^|/)memory/(\d{4})-(\d{2})-(\d{2})\.md$'
    match = re.search(date_pattern, path, re.IGNORECASE)

    if match:
        year = int(match.group(1))
        month = int(match.group(2))
        day = int(match.group(3))

        # 验证日期有效性
        try:
            from datetime import datetime, timezone
            dt = datetime(year, month, day, tzinfo=timezone.utc)
            timestamp = dt.timestamp() * 1000  # 转换为毫秒
            cache[cache_key] = timestamp
            return timestamp
        except ValueError:
            pass  # 无效日期

    # 尝试使用文件修改时间
    try:
        full_path = path if Path(path).is_absolute() else Path(workspace_dir) / path
        if Path(full_path).exists():
            mtime = Path(full_path).stat().st_mtime
            timestamp = mtime * 1000  # 转换为毫秒
            cache[cache_key] = timestamp
            return timestamp
    except (OSError, PermissionError):
        pass

    return None


# ============================================================================
# 辅助函数
# ============================================================================

def to_decay_lambda(half_life_days: float) -> float:
    """计算衰减常数 (lambda)

    基于半衰期计算指数衰减的 lambda 参数。
    公式：lambda = ln(2) / half_life_days

    Args:
        half_life_days: 半衰期 (天)

    Returns:
        衰减常数
    """
    if half_life_days <= 0 or not (half_life_days == half_life_days):
        return 0.0
    import math
    return math.log(2) / half_life_days


def calculate_temporal_decay_multiplier(
    age_in_days: float,
    half_life_days: float,
) -> float:
    """计算时间衰减乘数

    使用指数衰减公式：factor = e^(-lambda * age)

    Args:
        age_in_days: 经过的天数
        half_life_days: 半衰期 (天)

    Returns:
        衰减乘数 [0, 1]
    """
    lambda_param = to_decay_lambda(half_life_days)
    clamped_age = max(0, age_in_days)

    if lambda_param <= 0 or not (clamped_age == clamped_age):
        return 1.0

    import math
    return math.exp(-lambda_param * clamped_age)


def apply_temporal_decay_to_score(
    score: float,
    age_in_days: float,
    half_life_days: float,
) -> float:
    """应用时间衰减到分数

    Args:
        score: 原始分数
        age_in_days: 经过的天数
        half_life_days: 半衰期 (天)

    Returns:
        衰减后的分数
    """
    decay_factor = calculate_temporal_decay_multiplier(age_in_days, half_life_days)
    return score * decay_factor
