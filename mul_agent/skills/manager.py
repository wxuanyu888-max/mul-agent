"""Skill Manager - 技能管理器"""

import inspect
from typing import Any, Dict, List, Optional, Type

from .base import BaseSkill, SkillMetadata


class SkillManager:
    """技能管理器

    负责注册、管理和执行技能
    """

    def __init__(self, config_manager=None, agent_id: str = None):
        """初始化技能管理器

        Args:
            config_manager: 配置管理器
            agent_id: Agent ID
        """
        self.config_manager = config_manager
        self.agent_id = agent_id or "default"
        self._skills: Dict[str, BaseSkill] = {}  # skill_id -> instance
        self._skill_names: Dict[str, str] = {}  # skill_name -> skill_id
        self._load_builtin_skills()

    def _load_builtin_skills(self) -> None:
        """加载内置技能"""
        try:
            from . import builtin
            # 自动注册 builtin 模块中的所有 Skill 类
            for name, obj in inspect.getmembers(builtin):
                if (inspect.isclass(obj) and
                    issubclass(obj, BaseSkill) and
                    obj != BaseSkill and
                    hasattr(obj, 'skill_id')):
                    self.register_skill(obj)
        except ImportError:
            pass  # builtin 模块可能不存在

    def register_skill(self, skill_class: Type[BaseSkill], instance: Optional[BaseSkill] = None) -> Optional[str]:
        """注册技能

        Args:
            skill_class: 技能类
            instance: 可选的技能实例，如果不提供则创建新实例

        Returns:
            Optional[str]: 技能 ID，如果注册失败返回 None
        """
        try:
            # 创建或使用了提供的实例
            skill_instance = instance if instance is not None else skill_class(
                config_manager=self.config_manager,
                agent_id=self.agent_id
            )

            # 初始化技能
            if not skill_instance.initialize():
                print(f"Failed to initialize skill: {skill_class.skill_id}")
                return None

            # 检查是否已存在
            if skill_instance.skill_id in self._skills:
                print(f"Skill already registered: {skill_instance.skill_id}")
                return skill_instance.skill_id

            # 注册技能实例
            self._skills[skill_instance.skill_id] = skill_instance
            self._skill_names[skill_instance.skill_name] = skill_instance.skill_id

            return skill_instance.skill_id

        except Exception as e:
            print(f"Error registering skill {skill_class.skill_id}: {e}")
            return None

    def unregister_skill(self, skill_id: str) -> bool:
        """注销技能

        Args:
            skill_id: 技能 ID

        Returns:
            bool: 是否注销成功
        """
        if skill_id not in self._skills:
            return False

        skill = self._skills[skill_id]

        # 从名称映射中移除
        if skill.skill_name in self._skill_names:
            del self._skill_names[skill.skill_name]

        # 删除技能实例
        del self._skills[skill_id]
        return True

    def get_skill(self, skill_id: str) -> Optional[BaseSkill]:
        """获取技能

        Args:
            skill_id: 技能 ID

        Returns:
            Optional[BaseSkill]: 技能实例，如果不存在返回 None
        """
        return self._skills.get(skill_id)

    def get_skill_by_name(self, name: str) -> Optional[BaseSkill]:
        """根据名称获取技能

        Args:
            name: 技能名称

        Returns:
            Optional[BaseSkill]: 技能实例，如果不存在返回 None
        """
        skill_id = self._skill_names.get(name)
        if skill_id:
            return self._skills.get(skill_id)
        return None

    def get_skill_by_tag(self, tag: str) -> List[BaseSkill]:
        """根据标签获取技能

        Args:
            tag: 技能标签

        Returns:
            List[BaseSkill]: 技能实例列表
        """
        return [
            skill for skill in self._skills.values()
            if tag in skill.skill_tags
        ]

    def search_skills(self, query: str) -> List[Dict[str, Any]]:
        """搜索技能

        Args:
            query: 搜索关键词

        Returns:
            List[Dict]: 技能元数据列表
        """
        query = query.lower()
        results = []

        for skill in self._skills.values():
            # 在名称、描述、标签中搜索
            if (query in skill.skill_name.lower() or
                query in skill.skill_description.lower() or
                any(query in tag.lower() for tag in skill.skill_tags)):
                results.append(skill.get_metadata().__dict__)

        return results

    def list_skills(self) -> List[Dict[str, Any]]:
        """列出所有已注册的技能

        Returns:
            List[Dict]: 技能元数据列表
        """
        return [skill.get_metadata().__dict__ for skill in self._skills.values()]

    def execute_skill(self, skill_id: str, **kwargs) -> Any:
        """执行技能

        Args:
            skill_id: 技能 ID
            **kwargs: 执行参数

        Returns:
            Any: 技能执行结果
        """
        skill = self.get_skill(skill_id)

        if not skill:
            raise ValueError(f"Skill not found: {skill_id}")

        if not skill.enabled:
            raise ValueError(f"Skill is disabled: {skill_id}")

        # 验证参数
        if not skill.validate_params(kwargs):
            raise ValueError(f"Invalid parameters for skill: {skill_id}")

        return skill.execute(**kwargs)

    # =========================================================================
    # 管理方法
    # =========================================================================

    def enable_skill(self, skill_id: str) -> bool:
        """启用技能

        Args:
            skill_id: 技能 ID

        Returns:
            bool: 是否成功启用
        """
        skill = self.get_skill(skill_id)
        if skill:
            skill.enabled = True
            return True
        return False

    def disable_skill(self, skill_id: str) -> bool:
        """禁用技能

        Args:
            skill_id: 技能 ID

        Returns:
            bool: 是否成功禁用
        """
        skill = self.get_skill(skill_id)
        if skill:
            skill.enabled = False
            return True
        return False

    def reload_all(self) -> None:
        """重新加载所有技能"""
        # 清空所有技能
        self._skills.clear()
        self._skill_names.clear()

        # 重新加载内置技能
        self._load_builtin_skills()

    def to_dict(self) -> Dict[str, Any]:
        """将技能管理器转换为字典

        Returns:
            Dict: 技能管理器字典
        """
        return {
            "agent_id": self.agent_id,
            "skills_count": len(self._skills),
            "skills": self.list_skills(),
        }

    def __str__(self) -> str:
        """字符串表示"""
        return f"SkillManager(agent_id={self.agent_id}, skills={len(self._skills)})"

    def __repr__(self) -> str:
        """详细字符串表示"""
        return f"<SkillManager(agent_id='{self.agent_id}', skills={len(self._skills)})>"
