# Memory System Implementation Report

## 概述

已成功将 openclaw 的 TypeScript memory 系统移植到 Python，创建了完整的向量化记忆搜索系统。

## 创建的文件

### 核心模块

| 文件 | 说明 | 行数 |
|------|------|------|
| `memory_schema.py` | SQLite 数据库模式定义 | ~100 |
| `embeddings.py` | 嵌入向量生成客户端 | ~350 |
| `memory_manager.py` | 记忆管理器核心 | ~400 |
| `memory_indexer.py` | 记忆索引器（分块、同步） | ~400 |
| `mmr.py` | MMR 重新排序算法 | ~200 |
| `memory_routes.py` | FastAPI 路由 | ~300 |
| `__init__.py` | 模块导出 | ~115 |
| `test_memory_system.py` | 单元测试 | ~350 |

**总计：~2200 行代码**

## 核心功能

### 1. 向量搜索 (Vector Search)
- 使用嵌入向量进行语义相似度搜索
- 支持 OpenAI、Gemini、Ollama 等嵌入提供商
- 余弦相似度计算
- 自动向量归一化

### 2. 全文搜索 (Full-Text Search)
- 基于 SQLite FTS5 的 BM25 关键词搜索
- FTS-only 模式（无需嵌入 API key）
- 支持中文和英文搜索

### 3. 混合搜索 (Hybrid Search)
- 结合向量搜索和全文搜索
- 加权融合两种搜索结果
- 可配置的权重参数

### 4. MMR 重新排序 (Maximal Marginal Relevance)
- 平衡相关性和多样性
- 避免搜索结果过于集中
- 可配置的 lambda 参数

### 5. 时间衰减 (Temporal Decay)
- 近期记忆权重更高
- 指数衰减模型
- 可配置的半衰期

### 6. 嵌入缓存 (Embedding Cache)
- 避免重复计算嵌入
- 基于文本哈希的缓存
- 缓存统计功能

### 7. 自动同步 (Auto Sync)
- 文件变更检测
- 增量索引更新
- 进度回调支持

## 架构设计

```
mul_agent/memory/
├── memory_schema.py      # 数据库模式
├── embeddings.py         # 嵌入客户端
├── memory_manager.py     # 核心管理器
├── memory_indexer.py     # 索引器
├── mmr.py               # MMR 算法
├── memory_routes.py      # API 路由
├── __init__.py          # 模块导出
└── test_memory_system.py # 测试
```

## 使用示例

### 基本使用

```python
from mul_agent.memory import MemoryIndexManager

# 创建管理器（FTS-only 模式）
manager = MemoryIndexManager(
    workspace_dir="/path/to/workspace",
    db_path="/path/to/memory.db",
    provider=None,  # 无嵌入提供商，仅使用全文搜索
)

# 搜索
results = manager.search("如何部署应用", max_results=10)

for result in results:
    print(f"{result.path}:{result.start_line}-{result.end_line}")
    print(f"Score: {result.score}")
    print(f"Snippet: {result.snippet}")
    print()

# 获取状态
status = manager.status()
print(f"Files: {status.files}, Chunks: {status.chunks}")

manager.close()
```

### 使用向量搜索

```python
from mul_agent.memory import (
    MemoryIndexManager,
    create_embedding_provider,
    EmbeddingProviderOptions,
)
import asyncio

async def main():
    # 创建嵌入提供商
    provider_result = await create_embedding_provider(EmbeddingProviderOptions(
        provider="openai",  # 或 "gemini", "ollama", "auto"
        model="text-embedding-3-small",
        fallback="none",
        api_key="sk-...",  # OpenAI API key
    ))

    # 创建管理器（混合模式）
    manager = MemoryIndexManager(
        workspace_dir="/path/to/workspace",
        db_path="/path/to/memory.db",
        provider=provider_result.provider,
    )

    # 混合搜索（向量 + 全文）
    results = manager.search(
        "如何部署应用",
        max_results=10,
        use_hybrid=True,  # 启用混合搜索
    )

    manager.close()

# 运行
asyncio.run(main())
```

