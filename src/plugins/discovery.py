"""Plugins - 插件发现和加载"""

import importlib
import importlib.util
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
import logging
import json

from mul_agent.plugins.sdk import PluginAPI
from mul_agent.plugins.types import PluginManifest, ToolRegistry, HookRegistry, CommandRegistry

logger = logging.getLogger(__name__)

# 插件入口文件名
PLUGIN_ENTRY_FILES = ["__init__.py", "plugin.py", "main.py"]

# 插件清单文件名
PLUGIN_MANIFEST_FILES = ["plugin_manifest.json", "manifest.json"]


@dataclass
class PluginCandidate:
    """插件候选"""
    name: str
    path: Path
    origin: str  # bundled, workspace, managed
    manifest: Optional[Dict[str, Any]] = None


def discover_plugins(
    workspace_dir: Optional[Path] = None,
    bundled_dir: Optional[Path] = None,
    managed_dir: Optional[Path] = None,
) -> List[PluginCandidate]:
    """
    发现插件

    Args:
        workspace_dir: 工作区目录
        bundled_dir: 内置插件目录
        managed_dir: 管理的插件目录

    Returns:
        插件候选列表
    """
    candidates = []

    # 扫描内置插件
    if bundled_dir and bundled_dir.exists():
        candidates.extend(_scan_directory(bundled_dir, origin="bundled"))

    # 扫描工作区插件
    if workspace_dir and workspace_dir.exists():
        workspace_plugins = workspace_dir / "plugins"
        if workspace_plugins.exists():
            candidates.extend(_scan_directory(workspace_plugins, origin="workspace"))

    # 扫描管理的插件
    if managed_dir and managed_dir.exists():
        candidates.extend(_scan_directory(managed_dir, origin="managed"))

    return candidates


def _scan_directory(directory: Path, origin: str) -> List[PluginCandidate]:
    """扫描目录中的插件"""
    candidates = []

    for item in directory.iterdir():
        if not item.is_dir() or item.name.startswith(('.', '_')):
            continue
        if item.name in ('__pycache__', 'node_modules'):
            continue

        # 检查是否有入口文件
        has_entry = any((item / f).exists() for f in PLUGIN_ENTRY_FILES)
        if not has_entry:
            continue

        # 尝试加载清单
        manifest = _load_manifest(item)

        candidates.append(PluginCandidate(
            name=item.name,
            path=item,
            origin=origin,
            manifest=manifest,
        ))

    return candidates


def _load_manifest(plugin_dir: Path) -> Optional[Dict[str, Any]]:
    """加载插件清单"""
    for manifest_file in PLUGIN_MANIFEST_FILES:
        manifest_path = plugin_dir / manifest_file
        if manifest_path.exists():
            try:
                with open(manifest_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load manifest from {manifest_path}: {e}")
    return None


def load_plugin(plugin_candidate: PluginCandidate, api: PluginAPI) -> Optional[PluginManifest]:
    """
    加载单个插件

    Args:
        plugin_candidate: 插件候选
        api: PluginAPI 实例

    Returns:
        插件清单（如果加载成功）
    """
    plugin_path = plugin_candidate.path

    # 查找入口文件
    entry_file = _find_entry_file(plugin_path)
    if not entry_file:
        logger.warning(f"No entry file found in {plugin_path}")
        return None

    try:
        # 动态导入插件模块
        spec = importlib.util.spec_from_file_location(
            f"plugin_{plugin_candidate.name}",
            entry_file
        )
        if spec is None or spec.loader is None:
            logger.warning(f"Failed to load spec for {entry_file}")
            return None

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        # 调用插件初始化函数
        if not hasattr(module, 'plugin_init'):
            logger.warning(f"No plugin_init function in {entry_file}")
            return None

        # 执行初始化
        manifest = module.plugin_init(api)

        if not isinstance(manifest, PluginManifest):
            logger.warning(f"plugin_init did not return PluginManifest: {manifest}")
            return None

        return manifest

    except Exception as e:
        logger.error(f"Failed to load plugin {plugin_candidate.name}: {e}")
        return None


def _find_entry_file(plugin_dir: Path) -> Optional[Path]:
    """查找插件入口文件"""
    for entry_file in PLUGIN_ENTRY_FILES:
        candidate = plugin_dir / entry_file
        if candidate.exists():
            return candidate
    return None


# ========== 插件运行时 ==========

class PluginRuntime:
    """插件运行时"""

    def __init__(
        self,
        workspace_dir: Optional[Path] = None,
        bundled_dir: Optional[Path] = None,
        managed_dir: Optional[Path] = None,
    ):
        self.workspace_dir = workspace_dir
        self.bundled_dir = bundled_dir
        self.managed_dir = managed_dir

        # 注册表
        self.tool_registry = ToolRegistry()
        self.hook_registry = HookRegistry()
        self.command_registry = CommandRegistry()

        # API 实例
        self.api = PluginAPI(
            tool_registry=self.tool_registry,
            hook_registry=self.hook_registry,
            command_registry=self.command_registry,
        )

        # 已加载插件
        self._loaded_plugins: List[PluginManifest] = []

    def load_all(self) -> List[PluginManifest]:
        """加载所有发现的插件"""
        candidates = discover_plugins(
            workspace_dir=self.workspace_dir,
            bundled_dir=self.bundled_dir,
            managed_dir=self.managed_dir,
        )

        loaded = []
        for candidate in candidates:
            manifest = load_plugin(candidate, self.api)
            if manifest:
                loaded.append(manifest)
                self.api.load_plugin(manifest)

        self._loaded_plugins = loaded
        return loaded

    @property
    def loaded_plugins(self) -> List[PluginManifest]:
        """获取已加载的插件列表"""
        return self._loaded_plugins.copy()
