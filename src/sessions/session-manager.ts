/**
 * Session Manager - 会话管理器
 *
 * 负责：
 * 1. 创建和管理会话生命周期
 * 2. 会话上下文存储与检索
 * 3. 会话 Token 阈值管理
 * 4. 会话压缩触发
 */

import fs from 'node:fs/promises';
import path from 'node:path';
import { EventEmitter } from 'node:events';
import { v4 as uuidv4 } from 'uuid';

// ============================================================================
// 类型定义
// ============================================================================

export type SessionRole = 'user' | 'assistant' | 'system';

export interface SessionMessage {
  id: string;
  role: SessionRole;
  content: string;
  timestamp: number;
  metadata?: Record<string, unknown>;
}

export interface SessionContext {
  id: string;
  agentId: string;
  title?: string;
  messages: SessionMessage[];
  createdAt: number;
  updatedAt: number;
  tokenCount: number;
  bootstrapTokenCount: number;
  needsCompression: boolean;
  compressionReason?: string;
  metadata?: Record<string, unknown>;
}

export interface TokenThreshold {
  sessionWarning: number;      // Session 警告阈值
  sessionMax: number;          // Session 最大阈值
  bootstrapWarning: number;    // Bootstrap 警告阈值
  bootstrapMax: number;        // Bootstrap 最大阈值
  compressionTarget: number;   // 压缩后目标 token 数
}

export interface SessionManagerOptions {
  storagePath?: string;
  thresholds?: Partial<TokenThreshold>;
  defaultAgentId?: string;
}

// ============================================================================
// Token 估算工具
// ============================================================================

/**
 * 估算文本的 token 数量
 *
 * 使用简单的估算方法：
 * - 英文：约 4 个字符 = 1 token
 * - 中文：约 1.5 个字符 = 1 token
 */
export function estimateTokens(text: string): number {
  if (!text) return 0;

  // 检测中英文比例
  const chineseChars = Array.from(text).filter(c => /[\u4e00-\u9fff]/.test(c)).length;
  const otherChars = text.length - chineseChars;

  // 中文约 1.5 字符/token，英文约 4 字符/token
  return Math.floor(chineseChars / 1.5 + otherChars / 4);
}

// ============================================================================
// 默认配置
// ============================================================================

const DEFAULT_THRESHOLDS: TokenThreshold = {
  sessionWarning: 8000,
  sessionMax: 16000,
  bootstrapWarning: 4000,
  bootstrapMax: 8000,
  compressionTarget: 3000,
};

const DEFAULT_OPTIONS: Required<Omit<SessionManagerOptions, 'defaultAgentId'>> = {
  storagePath: 'storage/sessions',
  thresholds: DEFAULT_THRESHOLDS,
};

// ============================================================================
// SessionManager 类
// ============================================================================

export class SessionManager extends EventEmitter {
  private storagePath: string;
  private thresholds: TokenThreshold;
  private contextCache: Map<string, SessionContext>;
  private defaultAgentId?: string;

  constructor(options: SessionManagerOptions = {}) {
    super();
    const opts = { ...DEFAULT_OPTIONS, ...options };
    this.storagePath = this.resolveStoragePath(opts.storagePath);
    this.thresholds = { ...DEFAULT_THRESHOLDS, ...opts.thresholds };
    this.contextCache = new Map();
    this.defaultAgentId = options.defaultAgentId;
  }

  /**
   * 解析存储路径（支持 ~ 展开）
   */
  private resolveStoragePath(storagePath: string): string {
    if (storagePath.startsWith('~')) {
      const home = process.env.HOME || process.env.USERPROFILE || '';
      return path.join(home, storagePath.slice(1));
    }
    if (!path.isAbsolute(storagePath)) {
      return path.resolve(process.cwd(), storagePath);
    }
    return storagePath;
  }

  /**
   * 获取会话存储路径
   */
  getSessionPath(agentId: string, sessionId: string): string {
    const sessionPath = path.join(this.storagePath, agentId, sessionId);
    return sessionPath;
  }

  /**
   * 确保会话目录存在
   */
  private async ensureSessionDir(agentId: string, sessionId: string): Promise<string> {
    const sessionPath = this.getSessionPath(agentId, sessionId);
    await fs.mkdir(sessionPath, { recursive: true });
    return sessionPath;
  }

