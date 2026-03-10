/**
 * Session API Routes - 会话 API 路由
 *
 * 提供 RESTful API 用于管理会话：
 * - GET    /sessions          - 列出所有会话
 * - GET    /sessions/:id      - 获取会话详情
 * - POST   /sessions          - 创建新会话
 * - DELETE /sessions/:id      - 删除会话
 * - GET    /sessions/:id/history - 获取会话历史
 * - POST   /sessions/:id/compress - 压缩会话
 */

import { Router, Request, Response } from 'express';
import { SessionManager, type SessionContext } from './session-manager.js';

// ============================================================================
// 类型定义
// ============================================================================

interface SessionRequest extends Request {
  sessionManager?: SessionManager;
}

interface CreateSessionBody {
  sessionId?: string;
  agentId?: string;
  title?: string;
  initialMessages?: Array<{
    role: 'user' | 'assistant' | 'system';
    content: string;
    metadata?: Record<string, unknown>;
  }>;
  metadata?: Record<string, unknown>;
}

interface AddMessageBody {
  role: 'user' | 'assistant' | 'system';
  content: string;
  metadata?: Record<string, unknown>;
}

interface UpdateMetadataBody {
  title?: string;
  metadata?: Record<string, unknown>;
}

// ============================================================================
// 响应格式
// ============================================================================

interface SuccessResponse<T> {
  success: true;
  data: T;
}

interface ErrorResponse {
  success: false;
  error: string;
  code?: string;
}

type ApiResponse<T> = SuccessResponse<T> | ErrorResponse;

function successResponse<T>(data: T): SuccessResponse<T> {
  return { success: true, data };
}

function errorResponse(error: string, code?: string): ErrorResponse {
  return { success: false, error, code };
}

// ============================================================================
// 路由工厂
// ============================================================================

