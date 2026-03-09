"""CLI - 命令行接口"""

__all__ = ["main"]

def main():
    """CLI 主入口"""
    from mul_agent.cli.commands import run_cli
    run_cli()
