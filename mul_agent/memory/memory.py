"""Memory System"""

import json
import hashlib
import os
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List, Optional


class Memory:
    """记忆管理系统"""

    def __init__(self, agent_id: str, config: Dict):
        self.agent_id = agent_id
        self.config = config

        # Get paths from config - use absolute path based on project root
        base_dir = Path(__file__).parent.parent.parent / "storage" / "memory"

        # Base paths (without agent_id - added in _get_path)
        self.short_term_path = base_dir / "short_term"
        self.long_term_path = base_dir / "long_term"
        self.handover_path = base_dir / "handover"

        # Create directories
        self.short_term_path.mkdir(parents=True, exist_ok=True)
        self.long_term_path.mkdir(parents=True, exist_ok=True)
        self.handover_path.mkdir(parents=True, exist_ok=True)

    def _format_content(self, content: Any) -> str:
        """格式化内容为可读文本"""
        if isinstance(content, dict):
            lines = []
            for k, v in content.items():
                lines.append(f"- **{k}**: {v}")
            return "\n".join(lines)
        elif isinstance(content, list):
            return "\n".join(f"- {item}" for item in content)
        else:
            return str(content)

    def _parse_md_file(self, filepath: Path) -> Optional[Dict]:
        """解析 Markdown 记忆文件"""
        if not filepath.exists():
            return None

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()

            # 解析 YAML front matter
            import re
            yaml_match = re.match(r'^---\n(.*?)\n---', content, re.DOTALL)

            if not yaml_match:
                return None

            metadata = {}
            yaml_content = yaml_match.group(1)
            for line in yaml_content.strip().split('\n'):
                line = line.strip()
                if ':' in line:
                    key, value = line.split(':', 1)
                    metadata[key.strip()] = value.strip()

            # 提取内容（YAML front matter 之后的部分）
            body_start = yaml_match.end()
            body = content[body_start:].strip()

            return {
                "id": metadata.get("id", ""),
                "agent_id": metadata.get("agent_id", ""),
                "type": metadata.get("type", ""),
                "timestamp": metadata.get("timestamp", ""),
                "content": body
            }
        except Exception:
            return None

    def write(self, memory_type: str, content: Dict[str, Any]) -> str:
        """写入记忆"""
        timestamp = datetime.now().isoformat()
        memory_id = self._generate_id(content, timestamp)

        # Determine storage path - 使用 .md 格式
        path = self._get_path(memory_type)
        filepath = path / f"{memory_id}.md"

        # 构建 Markdown 内容
        lines = ["---"]
        lines.append(f"id: {memory_id}")
        lines.append(f"agent_id: {self.agent_id}")
        lines.append(f"type: {memory_type}")
        lines.append(f"timestamp: {timestamp}")
        lines.append("---\n")

        lines.append(f"# 记忆\n")
        lines.append(self._format_content(content))

        with open(filepath, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        return memory_id

    def read(self, memory_type: str, memory_id: Optional[str] = None) -> Optional[Dict]:
        """读取记忆"""
        if memory_id:
            path = self._get_path(memory_type) / f"{memory_id}.md"
            return self._parse_md_file(path)

        # Return latest if no id specified
        path = self._get_path(memory_type)
        files = sorted(path.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True)

        if files:
            return self._parse_md_file(files[0])
        return None

    def update(self, memory_id: str, content: Dict[str, Any]) -> bool:
        """更新记忆"""
        # Try all types
        for memory_type in ["short_term", "long_term", "handover"]:
            path = self._get_path(memory_type) / f"{memory_id}.md"
            if path.exists():
                # Read existing metadata
                memory = self._parse_md_file(path)
                if not memory:
                    return False

                # Rebuild MD file with new content
                timestamp = datetime.now().isoformat()
                memory_id = memory.get("id", memory_id)

                lines = ["---"]
                lines.append(f"id: {memory_id}")
                lines.append(f"agent_id: {self.agent_id}")
                lines.append(f"type: {memory_type}")
                lines.append(f"timestamp: {timestamp}")
                lines.append("---\n")

                lines.append(f"# 记忆\n")
                lines.append(self._format_content(content))

                with open(path, "w", encoding="utf-8") as f:
                    f.write("\n".join(lines))
                return True
        return False

    def delete(self, memory_id: str) -> bool:
        """删除记忆"""
        for memory_type in ["short_term", "long_term", "handover"]:
            path = self._get_path(memory_type) / f"{memory_id}.md"
            if path.exists():
                path.unlink()
                return True
        return False

    def list_memories(self, memory_type: str, limit: int = 10) -> List[Dict]:
        """列出记忆"""
        path = self._get_path(memory_type)
        files = sorted(path.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True)

        memories = []
        for f in files[:limit]:
            memory = self._parse_md_file(f)
            if memory:
                memories.append(memory)

        return memories

    def get_recent(self, memory_type: Optional[str] = None, limit: int = 10) -> List[Dict]:
        """获取最近的记忆"""
        if memory_type:
            return self.list_memories(memory_type, limit)

        # Get from all types
        all_memories = []
        for mt in ["short_term", "long_term", "handover"]:
            all_memories.extend(self.list_memories(mt, limit))

        # Sort by timestamp
        all_memories.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        return all_memories[:limit]

    def search(self, query: str, memory_type: Optional[str] = None) -> List[Dict]:
        """搜索记忆"""
        results = []

        types = [memory_type] if memory_type else ["short_term", "long_term", "handover"]

        for mt in types:
            for memory_file in self._get_path(mt).glob("*.md"):
                try:
                    memory = self._parse_md_file(memory_file)
                    if memory:
                        # Search in content
                        content = memory.get("content", "")
                        if query.lower() in content.lower():
                            results.append(memory)
                except Exception:
                    continue

        return results

    def create_handover(self, from_agent: str, to_agent: str, content: Dict[str, Any]) -> str:
        """创建交接文档"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        handover_id = f"handover_{from_agent}_{to_agent}_{timestamp}"
        timestamp_iso = datetime.now().isoformat()

        # 构建 Markdown 内容
        lines = ["---"]
        lines.append(f"id: {handover_id}")
        lines.append(f"from_agent: {from_agent}")
        lines.append(f"to_agent: {to_agent}")
        lines.append(f"timestamp: {timestamp_iso}")
        lines.append(f"status: pending")
        lines.append("---\n")

        lines.append(f"# 交接文档\n")
        lines.append(self._format_content(content))

        filepath = self.handover_path / f"{handover_id}.md"
        with open(filepath, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        return handover_id

    def read_handover(self, handover_id: str) -> Optional[Dict]:
        """读取交接文档"""
        filepath = self.handover_path / f"{handover_id}.md"
        return self._parse_md_file(filepath)

    def list_handoffs(self, agent_id: Optional[str] = None) -> List[Dict]:
        """列出交接文档"""
        handoffs = []
        for handoff_file in self.handover_path.glob("*.md"):
            handoff = self._parse_md_file(handoff_file)
            if handoff and (agent_id is None or handoff.get("from_agent") == agent_id or handoff.get("to_agent") == agent_id):
                handoffs.append(handoff)
        return sorted(handoffs, key=lambda x: x.get("timestamp", ""), reverse=True)

    def _get_path(self, memory_type: str) -> Path:
        """获取记忆存储路径"""
        if memory_type == "short_term":
            path = self.short_term_path / self.agent_id
        elif memory_type == "long_term":
            path = self.long_term_path / self.agent_id
        elif memory_type == "handover":
            path = self.handover_path
        else:
            path = self.short_term_path / self.agent_id

        # Ensure directory exists
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _generate_id(self, content: Dict, timestamp: str) -> str:
        """生成唯一ID"""
        content_str = json.dumps(content, sort_keys=True)
        raw = f"{self.agent_id}:{timestamp}:{content_str}"
        return hashlib.md5(raw.encode()).hexdigest()[:16]

    def cleanup(self, memory_type: str) -> int:
        """清理过期记忆"""
        if memory_type == "short_term":
            # Clean up old short-term memories
            path = self.short_term_path / self.agent_id
            if not path.exists():
                return 0

            count = 0
            for f in path.glob("*.md"):
                # Keep only recent files
                if datetime.fromtimestamp(f.stat().st_mtime) < datetime.now():
                    f.unlink()
                    count += 1
            return count
        return 0
