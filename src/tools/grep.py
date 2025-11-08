import fnmatch
from pathlib import Path
from typing import Optional, List

from langchain.tools import ToolRuntime, tool


from .ignore import DEFAULT_IGNORE_PATTERNS


@tool("grep", parse_docstring=True)
def grep_tool(
        runtime: ToolRuntime,
        pattern: str,
        paths: List[str],
        case_sensitive: bool = True,
        recursive: bool = False,
        invert: bool = False,
):
    """Searches for a text pattern in files/directories. Returns matching lines with context.

    Args:
        pattern: Text to search for (simple string matching, not regex).
        paths: List of absolute paths to files/directories to search.
        case_sensitive: Whether the search is case-sensitive (default: True).
        recursive: If paths include directories, search subdirectories (default: False).
        invert: Return lines that DO NOT match the pattern (default: False).
    """
    # 预处理模式（大小写不敏感时转为小写）
    target = pattern if case_sensitive else pattern.lower()

    # 收集所有要搜索的文件
    files_to_search: List[Path] = []
    for path_str in paths:
        path = Path(path_str)
        # 校验路径合法性
        if not path.is_absolute():
            return f"Error: {path_str} is not an absolute path. Provide absolute paths."
        if not path.exists():
            return f"Error: {path_str} does not exist. Provide valid paths."

        # 处理文件
        if path.is_file():
            files_to_search.append(path)
        # 处理目录（递归或非递归）
        elif path.is_dir():
            if recursive:
                # 递归遍历所有文件
                for file in path.rglob("*"):
                    if file.is_file():
                        files_to_search.append(file)
            else:
                # 仅当前目录文件
                for file in path.iterdir():
                    if file.is_file():
                        files_to_search.append(file)

    # 过滤文件（应用默认忽略规则）
    filtered_files = []
    for file in files_to_search:
        if not any(fnmatch.fnmatch(file.name, p) for p in DEFAULT_IGNORE_PATTERNS):
            filtered_files.append(file)
    files_to_search = filtered_files

    # 搜索文件内容
    results = []
    for file in files_to_search:
        try:
            # 读取文件内容（按行处理）
            with open(file, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()
        except (PermissionError, IsADirectoryError):
            continue  # 跳过无权限或意外目录

        # 检查每行是否匹配
        for line_num, line in enumerate(lines, 1):  # 行号从1开始
            content = line.strip()
            # 大小写处理
            line_to_check = content if case_sensitive else content.lower()
            # 匹配逻辑
            is_match = (target in line_to_check) != invert  # 取反如果invert=True
            if is_match:
                results.append(f"{file}:{line_num}: {content}")

    # 格式化输出
    if not results:
        return f"No matches found for '{pattern}'."

    return (
            f"Matches for '{pattern}' ({len(results)} total):\n```\n"
            + "\n".join(results)
            + "\n```"
    )