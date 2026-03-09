"""Tool Registration - 工具自动注册

将现有的 Handler 和 Tool 注册到统一的工具注册表
"""

from mul_agent.tools.registry import tool_registry, ToolDefinition, ToolParameter
from mul_agent.tools.builtins import BashTool, ReadTool, WriteTool


def register_builtin_tools():
    """注册内置工具到工具注册表"""

    # 1. 注册 BashTool
    bash_tool = BashTool()
    meta = bash_tool.metadata

    @tool_registry.register(
        name=meta.name,
        description=meta.description,
        examples=meta.examples
    )
    def bash_command(command: str, timeout: int = 60, cwd: str = None):
        """执行 shell 命令

        Args:
            command: 要执行的 shell 命令
            timeout: 超时时间（秒），默认 60
            cwd: 工作目录，默认当前目录

        Returns:
            执行结果，包含 stdout, stderr, returncode
        """
        result = bash_tool.execute(command=command, timeout=timeout, cwd=cwd)
        return result.to_dict()

    # 2. 注册 ReadTool
    read_tool = ReadTool()
    meta = read_tool.metadata

    @tool_registry.register(
        name=meta.name,
        description=meta.description,
        examples=meta.examples
    )
    def read_file(path: str, offset: int = 1, limit: int = 2000):
        """读取文件内容

        Args:
            path: 文件路径（绝对路径或相对路径）
            offset: 起始行号（从 1 开始），默认 1
            limit: 读取行数，默认 2000

        Returns:
            文件内容和元数据
        """
        result = read_tool.execute(path=path, offset=offset, limit=limit)
        return result.to_dict()

    # 3. 注册 WriteTool
    write_tool = WriteTool()
    meta = write_tool.metadata

    @tool_registry.register(
        name=meta.name,
        description=meta.description,
        examples=meta.examples
    )
    def write_file(path: str, content: str):
        """创建新文件或覆盖现有文件

        Args:
            path: 文件路径（绝对路径或相对路径）
            content: 文件内容

        Returns:
            写入结果
        """
        result = write_tool.execute(path=path, content=content)
        return result.to_dict()

    return tool_registry


# 自动注册
register_builtin_tools()
