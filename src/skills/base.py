"""Base Skill - 技能基类"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from pathlib import Path


@dataclass
class SkillMetadata:
    """技能元数据 - 用于提示词构建"""
    skill_id: str = ""
    skill_name: str = ""
    skill_version: str = "1.0.0"
    skill_description: str = ""
    skill_tags: List[str] = field(default_factory=list)
    priority: int = 5  # 1-10，数字越大优先级越高
    enabled: bool = True
    requires_confirmation: bool = False
    # Token 相关
    content_token_count: int = 0  # 内容占用的 token 数
    full_content: str = ""  # 完整内容（可能被截断）


class BaseSkill(ABC):
    """所有技能的基类"""

    # 技能元数据（类级别默认值）
    skill_id: str = "base_skill"
    skill_name: str = "Base Skill"
    skill_version: str = "1.0.0"
    skill_description: str = "Base skill for all skills"
    skill_tags: List[str] = []
    priority: int = 5
    requires_confirmation: bool = False

    # 实例级别配置
    enabled: bool = True

    def __init__(self, config_manager=None, agent_id: str = None):
        """初始化技能

        Args:
            config_manager: 配置管理器
            agent_id: Agent ID
        """
        self.config_manager = config_manager
        self.agent_id = agent_id or "default"
        self._initialized = False
        self._content_cache: Optional[str] = None  # 内容缓存

    def initialize(self) -> bool:
        """初始化技能

        Returns:
            bool: 是否初始化成功
        """
        if self._initialized:
            return True

        try:
            self._initialize()
            self._initialized = True
            return True
        except Exception as e:
            print(f"Error initializing skill {self.skill_id}: {e}")
            return False

    @abstractmethod
    def _initialize(self) -> None:
        """技能初始化逻辑（由子类实现）"""
        pass

    @abstractmethod
    def execute(self, **kwargs) -> Any:
        """执行技能

        Args:
            **kwargs: 执行参数

        Returns:
            Any: 执行结果
        """
        pass

    def validate_params(self, params: Dict[str, Any]) -> bool:
        """验证参数

        Args:
            params: 参数字典

        Returns:
            bool: 参数是否有效
        """
        return True

    def get_metadata(self) -> SkillMetadata:
        """获取技能元数据

        Returns:
            SkillMetadata: 技能元数据
        """
        return SkillMetadata(
            skill_id=self.skill_id,
            skill_name=self.skill_name,
            skill_version=self.skill_version,
            skill_description=self.skill_description,
            skill_tags=self.skill_tags.copy(),
            priority=self.priority,
            enabled=self.enabled,
            requires_confirmation=self.requires_confirmation,
        )

    def get_content_for_prompt(self, max_tokens: int = 500) -> str:
        """获取用于提示词的内容（支持截断）

        Args:
            max_tokens: 最大 token 数

        Returns:
            str: 截断后的内容
        """
        if self._content_cache is not None:
            return self._content_cache

        # 生成内容（由子类决定如何生成）
        content = self._generate_prompt_content()

        # 截断处理
        truncated_content = self._truncate_content(content, max_tokens)

        return truncated_content

    def _generate_prompt_content(self) -> str:
        """生成提示词内容（由子类覆盖）

        Returns:
            str: 提示词内容
        """
        # 默认返回技能描述
        return self.skill_description

    def _truncate_content(self, content: str, max_tokens: int) -> str:
        """截断内容到指定 token 数

        Args:
            content: 原始内容
            max_tokens: 最大 token 数

        Returns:
            str: 截断后的内容
        """
        if not content:
            return ""

        # 简单估算：1 token ≈ 4 个英文字符或 1.5 个中文字符
        # 这里使用字符数近似计算
        estimated_chars = max_tokens * 4  # 保守估计

        if len(content) <= estimated_chars:
            return content

        # 截断并添加标记
        truncated = content[:estimated_chars]
        # 尝试在完整句子处截断
        for sep in ['.\n', '\n\n', '. ', '。', '\n']:
            last_sep = truncated.rfind(sep)
            if last_sep > estimated_chars * 0.8:
                truncated = truncated[:last_sep + len(sep)]
                break

        return truncated + "\n\n...[内容已截断]"

    def to_dict(self) -> Dict[str, Any]:
        """将技能转换为字典

        Returns:
            Dict: 技能字典
        """
        return {
            **self.get_metadata().__dict__,
            "config_manager": self.config_manager.__class__.__name__ if self.config_manager else None,
        }

    def __str__(self) -> str:
        """字符串表示"""
        return f"{self.skill_name} v{self.skill_version}"

    def __repr__(self) -> str:
        """详细字符串表示"""
        return f"<{self.__class__.__name__}(id={self.skill_id}, name={self.skill_name})>"
