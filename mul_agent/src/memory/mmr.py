"""MMR - Maximal Marginal Relevance

最大边界相关性算法，用于搜索结果重新排序
在相关性和多样性之间取得平衡

@see Carbonell & Goldstein, "The Use of MMR, Diversity-Based Reranking" (1998)
基于 openclaw 的 mmr.ts 设计
"""

import re
from dataclasses import dataclass
from typing import TypeVar


@dataclass(frozen=True)
class MMRItem:
    """MMR 项目"""
    id: str
    score: float
    content: str


@dataclass
class MMRConfig:
    """MMR 配置"""
    enabled: bool = False
    lambda_param: float = 0.7  # λ 参数：0 = 最大多样性，1 = 最大相关性


DEFAULT_MMR_CONFIG = MMRConfig(enabled=False, lambda_param=0.7)


def tokenize(text: str) -> set[str]:
    """将文本分词用于 Jaccard 相似度计算

    提取字母数字下划线标记并转换为小写
    """
    tokens = re.findall(r'[a-z0-9_]+', text.lower())
    return set(tokens)


def jaccard_similarity(set_a: set[str], set_b: set[str]) -> float:
    """计算两个标记集的 Jaccard 相似度

    返回值范围 [0, 1]，1 表示完全相同
    """
    if not set_a and not set_b:
        return 1.0
    if not set_a or not set_b:
        return 0.0

    intersection = len(set_a & set_b)
    union = len(set_a | set_b)

    return intersection / union if union > 0 else 0.0


def text_similarity(content_a: str, content_b: str) -> float:
    """使用 Jaccard 相似度计算两个内容文本的相似度"""
    return jaccard_similarity(tokenize(content_a), tokenize(content_b))


def max_similarity_to_selected(
    item: MMRItem,
    selected_items: list[MMRItem],
    token_cache: dict[str, set[str]],
) -> float:
    """计算项目与所有已选项目的最大相似度"""
    if not selected_items:
        return 0.0

    max_sim = 0.0
    item_tokens = token_cache.get(item.id) or tokenize(item.content)

    for selected in selected_items:
        selected_tokens = token_cache.get(selected.id) or tokenize(selected.content)
        sim = jaccard_similarity(item_tokens, selected_tokens)
        if sim > max_sim:
            max_sim = sim

    return max_sim


def compute_mmr_score(relevance: float, max_similarity: float, lambda_param: float) -> float:
    """计算 MMR 分数

    MMR = λ * relevance - (1-λ) * max_similarity_to_selected
    """
    return lambda_param * relevance - (1 - lambda_param) * max_similarity


T = TypeVar('T', bound=MMRItem)


def mmr_rerank(items: list[T], config: MMRConfig | None = None) -> list[T]:
    """使用 MMR 重新排序项目

    算法迭代地选择平衡相关性和多样性的项目：
    1. 从最高分项目开始
    2. 对于每个剩余位置，选择最大化 MMR 分数的项目
    3. MMR 分数 = λ * relevance - (1-λ) * max_similarity_to_already_selected

    Args:
        items: 要重新排序的项目列表
        config: MMR 配置

    Returns:
        按 MMR 顺序排列的项目列表
    """
    cfg = config or DEFAULT_MMR_CONFIG

    # 提前退出
    if not cfg.enabled or len(items) <= 1:
        return list(items)

    # 限制 lambda 在有效范围内
    clamped_lambda = max(0, min(1, cfg.lambda_param))

    # 如果 lambda 为 1，只按相关性排序 (无多样性惩罚)
    if clamped_lambda == 1:
        return sorted(items, key=lambda x: x.score, reverse=True)

    # 预分词所有项目以提高效率
    token_cache: dict[str, set[str]] = {}
    for item in items:
        token_cache[item.id] = tokenize(item.content)

    # 归一化分数到 [0, 1] 范围以与相似度公平比较
    scores = [item.score for item in items]
    max_score = max(scores)
    min_score = min(scores)
    score_range = max_score - min_score

    def normalize_score(score: float) -> float:
        if score_range == 0:
            return 1.0  # 所有分数相同
        return (score - min_score) / score_range

    selected: list[T] = []
    remaining = set(items)

    # 迭代选择项目
    while remaining:
        best_item: T | None = None
        best_mmr_score = float('-inf')

        for candidate in remaining:
            normalized_relevance = normalize_score(candidate.score)
            max_sim = max_similarity_to_selected(candidate, selected, token_cache)
            mmr_score = compute_mmr_score(normalized_relevance, max_sim, clamped_lambda)

            # 使用原始分数作为决胜局 (越高越好)
            if (
                mmr_score > best_mmr_score or
                (mmr_score == best_mmr_score and
                 candidate.score > (best_item.score if best_item else float('-inf')))
            ):
                best_mmr_score = mmr_score
                best_item = candidate

        if best_item:
            selected.append(best_item)
            remaining.remove(best_item)
        else:
            # 安全退出 (不应该发生)
            break

    return selected


