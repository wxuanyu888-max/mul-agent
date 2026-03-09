"""Checkpoint System - 检查点系统

参考 Claude Code 的检查点功能：
1. 自动保存工作点
2. 支持恢复到任意检查点
3. 支持检查工作点历史
4. 支持删除检查点
"""

import json
import time
import hashlib
from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, asdict
import threading


@dataclass
class Checkpoint:
    """检查点"""
    checkpoint_id: str
    session_id: str
    agent_id: str
    timestamp: float
    description: str = ""
    working_directory: Optional[str] = None
    git_commit: Optional[str] = None  # 关联的 git commit
    files_changed: Optional[List[str]] = None  # 变更的文件
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Checkpoint":
        return cls(**data)


class CheckpointManager:
    """检查点管理器 - 单例模式"""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._initialized = True
        self._checkpoint_dir = Path("storage/checkpoints")
        self._checkpoint_dir.mkdir(parents=True, exist_ok=True)
        self._cache: Dict[str, Checkpoint] = {}
        self._lock = threading.RLock()

    def create_checkpoint(
        self,
        session_id: str,
        agent_id: str,
        description: str = "",
        working_directory: str = None,
        files_changed: List[str] = None,
        metadata: Dict[str, Any] = None
    ) -> Checkpoint:
        """创建检查点

        Args:
            session_id: 会话 ID
            agent_id: Agent ID
            description: 检查点描述
            working_directory: 工作目录
            files_changed: 变更的文件列表
            metadata: 元数据

        Returns:
            Checkpoint: 创建的检查点
        """
        # 生成检查点 ID
        timestamp = time.time()
        checkpoint_id = hashlib.md5(
            f"{session_id}:{timestamp}:{description}".encode()
        ).hexdigest()[:12]

        # 获取当前 git commit（如果有）
        git_commit = self._get_current_git_commit()

        checkpoint = Checkpoint(
            checkpoint_id=checkpoint_id,
            session_id=session_id,
            agent_id=agent_id,
            timestamp=timestamp,
            description=description,
            working_directory=working_directory,
            git_commit=git_commit,
            files_changed=files_changed or [],
            metadata=metadata or {}
        )

        # 保存检查点
        self._save_checkpoint(checkpoint)

        return checkpoint

    def get_checkpoint(self, checkpoint_id: str) -> Optional[Checkpoint]:
        """获取检查点

        Args:
            checkpoint_id: 检查点 ID

        Returns:
            Checkpoint: 检查点，如果不存在则返回 None
        """
        # 先从缓存加载
        if checkpoint_id in self._cache:
            return self._cache[checkpoint_id]

        # 从文件加载
        checkpoint_file = self._get_checkpoint_file(checkpoint_id)
        if not checkpoint_file.exists():
            return None

        try:
            with open(checkpoint_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            checkpoint = Checkpoint.from_dict(data)

            # 缓存到内存
            with self._lock:
                self._cache[checkpoint_id] = checkpoint

            return checkpoint
        except Exception:
            return None

    def list_checkpoints(
        self,
        session_id: str = None,
        agent_id: str = None,
        limit: int = 20
    ) -> List[Checkpoint]:
        """列出检查点

        Args:
            session_id: 会话 ID 过滤
            agent_id: Agent ID 过滤
            limit: 限制数量

        Returns:
            List[Checkpoint]: 检查点列表
        """
        checkpoints = []

        for checkpoint_file in self._checkpoint_dir.glob("*.json"):
            try:
                with open(checkpoint_file, "r", encoding="utf-8") as f:
                    data = json.load(f)

                checkpoint = Checkpoint.from_dict(data)

                # 应用过滤
                if session_id and checkpoint.session_id != session_id:
                    continue
                if agent_id and checkpoint.agent_id != agent_id:
                    continue

                checkpoints.append(checkpoint)
            except Exception:
                continue

        # 按时间戳排序（最新的在前）
        checkpoints.sort(key=lambda c: c.timestamp, reverse=True)

        return checkpoints[:limit]

    def delete_checkpoint(self, checkpoint_id: str) -> bool:
        """删除检查点

        Args:
            checkpoint_id: 检查点 ID

        Returns:
            bool: 是否删除成功
        """
        try:
            with self._lock:
                checkpoint_file = self._get_checkpoint_file(checkpoint_id)

                if checkpoint_file.exists():
                    checkpoint_file.unlink()

                # 从缓存移除
                self._cache.pop(checkpoint_id, None)

                return True
        except Exception:
            return False

    def restore_checkpoint(
        self,
        checkpoint_id: str
    ) -> Optional[Dict[str, Any]]:
        """恢复检查点

        Args:
            checkpoint_id: 检查点 ID

        Returns:
            Dict: 恢复信息，如果检查点不存在则返回 None
        """
        checkpoint = self.get_checkpoint(checkpoint_id)

        if not checkpoint:
            return None

        restore_info = {
            "checkpoint_id": checkpoint_id,
            "session_id": checkpoint.session_id,
            "description": checkpoint.description,
            "timestamp": checkpoint.timestamp,
            "working_directory": checkpoint.working_directory,
            "git_commit": checkpoint.git_commit,
            "files_changed": checkpoint.files_changed,
            "restore_command": None,
        }

        # 如果有关联的 git commit，生成恢复命令
        if checkpoint.git_commit:
            restore_info["restore_command"] = f"git checkout {checkpoint.git_commit}"

        return restore_info

    def get_checkpoint_diff(self, checkpoint_id: str) -> Optional[Dict[str, Any]]:
        """获取检查点的变更

        Args:
            checkpoint_id: 检查点 ID

        Returns:
            Dict: 变更信息
        """
        checkpoint = self.get_checkpoint(checkpoint_id)

        if not checkpoint:
            return None

        diff_info = {
            "checkpoint_id": checkpoint_id,
            "files_changed": checkpoint.files_changed,
            "file_count": len(checkpoint.files_changed) if checkpoint.files_changed else 0,
        }

        # 如果可能，获取 git diff
        if checkpoint.git_commit:
            diff_info["git_diff_command"] = f"git diff {checkpoint.git_commit}~1 {checkpoint.git_commit}"

        return diff_info

    def clear_old_checkpoints(self, days: int = 7) -> int:
        """清理旧的检查点

        Args:
            days: 保留天数

        Returns:
            int: 清理的检查点数量
        """
        cleaned = 0
        cutoff_time = time.time() - (days * 24 * 60 * 60)

        for checkpoint_file in self._checkpoint_dir.glob("*.json"):
            try:
                with open(checkpoint_file, "r", encoding="utf-8") as f:
                    data = json.load(f)

                timestamp = data.get("timestamp", 0)
                if timestamp < cutoff_time:
                    checkpoint_file.unlink()
                    cleaned += 1

                    # 从缓存移除
                    checkpoint_id = data.get("checkpoint_id", "")
                    self._cache.pop(checkpoint_id, None)
            except Exception:
                continue

        return cleaned

    def get_stats(self) -> Dict[str, Any]:
        """获取检查点统计"""
        checkpoints = self.list_checkpoints(limit=1000)

        by_agent = {}
        by_session = {}

        for cp in checkpoints:
            by_agent[cp.agent_id] = by_agent.get(cp.agent_id, 0) + 1
            by_session[cp.session_id] = by_session.get(cp.session_id, 0) + 1

        return {
            "total_checkpoints": len(checkpoints),
            "by_agent": by_agent,
            "by_session": by_session,
        }

    def _save_checkpoint(self, checkpoint: Checkpoint) -> None:
        """保存检查点"""
        try:
            checkpoint_file = self._get_checkpoint_file(checkpoint.checkpoint_id)

            with open(checkpoint_file, "w", encoding="utf-8") as f:
                json.dump(checkpoint.to_dict(), f, ensure_ascii=False, indent=2)

            # 缓存到内存
            with self._lock:
                self._cache[checkpoint.checkpoint_id] = checkpoint
        except Exception as e:
            print(f"Save checkpoint error: {e}")

    def _get_checkpoint_file(self, checkpoint_id: str) -> Path:
        """获取检查点文件路径"""
        return self._checkpoint_dir / f"{checkpoint_id}.json"

    def _get_current_git_commit(self) -> Optional[str]:
        """获取当前 git commit"""
        try:
            import subprocess
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                return result.stdout.strip()[:12]
        except Exception:
            pass
        return None


# 便捷函数
def create_checkpoint(
    session_id: str,
    agent_id: str,
    description: str = "",
    **kwargs
) -> Checkpoint:
    """便捷函数：创建检查点"""
    manager = CheckpointManager()
    return manager.create_checkpoint(
        session_id, agent_id, description, **kwargs
    )


def get_checkpoint(checkpoint_id: str) -> Optional[Checkpoint]:
    """便捷函数：获取检查点"""
    manager = CheckpointManager()
    return manager.get_checkpoint(checkpoint_id)


def list_checkpoints(
    session_id: str = None,
    agent_id: str = None,
    limit: int = 20
) -> List[Checkpoint]:
    """便捷函数：列出检查点"""
    manager = CheckpointManager()
    return manager.list_checkpoints(session_id, agent_id, limit)


def restore_checkpoint(checkpoint_id: str) -> Optional[Dict[str, Any]]:
    """便捷函数：恢复检查点"""
    manager = CheckpointManager()
    return manager.restore_checkpoint(checkpoint_id)


def delete_checkpoint(checkpoint_id: str) -> bool:
    """便捷函数：删除检查点"""
    manager = CheckpointManager()
    return manager.delete_checkpoint(checkpoint_id)


# 全局实例
checkpoint_manager = CheckpointManager()
