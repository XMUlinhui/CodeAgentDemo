import fnmatch
from pathlib import Path
from typing import Optional, List

from langchain.tools import ToolRuntime, tool


from .ignore import DEFAULT_IGNORE_PATTERNS


@tool("tree", parse_docstring=True)
def tree_tool(
        runtime: ToolRuntime,
        root: str,
        max_depth: Optional[int] = None,
        match: Optional[List[str]] = None,
        ignore: Optional[List[str]] = None,
):
    """Displays directory structure as a tree. Recursively lists subdirectories with indentation.

    Args:
        root: Absolute path to the root directory (relative paths are not allowed).
        max_depth: Maximum recursion depth (None = unlimited).
        match: Optional glob patterns to include items (e.g., ["*.md", "src/"]).
        ignore: Optional glob patterns to exclude items (e.g., ["__pycache__", "*.tmp"]).
    """
    root_path = Path(root)

    # 路径合法性校验
    if not root_path.is_absolute():
        return f"Error: {root} is not an absolute path. Provide an absolute path."
    if not root_path.exists():
        return f"Error: {root} does not exist. Provide a valid path."
    if not root_path.is_dir():
        return f"Error: {root} is not a directory. Provide a directory path."

    # 合并忽略模式
    ignore_patterns = (ignore or []) + DEFAULT_IGNORE_PATTERNS

    # 递归构建树形结构
    tree_lines = [f"{root_path.name}/"]  # 根目录作为第一行

    def _recurse(current_path: Path, prefix: str, depth: int):
        """递归遍历目录，生成树形行"""
        # 检查深度限制
        if max_depth is not None and depth > max_depth:
            return

        # 获取当前目录下的项目并过滤
        try:
            items = list(current_path.iterdir())
        except PermissionError:
            tree_lines.append(f"{prefix}├── [Permission Denied]")
            return

        # 过滤并排序（目录优先）
        filtered = []
        for item in items:
            # 应用忽略规则
            if any(fnmatch.fnmatch(item.name, p) for p in ignore_patterns):
                continue
            # 应用匹配规则
            if match and not any(fnmatch.fnmatch(item.name, p) for p in match):
                continue
            filtered.append(item)
        filtered.sort(key=lambda x: (x.is_file(), x.name.lower()))

        # 生成树形行
        for i, item in enumerate(filtered):
            is_last = i == len(filtered) - 1
            connector = "└──" if is_last else "├──"
            line = f"{prefix}{connector} {item.name}{'/' if item.is_dir() else ''}"
            tree_lines.append(line)

            # 递归处理子目录
            if item.is_dir():
                new_prefix = prefix + ("    " if is_last else "│   ")
                _recurse(item, new_prefix, depth + 1)

    # 从根目录的子项开始递归（深度为1）
    _recurse(root_path, "", 1)

    # 格式化输出
    return (
            f"Directory tree for {root}:\n```\n"
            + "\n".join(tree_lines)
            + "\n```"
    )