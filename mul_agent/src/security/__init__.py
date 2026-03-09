"""
Security - 安全模块
"""

__all__ = ["SecurityPolicy", "SecretsManager"]


class SecurityPolicy:
    """安全策略"""

    def __init__(self):
        self.ssrf_protection = True
        self.secret_encryption = True

    def validate_url(self, url: str) -> bool:
        return True


class SecretsManager:
    """Secret 管理器"""

    def __init__(self):
        self._secrets: dict[str, str] = {}

    def get(self, name: str) -> str | None:
        return self._secrets.get(name)

    def set(self, name: str, value: str) -> None:
        self._secrets[name] = value

    def rotate(self, name: str) -> str:
        import secrets
        new_value = secrets.token_urlsafe(32)
        self._secrets[name] = new_value
        return new_value