  /**
   * 加载会话上下文
   */
  async loadSession(
    sessionId: string,
    agentId?: string,
    maxMessages?: number
  ): Promise<SessionContext> {
    const effectiveAgentId = agentId || this.defaultAgentId || 'default';
    const cacheKey = `${effectiveAgentId}:${sessionId}`;

    // 检查缓存
    if (this.contextCache.has(cacheKey)) {
      const cached = this.contextCache.get(cacheKey)!;
      return this.applyMaxMessages(cached, maxMessages);
    }

    // 从文件系统加载
    const sessionPath = this.getSessionPath(effectiveAgentId, sessionId);
    const context: SessionContext = {
      id: sessionId,
      agentId: effectiveAgentId,
      messages: [],
      createdAt: Date.now(),
      updatedAt: Date.now(),
      tokenCount: 0,
      bootstrapTokenCount: 0,
      needsCompression: false,
    };

    try {
      // 加载对话历史
      const historyFile = path.join(sessionPath, 'history.jsonl');
      const historyContent = await fs.readFile(historyFile, 'utf-8');
      const lines = historyContent.split('\n').filter(line => line.trim());

      context.messages = lines.map(line => JSON.parse(line));

      // 应用消息数量限制
      if (maxMessages && context.messages.length > maxMessages) {
        context.messages = context.messages.slice(-maxMessages);
      }

      // 加载 bootstrap 内容
      const bootstrapFile = path.join(sessionPath, 'bootstrap.json');
      try {
        const bootstrapContent = await fs.readFile(bootstrapFile, 'utf-8');
        context.metadata = { ...context.metadata, bootstrap: JSON.parse(bootstrapContent) };
      } catch {
        // bootstrap 文件不存在，忽略
      }

      // 加载元数据
      const metaFile = path.join(sessionPath, 'context_meta.json');
      try {
        const metaContent = await fs.readFile(metaFile, 'utf-8');
        const meta = JSON.parse(metaContent);
        context.title = meta.title;
        context.createdAt = meta.createdAt || context.createdAt;
        context.updatedAt = meta.updatedAt || context.updatedAt;
      } catch {
        // 元数据文件不存在，忽略
      }

    } catch (error) {
      // 会话不存在，返回空上下文
      if ((error as NodeJS.ErrnoException).code !== 'ENOENT') {
        throw error;
      }
    }

    // 计算 token 数
    this.updateTokenCounts(context);

    // 检查是否需要压缩
    this.checkCompressionNeeded(context);

    // 缓存
    this.contextCache.set(cacheKey, context);

    return context;
  }

  /**
   * 创建新会话
   */
  async createSession(
    options: {
      sessionId?: string;
      agentId?: string;
      title?: string;
      initialMessages?: SessionMessage[];
      metadata?: Record<string, unknown>;
    } = {}
  ): Promise<SessionContext> {
    const sessionId = options.sessionId || uuidv4();
    const agentId = options.agentId || this.defaultAgentId || 'default';
    const cacheKey = `${agentId}:${sessionId}`;

    const context: SessionContext = {
      id: sessionId,
      agentId,
      title: options.title,
      messages: options.initialMessages || [],
      createdAt: Date.now(),
      updatedAt: Date.now(),
      tokenCount: 0,
      bootstrapTokenCount: 0,
      needsCompression: false,
      metadata: options.metadata,
    };

    // 计算初始 token 数
    this.updateTokenCounts(context);

    // 持久化
    await this.saveSession(context);

    // 缓存
    this.contextCache.set(cacheKey, context);

    // 触发事件
    this.emit('session:created', context);

    return context;
  }

  /**
   * 添加消息到会话
   */
  async addMessage(
    sessionId: string,
    role: SessionRole,
    content: string,
    options: {
      agentId?: string;
      metadata?: Record<string, unknown>;
    } = {}
  ): Promise<SessionContext> {
    const agentId = options.agentId || this.defaultAgentId || 'default';
    const context = await this.loadSession(sessionId, agentId);

    // 添加消息
    const message: SessionMessage = {
      id: uuidv4(),
      role,
      content,
      timestamp: Date.now(),
      metadata: options.metadata,
    };
    context.messages.push(message);
    context.updatedAt = Date.now();

    // 更新 token 计数
    this.updateTokenCounts(context);

    // 检查是否需要压缩
    this.checkCompressionNeeded(context);

    // 持久化
    await this.saveSession(context);

    return context;
  }

