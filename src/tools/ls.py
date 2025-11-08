import fnmatch
from pathlib import Path
from typing import Optional, List

from langchain.tools import ToolRuntime, tool


from .ignore import DEFAULT_IGNORE_PATTERNS


@tool("ls", parse_docstring=True)
def ls_tool(
        runtime: ToolRuntime,
        path: str,
        match: Optional[List[str]] = None,
        ignore: Optional[List[str]] = None,
):
    """Lists files and directories in a given path. Optionally provide glob patterns to match and ignore.

    Args:
        path: Absolute path to list contents from (relative paths are not allowed).
        match: Optional list of glob patterns to include (e.g., ["*.py", "docs/"]).
        ignore: Optional list of glob patterns to exclude (e.g., [".git", "*.log"]).
    """
    _path = Path(path)

    # 路径合法性校验
    if not _path.is_absolute():
        return f"Error: {path} is not an absolute path. Provide an absolute path."
    if not _path.exists():
        return f"Error: {path} does not exist. Provide a valid path."
    if not _path.is_dir():
        return f"Error: {path} is not a directory. Provide a directory path."

    # 读取目录内容（处理权限问题）
    try:
        items = list(_path.iterdir())
    except PermissionError:
        return f"Error: Permission denied to access {path}."

    # 排序：目录优先，按名称字母序
    items.sort(key=lambda x: (x.is_file(), x.name.lower()))

    # 应用匹配模式（match）
    if match:
        filtered = []
        for item in items:
            for pattern in match:
                if fnmatch.fnmatch(item.name, pattern):
                    filtered.append(item)
                    break
        items = filtered

    # 应用忽略模式（ignore + 默认忽略规则）
    ignore_patterns = (ignore or []) + DEFAULT_IGNORE_PATTERNS
    filtered = []
    for item in items:
        if not any(fnmatch.fnmatch(item.name, p) for p in ignore_patterns):
            filtered.append(item)
    items = filtered

    # 格式化输出
    if not items:
        return f"No items found in {path}."

    result_lines = [f"{item.name}/" if item.is_dir() else item.name for item in items]
    return (
            f"Contents of {path}:\n```\n"
            + "\n".join(result_lines)
            + "\n```"
    )