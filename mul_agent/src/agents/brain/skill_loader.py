#!/usr/bin/env python3
"""
Skill Loader - 加载和管理 Agent Skills

参考 openclaw 的 skills 系统，实现：
1. SKILL.md 文件解析
2. 运行时 Eligibility 检查
3. 提示词构建
"""

import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional


@dataclass
class SkillMetadata:
    """Skill 元数据（来自 YAML frontmatter）"""
    name: str = ""
    description: str = ""
    emoji: str = ""
    role: str = ""
    title: str = ""
    tools: list[str] = field(default_factory=list)
    os: list[str] = field(default_factory=list)
    requires: dict[str, Any] = field(default_factory=dict)


@dataclass
class SkillEntry:
    """Skill 条目"""
    skill_id: str
    name: str
    description: str
    base_dir: Path
    file_path: Path
    metadata: SkillMetadata
    content: str  # Markdown 正文内容
    enabled: bool = True


class SkillLoader:
    """Skill 加载器"""

    def __init__(self, agent_team_dir: str | Path):
        self.agent_team_dir = Path(agent_team_dir)
        self._cache: dict[str, SkillEntry] = {}

    def scan_skills(self) -> list[SkillEntry]:
        """扫描 agent-team 目录中的所有 Skill"""
        skills = []

        for item in self.agent_team_dir.iterdir():
            if not item.is_dir() or item.name.startswith('.'):
                continue
            if item.name in ('__pycache__', 'node_modules', '.templates', '.teams'):
                continue

            skill = self._load_skill(item)
            if skill:
                skills.append(skill)
                self._cache[skill.skill_id] = skill

        return skills

    def _load_skill(self, skill_dir: Path) -> Optional[SkillEntry]:
        """加载单个 Skill"""
        # 尝试 SKILL.md（新格式）
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.exists():
            # 回退到旧的 user.md / soul.md
            return self._load_legacy_skill(skill_dir)

        try:
            content = skill_md.read_text(encoding='utf-8')
            frontmatter, body = self._parse_frontmatter(content)

            if not frontmatter or 'name' not in frontmatter:
                return None

            metadata = self._parse_metadata(frontmatter)

            return SkillEntry(
                skill_id=metadata.name,
                name=metadata.name,
                description=metadata.description,
                base_dir=skill_dir,
                file_path=skill_md,
                metadata=metadata,
                content=body,
                enabled=True
            )
        except Exception as e:
            print(f"[WARN] Failed to load skill {skill_dir.name}: {e}")
            return None

    def _load_legacy_skill(self, skill_dir: Path) -> Optional[SkillEntry]:
        """加载旧格式的 Skill（向后兼容）"""
        # 优先 user.md
        user_md = skill_dir / "user.md"
        if user_md.exists():
            return self._parse_legacy_file(user_md, skill_dir)

        # 回退到 soul.md
        soul_md = skill_dir / "soul.md"
        if soul_md.exists():
            return self._parse_legacy_file(soul_md, skill_dir)

        return None

    def _parse_legacy_file(self, md_file: Path, skill_dir: Path) -> Optional[SkillEntry]:
        """解析旧格式文件"""
        try:
            content = md_file.read_text(encoding='utf-8')
            frontmatter, body = self._parse_frontmatter(content)

            if not frontmatter:
                return None

            # 提取基本信息
            agent_id = frontmatter.get('agent_id', skill_dir.name)
            name = frontmatter.get('name', agent_id)

            # 从 body 提取描述
            description = self._extract_description_from_body(body)

            # 解析工具配置
            tools = []
            role_info = frontmatter.get('role', {})
            if isinstance(role_info, dict):
                tools.append(role_info.get('type', 'unknown'))

            tool_list = frontmatter.get('tools', {})
            if isinstance(tool_list, dict):
                tools.extend([k for k, v in tool_list.items() if v])

            metadata = SkillMetadata(
                name=agent_id,
                description=description,
                role=role_info.get('type', '') if isinstance(role_info, dict) else '',
                title=role_info.get('title', '') if isinstance(role_info, dict) else '',
                tools=tools
            )

            return SkillEntry(
                skill_id=agent_id,
                name=name,
                description=description,
                base_dir=skill_dir,
                file_path=md_file,
                metadata=metadata,
                content=body,
                enabled=True
            )
        except Exception as e:
            print(f"[WARN] Failed to load legacy skill {skill_dir.name}: {e}")
            return None

    def _parse_frontmatter(self, content: str) -> tuple[dict[str, Any], str]:
        """解析 YAML frontmatter（简化版）"""
        lines = content.split('\n')

        if not lines or lines[0].strip() != '---':
            return {}, content

        # 查找结束标记
        end_index = -1
        for i in range(1, len(lines)):
            if lines[i].strip() == '---':
                end_index = i
                break

        if end_index == -1:
            return {}, content

        # 使用简单方法解析：尝试导入 yaml 模块，失败则用正则
        try:
            import yaml
            fm_text = '\n'.join(lines[1:end_index])
            frontmatter = yaml.safe_load(fm_text) or {}
        except ImportError:
            # 回退到简单解析
            frontmatter = self._simple_parse_yaml(lines[1:end_index])

        body = '\n'.join(lines[end_index + 1:]).strip()
        return frontmatter, body

    def _simple_parse_yaml(self, lines: list[str]) -> dict[str, Any]:
        """简单 YAML 解析（回退方案）"""
        result = {}
        current_section = None
        current_dict = None

        for line in lines:
            stripped = line.strip()
            if not stripped or stripped.startswith('#'):
                continue

            indent = len(line) - len(line.lstrip())

            # 顶级 key（无缩进）
            if indent == 0 and ':' in stripped:
                key, value = stripped.split(':', 1)
                key = key.strip()
                value = value.strip()
                current_section = key

                if value:
                    result[key] = self._parse_yaml_value(value)
                else:
                    result[key] = {}
                    current_dict = result[key]

            # 二级缩进
            elif indent > 0 and current_section and ':' in stripped:
                key, value = stripped.split(':', 1)
                key = key.strip()
                value = value.strip()

                if current_dict is not None:
                    current_dict[key] = self._parse_yaml_value(value)

            # 列表项
            elif stripped.startswith('- '):
                value = stripped[2:].strip()
                if current_section:
                    if not isinstance(result.get(current_section), list):
                        result[current_section] = []
                    result[current_section].append(self._parse_yaml_value(value))

        return result

    def _parse_yaml_value(self, value: str) -> Any:
        """解析 YAML 值"""
        if not value:
            return None

        # 引号字符串
        if (value.startswith('"') and value.endswith('"')) or \
           (value.startswith("'") and value.endswith("'")):
            return value[1:-1]

        # 布尔值
        if value.lower() in ('true', 'yes', 'on'):
            return True
        if value.lower() in ('false', 'no', 'off'):
            return False

        # 数字
        try:
            if '.' in value:
                return float(value)
            return int(value)
        except ValueError:
            pass

        return value

    def _parse_metadata(self, frontmatter: dict[str, Any]) -> SkillMetadata:
        """解析 Skill 元数据"""
        metadata = frontmatter.get('metadata', {})
        mul_agent = metadata.get('mul_agent', {}) if isinstance(metadata, dict) else {}

        tools = mul_agent.get('tools', [])
        if not isinstance(tools, list):
            tools = []

        requires = mul_agent.get('requires', {})
        if not isinstance(requires, dict):
            requires = {}

        os_list = mul_agent.get('os', [])
        if not isinstance(os_list, list):
            os_list = []

        return SkillMetadata(
            name=frontmatter.get('name', ''),
            description=frontmatter.get('description', ''),
            emoji=mul_agent.get('emoji', ''),
            role=mul_agent.get('role', ''),
            title=mul_agent.get('title', ''),
            tools=[str(t) for t in tools],
            os=[str(o) for o in os_list],
            requires=requires
        )

    def _extract_description_from_body(self, body: str) -> str:
        """从旧格式 body 中提取描述"""
        # 查找第一行标题
        lines = body.split('\n')
        for line in lines:
            if line.strip() and not line.strip().startswith('#'):
                return line.strip()[:200]
        return ''

    def get_skill(self, skill_id: str) -> Optional[SkillEntry]:
        """获取单个 Skill"""
        return self._cache.get(skill_id)

    def get_enabled_skills(self) -> list[SkillEntry]:
        """获取所有启用的 Skill"""
        return [s for s in self._cache.values() if s.enabled]

    def build_skills_prompt(self, skills: list[SkillEntry], max_skills: int = 50) -> str:
        """构建 Skills 提示词"""
        # 限制数量
        limited = skills[:max_skills]

        # 格式化
        lines = []
        lines.append("## Available Agents")
        lines.append("")
        lines.append("| ID | Name | Role | Description |")
        lines.append("|------|------|------|-------------|")

        for skill in limited:
            emoji = skill.metadata.emoji or ''
            role = skill.metadata.title or skill.metadata.role or 'Unknown'
            desc = skill.description[:80] + '...' if len(skill.description) > 80 else skill.description
            lines.append(f"| `{skill.skill_id}` | {emoji} {skill.name} | {role} | {desc} |")

        lines.append("")
        lines.append("### Usage")
        lines.append("- Use `chat agent_id:<id> message:...` to delegate tasks")
        lines.append("- Choose agent based on their description and role")

        return '\n'.join(lines)


def load_skills(agent_team_dir: str | Path) -> list[SkillEntry]:
    """便捷函数：加载所有 Skills"""
    loader = SkillLoader(agent_team_dir)
    return loader.scan_skills()


def build_skills_prompt(agent_team_dir: str | Path) -> str:
    """便捷函数：构建 Skills 提示词"""
    loader = SkillLoader(agent_team_dir)
    skills = loader.scan_skills()
    return loader.build_skills_prompt(skills)
