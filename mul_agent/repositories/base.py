"""Base Repository - 基础 Repository 类"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class BaseRepository(ABC):
    """Repository 基类"""

    @abstractmethod
    def find_by_id(self, id: str) -> Optional[Dict[str, Any]]:
        """根据 ID 查找"""
        pass

    @abstractmethod
    def find_all(self) -> List[Dict[str, Any]]:
        """查找所有"""
        pass

    @abstractmethod
    def save(self, id: str, data: Dict[str, Any]) -> bool:
        """保存"""
        pass

    @abstractmethod
    def delete(self, id: str) -> bool:
        """删除"""
        pass

    @abstractmethod
    def exists(self, id: str) -> bool:
        """检查是否存在"""
        pass
