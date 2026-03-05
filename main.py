#!/usr/bin/env python3
"""CLI Entry point for Self-Growing Agent Team"""

import sys
import json
import time
from pathlib import Path
from typing import Optional

import click

from mul_agent.brain.brain import Brain
from mul_agent.brain.router import Router
from mul_agent.brain.config_manager import ConfigManager
from mul_agent.brain.daemon import AgentDaemon, create_daemon
from mul_agent.brain.state_bar import StateBar, AgentState


# Default paths
BASE_DIR = Path(__file__).parent
STORAGE_DIR = BASE_DIR / "storage"
# 配置目录改为 storage/agents/
CONFIG_DIR = STORAGE_DIR


@click.group()
@click.pass_context
def cli(ctx):
    """Self-Growing Agent Team - CLI"""
    ctx.ensure_object(dict)
    ctx.obj["base_dir"] = BASE_DIR
    ctx.obj["storage_dir"] = STORAGE_DIR
    ctx.obj["config_dir"] = CONFIG_DIR


@cli.command()
@click.option("--config", default="core_brain", help="Agent config name")
@click.option("--json", "use_json", is_flag=True, help="Output raw JSON")
@click.option("--no-state-bar", is_flag=True, help="Disable state bar")
@click.pass_context
def brain(ctx, config, use_json, no_state_bar):
    """Start the core brain agent"""
    config_manager = ConfigManager(ctx.obj["config_dir"])
    brain_instance = Brain(config, config_manager)

    # Claude Code 风格
    click.echo("""
       ▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄
      ▐░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░▌
     ▐░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░▌
    ▐░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░▌
    █░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░█
    █░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░█
     ▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀

                           Wang Brain v1.0
                      自我进化的多Agent系统

                       help - 查看命令
                       exit - 退出
""")

    # 创建状态栏
    state_bar = StateBar(enabled=not no_state_bar)

    while True:
        try:
            # 显示空闲状态
            state_bar.set_state(AgentState.IDLE)
            click.echo("")  # 空行，让输入更清晰

            user_input = sys.stdin.readline()
            if not user_input:
                continue
            user_input = user_input.strip()
            if not user_input:
                click.echo("请输入内容，或输入 'exit' 退出")
                continue

            if user_input.lower() in ("exit", "quit", "q"):
                state_bar.clear()
                click.echo("\n👋 再见！")
                break
            if user_input.lower() in ("help", "h", "?"):
                state_bar.set_state(AgentState.IDLE)
                _show_help()
                continue

            # 设置思考状态
            state_bar.set_state(AgentState.THINKING, "分析用户输入")

            try:
                result = brain_instance.think(user_input)

                # 设置执行状态
                route = result.get("route", "unknown")
                state_bar.set_state(AgentState.EXECUTING, f"执行 {route}")

                if use_json:
                    click.echo(f"\n{json.dumps(result, indent=2, ensure_ascii=False)}\n")
                else:
                    _format_output(result)

                # 设置完成状态
                state_bar.set_state(AgentState.DONE)

            except Exception as e:
                state_bar.set_error(str(e))
                click.echo(f"Error: {e}", err=True)

        except KeyboardInterrupt:
            state_bar.clear()
            click.echo("\n👋 再见！")
            break
        except Exception as e:
            state_bar.set_error(str(e))
            click.echo(f"Error: {e}", err=True)


def _show_help():
    """显示帮助信息"""
    click.echo("""
可用命令:
  exit / quit / q   退出
  help / h / ?     查看帮助
  create / new     创建新Agent
  bash / $         执行shell命令
  memory           查看记忆
  heart            自我反思
""")


def _format_output(result: dict):
    """格式化输出"""
    route = result.get("route", "")
    response = result.get("response", "")
    result_data = result.get("result", {})

    # bash命令 - 显示输出
    if route == "bash":
        stdout = result_data.get("stdout", "")
        stderr = result_data.get("stderr", "")
        if stdout:
            click.echo(f"\n{stdout}")
        if stderr:
            click.echo(f"\n[stderr] {stderr}", err=True)
        return

    # response或direct_response - 显示回复
    if route in ("response", "direct_response"):
        message = result_data.get("message", response)
        if message:
            click.echo(f"\n{message}\n")
        return

    # 其他情况 - 显示response字段
    if response:
        if isinstance(response, str):
            try:
                inner = json.loads(response)
                if isinstance(inner, dict):
                    if "response" in inner:
                        inner_response = inner["response"]
                        if isinstance(inner_response, str):
                            try:
                                deeper = json.loads(inner_response)
                                click.echo(f"\n{deeper.get('response', inner_response)}\n")
                            except (json.JSONDecodeError, TypeError):
                                click.echo(f"\n{inner_response}\n")
                        else:
                            click.echo(f"\n{inner_response}\n")
                    else:
                        click.echo(f"\n{inner}\n")
                else:
                    click.echo(f"\n{response}\n")
            except (json.JSONDecodeError, TypeError):
                click.echo(f"\n{response}\n")
        else:
            click.echo(f"\n{response}\n")
        return


