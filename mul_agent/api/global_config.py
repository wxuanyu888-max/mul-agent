"""Global LLM Config - 全局 LLM 配置管理

所有 agent 共享同一个 LLM 配置
配置文件存储在 wang/.global_config/llm_config.json
"""
import json
from pathlib import Path
from typing import Any, Dict, Optional


class GlobalLLMConfig:
    """全局 LLM 配置管理器"""

    def __init__(self, wang_dir: Path):
        self.wang_dir = wang_dir
        self.config_dir = wang_dir / ".global_config"
        self.config_file = self.config_dir / "llm_config.json"
        self.config_dir.mkdir(parents=True, exist_ok=True)

    def get_config(self) -> Optional[Dict[str, Any]]:
        """获取全局 LLM 配置"""
        if not self.config_file.exists():
            return None

        try:
            with open(self.config_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None

    def save_config(self, config: Dict[str, Any]) -> bool:
        """保存全局 LLM 配置"""
        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            return True
        except Exception:
            return False

    def delete_config(self) -> bool:
        """删除全局 LLM 配置"""
        try:
            if self.config_file.exists():
                self.config_file.unlink()
            return True
        except Exception:
            return False
