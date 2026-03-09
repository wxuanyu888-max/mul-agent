"""内置工具

参考 OpenClaw 的核心工具设计：
- bash: 执行 shell 命令
- read: 读取文件内容
- write: 写入文件
- edit: 编辑文件（FileEditTool）

注意：这些工具已通过 Handler 架构集成到 Router 中
- BashTool -> BashHandler (route: bash)
- ReadTool -> FileEditHandler (action: read)
- WriteTool -> FileEditHandler (action: create)
- EditTool -> FileEditHandler (action: edit)
"""

from mul_agent.tools.builtins.bash import BashTool
from mul_agent.tools.builtins.read import ReadTool
from mul_agent.tools.builtins.write import WriteTool
from mul_agent.tools.builtins.edit import FileEditTool

# 别名：EditTool = FileEditTool（保持向后兼容）
EditTool = FileEditTool

__all__ = [
    "BashTool",
    "ReadTool",
    "WriteTool",
    "EditTool",
    "FileEditTool",
]
