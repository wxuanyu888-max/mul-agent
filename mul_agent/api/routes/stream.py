"""Stream Routes - 流式输出 API 端点

提供 SSE (Server-Sent Events) 端点，让前端实时接收 Agent 执行进度

使用方式:
    GET /api/v1/stream/{session_id}

    返回 SSE 格式:
    event: stream
    data: {"type": "execution_progress", "data": {...}}
"""

import json
import time
import asyncio
from typing import AsyncGenerator
from pathlib import Path

try:
    from fastapi import APIRouter, Request
    from fastapi.responses import StreamingResponse
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False

from mul_agent.brain.stream import stream_manager, StreamEvent


router = APIRouter(prefix="/stream", tags=["stream"])


async def stream_generator(session_id: str, request: Request = None) -> AsyncGenerator[str, None]:
    """SSE 流生成器

    Args:
        session_id: 会话 ID
        request: FastAPI 请求对象（用于检测断开）

    Yields:
        SSE 格式的事件数据
    """
    # 发送初始连接确认
    yield f"event: connected\ndata: {json.dumps({'session_id': session_id, 'status': 'connected'})}\n\n"

    # 读取已有的事件
    state_dir = Path("storage/stream_states")
    state_file = state_dir / f"{session_id.replace('-', '_')[:32]}.jsonl"

    last_sequence = -1
    if state_file.exists():
        with open(state_file, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    event_data = json.loads(line.strip())
                    seq = event_data.get("sequence", 0)
                    if seq > last_sequence:
                        last_sequence = seq
                        yield f"event: stream\ndata: {json.dumps(event_data, ensure_ascii=False)}\n\n"
                except json.JSONDecodeError:
                    continue

    # 持续轮询新事件
    while True:
        # 检查客户端是否断开
        if request and await request.is_disconnected():
            break

        # 读取新事件
        if state_file.exists():
            with open(state_file, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        event_data = json.loads(line.strip())
                        seq = event_data.get("sequence", 0)
                        if seq > last_sequence:
                            last_sequence = seq
                            yield f"event: stream\ndata: {json.dumps(event_data, ensure_ascii=False)}\n\n"
                    except json.JSONDecodeError:
                        continue

        # 等待一段时间后继续轮询
        await asyncio.sleep(0.1)


if FASTAPI_AVAILABLE:
    @router.get("/{session_id}")
    async def stream_endpoint(session_id: str, request: Request):
        """SSE 流端点

        客户端订阅此端点接收实时事件：
        ```javascript
        const evtSource = new EventSource('/api/v1/stream/' + sessionId);
        evtSource.onmessage = (event) => {
            const data = JSON.parse(event.data);
            console.log('Event:', data.type, data.data);
        };
        ```
        """
        return StreamingResponse(
            stream_generator(session_id, request),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"  # 禁用 Nginx 缓冲
            }
        )

    @router.get("/{session_id}/latest")
    async def get_latest_state(session_id: str):
        """获取最新状态（非流式）"""
        state = stream_manager.get_latest_state(session_id)
        if state:
            return {"status": "success", "data": state}
        return {"status": "not_found", "message": "No state found for session"}

    @router.post("/{session_id}/clear")
    async def clear_session_state(session_id: str):
        """清除会话状态"""
        stream_manager.clear_session(session_id)
        return {"status": "success", "message": "Session cleared"}

else:
    # FastAPI 不可用时，提供简单的 HTTP 处理器
    @router.get("/{session_id}/latest")
    async def get_latest_state(session_id: str):
        """获取最新状态"""
        state = stream_manager.get_latest_state(session_id)
        if state:
            return {"status": "success", "data": state}
        return {"status": "not_found", "message": "No state found for session"}


# 帮助函数 - 在非 FastAPI 环境中使用
def create_stream_endpoint_handler(session_id: str):
    """创建流端点处理器（用于内置 http.server）

    使用示例:
        from http.server import HTTPServer, BaseHTTPRequestHandler
        from mul_agent.brain.stream_routes import create_stream_endpoint_handler

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                if self.path.startswith('/stream/'):
                    session_id = self.path.split('/')[-1]
                    handler = create_stream_endpoint_handler(session_id)
                    handler(self)
                else:
                    super().do_GET()
    """
    def handler(request_handler):
        request_handler.send_response(200)
        request_handler.send_header("Content-type", "text/event-stream")
        request_handler.send_header("Cache-Control", "no-cache")
        request_handler.send_header("Connection", "keep-alive")
        request_handler.end_headers()

        try:
            state_dir = Path("storage/stream_states")
            state_file = state_dir / f"{session_id.replace('-', '_')[:32]}.jsonl"

            last_sequence = -1
            while True:
                if state_file.exists():
                    with open(state_file, "r", encoding="utf-8") as f:
                        for line in f:
                            try:
                                event_data = json.loads(line.strip())
                                seq = event_data.get("sequence", 0)
                                if seq > last_sequence:
                                    last_sequence = seq
                                    request_handler.wfile.write(
                                        f"event: stream\ndata: {json.dumps(event_data)}\n\n".encode()
                                    )
                                    request_handler.wfile.flush()
                            except json.JSONDecodeError:
                                continue

                time.sleep(0.1)
        except (BrokenPipeError, ConnectionResetError):
            pass  # 客户端断开连接

    return handler
