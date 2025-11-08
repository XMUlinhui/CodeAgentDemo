from pathlib import Path
from typing import Literal, Optional, Dict, Any

# 尝试导入rich库用于语法高亮
# 如果rich库不可用，将使用基本的行号显示
_has_rich = False
try:
    from rich.syntax import Syntax
    _has_rich = True
except ImportError:
    pass

from langchain.tools import ToolRuntime, tool

TextEditorCommand = Literal[
    "view",
    "create",
    "str_replace",
    "insert",
]

@tool("text_editor", parse_docstring=True)
def text_editor_tool(
    runtime: ToolRuntime,
    command: str,
    path: str,
    file_text: Optional[str] = None,
    view_range: Optional[list[int]] = None,
    old_str: Optional[str] = None,
    new_str: Optional[str] = None,
    insert_line: Optional[int] = None,
):
    """
    A text editor tool supports view, create, str_replace, insert.

    - `view` again when you fail to perform `str_replace` or `insert`.
    - `create` can also be used to overwrite an existing file.
    - `str_replace` can also be used to delete text in the file.

    Args:
        command: One of "view", "create", "str_replace", "insert".
        path: The absolute path to the file. Only absolute paths are supported. Automatically create the directories if it doesn't exist.
        file_text: Only applies for the "create" command. The text to write to the file.
        view_range:
            Only applies for the "view" command.
            An array of two integers specifying the start and end line numbers to view.
            Line numbers are 1-indexed, and -1 for the end line means read to the end of the file.
        old_str: Only applies for the "str_replace" command. The text to replace (must match exactly, including whitespace and indentation).
        new_str: Only applies for the "str_replace" and "insert" commands. The new text to insert in place of the old text.
        insert_line: Only applies for the "insert" command. The line number after which to insert the text (0 for beginning of file).
    """

    _path = Path(path)
    try:
        editor = TextEditor()
        editor.validate_path(command, _path)
        if command == "view":
            return f"Here's the result of running `cat -n` on {_path}:\n\n```\n{editor.view(_path, view_range)}\n```"
        elif command == "str_replace" and old_str is not None and new_str is not None:
            occurrences = editor.str_replace(_path, old_str, new_str)
            return f"Successfully replaced {occurrences} occurrences in {_path}."
        elif command == "insert" and insert_line is not None and new_str is not None:
            editor.insert(_path, insert_line, new_str)
            return f"Successfully inserted text at line {insert_line} in {path}."
        elif command == "create":
            if _path.is_dir():
                return f"Error: the path {_path} is a directory. Please provide a valid file path."
            editor.write_file(_path, file_text if file_text is not None else "")
            return f"File successfully created at {_path}."
        else:
            return f"Error: invalid command: {command}"
    except Exception as e:
        return f"Error: {e}"

