"""Config Manager - Configuration management"""

import json
import re
import shutil
from pathlib import Path
from typing import Any, Dict, Optional
from datetime import datetime

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False


class ConfigManager:
    """配置管理器"""

    CONFIG_TYPES = ["soul", "user", "skill", "memory"]
    PROMPT_CONFIG_TYPE = "prompt"

    def __init__(self, config_dir: Path):
        # config_dir 应该是 storage/ 目录
        self.base_dir = Path(config_dir)
        self.agents_dir = self.base_dir / "agents"
        self.snapshot_dir = self.base_dir / "snapshots"

        self.agents_dir.mkdir(parents=True, exist_ok=True)
        self.snapshot_dir.mkdir(parents=True, exist_ok=True)

    @property
    def config_dir(self) -> Path:
        """兼容旧接口"""
        return self.agents_dir

    def load(self, agent_id: str, config_type: str) -> Dict[str, Any]:
        """加载指定配置"""
        config_path = self._get_config_path(agent_id, config_type)

        if not config_path.exists():
            return self._get_default_config(config_type)

        try:
            # 尝试读取 .md 格式
            with open(config_path, "r", encoding="utf-8") as f:
                content = f.read()

            # 解析 YAML front matter
            return self._parse_md_config(content, config_type)

        except Exception as e:
            # 如果解析失败，尝试 JSON
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except json.JSONDecodeError:
                raise ValueError(f"Invalid config in {config_path}: {e}")

    def load_text_content(self, agent_id: str, config_type: str) -> str:
        """加载完整的 Markdown 文本内容（包含 front matter 后的所有内容）

        这个方法用于获取配置文件中存储的丰富文本信息，而不仅仅是结构化的 YAML 数据。
        适用于需要获取完整配置描述、说明文档等场景。

        Args:
            agent_id: Agent ID
            config_type: 配置类型 (soul/user/skill/memory)

        Returns:
            str: 完整的 Markdown 文本内容
        """
        config_path = self._get_config_path(agent_id, config_type)

        if not config_path.exists():
            return ""

        try:
            with open(config_path, "r", encoding="utf-8") as f:
                content = f.read()

            # 提取 YAML front matter 之后的内容
            yaml_match = re.match(r'^---\n.*?\n---\n', content, re.DOTALL)

            if yaml_match:
                # 返回 front matter 之后的所有内容
                return content[yaml_match.end():].strip()
            else:
                # 如果没有 front matter，返回完整内容
                return content.strip()

        except Exception as e:
            print(f"Error loading text content from {config_path}: {e}")
            return ""

    def load_all_text_contents(self, agent_id: str) -> Dict[str, str]:
        """加载所有配置类型的完整文本内容

        Args:
            agent_id: Agent ID

        Returns:
            Dict[str, str]: 配置类型到文本内容的映射
        """
        return {
            config_type: self.load_text_content(agent_id, config_type)
            for config_type in self.CONFIG_TYPES
        }

    def load_prompt(self, agent_id: str, prompt_name: str) -> Optional[str]:
        """加载指定提示词（可选的风格提示词）

        只从 prompt.md 加载用户自定义的风格提示词。
        系统提示词（如 llm_decision, context_prompt）不应该从这里加载。

        Args:
            agent_id: Agent ID
            prompt_name: 提示词名称（如 coder_style, writer_style 等）

        Returns:
            str: 提示词内容，如果没有找到则返回 None
        """
        # 先尝试从 prompt.md 加载
        try:
            content = self.load_text_content(agent_id, self.PROMPT_CONFIG_TYPE)
            if content:
                # 解析 Markdown 中的提示词块
                import re
                # 查找 ## 提示词名称 后的代码块
                pattern = rf'## {prompt_name}\s*\n```\n(.*?)```'
                match = re.search(pattern, content, re.DOTALL)
                if match:
                    return match.group(1).strip()
        except Exception:
            pass

        # 系统提示词不应该有 fallback，返回 None
        return None

    def load_all_prompts(self, agent_id: str) -> Dict[str, Optional[str]]:
        """加载所有可选提示词

        Args:
            agent_id: Agent ID

        Returns:
            Dict[str, Optional[str]]: 提示词名称到内容的映射
        """
        # 只加载可选的风格提示词
        optional_prompts = [
            "coder_style", "writer_style", "researcher_style",
            "greeting_style", "response_style"
        ]
        return {
            name: self.load_prompt(agent_id, name)
            for name in optional_prompts
        }

    def save_prompt(self, agent_id: str, prompt_name: str, content: str) -> bool:
        """保存提示词（暂未实现完整功能，仅支持读取）

        Args:
            agent_id: Agent ID
            prompt_name: 提示词名称
            content: 提示词内容

        Returns:
            bool: 是否成功保存
        """
        # TODO: 实现提示词保存功能
        return False

    def _parse_md_config(self, content: str, config_type: str) -> Dict[str, Any]:
        """解析 Markdown 配置文件 - 提取 YAML front matter"""
        # 提取 YAML front matter
        yaml_match = re.match(r'^---\n(.*?)\n---', content, re.DOTALL)

        if not yaml_match:
            # 没有 front matter，返回默认
            return self._get_default_config(config_type)

        yaml_content = yaml_match.group(1)

        # 使用PyYAML解析（支持嵌套结构）
        if HAS_YAML:
            try:
                config = yaml.safe_load(yaml_content)
                if config:
                    return config
            except Exception:
                pass

        # Fallback: 简单解析（只处理顶层键值对）
        config = {}
        for line in yaml_content.strip().split('\n'):
            line = line.strip()
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                config[key] = value

        return config

    def _dict_to_md(self, data: Dict[str, Any], config_type: str) -> str:
        """将字典转换为 Markdown 格式 - 完整 YAML front matter"""
        lines = ["---"]

        # 使用 YAML 序列化所有数据到 front matter（支持嵌套结构）
        if HAS_YAML:
            try:
                import yaml
                yaml_content = yaml.dump(data, default_flow_style=False, allow_unicode=True, sort_keys=False)
                lines.append(yaml_content.strip())
            except Exception:
                # Fallback: 简单序列化
                for key, value in data.items():
                    if isinstance(value, (str, int, float, bool)):
                        lines.append(f"{key}: {value}")
                    elif isinstance(value, dict):
                        lines.append(f"{key}:")
                        for k, v in value.items():
                            if isinstance(v, (str, int, float, bool)):
                                lines.append(f"  {k}: {v}")
                            elif isinstance(v, list):
                                lines.append(f"  {k}: {yaml.dump(v, default_flow_style=True).strip()}")
                    elif isinstance(value, list):
                        lines.append(f"{key}: {value}")
        else:
            # 无 YAML 库时的降级处理
            for key, value in data.items():
                if isinstance(value, (str, int, float, bool)):
                    lines.append(f"{key}: {value}")
                elif isinstance(value, dict):
                    lines.append(f"{key}:")
                    for k, v in value.items():
                        lines.append(f"  {k}: {v}")
                elif isinstance(value, list):
                    lines.append(f"{key}: {value}")

        lines.append("---\n")

        # 添加简要的内容说明（不重复 front matter 中已有的数据）
        lines.append(f"# {config_type.title()} 配置\n")
        lines.append(f"这是一个 {config_type} 配置文件，包含 Agent 的{self._get_config_description(config_type)}。\n")

        return "\n".join(lines)

    def _get_config_description(self, config_type: str) -> str:
        """获取配置类型描述"""
        descriptions = {
            "soul": "核心特质、行为模式、进化规则和约束条件",
            "user": "角色定义、能力、工具和权限配置",
            "skill": "技能列表和技能树结构",
            "memory": "记忆策略、交接配置和检索参数"
        }
        return descriptions.get(config_type, "配置信息")

    def load_all(self, agent_id: str) -> Dict[str, Any]:
        """加载所有配置"""
        return {
            config_type: self.load(agent_id, config_type)
            for config_type in self.CONFIG_TYPES
        }

    def save(self, agent_id: str, config_type: str, data: Dict[str, Any]) -> bool:
        """保存配置"""
        if config_type not in self.CONFIG_TYPES:
            raise ValueError(f"Invalid config type: {config_type}")

        # Create snapshot before saving
        self._create_snapshot(agent_id, config_type)

        config_path = self._get_config_path(agent_id, config_type)
        config_path.parent.mkdir(parents=True, exist_ok=True)

        # 保存为 .md 格式
        with open(config_path, "w", encoding="utf-8") as f:
            f.write(self._dict_to_md(data, config_type))

        return True

    def _get_config_path(self, agent_id: str, config_type: str) -> Path:
        """获取配置文件路径"""
        # 新目录结构: storage/agents/{agent_id}/{config_type}.md
        agent_dir = self.agents_dir / agent_id
        md_path = agent_dir / f"{config_type}.md"

        if md_path.exists():
            return md_path

        # 回退到旧结构: storage/agents/{agent_id}_{config_type}.md
        old_md_path = self.agents_dir / f"{agent_id}_{config_type}.md"
        if old_md_path.exists():
            return old_md_path

        # 返回新路径（新建时用）
        return md_path

    def _get_default_config(self, config_type: str) -> Dict[str, Any]:
        """获取默认配置"""
        defaults = {
            "soul": {
                "version": "1.0",
                "name": "core_brain",
                "description": "Core brain agent",
                "core_traits": {
                    "personality": "Adaptive and self-improving",
                    "values": ["efficiency", "growth", "autonomy"],
                    "goals": ["continuous_improvement", "team_coordination"]
                },
                "behavior_patterns": {
                    "decision_making": "data_driven",
                    "problem_solving": "systematic",
                    "communication": "collaborative"
                },
                "evolution_rules": {
                    "can_modify_self": True,
                    "modification_scope": self.CONFIG_TYPES,
                    "snapshot_before_change": True,
                    "self_check_required": False
                },
                "constraints": {
                    "boundaries": ["safe_execution", "no_destructive_actions"],
                    "forbidden_actions": []
                }
            },
            "user": {
                "version": "1.0",
                "agent_id": "core_brain",
                "role": {
                    "type": "coordinator",
                    "title": "Team Coordinator",
                    "responsibilities": ["coordinate_team", "delegate_tasks", "quality_control"]
                },
                "capabilities": {
                    "max_team_size": 10,
                    "can_create_agent": True,
                    "can_modify_config": True,
                    "can_execute_tools": True
                },
                "tools": {
                    "enabled": ["bash", "chrome_mcp", "web_search", "grep"],
                    "bash": {
                        "enabled": True,
                        "timeout": 30,
                        "allowed_commands": ["*"],
                        "forbidden_commands": []
                    },
                    "chrome_mcp": {
                        "enabled": True,
                        "headless": False
                    },
                    "web_search": {
                        "enabled": True,
                        "max_results": 10
                    },
                    "grep": {
                        "enabled": True,
                        "max_results": 100,
                        "default_context": 2,
                        "forbidden_paths": [
                            "/etc/passwd",
                            "/etc/shadow",
                            ".git/objects",
                            "node_modules/",
                            "__pycache__/",
                            ".venv/"
                        ]
                    }
                },
                "permissions": {
                    "file_read": ["*"],
                    "file_write": ["storage/**"],
                    "network_access": True
                }
            },
            "skill": {
                "version": "1.0",
                "agent_id": "core_brain",
                "skills": [
                    {
                        "id": "skill_001",
                        "name": "code_generation",
                        "description": "Generate and modify code",
                        "enabled": True,
                        "parameters": {
                            "languages": ["python", "javascript", "typescript"],
                            "frameworks": ["fastapi", "react", "nextjs"]
                        }
                    },
                    {
                        "id": "skill_002",
                        "name": "system_administration",
                        "description": "System management and maintenance",
                        "enabled": True,
                        "parameters": {
                            "os": ["linux", "macos", "windows"],
                            "tools": ["docker", "kubectl", "git"]
                        }
                    }
                ],
                "skill_tree": {
                    "root": "skill_001",
                    "children": {
                        "skill_001": ["skill_002"],
                        "skill_002": []
                    }
                }
            },
            "memory": {
                "version": "1.0",
                "agent_id": "core_brain",
                "memory_strategy": {
                    "short_term": {
                        "storage": "session",
                        "max_size": "10MB",
                        "auto_cleanup": True,
                        "ttl_seconds": 3600
                    },
                    "long_term": {
                        "storage": "file",
                        "path": "storage/memory/long_term",
                        "compression": False,
                        "auto_archive": True,
                        "archive_interval": "daily"
                    }
                },
                "handover": {
                    "required_fields": ["task_summary", "context", "next_steps"],
                    "format": "markdown",
                    "auto_generate": True
                },
                "retrieval": {
                    "default_limit": 10,
                    "relevance_threshold": 0.7,
                    "search_method": "keyword"
                }
            }
        }
        return defaults.get(config_type, {})

    def _create_snapshot(self, agent_id: str, config_type: str) -> Optional[str]:
        """创建配置快照"""
        config_path = self._get_config_path(agent_id, config_type)
        if not config_path.exists():
            return None

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        # Use same extension as source file
        ext = config_path.suffix if config_path.suffix else ".md"
        snapshot_name = f"{agent_id}_{config_type}_{timestamp}{ext}"
        snapshot_path = self.snapshot_dir / snapshot_name

        shutil.copy2(config_path, snapshot_path)
        return snapshot_name

    def restore_snapshot(self, snapshot_name: str) -> bool:
        """恢复快照"""
        snapshot_path = self.snapshot_dir / snapshot_name
        if not snapshot_path.exists():
            return False

        # Extract agent_id and config_type from snapshot name
        # Format: {agent_id}_{config_type}_{timestamp}.{ext}
        # Example: test_agent_soul_20260305_164352.md
        name_without_ext = snapshot_name

        # Known config types
        config_types = ["soul", "user", "skill", "memory"]

        # Try to find config_type in the name and extract agent_id
        agent_id = None
        config_type = None
        for ct in config_types:
            # Look for pattern: {something}_{config_type}_{timestamp}
            suffix = f"_{ct}_"
            idx = name_without_ext.find(suffix)
            if idx > 0:
                agent_id = name_without_ext[:idx]
                config_type = ct
                break

        if agent_id is None or config_type is None:
            return False

        config_path = self._get_config_path(agent_id, config_type)
        shutil.copy2(snapshot_path, config_path)
        return True

    def list_snapshots(self, agent_id: Optional[str] = None) -> list:
        """列出快照"""
        snapshots = []
        for snapshot in self.snapshot_dir.iterdir():
            if snapshot.is_file() and snapshot.suffix in (".json", ".md"):
                if agent_id and not snapshot.name.startswith(agent_id):
                    continue
                snapshots.append({
                    "name": snapshot.name,
                    "created": datetime.fromtimestamp(snapshot.stat().st_mtime).isoformat()
                })
        return sorted(snapshots, key=lambda x: x["created"], reverse=True)

    def list_agents(self) -> list:
        """列出所有Agent"""
        agents = []

        # 新目录结构: storage/agents/{agent_id}/
        if self.agents_dir.exists():
            for agent_dir in self.agents_dir.iterdir():
                if agent_dir.is_dir():
                    agents.append(agent_dir.name)

        return sorted(agents)

    def validate_config(self, agent_id: str) -> Dict[str, Any]:
        """验证配置完整性"""
        results = {
            "agent_id": agent_id,
            "valid": True,
            "missing": [],
            "errors": []
        }

        for config_type in self.CONFIG_TYPES:
            config_path = self._get_config_path(agent_id, config_type)
            if not config_path.exists():
                results["missing"].append(config_type)
                results["valid"] = False
                continue

            try:
                config = self.load(agent_id, config_type)
                if not config:
                    results["missing"].append(config_type)
                    results["valid"] = False
            except Exception as e:
                results["errors"].append(f"{config_type}: {str(e)}")
                results["valid"] = False

        return results
