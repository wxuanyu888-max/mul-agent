"""Agent State Manager - 管理 Agent 状态和状态栏显示"""

import sys
import time
from enum import Enum
from typing import Optional


class AgentState(Enum):
    """Agent 状态枚举"""
    IDLE = "idle"                    # 空闲，等待输入
    THINKING = "thinking"            # 正在思考决策
    LLM_DECIDING = "llm_deciding"   # LLM 正在决定路由
    LLM_WAITING = "llm_waiting"     # 等待 LLM 响应
    EXECUTING = "executing"          # 正在执行动作
    READING_MEMORY = "reading_memory" # 正在读取记忆
    WRITING_MEMORY = "writing_memory" # 正在写入记忆
    ERROR = "error"                  # 出错
    DONE = "done"                    # 完成


# ANSI 颜色代码
class Colors:
    """ANSI 颜色代码"""
    RESET = "\033[0m"
    BLACK = "\033[30m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"

    # 亮色
    BRIGHT_BLACK = "\033[90m"
    BRIGHT_RED = "\033[91m"
    BRIGHT_GREEN = "\033[92m"
    BRIGHT_YELLOW = "\033[93m"
    BRIGHT_BLUE = "\033[94m"
    BRIGHT_MAGENTA = "\033[95m"
    BRIGHT_CYAN = "\033[96m"
    BRIGHT_WHITE = "\033[97m"


class StateBar:
    """状态栏管理器"""

    # 状态对应的显示文本和颜色
    STATE_INFO = {
        AgentState.IDLE: ("空闲", Colors.CYAN),
        AgentState.THINKING: ("思考中", Colors.YELLOW),
        AgentState.LLM_DECIDING: ("LLM决策中", Colors.MAGENTA),
        AgentState.LLM_WAITING: ("等待LLM响应", Colors.MAGENTA),
        AgentState.EXECUTING: ("执行中", Colors.BLUE),
        AgentState.READING_MEMORY: ("读取记忆", Colors.CYAN),
        AgentState.WRITING_MEMORY: ("写入记忆", Colors.CYAN),
        AgentState.ERROR: ("出错", Colors.RED),
        AgentState.DONE: ("完成", Colors.GREEN),
    }

    # 状态对应的动画/指示器
    STATE_INDICATORS = {
        AgentState.IDLE: "●",
        AgentState.THINKING: "◐",
        AgentState.LLM_DECIDING: "◑",
        AgentState.LLM_WAITING: "◑",
        AgentState.EXECUTING: "◐",
        AgentState.READING_MEMORY: "◐",
        AgentState.WRITING_MEMORY: "◐",
        AgentState.ERROR: "✗",
        AgentState.DONE: "✓",
    }

    def __init__(self, enabled: bool = True):
        self.enabled = enabled
        self.current_state = AgentState.IDLE
        self.current_action: Optional[str] = None
        self.start_time: Optional[float] = None
        self.error_message: Optional[str] = None
        self._last_state_len = 0

    def set_state(self, state: AgentState, action: Optional[str] = None):
        """设置状态"""
        if not self.enabled:
            return
        self.current_state = state
        self.current_action = action
        self.start_time = time.time()
        self.error_message = None
        self._display()

    def set_error(self, message: str):
        """设置错误状态"""
        if not self.enabled:
            return
        self.current_state = AgentState.ERROR
        self.error_message = message
        self._display()

    def clear(self):
        """清除状态栏"""
        if not self.enabled:
            return
        # 清除上一行
        if self._last_state_len > 0:
            sys.stdout.write("\r" + " " * self._last_state_len + "\r")
            sys.stdout.flush()
        self._last_state_len = 0

    def _display(self, force: bool = False):
        """显示状态栏

        Args:
            force: 是否强制刷新显示
        """
        if not self.enabled:
            return

        state_text, color = self.STATE_INFO.get(
            self.current_state,
            ("未知", Colors.WHITE)
        )
        indicator = self.STATE_INDICATORS.get(self.current_state, "?")

        # 计算经过的时间（精确到毫秒）
        elapsed = ""
        if self.start_time:
            elapsed_sec = time.time() - self.start_time
            if elapsed_sec < 1:
                elapsed = f" ({elapsed_sec*1000:.0f}ms)"
            else:
                elapsed = f" ({elapsed_sec:.1f}s)"

        action_text = ""
        if self.current_action:
            action_text = f" - {self.current_action[:30]}"

        error_text = ""
        if self.error_message:
            error_text = f" | {Colors.RED}错误: {self.error_message[:40]}{Colors.RESET}"

        bar = f"{indicator} {Colors.BRIGHT_BLACK}[{color}{state_text}{Colors.RESET}{Colors.BRIGHT_BLACK}]{Colors.RESET}{elapsed}{action_text}{error_text}"

        # 清除上一行
        if self._last_state_len > 0:
            sys.stdout.write("\r" + " " * self._last_state_len + "\r")

        # 输出状态栏（不换行）
        sys.stdout.write(bar)
        sys.stdout.flush()
        self._last_state_len = len(bar.replace(Colors.RESET, "").replace("\033", ""))

    def refresh(self):
        """刷新显示（用于长时间操作时更新计时）"""
        self._display(force=True)

    def get_state(self) -> AgentState:
        """获取当前状态"""
        return self.current_state


def create_state_bar() -> StateBar:
    """创建状态栏实例"""
    return StateBar(enabled=True)