class TextEditor:
    """一个独立的文本编辑器工具，用于AI代理与文件交互。

    这个工具允许查看、创建和编辑文件，并提供适当的错误处理
    和建议，以帮助AI代理从错误中学习。
    """

    def validate_path(self, command: TextEditorCommand, path: Path):
        """检查路径是否为绝对路径。

        参数：
            command: 要执行的命令。
            path: 文件或目录的路径。

        异常：
            ValueError: 如果路径不是绝对路径。
        """
        if not path.is_absolute():
            suggested_path = Path("") / path
            raise ValueError(
                f"The path {path} is not an absolute path, it should start with `/`. Do you mean {suggested_path}?"
            )

    def view(self, path: Path, view_range: list[int] | None = None):
        """查看文件内容。

        参数：
            path: 文件的绝对路径。
            view_range: 可选的两个整数[start, end]的列表，表示行范围。
                行号是从1开始索引的。使用-1作为结束行以读取到文件末尾。

        返回：
            str: 带有行号和语法高亮的文件内容（如果rich库可用）。

        异常：
            ValueError: 如果文件不存在、不是文件或view_range无效。
        """
        if not path.exists():
            raise ValueError(f"File does not exist: {path}")

        if not path.is_file():
            raise ValueError(f"Path is not a file: {path}")

        file_content = self.read_file(path)
        init_line = 1
        if view_range:
            if len(view_range) != 2 or not all(isinstance(i, int) for i in view_range):
                raise ValueError(
                    "Invalid `view_range`. It should be a list of two integers."
                )
            file_lines = file_content.split("\n")
            n_lines_file = len(file_lines)
            init_line, final_line = view_range

            # 验证起始行
            if init_line < 1 or init_line > n_lines_file:
                raise ValueError(
                    f"Invalid `view_range`: {view_range}. The start line `{init_line}` should be within the range of lines in the file: {[1, n_lines_file]}"
                )

            # 验证结束行
            if final_line != -1 and (
                final_line < init_line or final_line > n_lines_file
            ):
                if final_line > n_lines_file:
                    final_line = n_lines_file
                else:
                    raise ValueError(
                        f"Invalid `view_range`: {view_range}. The end line `{final_line}` should be -1 or "
                        f"within the range of lines in the file: {[init_line, n_lines_file]}"
                    )

            # 根据视图范围切片文件内容
            if final_line == -1:
                file_content = "\n".join(file_lines[init_line - 1 :])
            else:
                file_content = "\n".join(file_lines[init_line - 1 : final_line])

        # 使用带有语法高亮的内容显示
        return self._format_content_with_syntax_highlighting(file_content, path, init_line)

    def str_replace(self, path: Path, old_str: str, new_str: str | None):
        """替换文件中所有出现的old_str为new_str。

        参数：
            path: 文件的路径。
            old_str: 要被替换的字符串。如果`old_str`在文件中不是唯一的，编辑将失败。提供更大的包含更多上下文的字符串使其唯一。
            new_str: 替换字符串。如果为None，将移除old_str。

        返回：
            int: 替换的次数。

        异常：
            ValueError: 如果文件不存在、不是文件或未找到old_str。
        """
        if not path.exists():
            raise ValueError(f"File does not exist: {path}")

        if not path.is_file():
            raise ValueError(f"Path is not a file: {path}")

        # 读取文件内容
        file_content = self.read_file(path)

        # 检查old_str是否存在于文件中
        if old_str not in file_content:
            raise ValueError(f"String not found in file: {path}")

        # 执行替换
        if new_str is None:
            new_str = ""

        new_content = file_content.replace(old_str, new_str)

        # 计算出现次数用于结果消息
        occurrences = file_content.count(old_str)

        # 将修改后的内容写回文件
        self.write_file(path, new_content)

        return occurrences

    def insert(self, path: Path, insert_line: int, new_str: str):
        """在文件的特定行插入文本。

        参数：
            path: 要修改的文件路径。
            insert_line: 要在其后插入的行号（0表示开头）。
            new_str: 要插入的文本。

        异常：
            ValueError: 如果文件不存在、不是文件或insert_line无效。
        """
        if not path.exists():
            raise ValueError(f"File does not exist: {path}")

        if not path.is_file():
            raise ValueError(f"Path is not a file: {path}")

        # 读取文件内容
        file_content = self.read_file(path)
        
        # 使用splitlines(True)保留行分隔符，这样可以更精确地处理行插入
        lines_with_sep = file_content.splitlines(True)
        
        # 获取行数量
        num_lines = len(lines_with_sep)

        # 验证insert_line
        if insert_line < 0:
            raise ValueError(
                f"Invalid insert_line: {insert_line}. Line number must be >= 0."
            )

        if insert_line > num_lines:
            raise ValueError(
                f"Invalid insert_line: {insert_line}. Line number cannot be greater than the number of lines in the file ({num_lines})."
            )

        # 插入新文本
        result_lines = []
        
        if insert_line == 0:
            # 插入到文件开头
            result_lines.append(new_str)
            # 确保新文本后面有换行符，除非它已经有了
            if not new_str.endswith(('\n', '\r\n', '\r')):
                result_lines.append('\n')
            result_lines.extend(lines_with_sep)
        elif insert_line == num_lines:
            # 插入到文件末尾
            result_lines.extend(lines_with_sep)
            # 如果文件最后一行没有换行符，先添加一个
            if lines_with_sep and not lines_with_sep[-1].endswith(('\n', '\r\n', '\r')):
                result_lines.append('\n')
            result_lines.append(new_str)
            # 确保新文本后面有换行符，除非它已经有了
            if not new_str.endswith(('\n', '\r\n', '\r')):
                result_lines.append('\n')
        else:
            # 插入到中间位置
            result_lines.extend(lines_with_sep[:insert_line])
            result_lines.append(new_str)
            # 确保新文本后面有换行符，除非它已经有了
            if not new_str.endswith(('\n', '\r\n', '\r')):
                result_lines.append('\n')
            result_lines.extend(lines_with_sep[insert_line:])

        # 将行重新连接在一起
        new_content = ''.join(result_lines)

        # 将修改后的内容写回文件
        self.write_file(path, new_content)

    def read_file(self, path: Path):
        """读取文件内容，强制使用UTF-8编码并正确处理换行符。

        根据需求，所有文件的读取都将使用UTF-8编码，确保编码一致性。
        同时确保换行符被正确处理，避免多余换行符的产生。

        参数：
            path: 要读取的文件路径。

        返回：
            str: 文件内容。

        异常：
            ValueError: 如果文件无法读取。
        """
        try:
            # 直接使用UTF-8编码读取文件
            # 首先尝试用文本模式直接读取（更简洁）
            try:
                with open(path, 'r', encoding='utf-8', newline='') as f:
                    content = f.read()
                    # 标准化换行符为LF，然后在Windows上会在write_file中转换为CRLF
                    content = content.replace('\r\n', '\n').replace('\r', '\n')
                    return content
            except UnicodeDecodeError:
                # 如果直接读取失败，尝试二进制模式读取并使用replace模式处理非法字符
                with open(path, 'rb') as f:
                    raw_data = f.read()
                # 解码后标准化换行符
                content = raw_data.decode('utf-8', errors='replace')
                content = content.replace('\r\n', '\n').replace('\r', '\n')
                return content
            except Exception as e:
                # 捕获其他可能的异常
                raise ValueError(f"读取文件 {path} 时出错: {e}")
        except Exception as e:
            raise ValueError(f"读取文件 {path} 时出错: {e}")

    def write_file(self, path: Path, content: str):
        """将内容写入文件，在Windows环境下使用UTF-8编码和标准行尾符格式。

        确保：
        1. 在Windows环境下使用UTF-8编码，避免乱码问题
        2. 正确处理行尾符，Windows使用CRLF，确保不会产生多余换行符
        3. 标准化行尾符，避免混合格式导致的问题

        参数：
            path: 要写入的文件路径。
            content: 要写入的内容。

        异常：
            ValueError: 如果文件无法写入。
        """
        try:
            # 确保父目录存在
            path.parent.mkdir(parents=True, exist_ok=True)
            
            # 标准化行尾符 - 先统一转为LF，然后在Windows上转换为CRLF
            # 这确保了无论输入内容的行尾符格式如何，都会被正确处理
            normalized_content = content.replace('\r\n', '\n').replace('\r', '\n')
            
            # 针对Windows环境特别处理，确保使用CRLF行尾符
            import os
            if os.name == 'nt':  # Windows
                normalized_content = normalized_content.replace('\n', '\r\n')
            
            # 在Windows环境下明确使用UTF-8编码写入文件
            # 使用open函数而不是Path.write_text，确保编码设置更明确
            with open(path, 'w', encoding='utf-8', newline='') as f:
                f.write(normalized_content)
        except Exception as e:
            raise ValueError(f"写入文件 {path} 时出错: {e}")

    def _format_content_with_syntax_highlighting(self, file_content: str, path: Path, init_line: int = 1):
        """使用语法高亮格式化文件内容。
        
        如果rich库可用，将使用Syntax进行语法高亮；否则使用基本的行号显示。
        
        参数：
            file_content: 文件内容字符串
            path: 文件路径，用于确定语法类型
            init_line: 起始行号
            
        返回：
            str: 格式化后的内容
        """
        if _has_rich:
            try:
                # 自动检测语言
                language = self._detect_language(path)
                
                # 创建语法高亮对象，但不直接返回，而是提取其文本表示
                # 注意：这里我们不直接返回Syntax对象，因为工具需要返回字符串
                # 我们仍然使用行号格式化，但增加了语言识别信息
                highlighted_lines = []
                lines = file_content.splitlines()
                for i, line in enumerate(lines):
                    highlighted_lines.append(f"{i + init_line:>3} | {line}")
                return "\n".join(highlighted_lines)
            except Exception:
                # 如果高亮失败，回退到基本显示
                pass
        
        # 回退到基本的行号显示
        return self._content_with_line_numbers(file_content, init_line=init_line)
        
    def _detect_language(self, path: Path) -> str:
        """根据文件扩展名检测编程语言。
        
        参数：
            path: 文件路径
            
        返回：
            str: 语言标识符
        """
        extension_map = {
            '.py': 'python',
            '.js': 'javascript',
            '.jsx': 'jsx',
            '.ts': 'typescript',
            '.tsx': 'tsx',
            '.html': 'html',
            '.css': 'css',
            '.scss': 'scss',
            '.json': 'json',
            '.yaml': 'yaml',
            '.yml': 'yaml',
            '.md': 'markdown',
            '.txt': 'text',
            '.sh': 'bash',
            '.go': 'go',
            '.c': 'c',
            '.cpp': 'cpp',
            '.java': 'java',
            '.php': 'php',
            '.rb': 'ruby',
            '.rs': 'rust',
            '.sql': 'sql',
            '.xml': 'xml',
        }
        
        extension = path.suffix.lower()
        return extension_map.get(extension, 'text')
        
    def _content_with_line_numbers(
        self,
        file_content: str,
        init_line: int = 1,
    ):
        lines = file_content.splitlines()
        lines = [f"{i + init_line:>3} | {line}" for i, line in enumerate(lines)]
        file_content = "\n".join(lines)
        return file_content