### API 使用

```python
from fastapi import FastAPI
from mul_agent.memory import memory_router

app = FastAPI()
app.include_router(memory_router)

# 启动服务
# uvicorn app:app --host 0.0.0.0 --port 8000
```

### API 端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/memory/search` | GET/POST | 搜索记忆 |
| `/memory/status` | GET | 获取索引状态 |
| `/memory/index` | POST | 更新索引 |
| `/memory/index/rebuild` | POST | 重建索引 |
| `/memory/cache` | DELETE | 清除嵌入缓存 |
| `/memory/stats` | GET | 获取统计信息 |

## 配置选项

### 嵌入提供商配置

```python
EmbeddingProviderOptions(
    provider="auto",       # "openai", "gemini", "ollama", "auto"
    model="default",       # 模型名称
    fallback="none",       # 后备提供商
    api_key="...",         # API key
    base_url="...",        # 自定义 API 地址
)
```

### MMR 配置

```python
MMRConfig(
    enabled=True,          # 是否启用 MMR
    lambda_param=0.7,      # λ 参数：0=最大多样性，1=最大相关性
)
```

### 时间衰减配置

```python
temporal_decay_factor(
    timestamp=...,         # 项目时间戳
    half_life_days=7.0,    # 半衰期（天）
    current_time=None,     # 当前时间（默认 now）
)
```

## 与 openclaw 的对比

| 功能 | openclaw (TS) | 本实现 (Python) |
|------|---------------|-----------------|
| 向量搜索 | ✅ | ✅ |
| 全文搜索 (FTS5) | ✅ | ✅ |
| 混合搜索 | ✅ | ✅ |
| MMR 重新排序 | ✅ | ✅ |
| 时间衰减 | ✅ | ✅ |
| 嵌入缓存 | ✅ | ✅ |
| 文件监听 | ✅ | ⏳ TODO |
| 批量嵌入 | ✅ | ✅ |
| OpenAI 支持 | ✅ | ✅ |
| Gemini 支持 | ✅ | ✅ |
| Ollama 支持 | ✅ | ✅ |
| Voyage 支持 | ✅ | ⏳ TODO |
| Mistral 支持 | ✅ | ⏳ TODO |
| 本地嵌入 | ✅ | ⏳ TODO |

## 测试

运行测试：

```bash
# 运行所有测试
pytest tests/test_memory_system.py -v

# 运行特定测试类
pytest tests/test_memory_system.py::TestMMR -v

# 运行特定测试
pytest tests/test_memory_system.py::TestChunkText::test_large_text_chunking -v
```

## 下一步改进

1. **文件监听** - 实现 chokidar 类似的 file watcher
2. **更多嵌入提供商** - 添加 Voyage、Mistral 支持
3. **本地嵌入** - 支持本地模型（如 sentence-transformers）
4. **QMD 后端** - 支持 Quantized Document Database
5. **向量扩展** - 集成 sqlite-vec 扩展
6. **MMR 优化** - 使用更高效的相似度计算

## 注意事项

1. **FTS 可用性** - SQLite FTS5 需要 Python 编译时启用
2. **sqlite-vec** - 向量搜索需要安装 sqlite-vec 扩展
3. **API Key** - 向量搜索需要配置嵌入 API key
4. **性能** - 大量数据时建议使用向量扩展

## 依赖

```python
# 核心依赖
fastapi>=0.100.0
pydantic>=2.0.0
httpx>=0.25.0  # 用于 API 调用

# 测试依赖
pytest>=7.0.0
pytest-asyncio>=0.21.0
```

## 参考文档

- [openclaw memory system](https://github.com/openclaw/openclaw/tree/main/src/memory)
- [SQLite FTS5](https://www.sqlite.org/fts5.html)
- [MMR Paper](http://www.cs.cmu.edu/~jgc/publication/The_Use_of_MMR_Diversity_Based_LTM_for_Information_Retrieval_1998.pdf)
