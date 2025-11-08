import subprocess
import os
import platform
import time
from typing import Optional, List, Dict, Any
from pathlib import Path

from langchain.tools import ToolRuntime, tool

# 常见的安全命令白名单示例
DEFAULT_ALLOWED_COMMANDS = [
    "ls", "dir", "pwd", "cd", "echo", "cat", "head", "tail", "find", 
    "grep", "wc", "mkdir", "rmdir", "touch", "cp", "mv", "rm", 
    "chmod", "chown", "date", "time", "whoami", "env", "printenv"
]

# 危险命令黑名单
DANGEROUS_COMMANDS = [
    "sudo", "su", "chroot", "mount", "umount", "dd", "fdisk", 
    "mkfs", "rm -rf", "shutdown", "reboot", "halt", "poweroff"
]

# 全局状态变量
_command_history: List[Dict[str, Any]] = []
_default_timeout = 30
_enable_security_checks = True


def _check_security(command: str) -> tuple[bool, str]:
    """检查命令的安全性。"""
    if not command.strip():
        return False, "命令不能为空"
        
    # 检查危险命令
    for dangerous_cmd in DANGEROUS_COMMANDS:
        if dangerous_cmd in command:
            return False, f"命令包含危险操作: {dangerous_cmd}"
    
    # 检查白名单
    # 提取命令名（第一个单词）
    cmd_parts = command.strip().split()
    if not cmd_parts:
        return False, "无效的命令格式"
        
    cmd_name = cmd_parts[0]
    
    # 检查命令是否在白名单中
    if cmd_name not in DEFAULT_ALLOWED_COMMANDS:
        return False, f"命令 '{cmd_name}' 不在允许的列表中"
    
    return True, ""


def _execute_command(
    command: str,
    timeout: int,
    cwd: Optional[str] = None,
    env_vars: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """内部方法：执行命令并返回结果。"""
    start_time = time.time()
    system_type = platform.system()
    
    # 构建执行环境
    env = os.environ.copy()
    if env_vars:
        env.update(env_vars)
    
    # 验证工作目录
    if cwd:
        cwd_path = Path(cwd)
        if not cwd_path.is_absolute():
            return {
                "success": False,
                "output": "",
                "error": f"工作目录 '{cwd}' 不是绝对路径",
                "return_code": -1,
                "command": command,
                "duration_ms": int((time.time() - start_time) * 1000),
                "system": system_type
            }
        if not cwd_path.exists() or not cwd_path.is_dir():
            return {
                "success": False,
                "output": "",
                "error": f"工作目录 '{cwd}' 不存在或不是目录",
                "return_code": -1,
                "command": command,
                "duration_ms": int((time.time() - start_time) * 1000),
                "system": system_type
            }
    
    try:
        # 根据系统选择shell类型
        shell_type = True
        if system_type == "Windows":
            # 在Windows上使用PowerShell
            cmd_args = ["powershell", "-Command", command]
            shell_type = False
        else:
            # 在Unix-like系统上使用bash
            cmd_args = ["bash", "-c", command]
            shell_type = False
        
        # 执行命令
        result = subprocess.run(
            cmd_args,
            shell=shell_type,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout,
            cwd=cwd,
            env=env
        )
        
        # 计算执行时间
        duration_ms = int((time.time() - start_time) * 1000)
        
        # 返回结果
        return {
            "success": result.returncode == 0,
            "output": result.stdout,
            "error": result.stderr,
            "return_code": result.returncode,
            "command": command,
            "duration_ms": duration_ms,
            "system": system_type
        }
        
    except subprocess.TimeoutExpired:
        duration_ms = int((time.time() - start_time) * 1000)
        return {
            "success": False,
            "output": "",
            "error": f"命令执行超时（{timeout}秒）",
            "return_code": -2,
            "command": command,
            "duration_ms": duration_ms,
            "system": system_type
        }
    except PermissionError:
        duration_ms = int((time.time() - start_time) * 1000)
        return {
            "success": False,
            "output": "",
            "error": "权限不足，无法执行命令",
            "return_code": -3,
            "command": command,
            "duration_ms": duration_ms,
            "system": system_type
        }
    except Exception as e:
        duration_ms = int((time.time() - start_time) * 1000)
        return {
            "success": False,
            "output": "",
            "error": f"执行命令时发生错误: {str(e)}",
            "return_code": -1,
            "command": command,
            "duration_ms": duration_ms,
            "system": system_type
        }


@tool("bash", parse_docstring=True)
def bash_tool(
    runtime: ToolRuntime,
    command: str,
    cwd: Optional[str] = None,
    env_vars: Optional[Dict[str, str]] = None
) -> str:
    """执行Bash/shell命令并返回格式化结果。

    Args:
        runtime: ToolRuntime实例，由LangChain框架提供。
        command: 要执行的命令字符串。
        cwd: 执行命令的工作目录，None表示使用当前目录。
        env_vars: 额外的环境变量，将与当前环境变量合并。
    """
    # 执行安全检查
    if _enable_security_checks:
        is_safe, error_msg = _check_security(command)
        if not is_safe:
            result = {
                "success": False,
                "output": "",
                "error": error_msg,
                "return_code": -4,
                "command": command,
                "duration_ms": 0,
                "system": platform.system()
            }
            _command_history.append(result)
            return f"Error: {error_msg}"
    
    # 执行命令
    result = _execute_command(
        command=command,
        timeout=_default_timeout,
        cwd=cwd,
        env_vars=env_vars
    )
    
    # 记录到历史
    _command_history.append(result)
    # 只保留最近100条历史记录
    if len(_command_history) > 100:
        _command_history.pop(0)
    
    # 格式化输出结果
    if result["success"]:
        output_lines = []
        if result["output"]:
            output_lines.append(result["output"])
        return f"Command executed successfully (exit code: {result['return_code']}, duration: {result['duration_ms']}ms):\n```\n" + "\n".join(output_lines) + "\n```"
    else:
        error_msg = result["error"] if result["error"] else "Unknown error"
        return f"Command failed (exit code: {result['return_code']}, duration: {result['duration_ms']}ms):\n```\n{error_msg}\n```"

