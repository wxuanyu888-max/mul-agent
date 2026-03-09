"""
Channels - 消息渠道系统

支持多种消息渠道：
- Telegram
- Discord
- Slack
- WhatsApp
- Signal
- Web
"""

__all__ = [
    "ChannelRegistry",
    "BaseChannel",
    "ChannelConfig",
]


class BaseChannel:
    """渠道基类"""

    channel_id: str
    channel_name: str

    async def connect(self) -> None:
        raise NotImplementedError

    async def disconnect(self) -> None:
        raise NotImplementedError

    async def send(self, message: str) -> None:
        raise NotImplementedError

    async def receive(self) -> None:
        raise NotImplementedError


class ChannelConfig:
    """渠道配置"""

    def __init__(self, channel_id: str, enabled: bool = True, config: dict | None = None):
        self.channel_id = channel_id
        self.enabled = enabled
        self.config = config or {}


class ChannelRegistry:
    """渠道注册表"""

    def __init__(self):
        self._channels: dict[str, BaseChannel] = {}

    def register(self, channel: BaseChannel) -> None:
        self._channels[channel.channel_id] = channel

    def unregister(self, channel_id: str) -> None:
        self._channels.pop(channel_id, None)

    def get(self, channel_id: str) -> BaseChannel | None:
        return self._channels.get(channel_id)

    def list(self) -> list[str]:
        return list(self._channels.keys())