@cli.command()
@click.argument("agent_id")
@click.pass_context
def agent(ctx, agent_id):
    """Start a specific agent"""
    config_manager = ConfigManager(ctx.obj["config_dir"])
    brain_instance = Brain(agent_id, config_manager)

    click.echo(f"Starting agent: {agent_id}")

    while True:
        try:
            user_input = sys.stdin.readline()
            if not user_input:
                continue
            user_input = user_input.strip()
            if not user_input:
                continue

            if user_input.lower() in ("exit", "quit", "q"):
                break

            result = brain_instance.think(user_input)
            click.echo(f"\n{json.dumps(result, indent=2, ensure_ascii=False)}\n")
        except KeyboardInterrupt:
            break
        except Exception as e:
            click.echo(f"Error: {e}", err=True)


@cli.command()
@click.pass_context
def team(ctx):
    """Show team status"""
    config_manager = ConfigManager(ctx.obj["config_dir"])
    agents = config_manager.list_agents()

    click.echo("=== Team Status ===\n")
    if not agents:
        click.echo("No agents found")
        return

    for agent_id in agents:
        config = config_manager.load_all(agent_id)
        role = config.get("user", {}).get("role", {}).get("title", "Unknown")
        click.echo(f"  {agent_id}: {role}")


@cli.command()
@click.argument("route")
@click.option("--params", default="{}", help="JSON params")
@click.pass_context
def route(ctx, route, params):
    """Trigger a specific route manually"""
    config_manager = ConfigManager(ctx.obj["config_dir"])
    router = Router(config_manager)

    try:
        params_dict = json.loads(params)
    except json.JSONDecodeError:
        click.echo("Invalid JSON params", err=True)
        sys.exit(1)

    result = router.dispatch(route, params_dict)
    click.echo(json.dumps(result, indent=2, ensure_ascii=False))


@cli.command()
@click.pass_context
def repl(ctx):
    """Start REPL mode (alias for brain)"""
    ctx.invoke(brain, config="core_brain")


# 全局守护进程实例
_global_daemon: Optional[AgentDaemon] = None


def _get_daemon(ctx) -> AgentDaemon:
    """获取或创建全局守护进程"""
    global _global_daemon
    if _global_daemon is None:
        config_manager = ConfigManager(ctx.obj["config_dir"])
        _global_daemon = create_daemon(
            ctx.obj["config_dir"],
            idle_timeout=300,   # 5分钟空闲进入休息
            grow_interval=3600  # 1小时自我成长一次
        )
    return _global_daemon


