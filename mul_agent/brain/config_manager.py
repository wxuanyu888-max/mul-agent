"""Config Manager - Configuration management"""

import json
import re
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False


class ConfigManager:
    """配置管理器

    所有存储都在 wang/ 目录下:
    - wang/agent-team/ - Agent 配置文件 (user.md, soul.md, skill.md, memory.md, logic.md)
    - wang/token_usage/ - Token 使用统计
    - wang/snapshots/ - 配置快照
    - wang/projects/ - 项目配置
    - wang/file-history/ - 文件历史 (工作缓冲区)
    """

    # 核心配置类型：每个 agent 只保留这 5 个文件在 wang/agent-team 中
    CONFIG_TYPES = ["soul", "user", "skill", "memory", "logic"]
    # 特殊配置类型
    PROMPT_CONFIG_TYPE = "prompt"
    # 标准提示词模板路径（存放在 wang/agent-team/.templates/prompt.md）
    STANDARD_PROMPT_TEMPLATE = None  # 运行时动态设置

    def __init__(self, config_dir: Path, wang_dir: Optional[Path] = None):
        # config_dir 和 wang_dir 都指向 wang/ 目录 (所有存储都在 wang 内)
        self.wang_dir = wang_dir or Path(config_dir)

        # Agent 配置目录
        self.agent_team_dir = self.wang_dir / "agent-team"

        # 其他存储目录 (都在 wang/ 内)
        self.token_usage_dir = self.wang_dir / "token_usage"
        self.snapshot_dir = self.wang_dir / "snapshots"
        self.projects_dir = self.wang_dir / "projects"
        self.file_history_dir = self.wang_dir / "file-history"

        # 创建目录 (如果不存在)
        self.agent_team_dir.mkdir(parents=True, exist_ok=True)
        self.token_usage_dir.mkdir(parents=True, exist_ok=True)
        self.snapshot_dir.mkdir(parents=True, exist_ok=True)
        self.projects_dir.mkdir(parents=True, exist_ok=True)
        self.file_history_dir.mkdir(parents=True, exist_ok=True)

    @property
    def config_dir(self) -> Path:
        """兼容旧接口 - 返回 agent-team 目录"""
        return self.agent_team_dir

    @property
    def agents_dir(self) -> Path:
        """兼容旧接口 - 返回 wang/agents 目录 (如果有)"""
        agents_dir = self.wang_dir / "agents"
        agents_dir.mkdir(parents=True, exist_ok=True)
        return agents_dir

    def _get_wang_config_path(self, agent_id: str, config_type: str) -> Path:
        """获取 wang/agent-team 配置文件路径"""
        agent_dir = self.agent_team_dir / agent_id
        return agent_dir / f"{config_type}.md"

    def _load_from_wang(self, agent_id: str, config_type: str) -> Optional[Dict[str, Any]]:
        """从 wang/agent-team 加载配置

        Args:
            agent_id: Agent ID
            config_type: 配置类型

        Returns:
            配置字典，如果不存在则返回 None
        """
        wang_path = self._get_wang_config_path(agent_id, config_type)

        if not wang_path.exists():
            return None

        try:
            with open(wang_path, "r", encoding="utf-8") as f:
                content = f.read()
            return self._parse_md_config(content, config_type)
        except Exception as e:
            print(f"Error loading config from wang {wang_path}: {e}")
            return None

    def save_to_wang(
        self, agent_id: str, config_type: str, data: Dict[str, Any]
    ) -> bool:
        """保存配置到 wang/agent-team

        Args:
            agent_id: Agent ID
            config_type: 配置类型
            data: 配置数据

        Returns:
            是否保存成功
        """
        if config_type not in self.CONFIG_TYPES:
            raise ValueError(f"Invalid config type: {config_type}")

        wang_path = self._get_wang_config_path(agent_id, config_type)
        wang_path.parent.mkdir(parents=True, exist_ok=True)

        # 保存为 .md 格式
        with open(wang_path, "w", encoding="utf-8") as f:
            f.write(self._dict_to_md(data, config_type))

        return True

    def load(self, agent_id: str, config_type: str) -> Dict[str, Any]:
        """加载指定配置

        从 wang/agent-team/{agent_id}/ 加载配置
        """
        # 1. 先尝试从 wang/agent-team 加载
        config = self._load_from_wang(agent_id, config_type)
        if config:
            return config

        # 2. 如果没有找到，返回默认配置
        return self._get_default_config(config_type)

    def load_text_content(self, agent_id: str, config_type: str) -> str:
        """加载完整的 Markdown 文本内容（包含 front matter 后的所有内容）

        从 wang/agent-team/{agent_id}/ 加载

        Args:
            agent_id: Agent ID
            config_type: 配置类型 (soul/user/skill/memory/logic)

        Returns:
            str: 完整的 Markdown 文本内容
        """
        # 从 wang/agent-team 加载
        wang_path = self._get_wang_config_path(agent_id, config_type)
        if wang_path.exists():
            try:
                with open(wang_path, "r", encoding="utf-8") as f:
                    content = f.read()
                yaml_match = re.match(r'^---\n.*?\n---\n', content, re.DOTALL)
                if yaml_match:
                    return content[yaml_match.end():].strip()
                else:
                    return content.strip()
            except Exception as e:
                print(f"Error loading text content from {wang_path}: {e}")

        # 返回空字符串（如果没有找到）
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
        """加载指定提示词

        加载优先级：
        1. 先从 wang/agent-team/prompt.md 加载（用户自定义）
        2. 再从 wang/agent-team/.templates/prompt.md 加载（标准模板）

        Args:
            agent_id: Agent ID
            prompt_name: 提示词名称（如 default_assistant, empty_input_style 等）

        Returns:
            str: 提示词内容，如果没有找到则返回 None
        """
        # 1. 先尝试从 agent 自定义的 prompt.md 加载
        try:
            content = self.load_text_content(agent_id, self.PROMPT_CONFIG_TYPE)
            if content:
                # 解析 Markdown 中的提示词块
                import re
                # 查找 ## 提示词名称 后的内容（支持代码块和纯文本）
                # 注意：## 后面可能跟有描述文字，如 "## default_assistant - 默认助手提示词"
                pattern = rf'## {prompt_name}(?:\s*-.*?)*\s*\n(.*?)(?:\n---|\n##|\Z)'
                match = re.search(pattern, content, re.DOTALL)
                if match:
                    result = match.group(1).strip()
                    # 去除开头的代码块标记（如果有）
                    if result.startswith('```'):
                        code_end = result.find('```', 3)
                        if code_end > 0:
                            result = result[code_end + 3:].strip()
                    return result
        except Exception:
            pass

        # 2. 从标准模板加载 (wang/agent-team/.templates/prompt.md.template)
        try:
            template_path = self.agent_team_dir / ".templates" / "prompt.md.template"
            if template_path.exists():
                with open(template_path, "r", encoding="utf-8") as f:
                    content = f.read()

                import re
                # 查找 ## 提示词名称 后的内容
                # 注意：## 后面可能跟有描述文字，如 "## default_assistant - 默认助手提示词"
                pattern = rf'## {prompt_name}(?:\s*-.*?)*\s*\n(.*?)(?:\n---|\n##|\Z)'
                match = re.search(pattern, content, re.DOTALL)
                if match:
                    result = match.group(1).strip()
                    # 去除开头的代码块标记（如果有）
                    if result.startswith('```'):
                        code_end = result.find('```', 3)
                        if code_end > 0:
                            result = result[code_end + 3:].strip()
                    return result
        except Exception:
            pass

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
        """保存配置到 wang/agent-team/{agent_id}/{config_type}.md"""
        if config_type not in self.CONFIG_TYPES:
            raise ValueError(f"Invalid config type: {config_type}")

        # Create snapshot before saving
        self._create_snapshot(agent_id, config_type)

        # 保存到 wang/agent-team/{agent_id}/{config_type}.md
        config_path = self._get_wang_config_path(agent_id, config_type)
        config_path.parent.mkdir(parents=True, exist_ok=True)

        # 保存为 .md 格式
        with open(config_path, "w", encoding="utf-8") as f:
            f.write(self._dict_to_md(data, config_type))

        return True

    def load_token_usage(self, agent_id: str) -> Dict[str, Any]:
        """加载 Token 使用统计

        Args:
            agent_id: Agent ID

        Returns:
            Dict[str, Any]: Token 使用数据
        """
        json_path = self.token_usage_dir / f"{agent_id}.json"

        if not json_path.exists():
            return self._get_default_token_usage(agent_id)

        try:
            with open(json_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading token usage from {json_path}: {e}")
            return self._get_default_token_usage(agent_id)

    def save_token_usage(self, agent_id: str, data: Dict[str, Any]) -> bool:
        """保存 Token 使用统计

        Args:
            agent_id: Agent ID
            data: Token 使用数据

        Returns:
            bool: 是否保存成功
        """
        json_path = self.token_usage_dir / f"{agent_id}.json"
        json_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Error saving token usage to {json_path}: {e}")
            return False

    def _get_default_token_usage(self, agent_id: str) -> Dict[str, Any]:
        """获取默认 Token 使用数据"""
        return {
            "agent_id": agent_id,
            "totals": {
                "total_tokens": 0,
                "input_tokens": 0,
                "output_tokens": 0,
                "access_count": 0
            },
            "by_model": {},
            "by_function": {},
            "by_date": {},
            "llm_logs": []
        }

    def load_logic(self, agent_id: str) -> Dict[str, Any]:
        """加载 Logic 配置

        Args:
            agent_id: Agent ID

        Returns:
            Dict[str, Any]: Logic 配置数据
        """
        # 从 wang/agent-team/{agent_id}/logic.md 加载
        logic_path = self.agent_team_dir / agent_id / "logic.md"

        if not logic_path.exists():
            return self._get_default_logic(agent_id)

        try:
            with open(logic_path, "r", encoding="utf-8") as f:
                content = f.read()
            return self._parse_md_config(content, "logic")
        except Exception as e:
            print(f"Error loading logic from {logic_path}: {e}")
            return self._get_default_logic(agent_id)

    def save_logic(self, agent_id: str, data: Dict[str, Any]) -> bool:
        """保存 Logic 配置

        Args:
            agent_id: Agent ID
            data: Logic 配置数据

        Returns:
            bool: 是否保存成功
        """
        logic_path = self.agent_team_dir / agent_id / "logic.md"
        logic_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            with open(logic_path, "w", encoding="utf-8") as f:
                f.write(self._dict_to_md(data, "logic"))
            return True
        except Exception as e:
            print(f"Error saving logic to {logic_path}: {e}")
            return False

    def _get_default_logic(self, agent_id: str) -> Dict[str, Any]:
        """获取默认 Logic 配置"""
        return {
            "version": "1.0",
            "agent_id": agent_id,
            "available_actions": [
                "response", "bash", "memory", "chat", "heart", "create_user", "create_team"
            ],
            "tool_permissions": {
                "bash": {"allowed": ["*"], "forbidden": ["rm -rf /", "sudo"]},
                "memory": {"short_term": True, "long_term": True, "handover": True}
            },
            "behavior_rules": {
                "user_first": True,
                "safety_first": True,
                "transparent_execution": True,
                "error_handling": "clear_report"
            },
            "evolution_rules": {
                "can_modify_self": False,
                "requires_user_confirmation": True
            }
        }


    def _get_default_config(self, config_type: str) -> Dict[str, Any]:
        """获取默认配置"""
        defaults = {
            "soul": {
                "version": "1.0",
                "name": "wang",
                "description": "Wang - Core brain agent",
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
                "agent_id": "wang",
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
                "llm_config": {
                    "url": "https://api.anthropic.com/v1",
                    "provider": "anthropic",
                    "model": "claude-sonnet-4-20250514",
                    "key": ""  # 需要用户手动填写
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
                "agent_id": "wang",
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
                "agent_id": "wang",
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
        """创建配置快照 - 从 wang/agent-team 创建快照"""
        config_path = self._get_wang_config_path(agent_id, config_type)
        if not config_path.exists():
            return None

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        snapshot_name = f"{agent_id}_{config_type}_{timestamp}.md"
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

        config_path = self._get_wang_config_path(agent_id, config_type)
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
        """列出所有 Agent - 从 wang/agent-team 读取"""
        agents = set()

        # 从 wang/agent-team 列出
        if self.agent_team_dir.exists():
            for agent_dir in self.agent_team_dir.iterdir():
                if agent_dir.is_dir():
                    agent_id = agent_dir.name
                    # 跳过隐藏目录（以.开头）
                    if agent_id.startswith('.'):
                        continue
                    agents.add(agent_id)

        return sorted(list(agents))

    def list_teams(self) -> Dict[str, List[str]]:
        """列出所有团队及其成员

        团队定义：
        1. 从 wang/.teams/ 目录读取已创建的团队
        2. 如果没有创建任何团队，所有 Agent 默认属于 wang 团队

        Returns:
            Dict[str, List[str]]: 团队名到 Agent 列表的映射
        """
        teams: Dict[str, List[str]] = {}

        # 1. 先从 wang/.teams/ 读取已创建的团队
        teams_dir = self.wang_dir / ".teams"
        if teams_dir.exists():
            import json
            for team_file in teams_dir.glob("*.json"):
                try:
                    with open(team_file, "r", encoding="utf-8") as f:
                        team_data = json.load(f)
                    team_name = team_data.get("name", team_file.stem)
                    teams[team_name] = []  # 先创建空团队
                except Exception:
                    pass

        # 2. 从 wang/agent-team 读取 Agent 并分配到团队
        if self.agent_team_dir.exists():
            for agent_dir in self.agent_team_dir.iterdir():
                if agent_dir.is_dir():
                    agent_id = agent_dir.name
                    # 跳过隐藏目录（以.开头）
                    if agent_id.startswith('.'):
                        continue

                    # 读取 Agent 的团队信息
                    user_path = agent_dir / "user.md"
                    if user_path.exists():
                        try:
                            with open(user_path, "r", encoding="utf-8") as f:
                                content = f.read()
                            yaml_match = re.match(r'^---\n(.*?)\n---', content, re.DOTALL)
                            if yaml_match:
                                yaml_content = yaml_match.group(1)
                                if HAS_YAML:
                                    import yaml
                                    user_data = yaml.safe_load(yaml_content)
                                    agent_team = user_data.get("team", {}).get("name", "wang")
                                else:
                                    agent_team = "wang"
                            else:
                                agent_team = "wang"
                        except Exception:
                            agent_team = "wang"
                    else:
                        agent_team = "wang"

                    # 如果团队不存在于 teams 中，说明这个团队没有被正式创建
                    # 将 Agent 归入 wang 团队（默认主团队）
                    if agent_team not in teams:
                        # 如果连 wang 团队都没有，说明还没有创建任何团队
                        # 所有 Agent 都归入 wang 团队
                        if "wang" not in teams:
                            teams["wang"] = []
                        teams["wang"].append(agent_id)
                    else:
                        teams[agent_team].append(agent_id)

        # 3. 如果没有任何团队且没有 Agent，创建默认的 wang 团队
        if not teams:
            teams["wang"] = []

        return teams

    def validate_config(self, agent_id: str) -> Dict[str, Any]:
        """验证配置完整性"""
        results = {
            "agent_id": agent_id,
            "valid": True,
            "missing": [],
            "errors": []
        }

        for config_type in self.CONFIG_TYPES:
            config_path = self._get_wang_config_path(agent_id, config_type)
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

    def get_llm_config(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """获取 Agent 的 LLM 配置

        Args:
            agent_id: Agent ID

        Returns:
            LLM 配置字典，包含 url, provider, model, key，如果不存在则返回 None
        """
        user_config = self.load(agent_id, "user")
        if user_config:
            return user_config.get("llm_config")
        return None

    def save_llm_config(self, agent_id: str, llm_config: Dict[str, Any]) -> bool:
        """保存 Agent 的 LLM 配置

        Args:
            agent_id: Agent ID
            llm_config: LLM 配置数据，包含 url, provider, model, key

        Returns:
            是否保存成功
        """
        # 验证必需字段
        required_fields = ["url", "provider", "model", "key"]
        for field in required_fields:
            if field not in llm_config:
                raise ValueError(f"Missing required field: {field}")

        # 获取当前的 user 配置
        user_config = self.load(agent_id, "user")
        if not user_config:
            user_config = {}

        # 更新 llm_config
        user_config["llm_config"] = {
            "url": llm_config["url"],
            "provider": llm_config["provider"],
            "model": llm_config["model"],
            "key": llm_config["key"]
        }

        # 保存回 user.md
        return self.save(agent_id, "user", user_config)