  /**
   * 更新会话元数据
   */
  async updateSessionMetadata(
    sessionId: string,
    updates: {
      title?: string;
      metadata?: Record<string, unknown>;
      agentId?: string;
    },
    agentId?: string
  ): Promise<SessionContext> {
    const effectiveAgentId = agentId || this.defaultAgentId || 'default';
    const context = await this.loadSession(sessionId, effectiveAgentId);

    if (updates.title !== undefined) {
      context.title = updates.title;
    }
    if (updates.metadata !== undefined) {
      context.metadata = { ...context.metadata, ...updates.metadata };
    }
    context.updatedAt = Date.now();

    await this.saveSession(context);
    return context;
  }

  /**
   * 删除会话
   */
  async deleteSession(sessionId: string, agentId?: string): Promise<void> {
    const effectiveAgentId = agentId || this.defaultAgentId || 'default';
    const cacheKey = `${effectiveAgentId}:${sessionId}`;
    const sessionPath = this.getSessionPath(effectiveAgentId, sessionId);

    try {
      await fs.rm(sessionPath, { recursive: true, force: true });
    } catch (error) {
      if ((error as NodeJS.ErrnoException).code !== 'ENOENT') {
        throw error;
      }
    }

    // 清除缓存
    this.contextCache.delete(cacheKey);

    // 触发事件
    this.emit('session:deleted', { sessionId, agentId: effectiveAgentId });
  }

  /**
   * 列出所有会话
   */
  async listSessions(agentId?: string): Promise<SessionContext[]> {
    const effectiveAgentId = agentId || this.defaultAgentId || 'default';
    const agentPath = path.join(this.storagePath, effectiveAgentId);
    const sessions: SessionContext[] = [];

    try {
      const entries = await fs.readdir(agentPath, { withFileTypes: true });
      for (const entry of entries) {
        if (entry.isDirectory()) {
          try {
            const context = await this.loadSession(entry.name, effectiveAgentId);
            sessions.push(context);
          } catch {
            // 跳过无法加载的会话
          }
        }
      }
    } catch (error) {
      if ((error as NodeJS.ErrnoException).code !== 'ENOENT') {
        throw error;
      }
    }

    // 按更新时间排序
    sessions.sort((a, b) => b.updatedAt - a.updatedAt);

    return sessions;
  }

  /**
   * 获取压缩提示
   */
  getCompressionHint(context: SessionContext): CompressionHint {
    if (!context.needsCompression) {
      return {
        needsCompression: false,
        hint: null,
      };
    }

    // 判断压缩类型
    const compressionType = context.bootstrapTokenCount >= this.thresholds.bootstrapWarning
      ? 'bootstrap'
      : 'session';

    return {
      needsCompression: true,
      type: compressionType,
      currentTokens: {
        session: context.tokenCount,
        bootstrap: context.bootstrapTokenCount,
      },
      targetTokens: this.thresholds.compressionTarget,
      reason: context.compressionReason,
      prompt: this.buildCompressionPrompt(context, compressionType),
    };
  }

  // ============================================================================
  // 私有方法
  // ============================================================================

  /**
   * 应用消息数量限制
   */
  private applyMaxMessages(context: SessionContext, maxMessages?: number): SessionContext {
    if (!maxMessages || context.messages.length <= maxMessages) {
      return context;
    }
    return {
      ...context,
      messages: context.messages.slice(-maxMessages),
    };
  }

  /**
   * 更新 Token 计数
   */
  private updateTokenCounts(context: SessionContext): void {
    // 计算 session token
    let sessionTokens = 0;
    for (const msg of context.messages) {
      sessionTokens += estimateTokens(msg.content);
    }
    context.tokenCount = sessionTokens;

    // 计算 bootstrap token
    const bootstrapContent = context.metadata?.bootstrap;
    if (bootstrapContent) {
      const bootstrapText = JSON.stringify(bootstrapContent, null, 2);
      context.bootstrapTokenCount = estimateTokens(bootstrapText);
    } else {
      context.bootstrapTokenCount = 0;
    }
  }