def apply_mmr_to_hybrid_results(
    results: list[T],
    config: MMRConfig | None = None,
) -> list[T]:
    """将 MMR 重新排序应用于混合搜索结果

    Args:
        results: 混合搜索结果列表
        config: MMR 配置

    Returns:
        经过 MMR 重新排序的结果列表
    """
    if not results:
        return results

    # 创建从 ID 到原始项目的映射
    item_by_id: dict[str, T] = {}

    # 创建 MMR 项目，使用唯一 ID
    mmr_items: list[MMRItem] = []
    for i, r in enumerate(results):
        item_id = f"{r.path}:{getattr(r, 'start_line', 0)}:{i}"
        mmr_item = MMRItem(id=item_id, score=r.score, content=getattr(r, 'snippet', ''))
        mmr_items.append(mmr_item)
        item_by_id[item_id] = r

    reranked = mmr_rerank(mmr_items, config)

    # 映射回原始项目
    return [item_by_id[item.id] for item in reranked]


# ============================================================================
# 时间衰减支持
# ============================================================================

import time


def temporal_decay_factor(
    timestamp: float,
    half_life_days: float = 7.0,
    current_time: float | None = None,
) -> float:
    """计算时间衰减因子

    使用指数衰减模型：factor = 0.5 ^ (days_elapsed / half_life_days)

    Args:
        timestamp: 项目的时间戳 (Unix 时间)
        half_life_days: 半衰期 (天)
        current_time: 当前时间 (默认为 now)

    Returns:
        时间衰减因子 [0, 1]
    """
    now = current_time or time.time()
    days_elapsed = (now - timestamp) / 86400  # 86400 秒/天

    return 0.5 ** (days_elapsed / half_life_days)


def apply_temporal_decay(
    results: list[T],
    timestamps: dict[str, float],
    half_life_days: float = 7.0,
) -> list[T]:
    """应用时间衰减到搜索结果

    Args:
        results: 搜索结果列表
        timestamps: 项目 ID 到时间戳的映射
        half_life_days: 半衰期 (天)

    Returns:
        应用时间衰减后的结果列表
    """
    decayed_results = []

    for r in results:
        item_id = f"{r.path}:{getattr(r, 'start_line', 0)}"
        timestamp = timestamps.get(item_id, time.time())
        decay_factor = temporal_decay_factor(timestamp, half_life_days)

        # 创建新对象并应用衰减
        if hasattr(r, '__dict__'):
            decayed = type(r)(**r.__dict__)
            decayed.score *= decay_factor
            decayed_results.append(decayed)
        else:
            # 对于 dataclass 或其他不可变对象，直接附加
            decayed_results.append(r)

    # 按衰减后的分数重新排序
    return sorted(decayed_results, key=lambda x: x.score, reverse=True)