@cli.command()
@click.option("--idle-timeout", default=300, help="空闲超时秒数，进入休息状态")
@click.option("--grow-interval", default=3600, help="自我成长间隔秒数")
@click.option("--no-growth", is_flag=True, help="禁用自动自我成长")
@click.pass_context
def daemon(ctx, idle_timeout, grow_interval, no_growth):
    """启动带守护进程的 Brain（实验性）"""
    config_manager = ConfigManager(ctx.obj["config_dir"])
    brain_instance = Brain("core_brain", config_manager)

    # 创建守护进程
    daemon_instance = AgentDaemon(
        config_manager=config_manager,
        idle_timeout=idle_timeout,
        grow_interval=grow_interval
    )

    if not no_growth:
        daemon_instance.add_default_growth_task()

    # 设置状态变化回调
    def on_state_change(old_state, new_state):
        state_name = new_state.value
        click.echo(f"\n[守护] 状态变化: {old_state.value} -> {state_name}")

    daemon_instance.on_state_change = on_state_change

    # 启动守护进程
    daemon_instance.start()

    global _global_daemon
    _global_daemon = daemon_instance

    click.echo("""
    ╔═══════════════════════════════════════════════════════════╗
    ║              Wang Brain v1.0 - 守护模式                   ║
    ╠═══════════════════════════════════════════════════════════╣
    ║  工作状态: 正在处理用户请求                               ║
    ║  休息状态: 定时执行任务 + 自我成长                       ║
    ║                                                           ║
    ║  进入休息后，每隔一定时间会:                               ║
    ║    - 执行已安排的定时任务                                 ║
    ║    - 进行自我成长（调用 heart 路由）                      ║
    ╚═══════════════════════════════════════════════════════════╝
    """)

    click.echo("帮助命令:")
    click.echo("  exit / quit / q   退出")
    click.echo("  status            查看守护状态")
    click.echo("  task add <action> <interval>  添加定时任务")
    click.echo("  task list         查看定时任务")
    click.echo("  task del <id>     删除定时任务")
    click.echo("  rest              强制进入休息状态")
    click.echo("  work              强制进入工作状态")
    click.echo("  grow              立即触发自我成长")
    click.echo("")

    while True:
        try:
            user_input = sys.stdin.readline()
            if not user_input:
                continue
            user_input = user_input.strip()
            if not user_input:
                click.echo("请输入内容")
                continue

            if user_input.lower() in ("exit", "quit", "q"):
                daemon_instance.stop()
                click.echo("\n👋 再见！")
                break

            # 守护进程内置命令
            if user_input.lower() == "status":
                status = daemon_instance.get_status()
                click.echo(f"\n状态: {status['state']}")
                click.echo(f"空闲时间: {status['idle_time']:.0f}秒")
                click.echo(f"上次成长: {status['time_since_growth']:.0f}秒前")
                click.echo(f"定时任务数: {status['scheduled_tasks_count']}")
                if status['scheduled_tasks']:
                    click.echo("\n定时任务:")
                    for t in status['scheduled_tasks']:
                        next_run = t['next_run'] - time.time() if t['next_run'] else 0
                        click.echo(f"  - {t['name']} ({t['action']}): {t['interval']}s, 下次 {max(0, next_run):.0f}秒后")
                continue

            if user_input.lower().startswith("task add "):
                # task add <action> <interval> [params]
                parts = user_input.split()
                if len(parts) >= 4:
                    action = parts[2]
                    interval = int(parts[3])
                    params = {}
                    if len(parts) > 4:
                        try:
                            params = json.loads(" ".join(parts[4:]))
                        except:
                            params = {"note": " ".join(parts[4:])}
                    task_id = daemon_instance.add_scheduled_task(
                        name=f"自定义任务 {action}",
                        action=action,
                        params=params,
                        interval=interval
                    )
                    click.echo(f"已添加定时任务: {task_id}")
                else:
                    click.echo("用法: task add <action> <interval> [params_json]")
                continue

            if user_input.lower() == "task list":
                tasks = daemon_instance.list_scheduled_tasks()
                if tasks:
                    click.echo("\n定时任务:")
                    for t in tasks:
                        click.echo(f"  - {t['name']}: {t['action']} (间隔{t['interval']}s)")
                else:
                    click.echo("无定时任务")
                continue

            if user_input.lower().startswith("task del "):
                parts = user_input.split()
                if len(parts) >= 3:
                    task_id = parts[2]
                    if daemon_instance.remove_scheduled_task(task_id):
                        click.echo(f"已删除任务: {task_id}")
                    else:
                        click.echo(f"任务不存在: {task_id}")
                continue

            if user_input.lower() == "rest":
                daemon_instance.force_rest()
                click.echo("已进入休息状态")
                continue

            if user_input.lower() == "work":
                daemon_instance.force_work()
                click.echo("已进入工作状态")
                continue

            if user_input.lower() == "grow":
                result = daemon_instance._run_growth()
                click.echo(f"自我成长完成: {result.get('status')}")
                continue

            # 正常用户输入，记录活动
            daemon_instance.record_activity()

            # 处理用户请求
            result = brain_instance.think(user_input)
            _format_output(result)

        except KeyboardInterrupt:
            daemon_instance.stop()
            click.echo("\n👋 再见！")
            break
        except Exception as e:
            click.echo(f"Error: {e}", err=True)


@cli.command()
@click.pass_context
def daemon_status(ctx):
    """查看守护进程状态"""
    daemon = _get_daemon(ctx)
    status = daemon.get_status()
    click.echo(json.dumps(status, indent=2, ensure_ascii=False))


@cli.command()
@click.argument("action")
@click.argument("interval", type=int)
@click.argument("params", default="{}")
@click.pass_context
def task_add(ctx, action, interval, params):
    """添加定时任务: task add <action> <interval_seconds> [params_json]"""
    daemon = _get_daemon(ctx)
    try:
        params_dict = json.loads(params)
    except json.JSONDecodeError:
        params_dict = {}

    task_id = daemon.add_scheduled_task(
        name=f"自定义任务 {action}",
        action=action,
        params=params_dict,
        interval=interval
    )
    click.echo(f"已添加定时任务: {task_id}")


def main():
    cli(obj={})


if __name__ == "__main__":
    main()