  /**
   * 检查是否需要压缩
   */
  private checkCompressionNeeded(context: SessionContext): void {
    const reasons: string[] = [];

    // 检查 session token
    if (context.tokenCount >= this.thresholds.sessionMax) {
      context.needsCompression = true;
      reasons.push(`Session tokens (${context.tokenCount}) exceed max (${this.thresholds.sessionMax})`);
    } else if (context.tokenCount >= this.thresholds.sessionWarning) {
      context.needsCompression = true;
      context.compressionReason = `Session tokens (${context.tokenCount}) approaching max`;
      return;
    }

    // 检查 bootstrap token
    if (context.bootstrapTokenCount >= this.thresholds.bootstrapMax) {
      context.needsCompression = true;
      reasons.push(`Bootstrap tokens (${context.bootstrapTokenCount}) exceed max (${this.thresholds.bootstrapMax})`);
    } else if (context.bootstrapTokenCount >= this.thresholds.bootstrapWarning) {
      context.needsCompression = true;
      reasons.push(`Bootstrap tokens (${context.bootstrapTokenCount}) approaching max`);
    }

    if (reasons.length > 0) {
      context.compressionReason = reasons.join('; ');
    }
  }

  /**
   * 保存会话到磁盘
   */
  private async saveSession(context: SessionContext): Promise<void> {
    const sessionPath = await this.ensureSessionDir(context.agentId, context.id);

    // 保存对话历史
    const historyFile = path.join(sessionPath, 'history.jsonl');
    const historyContent = context.messages
      .map(msg => JSON.stringify(msg, null, 2))
      .join('\n');
    await fs.writeFile(historyFile, historyContent, 'utf-8');

    // 保存 bootstrap 内容
    if (context.metadata?.bootstrap) {
      const bootstrapFile = path.join(sessionPath, 'bootstrap.json');
      await fs.writeFile(
        bootstrapFile,
        JSON.stringify(context.metadata.bootstrap, null, 2),
        'utf-8'
      );
    }

    // 保存元数据
    const metaFile = path.join(sessionPath, 'context_meta.json');
    const meta = {
      title: context.title,
      agentId: context.agentId,
      sessionId: context.id,
      tokenCount: context.tokenCount,
      bootstrapTokenCount: context.bootstrapTokenCount,
      needsCompression: context.needsCompression,
      compressionReason: context.compressionReason,
      createdAt: context.createdAt,
      updatedAt: context.updatedAt,
      messageCount: context.messages.length,
    };
    await fs.writeFile(metaFile, JSON.stringify(meta, null, 2), 'utf-8');
  }

  /**
   * 构建压缩提示词
   */
  private buildCompressionPrompt(
    context: SessionContext,
    compressionType: 'session' | 'bootstrap'
  ): string {
    if (compressionType === 'bootstrap') {
      return `【压缩请求】Bootstrap 内容接近 token 上限

当前 Bootstrap Token 数：${context.bootstrapTokenCount}
最大允许：${this.thresholds.bootstrapMax}
警告阈值：${this.thresholds.bootstrapWarning}

请将旧的 bootstrap 内容压缩存档到 memory 系统，并更新 bootstrap 为精简版本。

压缩要求：
1. 保留最关键的上下文信息
2. 将详细信息存档到 memory
3. 压缩后目标 token 数：${this.thresholds.compressionTarget}

当前 bootstrap 内容摘要：
${JSON.stringify(context.metadata?.bootstrap || {}, null, 2).slice(0, 500)}...
`;
    }

    // Session 压缩
    const recentMessages = context.messages.length > 10
      ? context.messages.slice(-10)
      : context.messages;
    const earlyMessages = context.messages.length > 10
      ? context.messages.slice(0, -10)
      : [];

    return `【压缩请求】会话内容接近 token 上限

当前 Session Token 数：${context.tokenCount}
最大允许：${this.thresholds.sessionMax}
警告阈值：${this.thresholds.sessionWarning}

请压缩早期对话历史，保留最近消息完整。

压缩要求：
1. 将早期对话（前 ${earlyMessages.length} 条）压缩为摘要
2. 保留最近 ${recentMessages.length} 条消息完整
3. 将压缩摘要存档到 memory 系统
4. 压缩后目标 token 数：${this.thresholds.compressionTarget}

最近消息预览：
${recentMessages.slice(0, 5).map(m => `- [${m.role}] ${m.content.slice(0, 100)}...`).join('\n')}
`;
  }
}

// ============================================================================
// 辅助类型
// ============================================================================

export interface CompressionHint {
  needsCompression: boolean;
  type?: 'session' | 'bootstrap';
  currentTokens?: {
    session: number;
    bootstrap: number;
  };
  targetTokens?: number;
  reason?: string;
  prompt?: string;
}
