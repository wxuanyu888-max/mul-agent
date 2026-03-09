"""
Config - 配置系统
"""

__all__ = ["ConfigManager", "Config"]


class Config:
    """配置基类"""

    def __init__(self, data: dict | None = None):
        self._data = data or {}

    def get(self, key: str, default=None):
        return self._data.get(key, default)

    def set(self, key: str, value) -> None:
        self._data[key] = value

    def to_dict(self) -> dict:
        return self._data.copy()


class ConfigManager:
    """配置管理器"""

    def __init__(self, config_dir: str | None = None):
        self.config_dir = config_dir
        self._configs: dict[str, Config] = {}

    def get(self, name: str) -> Config | None:
        return self._configs.get(name)

    def set(self, name: str, config: Config) -> None:
        self._configs[name] = config

    def list(self) -> list[str]:
        return list(self._configs.keys())
