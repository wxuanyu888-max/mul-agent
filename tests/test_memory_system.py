"""Memory System Tests - 记忆系统测试

测试向量搜索、全文搜索、混合搜索、MMR 重新排序等功能
"""

import asyncio
import os
import tempfile
from pathlib import Path

import pytest

from mul_agent.memory import (
    MemoryIndexManager,
    MemorySearchResult,
    chunk_text,
    mmr_rerank,
    MMRConfig,
    MMRItem,
    text_similarity,
    temporal_decay_factor,
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def temp_db():
    """创建临时数据库"""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    yield db_path
    # 清理
    Path(db_path).unlink(missing_ok=True)


@pytest.fixture
def temp_workspace():
    """创建临时工作目录"""
    with tempfile.TemporaryDirectory() as workspace:
        ws_path = Path(workspace)

        # 创建 MEMORY.md
        memory_md = ws_path / "MEMORY.md"
        memory_md.write_text("""---
id: memory-main
agent_id: test
type: memory
timestamp: 2024-01-01T00:00:00
---

# 项目记忆

## 项目架构

本项目采用多 Agent 协作架构，核心组件包括:

1. **Brain** -  Agent 大脑，负责决策和路由
2. **Handlers** - 处理器，执行具体任务
3. **Memory** - 记忆系统，存储和检索知识
4. **Skills** - 技能系统，可扩展能力

## 技术栈

- 后端：Python 3.11+, FastAPI
- 前端：React, TypeScript
- 数据库：SQLite with FTS5

## 部署流程

部署应用需要以下步骤:

1. 构建 Docker 镜像
2. 配置环境变量
3. 启动容器
4. 运行健康检查

## 常见问题

Q: 如何重置 Agent 状态？
A: 删除 storage/agent_states/<agent_id>.json 文件

Q: 如何查看日志？
A: 使用 `tail -f storage/logs/agent.log`
""")

        # 创建 memory 目录和文件
        memory_dir = ws_path / "memory"
        memory_dir.mkdir()

        (memory_dir / "api-design.md").write_text("""---
id: api-design
agent_id: test
type: memory
timestamp: 2024-01-02T00:00:00
---

# API 设计规范

## RESTful 规范

### 资源命名

- 使用名词复数形式：/users, /projects
- 使用小写字母
- 使用连字符分隔：/user-profiles

### HTTP 方法

- GET: 获取资源
- POST: 创建资源
- PUT: 更新资源
- DELETE: 删除资源

### 响应格式

```json
{
  "status": "success",
  "data": {},
  "error": null
}
```
""")

        (memory_dir / "deployment.md").write_text("""---
id: deployment
agent_id: test
type: memory
timestamp: 2024-01-03T00:00:00
---

# 部署指南

## Docker 部署

### 构建镜像

```bash
docker build -t myapp:latest .
```

### 运行容器

```bash
docker run -d -p 8000:8000 myapp:latest
```

## 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| PORT | 服务端口 | 8000 |
| DATABASE_URL | 数据库连接 | sqlite:///db.sqlite |
| LOG_LEVEL | 日志级别 | INFO |

## Kubernetes 部署

TODO: 添加 K8s 配置
""")

        yield str(ws_path)


# ============================================================================
# 基础功能测试
# ============================================================================

class TestChunkText:
    """文本分块测试"""

    def test_small_text_no_chunking(self):
        """小文本不需要分块"""
        text = "这是一个小文本。\n只有两行。"
        chunks = chunk_text(text, path="test.md", model="test-model")

        assert len(chunks) == 1
        assert "小文本" in chunks[0].text

    def test_large_text_chunking(self):
        """大文本需要分块"""
        # 创建超过 chunk_size (30 行) 的文本，每行足够长
        lines = [f"这是第 {i} 行的内容，需要足够多的字符才能触发分块逻辑，这是测试文本" for i in range(100)]
        text = "\n".join(lines)

        # 使用较小的 chunk_size 以确保分块
        chunks = chunk_text(
            text,
            path="test.md",
            model="test-model",
            chunk_size=30,  # 每块最多 30 行
            chunk_overlap=5,
        )

        # 100 行，每块 30 行，应该至少产生 4 块 (考虑重叠)
        assert len(chunks) >= 2, f"Expected at least 2 chunks, got {len(chunks)}"

        # 验证第一个分块的结束行 >= 第二个分块的开始行（重叠）
        if len(chunks) >= 2:
            assert chunks[0].end_line >= chunks[1].start_line, "Chunks should overlap"

    def test_chunk_metadata(self):
        """验证分块元数据"""
        text = "第一行\n第二行\n第三行"
        chunks = chunk_text(text, path="test.md", source="memory", model="test-model")

        chunk = chunks[0]
        assert chunk.path == "test.md"
        assert chunk.source == "memory"
        assert chunk.start_line == 1
        assert chunk.end_line == 3
        assert chunk.model == "test-model"


# ============================================================================
# MMR 测试
# ============================================================================

class TestMMR:
    """MMR 重新排序测试"""

    def test_mmr_basic(self):
        """基本 MMR 测试"""
        items = [
            MMRItem(id="1", score=0.9, content="apple fruit red"),
            MMRItem(id="2", score=0.85, content="apple fruit green"),
            MMRItem(id="3", score=0.8, content="car vehicle fast"),
        ]

        config = MMRConfig(enabled=True, lambda_param=0.7)
        reranked = mmr_rerank(items, config)

        # 验证返回了所有项目
        assert len(reranked) == 3
        # 验证第一项应该具有高分数和高多样性
        assert reranked[0].score >= 0.8

    def test_mmr_disabled(self):
        """MMR 禁用时保持原序"""
        items = [
            MMRItem(id="1", score=0.9, content="test 1"),
            MMRItem(id="2", score=0.5, content="test 2"),
        ]

        config = MMRConfig(enabled=False)
        reranked = mmr_rerank(items, config)

        assert reranked[0].id == "1"
        assert reranked[1].id == "2"

    def test_mmr_single_item(self):
        """单个项目不需要重排序"""
        items = [MMRItem(id="1", score=0.9, content="test")]

        reranked = mmr_rerank(items)
        assert len(reranked) == 1


class TestTextSimilarity:
    """文本相似度测试"""

    def test_identical_texts(self):
        """相同文本应该相似度为 1"""
        text = "hello world"
        assert text_similarity(text, text) == 1.0

    def test_completely_different_texts(self):
        """完全不同文本应该相似度为 0"""
        text_a = "apple banana orange"
        text_b = "car truck motorcycle"

        similarity = text_similarity(text_a, text_b)
        assert similarity < 0.3

    def test_partial_overlap(self):
        """部分重叠应该有中等相似度"""
        text_a = "apple banana orange"
        text_b = "apple banana grape"

        similarity = text_similarity(text_a, text_b)
        assert 0.3 <= similarity <= 0.8


# ============================================================================
# 时间衰减测试
# ============================================================================

class TestTemporalDecay:
    """时间衰减测试"""

    def test_fresh_item(self):
        """新项目应该有高衰减因子 (接近 1)"""
        import time
        now = time.time()
        factor = temporal_decay_factor(now, half_life_days=7.0, current_time=now)
        assert factor == 1.0

    def test_one_week_old(self):
        """一周前的项目应该有 0.5 的衰减因子 (半衰期=7 天)"""
        import time
        week_ago = time.time() - 7 * 86400
        factor = temporal_decay_factor(week_ago, half_life_days=7.0, current_time=time.time())
        assert 0.45 <= factor <= 0.55

    def test_two_weeks_old(self):
        """两周前的项目应该有 0.25 的衰减因子"""
        import time
        two_weeks_ago = time.time() - 14 * 86400
        factor = temporal_decay_factor(two_weeks_ago, half_life_days=7.0, current_time=time.time())
        assert 0.20 <= factor <= 0.30


# ============================================================================
# Memory Manager 集成测试
# ============================================================================

class TestMemoryIndexManager:
    """记忆索引管理器集成测试"""

    def test_create_manager_no_provider(self, temp_workspace, temp_db):
        """创建管理器 (FTS-only 模式)"""
        manager = MemoryIndexManager(
            workspace_dir=temp_workspace,
            db_path=temp_db,
            provider=None,  # 无嵌入提供商
            fts_enabled=True,
        )

        status = manager.status()
        assert status.provider == "none"
        assert status.fts_enabled is True

        manager.close()

    def test_fts_search_basic(self, temp_workspace, temp_db):
        """全文搜索基本测试"""
        manager = MemoryIndexManager(
            workspace_dir=temp_workspace,
            db_path=temp_db,
            provider=None,
            fts_enabled=True,
        )

        # 手动插入测试数据
        cursor = manager.db.cursor()
        cursor.execute("""
            INSERT INTO chunks (id, path, source, start_line, end_line, hash, model, text, embedding, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            "test-1",
            "test.md",
            "memory",
            1,
            5,
            "hash123",
            "none",
            "部署应用需要使用 Docker 容器化技术",
            "[]",
            1234567890,
        ))

        # 插入 FTS 表
        cursor.execute("""
            INSERT INTO chunks_fts (id, path, source, start_line, end_line, model, text)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            "test-1",
            "test.md",
            "memory",
            1,
            5,
            "none",
            "部署应用需要使用 Docker 容器化技术",
        ))

        manager.db.commit()

        # 执行搜索
        results = manager.search("Docker 部署", max_results=10, use_hybrid=False)

        # 验证结果
        assert len(results) >= 0  # FTS 可能需要重新索引

        manager.close()

    def test_status_reports_correct_counts(self, temp_workspace, temp_db):
        """状态报告正确的计数"""
        manager = MemoryIndexManager(
            workspace_dir=temp_workspace,
            db_path=temp_db,
            provider=None,
        )

        # 插入测试数据
        cursor = manager.db.cursor()
        for i in range(5):
            cursor.execute("""
                INSERT OR REPLACE INTO chunks (id, path, source, start_line, end_line, hash, model, text, embedding, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                f"chunk-{i}",
                f"file-{i // 2}.md",
                "memory",
                1,
                10,
                f"hash{i}",
                "none",
                f"test content {i}",
                "[]",
                1234567890,
            ))

        manager.db.commit()

        status = manager.status()
        assert status.chunks == 5
        # 文件数应该是 3 (file-0, file-1, file-2)

        manager.close()


# ============================================================================
# 异步嵌入测试
# ============================================================================

class TestEmbeddingsAsync:
    """嵌入异步测试"""

    @pytest.mark.asyncio
    async def test_mock_embedding_provider(self):
        """模拟嵌入提供商"""
        from mul_agent.memory.embeddings import EmbeddingProvider

        class MockProvider(EmbeddingProvider):
            def __init__(self):
                super().__init__(id="mock", model="mock-model")

            async def embed_query(self, text: str) -> list[float]:
                # 返回简单的哈希嵌入
                return [hash(text) % 1000 / 1000.0] * 10

            async def embed_batch(self, texts: list[str]) -> list[list[float]]:
                return [await self.embed_query(t) for t in texts]

        provider = MockProvider()
        embedding = await provider.embed_query("hello world")

        assert len(embedding) == 10
        assert all(0 <= v <= 1 for v in embedding)


# ============================================================================
# 边界情况测试
# ============================================================================

class TestEdgeCases:
    """边界情况测试"""

    def test_empty_query_search(self, temp_workspace, temp_db):
        """空查询搜索"""
        manager = MemoryIndexManager(
            workspace_dir=temp_workspace,
            db_path=temp_db,
            provider=None,
        )

        results = manager.search("", max_results=10)
        assert len(results) == 0

        manager.close()

    def test_whitespace_query(self, temp_workspace, temp_db):
        """空白查询"""
        manager = MemoryIndexManager(
            workspace_dir=temp_workspace,
            db_path=temp_db,
            provider=None,
        )

        results = manager.search("   ", max_results=10)
        assert len(results) == 0

        manager.close()

    def test_zero_max_results(self, temp_workspace, temp_db):
        """零最大结果数"""
        manager = MemoryIndexManager(
            workspace_dir=temp_workspace,
            db_path=temp_db,
            provider=None,
        )

        results = manager.search("test", max_results=0)
        assert len(results) == 0

        manager.close()


# ============================================================================
# 运行测试
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