export function createSessionRoutes(sessionManager: SessionManager): Router {
  const router = Router();

  // 中间件：注入 sessionManager
  router.use((req: Request, _res: Response, next) => {
    (req as SessionRequest).sessionManager = sessionManager;
    next();
  });

  /**
   * GET /sessions
   * 列出所有会话
   *
   * Query Parameters:
   * - agentId?: string - 按 agent ID 过滤
   * - limit?: number - 返回数量限制
   */
  router.get('/', async (req: Request, res: Response) => {
    try {
      const sm = (req as SessionRequest).sessionManager!;
      const { agentId, limit } = req.query;

      let sessions = await sm.listFiles(agentId as string | undefined);

      // 应用限制
      if (limit) {
        const limitNum = parseInt(limit as string, 10);
        if (!isNaN(limitNum) && limitNum > 0) {
          sessions = sessions.slice(0, limitNum);
        }
      }

      // 简化响应（移除消息内容）
      const summarySessions = sessions.map(s => ({
        id: s.id,
        agentId: s.agentId,
        title: s.title,
        createdAt: s.createdAt,
        updatedAt: s.updatedAt,
        tokenCount: s.tokenCount,
        messageCount: s.messages.length,
        needsCompression: s.needsCompression,
      }));

      res.json(successResponse(summarySessions));
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Unknown error';
      res.status(500).json(errorResponse(message, 'INTERNAL_ERROR'));
    }
  });

  /**
   * GET /sessions/:id
   * 获取会话详情
   */
  router.get('/:id', async (req: Request, res: Response) => {
    try {
      const sm = (req as SessionRequest).sessionManager!;
      const { id } = req.params;
      const { agentId, maxMessages } = req.query;

      const session = await sm.loadSession(
        id,
        agentId as string | undefined,
        maxMessages ? parseInt(maxMessages as string, 10) : undefined
      );

      if (!session) {
        res.status(404).json(errorResponse('Session not found', 'NOT_FOUND'));
        return;
      }

      res.json(successResponse(session));
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Unknown error';
      res.status(500).json(errorResponse(message, 'INTERNAL_ERROR'));
    }
  });

  /**
   * POST /sessions
   * 创建新会话
   */
  router.post('/', async (req: Request, res: Response) => {
    try {
      const sm = (req as SessionRequest).sessionManager!;
      const body = req.body as CreateSessionBody;

      const session = await sm.createSession({
        sessionId: body.sessionId,
        agentId: body.agentId,
        title: body.title,
        initialMessages: body.initialMessages,
        metadata: body.metadata,
      });

      res.status(201).json(successResponse(session));
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Unknown error';
      res.status(500).json(errorResponse(message, 'INTERNAL_ERROR'));
    }
  });

  /**
   * DELETE /sessions/:id
   * 删除会话
   */
  router.delete('/:id', async (req: Request, res: Response) => {
    try {
      const sm = (req as SessionRequest).sessionManager!;
      const { id } = req.params;
      const { agentId } = req.query;

      await sm.deleteSession(id, agentId as string | undefined);

      res.json(successResponse({ deleted: true, sessionId: id }));
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Unknown error';
      res.status(500).json(errorResponse(message, 'INTERNAL_ERROR'));
    }
  });

  /**
   * GET /sessions/:id/history
   * 获取会话历史消息
   */
  router.get('/:id/history', async (req: Request, res: Response) => {
    try {
      const sm = (req as SessionRequest).sessionManager!;
      const { id } = req.params;
      const { agentId, limit, includeTools } = req.query;

      const session = await sm.loadSession(
        id,
        agentId as string | undefined,
        limit ? parseInt(limit as string, 10) : undefined
      );

      let messages = session.messages;

      // 过滤工具消息
      if (includeTools === 'false') {
        messages = messages.filter(m => m.role !== 'tool');
      }

      res.json(successResponse({
        sessionId: id,
        messages,
        totalCount: session.messages.length,
        tokenCount: session.tokenCount,
      }));
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Unknown error';
      res.status(500).json(errorResponse(message, 'INTERNAL_ERROR'));
    }
  });

  /**
   * POST /sessions/:id/messages
   * 添加消息到会话
   */
  router.post('/:id/messages', async (req: Request, res: Response) => {
    try {
      const sm = (req as SessionRequest).sessionManager!;
      const { id } = req.params;
      const { agentId } = req.query;
      const body = req.body as AddMessageBody;

      if (!body.role || !body.content) {
        res.status(400).json(errorResponse('role and content are required', 'INVALID_REQUEST'));
        return;
      }

      const session = await sm.addMessage(
        id,
        body.role,
        body.content,
        {
          agentId: agentId as string | undefined,
          metadata: body.metadata,
        }
      );

      res.json(successResponse({
        sessionId: id,
        messageCount: session.messages.length,
        tokenCount: session.tokenCount,
        needsCompression: session.needsCompression,
        compressionReason: session.compressionReason,
      }));
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Unknown error';
      res.status(500).json(errorResponse(message, 'INTERNAL_ERROR'));
    }
  });

  /**
   * PUT /sessions/:id/metadata
   * 更新会话元数据
   */
  router.put('/:id/metadata', async (req: Request, res: Response) => {
    try {
      const sm = (req as SessionRequest).sessionManager!;
      const { id } = req.params;
      const { agentId } = req.query;
      const body = req.body as UpdateMetadataBody;

      const session = await sm.updateSessionMetadata(
        id,
        {
          title: body.title,
          metadata: body.metadata,
        },
        agentId as string | undefined
      );

      res.json(successResponse(session));
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Unknown error';
      res.status(500).json(errorResponse(message, 'INTERNAL_ERROR'));
    }
  });

  /**
   * POST /sessions/:id/compress
   * 获取压缩提示
   */
  router.post('/:id/compress', async (req: Request, res: Response) => {
    try {
      const sm = (req as SessionRequest).sessionManager!;
      const { id } = req.params;
      const { agentId } = req.query;

      const session = await sm.loadSession(id, agentId as string | undefined);
      const hint = sm.getCompressionHint(session);

      res.json(successResponse(hint));
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Unknown error';
      res.status(500).json(errorResponse(message, 'INTERNAL_ERROR'));
    }
  });

  return router;
}

// ============================================================================
// Express 应用集成示例
// ============================================================================

/*
import express from 'express';
import { SessionManager } from './session-manager.js';
import { createSessionRoutes } from './session-routes.js';

const app = express();
app.use(express.json());

// 创建 SessionManager 实例
const sessionManager = new SessionManager({
  storagePath: 'storage/sessions',
  defaultAgentId: 'default',
});

// 注册路由
app.use('/api/sessions', createSessionRoutes(sessionManager));

// 监听事件
sessionManager.on('session:created', (ctx) => {
  console.log(`Session created: ${ctx.id}`);
});

sessionManager.on('session:deleted', ({ sessionId }) => {
  console.log(`Session deleted: ${sessionId}`);
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
  console.log(`Session API: http://localhost:${PORT}/api/sessions`);
});
*/
