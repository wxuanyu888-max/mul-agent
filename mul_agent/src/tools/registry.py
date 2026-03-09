"""Tool Registry - 工具注册表系统

参考 Claude Code 的设计：
1. 使用装饰器注册工具
2. 自动生成工具签名和文档
3. LLM 可以程序化查询可用工具
"""

import inspect
from typing import Any, Callable, Dict, List, Optional, get_type_hints
from dataclasses import dataclass, field
from enum import Enum


class ToolStatus(Enum):
    """工具状态"""
    READY = "ready"
    BUSY = "busy"
    ERROR = "error"


@dataclass
class ToolParameter:
    """工具参数定义"""
    name: str
    type: str
    description: str
    required: bool = True
    default: Any = None


@dataclass
class ToolDefinition:
    """工具定义"""
    name: str
    description: str
    func: Callable
    parameters: List[ToolParameter] = field(default_factory=list)
    returns: str = "Any"
    examples: List[str] = field(default_factory=list)
    status: ToolStatus = ToolStatus.READY

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式，供 LLM 使用"""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": [
                {
                    "name": p.name,
                    "type": p.type,
                    "description": p.description,
                    "required": p.required,
                    "default": p.default
                }
                for p in self.parameters
            ],
            "returns": self.returns,
            "examples": self.examples,
            "status": self.status.value
        }

    def to_prompt(self) -> str:
        """生成提示词格式，供 LLM 理解"""
        params_str = ", ".join(
            f"{p.name}: {p.type}" + (" = " + str(p.default) if not p.required else "")
            for p in self.parameters
        )
        required_params = [p.name for p in self.parameters if p.required]

        return f"""### {self.name}
{self.description}

**参数**: {params_str or "无"}
**必需参数**: {', '.join(required_params) or "无"}
**返回**: {self.returns}

{f'**示例**: {self.examples[0]}' if self.examples else ''}
"""


class ToolRegistry:
    """工具注册表 - 单例模式"""

    _instance = None
    _tools: Dict[str, ToolDefinition] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def get_instance(cls) -> "ToolRegistry":
        """获取单例实例"""
        return cls()

    def register(
        self,
        name: str = None,
        description: str = "",
        examples: List[str] = None
    ):
        """工具注册装饰器

        用法:
            @tool_registry.register(name="read_file", description="读取文件内容")
            def read_file(path: str, range: Optional[str] = None) -> str:
                ...
        """
        def decorator(func: Callable) -> Callable:
            nonlocal name
            if name is None:
                name = func.__name__

            # 获取函数签名
            sig = inspect.signature(func)
            type_hints = get_type_hints(func)

            # 解析参数
            parameters = []
            for param_name, param in sig.parameters.items():
                param_type = type_hints.get(param_name, Any)
                type_str = self._type_to_string(param_type)

                # 判断是否必需
                required = param.default is inspect.Parameter.empty

                parameters.append(ToolParameter(
                    name=param_name,
                    type=type_str,
                    description="",  # 可以从 docstring 提取
                    required=required,
                    default=None if required else param.default
                ))

            # 解析返回值
            return_type = type_hints.get('return', Any)
            returns_str = self._type_to_string(return_type)

            # 从 docstring 提取参数描述
            docstring = inspect.getdoc(func) or ""
            param_descriptions = self._parse_docstring(docstring)
            for p in parameters:
                if p.name in param_descriptions:
                    p.description = param_descriptions[p.name]

            # 注册工具
            self._tools[name] = ToolDefinition(
                name=name,
                description=description or docstring.split('\n')[0],
                func=func,
                parameters=parameters,
                returns=returns_str,
                examples=examples or []
            )

            return func
        return decorator

    def _type_to_string(self, typ) -> str:
        """将 Python 类型转换为字符串表示"""
        if typ is str:
            return "str"
        elif typ is int:
            return "int"
        elif typ is float:
            return "float"
        elif typ is bool:
            return "bool"
        elif typ is dict:
            return "Dict"
        elif typ is list:
            return "List"
        elif typ is Any:
            return "Any"
        elif hasattr(typ, '__name__'):
            return typ.__name__
        else:
            return str(typ)

    def _parse_docstring(self, docstring: str) -> Dict[str, str]:
        """从 docstring 解析参数描述

        支持 Google 和 NumPy 风格:
        Args:
            path: 文件路径
            range: 行范围
        """
        descriptions = {}
        in_args = False

        for line in docstring.split('\n'):
            line = line.strip()

            if line.lower() in ['args:', 'arguments:', 'parameters:']:
                in_args = True
                continue

            if in_args:
                if line.endswith(':') or (not line and descriptions):
                    in_args = False
                    continue

                # 解析 "param: description" 或 "param - description"
                if ':' in line:
                    parts = line.split(':', 1)
                    param_name = parts[0].strip()
                    param_desc = parts[1].strip() if len(parts) > 1 else ""
                    descriptions[param_name] = param_desc
                elif ' - ' in line:
                    parts = line.split(' - ', 1)
                    param_name = parts[0].strip()
                    param_desc = parts[1].strip() if len(parts) > 1 else ""
                    descriptions[param_name] = param_desc

        return descriptions

    def get_tool(self, name: str) -> Optional[ToolDefinition]:
        """获取工具定义"""
        return self._tools.get(name)

    def list_tools(self) -> List[ToolDefinition]:
        """列出所有已注册工具"""
        return list(self._tools.values())

    def list_tools_dict(self) -> Dict[str, Dict]:
        """以字典形式列出所有工具（供 LLM 查询）"""
        return {name: tool.to_dict() for name, tool in self._tools.items()}

    def get_tools_prompt(self) -> str:
        """生成工具列表提示词（供 LLM 理解可用工具）"""
        if not self._tools:
            return "没有可用工具。"

        prompt_parts = ["## 可用工具\n"]
        for tool in self._tools.values():
            prompt_parts.append(tool.to_prompt())

        return "\n".join(prompt_parts)

    def execute(self, name: str, **kwargs) -> Any:
        """执行工具"""
        tool = self.get_tool(name)
        if not tool:
            raise ValueError(f"未知工具：{name}")

        if tool.status == ToolStatus.ERROR:
            raise RuntimeError(f"工具 {name} 处于错误状态")

        try:
            tool.status = ToolStatus.BUSY
            result = tool.func(**kwargs)
            tool.status = ToolStatus.READY
            return result
        except Exception as e:
            tool.status = ToolStatus.ERROR
            raise


# 全局注册表实例
tool_registry = ToolRegistry.get_instance()


# 便捷装饰器
def tool(name: str = None, description: str = "", examples: List[str] = None):
    """便捷工具注册装饰器

    用法:
        @tool(description="读取文件内容")
        def read_file(path: str) -> str:
            ...
    """
    return tool_registry.register(name=name, description=description, examples=examples)
