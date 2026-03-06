"""Token Usage Center - Token 使用统计中心"""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional


class TokenUsageCenter:
    """Token 使用统计中心

    记录每个 Agent 的 Token 消耗和远程 LLM 访问次数。
    支持按模型、按功能、按日期统计。

    使用方式：
        center = TokenUsageCenter(config_manager)
        center.record_usage(
            agent_id="core_brain",
            model="claude-sonnet-4-20250514",
            function="think",
            input_tokens=100,
            output_tokens=50
        )
        stats = center.get_usage("core_brain")
    """

    # 功能类型枚举
    FUNCTION_THINK = "think"  # 决策
    FUNCTION_CHAT = "chat"    # 对话
    FUNCTION_EVOLUTION = "evolution"  # 进化
    FUNCTION_ANALYSIS = "analysis"  # 分析
    FUNCTION_OTHER = "other"  # 其他

    def __init__(self, config_manager):
        """初始化 Token 使用中心

        Args:
            config_manager: ConfigManager 实例
        """
        self.config_manager = config_manager
        self._usage_cache: Dict[str, Dict] = {}

    def record_usage(
        self,
        agent_id: str,
        model: str,
        function: str,
        input_tokens: int,
        output_tokens: int,
        extra: Optional[Dict[str, Any]] = None
    ) -> bool:
        """记录 Token 使用

        Args:
            agent_id: Agent ID
            model: 使用的模型名称
            function: 功能类型 (think/chat/evolution/analysis/other)
            input_tokens: 输入 Token 数
            output_tokens: 输出 Token 数
            extra: 额外信息（可选）

        Returns:
            bool: 是否成功记录
        """
        try:
            # 加载或初始化使用统计
            usage = self._load_usage(agent_id)

            # 更新时间戳
            now = datetime.now()
            usage["updated_at"] = now.isoformat()
            usage["last_access_time"] = now.isoformat()

            # 更新总计
            usage["totals"]["input_tokens"] += input_tokens
            usage["totals"]["output_tokens"] += output_tokens
            usage["totals"]["total_tokens"] += input_tokens + output_tokens
            usage["totals"]["access_count"] += 1

            # 更新模型统计
            if model not in usage["by_model"]:
                usage["by_model"][model] = {
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "total_tokens": 0,
                    "access_count": 0
                }
            usage["by_model"][model]["input_tokens"] += input_tokens
            usage["by_model"][model]["output_tokens"] += output_tokens
            usage["by_model"][model]["total_tokens"] += input_tokens + output_tokens
            usage["by_model"][model]["access_count"] += 1

            # 更新功能统计
            if function not in usage["by_function"]:
                usage["by_function"][function] = {
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "total_tokens": 0,
                    "access_count": 0
                }
            usage["by_function"][function]["input_tokens"] += input_tokens
            usage["by_function"][function]["output_tokens"] += output_tokens
            usage["by_function"][function]["total_tokens"] += input_tokens + output_tokens
            usage["by_function"][function]["access_count"] += 1

            # 更新每日统计
            date_key = now.strftime("%Y-%m-%d")
            if date_key not in usage["by_date"]:
                usage["by_date"][date_key] = {
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "total_tokens": 0,
                    "access_count": 0
                }
            usage["by_date"][date_key]["input_tokens"] += input_tokens
            usage["by_date"][date_key]["output_tokens"] += output_tokens
            usage["by_date"][date_key]["total_tokens"] += input_tokens + output_tokens
            usage["by_date"][date_key]["access_count"] += 1

            # 添加详细记录（用于审计）
            if extra:
                log_entry = {
                    "timestamp": now.isoformat(),
                    "model": model,
                    "function": function,
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "extra": extra
                }
                usage["logs"].append(log_entry)
                # 保留最近 100 条记录
                if len(usage["logs"]) > 100:
                    usage["logs"] = usage["logs"][-100:]

            # 保存到文件
            self._save_usage(agent_id, usage)

            # 更新缓存
            self._usage_cache[agent_id] = usage

            return True

        except Exception as e:
            print(f"TokenUsageCenter.record_usage error: {e}")
            return False

    def get_usage(self, agent_id: str) -> Dict[str, Any]:
        """获取 Agent 的使用统计

        Args:
            agent_id: Agent ID

        Returns:
            Dict: 使用统计数据
        """
        return self._load_usage(agent_id)

    def get_usage_summary(self, agent_id: str) -> Dict[str, Any]:
        """获取使用统计摘要

        Args:
            agent_id: Agent ID

        Returns:
            Dict: 使用统计摘要
        """
        usage = self._load_usage(agent_id)
        totals = usage.get("totals", {})

        return {
            "agent_id": agent_id,
            "total_tokens": totals.get("total_tokens", 0),
            "input_tokens": totals.get("input_tokens", 0),
            "output_tokens": totals.get("output_tokens", 0),
            "access_count": totals.get("access_count", 0),
            "last_access_time": usage.get("last_access_time"),
            "updated_at": usage.get("updated_at")
        }

    def reset_usage(self, agent_id: str) -> bool:
        """重置使用统计

        Args:
            agent_id: Agent ID

        Returns:
            bool: 是否成功重置
        """
        try:
            # 创建新的空白统计
            usage = self._create_empty_usage(agent_id)
            usage["created_at"] = datetime.now().isoformat()
            usage["updated_at"] = datetime.now().isoformat()

            # 保存
            self._save_usage(agent_id, usage)
            self._usage_cache[agent_id] = usage

            return True
        except Exception as e:
            print(f"TokenUsageCenter.reset_usage error: {e}")
            return False

    def get_all_agents_usage(self) -> Dict[str, Dict[str, Any]]:
        """获取所有 Agent 的使用统计

        Returns:
            Dict: 所有 Agent 的使用统计
        """
        agents = self.config_manager.list_agents()
        result = {}
        for agent_id in agents:
            result[agent_id] = self.get_usage_summary(agent_id)
        return result

    def _create_empty_usage(self, agent_id: str) -> Dict[str, Any]:
        """创建空白的使用统计结构"""
        return {
            "version": "1.0",
            "agent_id": agent_id,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "last_access_time": None,
            "totals": {
                "input_tokens": 0,
                "output_tokens": 0,
                "total_tokens": 0,
                "access_count": 0
            },
            "by_model": {},
            "by_function": {},
            "by_date": {},
            "logs": []
        }

    def _load_usage(self, agent_id: str) -> Dict[str, Any]:
        """加载使用统计"""
        # 检查缓存
        if agent_id in self._usage_cache:
            return self._usage_cache[agent_id]

        # 从文件加载
        try:
            content = self.config_manager.load_text_content(agent_id, "token_usage")
            if content:
                return self._parse_token_usage_md(content, agent_id)
        except Exception:
            pass

        # 创建新的空白统计
        usage = self._create_empty_usage(agent_id)
        self._usage_cache[agent_id] = usage
        return usage

    def _save_usage(self, agent_id: str, usage: Dict[str, Any]) -> bool:
        """保存使用统计到文件"""
        try:
            # 转换为 Markdown 格式
            md_content = self._to_token_usage_md(usage)

            # 保存到文件
            agent_dir = self.config_manager.agents_dir / agent_id
            agent_dir.mkdir(parents=True, exist_ok=True)

            file_path = agent_dir / "token_usage.md"
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(md_content)

            # 更新缓存
            self._usage_cache[agent_id] = usage

            return True
        except Exception as e:
            print(f"TokenUsageCenter._save_usage error: {e}")
            return False

    def _parse_token_usage_md(self, content: str, agent_id: str) -> Dict[str, Any]:
        """解析 Markdown 格式的 Token 使用统计"""
        usage = self._create_empty_usage(agent_id)

        # 解析 YAML front matter
        yaml_match = re.match(r'^---\n(.*?)\n---', content, re.DOTALL)
        if yaml_match:
            yaml_content = yaml_match.group(1)
            try:
                import yaml
                front_matter = yaml.safe_load(yaml_content)
                if front_matter:
                    usage["version"] = front_matter.get("version", "1.0")
                    usage["agent_id"] = front_matter.get("agent_id", agent_id)
                    usage["created_at"] = front_matter.get("created_at")
                    usage["updated_at"] = front_matter.get("updated_at")
                    usage["last_access_time"] = front_matter.get("last_access_time")
            except Exception:
                pass

        # 解析表格数据（简化解析，用于兼容旧格式）
        lines = content.split('\n')
        current_section = None

        for line in lines:
            line = line.strip()

            # 检测章节
            if line.startswith("## 总计"):
                current_section = "totals"
            elif line.startswith("## 按模型统计"):
                current_section = "by_model"
            elif line.startswith("## 按功能统计"):
                current_section = "by_function"
            elif line.startswith("## 每日统计"):
                current_section = "by_date"

        return usage

    def _to_token_usage_md(self, usage: Dict[str, Any]) -> str:
        """将使用统计转换为 Markdown 格式"""
        totals = usage.get("totals", {})
        by_model = usage.get("by_model", {})
        by_function = usage.get("by_function", {})
        by_date = usage.get("by_date", {})

        lines = [
            "---",
            f"version: \"{usage.get('version', '1.0')}\"",
            f"agent_id: {usage.get('agent_id', 'unknown')}",
            f"created_at: \"{usage.get('created_at', '')}\"",
            f"updated_at: \"{usage.get('updated_at', '')}\"",
            "---",
            "",
            "# Token 使用统计",
            "",
            "## 总计",
            "",
            "| 指标 | 数值 |",
            "|------|------|",
            f"| 总输入 Token | {totals.get('input_tokens', 0)} |",
            f"| 总输出 Token | {totals.get('output_tokens', 0)} |",
            f"| 总 Token | {totals.get('total_tokens', 0)} |",
            f"| 远程访问次数 | {totals.get('access_count', 0)} |",
            f"| 最后访问时间 | {usage.get('last_access_time', '-')} |",
            "",
            "## 按模型统计",
            "",
            "| 模型 | 输入 Token | 输出 Token | 总 Token | 访问次数 |",
            "|------|----------|-----------|---------|---------|",
        ]

        for model, stats in by_model.items():
            lines.append(
                f"| {model} | {stats.get('input_tokens', 0)} | "
                f"{stats.get('output_tokens', 0)} | {stats.get('total_tokens', 0)} | "
                f"{stats.get('access_count', 0)} |"
            )

        lines.extend([
            "",
            "## 按功能统计",
            "",
            "| 功能 | 输入 Token | 输出 Token | 总 Token | 访问次数 |",
            "|------|----------|-----------|---------|---------|",
        ])

        function_names = {
            "think": "决策",
            "chat": "对话",
            "evolution": "进化",
            "analysis": "分析",
            "other": "其他"
        }
        for func, stats in by_function.items():
            func_name = function_names.get(func, func)
            lines.append(
                f"| {func_name} ({func}) | {stats.get('input_tokens', 0)} | "
                f"{stats.get('output_tokens', 0)} | {stats.get('total_tokens', 0)} | "
                f"{stats.get('access_count', 0)} |"
            )

        lines.extend([
            "",
            "## 每日统计",
            "",
            "| 日期 | 输入 Token | 输出 Token | 总 Token | 访问次数 |",
            "|------|----------|-----------|---------|---------|",
        ])

        # 按日期倒序排列
        for date in sorted(by_date.keys(), reverse=True):
            stats = by_date[date]
            lines.append(
                f"| {date} | {stats.get('input_tokens', 0)} | "
                f"{stats.get('output_tokens', 0)} | {stats.get('total_tokens', 0)} | "
                f"{stats.get('access_count', 0)} |"
            )

        return "\n".join(lines)
