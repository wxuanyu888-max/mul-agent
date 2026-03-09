"""Skill Manager - 技能管理器"""

import importlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Type
import re

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

from mul_agent.skills.base import BaseSkill


class SkillManager:
    """技能管理器

    负责：
    - 加载技能（从文件和内置）
    - 注册技能
    - 执行技能
    - 技能生命周期管理
    """

    def __init__(self, config_manager, agent_id: str = None):
        """初始化技能管理器

        Args:
            config_manager: 配置管理器
            agent_id: Agent ID
        """
        self.config_manager = config_manager
        self.agent_id = agent_id or "wangyue"

        # 已注册的技能实例
        self._skills: Dict[str, BaseSkill] = {}

        # 技能元数据缓存
        self._skill_metadata: Dict[str, Dict[str, Any]] = {}

        # 加载内置技能和配置文件技能
        self._load_builtin_skills()
        self._load_skill_configs()

    def _load_builtin_skills(self) -> None:
        """加载内置技能"""
        builtin_skills = [
            "mul_agent.skills.builtin.BashSkill",
            "mul_agent.skills.builtin.MemorySkill",
            "mul_agent.skills.builtin.ChatSkill",
            "mul_agent.skills.builtin.CodeSkill",
            "mul_agent.skills.builtin.SearchSkill",
            "mul_agent.skills.builtin.ProjectExplorer",
        ]

        for skill_path in builtin_skills:
            try:
                module_path, class_name = skill_path.rsplit(".", 1)
                module = importlib.import_module(module_path)
                skill_class = getattr(module, class_name)
                self.register_skill(skill_class)
            except Exception as e:
                print(f"Error loading builtin skill {skill_path}: {e}")

    def _load_skill_configs(self) -> None:
        """从配置加载技能"""
        try:
            skill_config = self.config_manager.load(self.agent_id, "skill")
            skills_list = skill_config.get("skills", [])

            for skill_data in skills_list:
                skill_id = skill_data.get("id")
                enabled = skill_data.get("enabled", True)

                if not enabled:
                    continue

                # 尝试加载动态技能
                module_path = skill_data.get("module_path")
                if module_path:
                    try:
                        module = importlib.import_module(module_path)
                        class_name = skill_data.get("class_name", "DynamicSkill")
                        skill_class = getattr(module, class_name)
                        self.register_skill(skill_class)
                    except Exception as e:
                        print(f"Error loading dynamic skill {module_path}: {e}")
        except Exception as e:
            print(f"Error loading skill configs: {e}")

    def register_skill(self, skill_class: Type[BaseSkill], instance: BaseSkill = None) -> str:
        """注册技能

        Args:
            skill_class: 技能类
            instance: 技能实例（如果为 None 则自动创建）

        Returns:
            str: 技能 ID
        """
        if instance is None:
            instance = skill_class(
                config_manager=self.config_manager,
                agent_id=self.agent_id
            )

        # 初始化技能
        if not instance.initialize():
            raise ValueError(f"Failed to initialize skill {instance.skill_id}")

        # 注册
        self._skills[instance.skill_id] = instance
        self._skill_metadata[instance.skill_id] = instance.get_metadata()

        return instance.skill_id

    def get_skill(self, skill_id: str) -> Optional[BaseSkill]:
        """获取技能实例

        Args:
            skill_id: 技能 ID

        Returns:
            BaseSkill: 技能实例，如果不存在则返回 None
        """
        return self._skills.get(skill_id)

    def execute_skill(self, skill_id: str, **kwargs) -> Any:
        """执行技能

        Args:
            skill_id: 技能 ID
            **kwargs: 执行参数

        Returns:
            Any: 执行结果
        """
        skill = self.get_skill(skill_id)
        if not skill:
            raise ValueError(f"Skill not found: {skill_id}")

        if not skill.enabled:
            raise ValueError(f"Skill is disabled: {skill_id}")

        # 验证参数
        if not skill.validate_params(kwargs):
            raise ValueError(f"Invalid parameters for skill {skill_id}")

        # 需要确认的技能
        if skill.requires_confirmation:
            # TODO: 实现确认逻辑
            pass

        return skill.execute(**kwargs)

    def list_skills(self, include_disabled: bool = True) -> List[Dict[str, Any]]:
        """列出所有技能

        Args:
            include_disabled: 是否包含禁用的技能

        Returns:
            List[Dict]: 技能元数据列表
        """
        skills = []
        for skill_id, metadata in self._skill_metadata.items():
            if not include_disabled and not metadata.get("enabled", True):
                continue
            skills.append(metadata)
        return sorted(skills, key=lambda x: x.get("priority", 5), reverse=True)

    def search_skills(self, query: str, tags: List[str] = None) -> List[Dict[str, Any]]:
        """搜索技能

        Args:
            query: 搜索关键词
            tags: 标签过滤

        Returns:
            List[Dict]: 匹配的技能元数据
        """
        results = []
        query_lower = query.lower()

        for skill_id, metadata in self._skill_metadata.items():
            score = 0

            # 搜索名称和描述
            if query_lower in metadata.get("skill_name", "").lower():
                score += 10
            if query_lower in metadata.get("skill_description", "").lower():
                score += 5
            if query_lower in metadata.get("skill_id", "").lower():
                score += 3

            # 搜索标签
            if tags:
                skill_tags = metadata.get("skill_tags", [])
                matching_tags = set(tags) & set(skill_tags)
                score += len(matching_tags) * 5

            if score > 0:
                results.append({**metadata, "relevance_score": score})

        return sorted(results, key=lambda x: x.get("relevance_score", 0), reverse=True)

    def enable_skill(self, skill_id: str) -> bool:
        """启用技能"""
        skill = self.get_skill(skill_id)
        if skill:
            skill.enabled = True
            self._skill_metadata[skill_id]["enabled"] = True
            return True
        return False

    def disable_skill(self, skill_id: str) -> bool:
        """禁用技能"""
        skill = self.get_skill(skill_id)
        if skill:
            skill.enabled = False
            self._skill_metadata[skill_id]["enabled"] = False
            return True
        return False

    def unload_skill(self, skill_id: str) -> bool:
        """卸载技能"""
        if skill_id in self._skills:
            del self._skills[skill_id]
        if skill_id in self._skill_metadata:
            del self._skill_metadata[skill_id]
        return True

    def reload_all(self) -> None:
        """重新加载所有技能"""
        self._skills.clear()
        self._skill_metadata.clear()
        self._load_builtin_skills()
        self._load_skill_configs()

    def get_skill_by_tag(self, tag: str) -> List[BaseSkill]:
        """根据标签获取技能"""
        results = []
        for skill_id, skill in self._skills.items():
            if tag in skill.skill_tags:
                results.append(skill)
        return results

    def to_dict(self) -> Dict[str, Any]:
        """将技能管理器状态转换为字典"""
        return {
            "agent_id": self.agent_id,
            "skills_count": len(self._skills),
            "skills": self.list_skills(),
        }
