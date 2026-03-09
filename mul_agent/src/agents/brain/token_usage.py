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
            agent_id="wang",
            model="claude-sonnet-4-20250514",
            function="think",
            input_tokens=100,
            output_tokens=50
        )
        stats = center.get_usage("wang")
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

            # 添加详细记录（用于审计和调试）
            # 记录每次 LLM 调用的输入输出文本、上下文来源、工具调用
            log_entry = {
                "timestamp": now.isoformat(),
                "model": model,
                "function": function,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
            }

            # 添加输入输出文本（如果提供）
            if extra:
                if "input" in extra:
                    log_entry["input_text"] = extra["input"]
                if "output" in extra:
                    log_entry["output_text"] = extra["output"]
                if "context_sources" in extra:
                    log_entry["context_sources"] = extra["context_sources"]
                if "tool_calls" in extra:
                    log_entry["tool_calls"] = extra["tool_calls"]
                # 保留其他 extra 字段（向后兼容）
                for key, value in extra.items():
                    if key not in ("input", "output", "context_sources", "tool_calls"):
                        log_entry[key] = value

            usage["llm_logs"].append(log_entry)
            # 保留最近 200 条记录
            if len(usage["llm_logs"]) > 200:
                usage["llm_logs"] = usage["llm_logs"][-200:]

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
            "llm_logs": []  # LLM 调用日志（包含输入输出文本、上下文来源、工具调用）
        }

    def _load_usage(self, agent_id: str) -> Dict[str, Any]:
        """加载使用统计

        优先从 storage/token_usage/{agent_id}.json 加载
        """
        # 检查缓存
        if agent_id in self._usage_cache:
            return self._usage_cache[agent_id]

        # 优先从 storage/token_usage/{agent_id}.json 加载
        try:
            json_file_path = self.config_manager.token_usage_dir / f"{agent_id}.json"
            if json_file_path.exists():
                with open(json_file_path, "r", encoding="utf-8") as f:
                    usage = json.load(f)
                # 兼容旧数据：如果有 logs 字段，重命名为 llm_logs
                if "logs" in usage and "llm_logs" not in usage:
                    usage["llm_logs"] = usage["logs"]
                    del usage["logs"]
                # 确保 llm_logs 字段存在
                if "llm_logs" not in usage:
                    usage["llm_logs"] = []
                self._usage_cache[agent_id] = usage
                return usage
        except Exception as e:
            print(f"TokenUsageCenter._load_usage JSON load error: {e}")

        # 创建新的空白统计
        usage = self._create_empty_usage(agent_id)
        self._usage_cache[agent_id] = usage
        return usage

    def _save_usage(self, agent_id: str, usage: Dict[str, Any]) -> bool:
        """保存使用统计到 storage/token_usage/ 目录

        只保存 JSON 文件（用于程序读取和存储完整数据）
        Markdown 文件不再保存（因为 token_usage 已经移到 storage 目录）
        """
        try:
            # 保存到 storage/token_usage/{agent_id}.json
            token_usage_dir = self.config_manager.token_usage_dir
            token_usage_dir.mkdir(parents=True, exist_ok=True)

            json_file_path = token_usage_dir / f"{agent_id}.json"
            with open(json_file_path, "w", encoding="utf-8") as f:
                json.dump(usage, f, indent=2, ensure_ascii=False)

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
        logs = usage.get("llm_logs", [])

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

        # 添加 LLM 调用日志（详细记录每次远程调用）
        if logs:
            lines.extend([
                "",
                "## LLM 调用日志",
                "",
                "每次调用包含：输入文本、输出文本、上下文来源地址、工具调用情况",
                "",
            ])
            for i, log in enumerate(logs):
                lines.append(f"### 调用 #{i+1}")
                lines.append("")
                lines.append(f"- **时间**: {log.get('timestamp', '')}")
                lines.append(f"- **模型**: {log.get('model', '')}")
                lines.append(f"- **功能**: {log.get('function', '')}")
                lines.append(f"- **Token**: 输入={log.get('input_tokens', 0)}, 输出={log.get('output_tokens', 0)}")

                # 输入文本
                input_text = log.get('input_text', '')
                if input_text:
                    lines.append("")
                    lines.append("**输入文本**:")
                    lines.append("```")
                    # 只显示前 2000 字符，避免文件过大
                    input_preview = input_text[:2000] + "..." if len(input_text) > 2000 else input_text
                    lines.append(input_preview)
                    lines.append("```")

                # 输出文本
                output_text = log.get('output_text', '')
                if output_text:
                    lines.append("")
                    lines.append("**输出文本**:")
                    lines.append("```")
                    output_preview = output_text[:2000] + "..." if len(output_text) > 2000 else output_text
                    lines.append(output_preview)
                    lines.append("```")

                # 上下文来源地址列表
                context_sources = log.get('context_sources', [])
                if context_sources:
                    lines.append("")
                    lines.append("**上下文来源地址**:")
                    for src in context_sources:
                        lines.append(f"- {src}")

                # 工具调用情况
                tool_calls = log.get('tool_calls', [])
                if tool_calls:
                    lines.append("")
                    lines.append("**工具调用**:")
                    for tool in tool_calls:
                        if isinstance(tool, dict):
                            tool_name = tool.get('name', 'unknown')
                            tool_input = tool.get('input', '')
                            lines.append(f"- **{tool_name}**: {tool_input[:200] if tool_input else 'N/A'}")
                        else:
                            lines.append(f"- {tool}")

                lines.append("")
                lines.append("---")
                lines.append("")

        return "\n".join(lines)
