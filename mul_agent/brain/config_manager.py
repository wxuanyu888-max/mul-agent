"""Config Manager - 配置管理器"""

import json
from pathlib import Path
from typing import Any, Dict, Optional


class ConfigManager:
    """配置管理器

    负责管理 Agent 的配置
    """

    def __init__(self, storage_dir: Optional[str] = None):
        """初始化配置管理器

        Args:
            storage_dir: 存储目录，如果不提供则使用默认目录
        """
        if storage_dir:
            self.storage_dir = Path(storage_dir)
        else:
            # 默认存储目录
            self.storage_dir = Path.home() / ".mul_agent" / "storage"

        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.config_file = self.storage_dir / "config.json"
        self._config: Dict[str, Any] = {}
        self._load_config()

    def _load_config(self) -> None:
        """加载配置"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    self._config = json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                print(f"Error loading config: {e}")
                self._config = {}
        else:
            self._config = {}

    def _save_config(self) -> None:
        """保存配置"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self._config, f, indent=2, ensure_ascii=False)
        except IOError as e:
            print(f"Error saving config: {e}")

    def get_config(self, key: Optional[str] = None, default: Any = None) -> Any:
        """获取配置

        Args:
            key: 配置键，如果不提供则返回完整配置
            default: 默认值

        Returns:
            Any: 配置值
        """
        if key is None:
            return self._config.copy()

        keys = key.split(".")
        value = self._config

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        return value

    def set_config(self, key: str, value: Any) -> bool:
        """设置配置

        Args:
            key: 配置键
            value: 配置值

        Returns:
            bool: 是否设置成功
        """
        keys = key.split(".")
        config = self._config

        # 遍历到倒数第二个键
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]

        # 设置最后一个键
        config[keys[-1]] = value
        self._save_config()
        return True

    def delete_config(self, key: str) -> bool:
        """删除配置

        Args:
            key: 配置键

        Returns:
            bool: 是否删除成功
        """
        keys = key.split(".")
        config = self._config

        # 遍历到倒数第二个键
        for k in keys[:-1]:
            if k not in config:
                return False
            config = config[k]

        # 删除最后一个键
        if keys[-1] in config:
            del config[keys[-1]]
            self._save_config()
            return True
        return False

    def has_config(self, key: str) -> bool:
        """检查配置是否存在

        Args:
            key: 配置键

        Returns:
            bool: 是否存在
        """
        keys = key.split(".")
        value = self._config

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return False

        return True

    def clear_config(self) -> None:
        """清空配置"""
        self._config = {}
        self._save_config()

    def get_agent_config(self, agent_id: str) -> Dict[str, Any]:
        """获取 Agent 配置

        Args:
            agent_id: Agent ID

        Returns:
            Dict: Agent 配置
        """
        return self.get_config(f"agents.{agent_id}", {})

    def set_agent_config(self, agent_id: str, config: Dict[str, Any]) -> bool:
        """设置 Agent 配置

        Args:
            agent_id: Agent ID
            config: Agent 配置

        Returns:
            bool: 是否设置成功
        """
        return self.set_config(f"agents.{agent_id}", config)

    def list_agents(self) -> list:
        """列出所有 Agent

        Returns:
            list: Agent ID 列表
        """
        agents = self.get_config("agents", {})
        if isinstance(agents, dict):
            return list(agents.keys())
        return []

    def to_dict(self) -> Dict[str, Any]:
        """将配置管理器转换为字典

        Returns:
            Dict: 配置管理器字典
        """
        return {
            "storage_dir": str(self.storage_dir),
            "config_file": str(self.config_file),
            "config": self._config.copy(),
        }

    def __str__(self) -> str:
        """字符串表示"""
        return f"ConfigManager(storage_dir={self.storage_dir})"

    def __repr__(self) -> str:
        """详细字符串表示"""
        return f"<ConfigManager(storage_dir='{self.storage_dir}')>"
