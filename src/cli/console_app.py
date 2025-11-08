import asyncio
import re
from pathlib import Path

from langchain.messages import AIMessage, AnyMessage, HumanMessage, ToolMessage
from langgraph.graph.state import CompiledStateGraph
from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Vertical, VerticalScroll
from textual.widgets import Footer, Header, Input, TabbedContent, TabPane, Static, TextArea

from src.agents.code_agent import create_code_agent
from src.tools.bash import bash_tool
from src.tools.text_editor import text_editor_tool
from src.mcp.load_mcp import load_mcp


class ChatView(Vertical):
    """聊天视图组件"""
    
    def __init__(self, id=None):
        super().__init__(id=id)
        self.input = Input(id="chat-input", placeholder="输入命令或问题...")
        self.is_generating = False
        self.messages = []  # 存储所有消息的列表
    
    def compose(self) -> ComposeResult:
        # 可滚动的消息区域 - 使用flex布局来占据剩余空间
        yield VerticalScroll(id="chat-messages", classes="chat-messages")
        # 固定的底部区域 - 包含加载指示器和输入框
        with Vertical(id="chat-footer", classes="chat-footer"):
            yield Static(id="loading-indicator", classes="loading-indicator hidden")
            yield self.input
            
    def on_mount(self):
        """组件挂载时的初始化"""
        # 在挂载时向消息区域添加内容静态组件
        messages_container = self.query_one("#chat-messages", VerticalScroll)
        messages_container.mount(Static(id="chat-content", classes="chat-content"))
        # 获取滚动容器并设置滚动行为
        messages_container.can_focus = True
        messages_container.auto_height = False

    def add_message(self, message):
        # 将消息添加到列表中
        self.messages.append(message)
        # 重新构建完整的消息内容
        self._update_chat_content()
    
    def _update_chat_content(self):
        """更新聊天内容显示"""
        try:
            # 尝试查询聊天内容节点
            content = self.query_one("#chat-content", Static)
        except Exception:
            # 如果节点不存在，先创建它
            messages_container = self.query_one("#chat-messages", VerticalScroll)
            messages_container.mount(Static(id="chat-content", classes="chat-content"))
            content = self.query_one("#chat-content", Static)
        
        full_content = ""
        
        # 重新构建所有消息
        for message in self.messages:
            if hasattr(message, 'content'):
                # 获取原始内容，不进行特殊格式化
                raw_content = str(message.content)
                
                if isinstance(message, HumanMessage):
                    full_content += f"\n\n👤 你: {raw_content}"
                elif isinstance(message, AIMessage):
                    full_content += f"\n\n🤖 AI: {raw_content}"
                elif isinstance(message, ToolMessage):
                    full_content += f"\n\n🔧 工具: {raw_content}"
        
        try:
            # 禁用标记语言解析，直接显示原始文本
            content._render_markup = False
            # 一次性更新内容
            content.update(full_content.strip())
        except Exception as e:
            # 如果更新失败，显示错误信息
            error_msg = f"更新聊天内容时出错: {str(e)}"
            print(error_msg)
            content.update(error_msg)
        
        # 确保视图刷新
        self.refresh()
        # 滚动消息区域到底部
        messages_scroll = self.query_one("#chat-messages", VerticalScroll)
        messages_scroll.call_later(messages_scroll.scroll_end, animate=True)
    

    
    def update_loading_indicator(self, is_loading):
        """更新加载指示器的显示状态"""
        indicator = self.query_one("#loading-indicator", Static)
        if is_loading:
            indicator.update("🤖 AI 正在思考...")
            indicator.remove_class("hidden")
        else:
            indicator.add_class("hidden")
    
    def focus_input(self):
        self.input.focus()
    
    @property
    def disabled(self):
        return self.input.disabled
    
    @disabled.setter
    def disabled(self, value):
        self.input.disabled = value


class TerminalView(VerticalScroll):
    """可滚动的终端视图组件"""
    
    def __init__(self, id=None):
        super().__init__(id=id)
        self._content = "=== 终端视图 ===\n欢迎使用CodeAgentDemo终端!"
    
    def compose(self) -> ComposeResult:
        yield Static(self._content, id="terminal-content")
    
    def write(self, text, is_result=False):
        try:
            # 首先更新内部内容变量
            self._content += ("\n" if self._content.strip() else "") + text
            
            # 然后更新UI组件
            content = self.query_one("#terminal-content", Static)
            content.update(self._content)
            self.scroll_end(animate=False)
        except Exception as e:
            print(f"终端写入错误: {str(e)}")


from textual.widgets import Input, Button, Label, Static
from pathlib import Path
from typing import Dict, Optional
from textual.containers import Container, Horizontal

class EditorTabs(Vertical):
    """编辑器标签组件"""
    
    def __init__(self, id=None):
        super().__init__(id=id)
        self._open_files: Dict[str, str] = {}  # {文件路径: 文件内容}
        self._current_file: Optional[str] = None
    
    def compose(self) -> ComposeResult:
        # 标签栏
        with Horizontal(id="tabs-bar", classes="tabs-bar"):
            pass
        # 文件内容编辑区域
        with Container(id="editor-container", classes="editor-container"):
            yield TextArea("编辑器区域", id="editor-content", classes="editor-text")
        # 底部状态栏
        with Horizontal(id="editor-status-bar", classes="editor-status-bar"):
            yield Label("就绪", id="status-label")
            yield Button("保存", id="save-button")
    
    def open_welcome(self):
        """打开欢迎页面"""
        content = self.query_one("#editor-content", TextArea)
        self._current_file = None
        welcome_text = """
欢迎使用 Code Agent Console!

您可以在这里与代码代理交互，执行各种代码任务。

可用工具:
- bash: 执行命令行操作
- text_editor: 查看、创建、编辑文件
- ls: 列出目录内容
- grep: 搜索文件内容
- tree: 查看目录树
        """.strip()
        content.text = welcome_text
        # 将编辑器设置为只读模式
        content.disabled = True
        self.update_status_bar("就绪 - 欢迎页面为只读模式")
    
    def open_file(self, file_path: str):
        """打开文件并显示内容"""
        try:
            # 从text_editor.py导入TextEditor类
            from src.tools.text_editor import TextEditor
            
            path = Path(file_path)
            if not path.exists() or not path.is_file():
                self.update_status_bar(f"错误: 文件不存在或不是有效文件")
                return
            
            # 实例化TextEditor并读取文件内容
            editor = TextEditor()
            content = editor.read_file(path)
            
            # 保存到打开的文件列表
            self._open_files[file_path] = content
            self._current_file = file_path
            
            # 显示文件内容
            editor_content = self.query_one("#editor-content", TextArea)
            # 确保编辑器处于可编辑模式
            editor_content.disabled = False
            editor_content.text = content
            
            # 设置语法高亮（如果支持）
            try:
                # 尝试根据文件扩展名设置语法高亮
                ext = path.suffix.lstrip('.')
                if ext in editor_content.language_names:
                    editor_content.language = ext
            except Exception:
                # 如果设置语法高亮失败，忽略错误
                pass
            
            # 更新标签栏
            self._update_tabs_bar()
            
            # 更新状态栏
            display_name = path.name if path.name else str(path)
            self.update_status_bar(f"已打开: {display_name}")
            
        except Exception as e:
            self.update_status_bar(f"错误: {str(e)}")
    
    def save_file(self):
        """保存当前文件"""
        if not self._current_file:
            self.update_status_bar("没有打开的文件可保存")
            return
        
        try:
            # 从text_editor.py导入TextEditor类
            from src.tools.text_editor import TextEditor
            
            path = Path(self._current_file)
            
            # 从TextArea获取最新内容
            editor_content = self.query_one("#editor-content", TextArea)
            content = editor_content.text
            
            # 更新内存中的文件内容
            self._open_files[self._current_file] = content
            
            # 实例化TextEditor并保存文件
            editor = TextEditor()
            editor.write_file(path, content)
            
            # 更新状态栏
            display_name = path.name if path.name else str(path)
            self.update_status_bar(f"已保存: {display_name}")
            
        except Exception as e:
            self.update_status_bar(f"保存失败: {str(e)}")
    
    def update_file_content(self, new_content: str):
        """更新当前文件内容"""
        if not self._current_file:
            return
        
        # 更新内存中的文件内容
        self._open_files[self._current_file] = new_content
        
        # 更新显示内容
        editor_content = self.query_one("#editor-content", TextArea)
        editor_content.text = new_content
        
        # 设置语法高亮（如果支持）
        try:
            path = Path(self._current_file)
            ext = path.suffix.lstrip('.')
            if ext in editor_content.language_names:
                editor_content.language = ext
        except Exception:
            # 如果设置语法高亮失败，忽略错误
            pass
        
        # 更新状态栏
        path = Path(self._current_file)
        display_name = path.name if path.name else str(path)
        self.update_status_bar(f"已修改: {display_name}")
    
    def _update_tabs_bar(self):
        """更新标签栏（增量更新方式）"""
        tabs_bar = self.query_one("#tabs-bar", Horizontal)
        
        # 使用基于文件路径的唯一哈希值生成ID，避免冲突
        import hashlib
        
        # 记录当前需要保留的标签ID
        current_tab_ids = set()
        
        for file_path in self._open_files:
            path = Path(file_path)
            is_active = file_path == self._current_file
            
            # 创建标签按钮
            display_name = path.name if path.name else str(path)
            
            # 使用文件路径的哈希值生成唯一ID，避免不同会话间的冲突
            file_hash = hashlib.md5(file_path.encode()).hexdigest()[:6]
            tab_id = f"tab-{file_hash}"
            
            # 记录当前需要的ID
            current_tab_ids.add(tab_id)
            
            # 检查标签按钮是否已存在
            try:
                tab_button = tabs_bar.query_one(f"#{tab_id}", Button)
                # 更新现有标签按钮的文本和活动状态
                tab_button.label = display_name
                tab_button.classes = "tab-button active" if is_active else "tab-button"
                # 确保data属性正确设置
                tab_button.data = file_path
            except Exception:
                # 标签按钮不存在，创建新的
                tab_button = Button(
                    display_name,
                    id=tab_id,
                    classes="tab-button active" if is_active else "tab-button"
                )
                tab_button.data = file_path  # 存储文件路径
                tabs_bar.mount(tab_button)
        
        # 移除不再需要的标签按钮
        all_buttons = list(tabs_bar.query(Button))
        for button in all_buttons:
            button_id = button.id
            # 如果按钮ID不在当前需要保留的列表中，则移除它
            if button_id.startswith("tab-") and button_id not in current_tab_ids:
                try:
                    button.remove()
                except Exception:
                    # 忽略移除时可能发生的错误
                    pass
        
        # 刷新布局确保更新生效
        tabs_bar.refresh()
    
    def update_status_bar(self, message: str):
        """更新状态栏消息"""
        status_label = self.query_one("#status-label", Label)
        status_label.update(message)
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """处理按钮点击事件"""
        button = event.button
        
        if button.id == "save-button":
            # 保存文件
            self.save_file()
        elif "tab-" in button.id and hasattr(button, "data"):
            # 切换标签
            file_path = button.data
            if file_path in self._open_files:
                self._current_file = file_path
                self.open_file(file_path)  # 重新打开文件来刷新显示
    
    def on_text_area_changed(self, event: TextArea.Changed) -> None:
        """处理文本区域内容变化事件"""
        # 只有在当前有打开的文件时才处理变化
        if self._current_file:
            # 更新内存中的文件内容
            self._open_files[self._current_file] = event.text_area.text
            # 更新状态栏
            path = Path(self._current_file)
            display_name = path.name if path.name else str(path)
            self.update_status_bar(f"已修改: {display_name}")
        else:
            # 如果是welcome文本，忽略更改并重置内容
            event.text_area.text = """
欢迎使用 Code Agent Console!

您可以在这里与代码代理交互，执行各种代码任务。

可用工具:
- bash: 执行命令行操作
- text_editor: 查看、创建、编辑文件
- ls: 列出目录内容
- grep: 搜索文件内容
- tree: 查看目录树
        """.strip()






class CodeAgentConsole(App):
    """Code Agent 控制台应用"""

    TITLE = "Code Agent Console"

    CSS = """
    Screen {
        layout: horizontal;
        background: $background;
    }
    
    Header {
        background: #161c10;
    }
    
    Footer {
        background: #181c40;
    }
    
    #left-panel {
        width: 3fr;
        background: $panel;
    }
    
    #right-panel {
        width: 4fr;
        background: $boost;
    }
    
    #editor-tabs {
        height: 70%;
    }
    
    #bottom-right-tabs {
        height: 30%;
        background: $panel;
    }
    
    #bottom-right-tabs TabPane {
        padding: 0;
    }
    
    /* 编辑器标签样式 */
    .tabs-bar {
        background: $boost;
        border-bottom: solid $accent;
        padding: 0 1;
        height: auto;
        overflow-x: auto;
    }
    
    .tab-button {
        background: $panel;
        border-top: solid $panel;
        border-left: solid $panel;
        border-right: solid $panel;
        border-bottom: solid $panel;
        padding: 0 2;
        margin: 0 1;
        min-width: 10;
        height: auto;
    }
    
    .tab-button.active {
        background: $boost;
        border-bottom: solid $boost;
        color: $accent;
    }
    

    
    .editor-container {
        height: 1fr;
        background: $boost;
        overflow: auto;
    }
    
    .editor-text {
        padding: 1 2;
        color: $text;
        height: 100%;
    }
    
    .editor-status-bar {
        background: $panel;
        border-top: solid $accent;
        padding: 0 2;
        height: auto;
    }
    
    ChatView {
        height: 1fr;
        layout: vertical;
    }
    
    .chat-messages {
        height: 1fr;
        background: $panel;
        overflow: auto;
    }
    
    .chat-content {
        padding: 1 2;
        height: auto;
        width: 100%;
    }
    
    .chat-footer {
        background: $boost;
        border-top: solid $accent;
        height: auto;
    }
    
    .loading-indicator {
        padding: 1 2;
        color: $accent;
        background: $boost;
        text-style: bold;
        width: 100%;
    }
    
    .hidden {
        display: none;
    }
    
    #chat-input {
        width: 100%;
        border: none;
        background: $background;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "退出"),
        Binding("ctrl+c", "quit", "退出", show=False),
    ]

    _coding_agent: CompiledStateGraph

    _is_generating = False

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._coding_agent = create_code_agent()

    @property
    def is_generating(self) -> bool:
        return self._is_generating

    @is_generating.setter
    def is_generating(self, value: bool) -> None:
        self._is_generating = value
        chat_view = self.query_one("#chat-view", ChatView)
        chat_view.is_generating = value
        chat_view.disabled = value
        # 更新加载指示器
        chat_view.update_loading_indicator(value)

    def compose(self) -> ComposeResult:
        yield Header(id="header")
        with Vertical(id="left-panel"):
            yield ChatView(id="chat-view")
        with Vertical(id="right-panel"):
            yield EditorTabs(id="editor-tabs")
            with TabbedContent(id="bottom-right-tabs"):
                with TabPane(id="terminal-tab", title="终端"):
                    yield TerminalView(id="terminal-view")
        yield Footer(id="footer")
        
    def _init_agent(self) -> None:
        """初始化代理并加载工具"""
        # 确保先找到终端视图组件
        try:
            terminal_view = self.query_one("#terminal-view", TerminalView)
            terminal_view.write("$ 正在加载工具...")
        except Exception as e:
            print(f"找不到终端视图: {str(e)}")
        
        # 继续初始化代理逻辑...
        self.refresh()

    def focus_input(self) -> None:
        chat_view = self.query_one("#chat-view", ChatView)
        chat_view.focus_input()

    def on_mount(self) -> None:
        # 设置基本的暗色主题
        self.sub_title = str(Path.cwd())
        self.focus_input()
        editor_tabs = self.query_one("#editor-tabs", EditorTabs)
        editor_tabs.open_welcome()

        # 初始化代理并加载工具
        asyncio.create_task(self._init_agent())
        
    async def handle_tool_result(self, tool_name: str, tool_result: str, tool_call_id=None):
        """处理工具执行结果"""
        # 先获取终端视图用于后续日志输出
        terminal_view = None
        try:
            # 确保从根组件获取终端视图，而不是在EditorTabs内部查找
            if hasattr(self, "app") and self.app:
                terminal_view = self.app.query_one("#terminal-view", TerminalView)
            else:
                # 尝试直接从当前组件获取（如果当前是根组件）
                terminal_view = self.query_one("#terminal-view", TerminalView)
        except Exception as e:
            # 如果获取终端视图失败，仍然继续处理逻辑
            print(f"获取终端视图失败: {str(e)}")
        
        # 记录接收到工具结果的日志
        if terminal_view:
            terminal_view.write(f"处理工具调用结果 - 工具名: {tool_name}")
        
        if tool_name == "text_editor":
            # 解析text_editor工具的结果
            import re
            if terminal_view:
                terminal_view.write(f"tool result是: {tool_result}")
                        
            # 优化的正则表达式，更健壮地匹配Windows文件路径
            # 支持盘符、反斜杠和各种路径格式
            view_match = re.search(r'Here\'s the result of running.*?on\s+((?:[a-zA-Z]:)?(?:[\\/][^\\/:\n]+)*[\\/]?[^\\/:\n]*):', tool_result)
            if view_match:
                file_path = view_match.group(1).strip()
                
                # 移除可能的引号和反斜杠转义
                if (file_path.startswith('"') and file_path.endswith('"')) or (file_path.startswith("'") and file_path.endswith("'")):
                    file_path = file_path[1:-1]
                
                # 规范化路径分隔符，处理Windows路径格式
                file_path = file_path.replace('\\', '/')
                
                # 确保文件路径存在
                from pathlib import Path
                path_obj = Path(file_path)
                
                # 尝试处理相对路径，相对于当前工作目录
                if not path_obj.is_absolute():
                    path_obj = Path.cwd() / path_obj
                    if terminal_view:
                        terminal_view.write(f"转换相对路径为绝对路径: {path_obj}")
                
                # 记录解析后的文件路径信息
                if terminal_view:
                    terminal_view.write(f"解析后的文件路径: {path_obj}")
                    terminal_view.write(f"路径是否绝对路径: {path_obj.is_absolute()}")
                    terminal_view.write(f"路径是否存在: {path_obj.exists()}")
                    terminal_view.write(f"是否为文件: {path_obj.is_file()}")
                
                if not path_obj.exists() or not path_obj.is_file():
                    # 记录日志
                    if terminal_view:
                        terminal_view.write(f"文件不存在或不是有效文件，尝试直接从输出中提取内容: {file_path}")
                        
                    # 尝试直接从tool_result中提取文件内容
                    content_match = re.search(r'```\n(.*?)```', tool_result, re.DOTALL)
                    if content_match:
                        raw_content = content_match.group(1)
                        
                        # 记录提取到内容的日志
                        if terminal_view:
                            terminal_view.write(f"成功从输出中提取到文件内容，长度: {len(raw_content)} 字符")
                        
                        # 直接更新编辑器内容，而不依赖文件存在
                        try:
                            editor_tabs = self.query_one("#editor-tabs", EditorTabs)
                            editor_tabs._current_file = str(path_obj)
                            editor_tabs._open_files[str(path_obj)] = raw_content
                            
                            # 更新显示
                            editor_content = editor_tabs.query_one("#editor-content", Static)
                            editor_content.update(raw_content)
                            
                            # 更新标签栏和状态栏
                            editor_tabs._update_tabs_bar()
                            editor_tabs.update_status_bar(f"已查看: {path_obj.name}")
                        except Exception as e:
                            if terminal_view:
                                terminal_view.write(f"更新编辑器内容时出错: {str(e)}")
                    else:
                        if terminal_view:
                            terminal_view.write(f"未能从输出中提取到内容块")
                else:
                    # 文件存在，使用open_file方法打开
                    if terminal_view:
                        terminal_view.write(f"文件存在且有效，使用open_file方法打开: {file_path}")
                    
                    try:
                        editor_tabs = self.query_one("#editor-tabs", EditorTabs)
                        editor_tabs.open_file(str(path_obj))
                    except Exception as e:
                        if terminal_view:
                            terminal_view.write(f"调用open_file方法时出错: {str(e)}")
            else:
                # 尝试其他命令的结果格式（create, str_replace, insert）
                # 尝试多种格式匹配文件路径
                path_patterns = [
                    r'Successfully replaced .*? occurrences in (.*?)\.',
                    r'Successfully inserted text at line .*? in (.*?)\.',
                    r'File successfully created at (.*?)\.',
                    r'File does not exist: (.*?)\.',
                    r'Path is not a file: (.*?)\.',
                    r'Error: the path (.*?) is a directory\.'
                ]
                
                file_path = None
                for pattern in path_patterns:
                    path_match = re.search(pattern, tool_result)
                    if path_match:
                        file_path = path_match.group(1).strip()
                        # 移除可能的引号
                        if file_path.startswith('"') and file_path.endswith('"') or file_path.startswith("'") and file_path.endswith("'"):
                            file_path = file_path[1:-1]
                        break
                
                # 如果是创建或修改文件操作，尝试重新打开文件以显示最新内容
                if file_path and any(cmd in tool_result.lower() for cmd in ['created', 'replaced', 'inserted']):
                    if terminal_view:
                        terminal_view.write(f"检测到文件创建或修改操作，尝试重新打开文件: {file_path}")
                    
                    try:
                        editor_tabs = self.query_one("#editor-tabs", EditorTabs)
                        # 如果当前正在查看该文件，则重新打开以显示最新内容
                        if file_path in editor_tabs._open_files or file_path == editor_tabs._current_file:
                            editor_tabs.open_file(file_path)
                            if terminal_view:
                                terminal_view.write(f"成功重新打开文件显示最新内容")
                    except Exception as e:
                        if terminal_view:
                            terminal_view.write(f"重新打开文件时出错: {str(e)}")
        
        # 将结果写入到终端视图
        try:
            if terminal_view:
                terminal_view.write(f"$ {tool_name} 命令执行结果:\n{tool_result}\n", is_result=True)
        except Exception as e:
            # 最后的错误处理，如果terminal_view对象存在但写入失败
            pass
        
        # 将结果添加到聊天视图
        chat_view = self.query_one("#chat-view", ChatView)
        chat_view.add_message(ToolMessage(content=tool_result))
    
    # 确保覆盖了所有text_editor命令的处理
    # 如果是其他命令（create, str_replace, insert），我们已经在修改后的代码中包含了文件路径检查逻辑

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if not self.is_generating and event.input.id == "chat-input":
            user_input = event.value.strip()
            if user_input:
                if user_input.lower() in ["exit", "quit", "退出"]:
                    self.exit()
                    return
                event.input.value = ""
                user_message = HumanMessage(content=user_input)
                self._handle_user_input(user_message)

    async def _init_agent(self) -> None:
        terminal_view = self.query_one("#terminal-view", TerminalView)
        terminal_view.write("$ 正在加载工具...")
        try:
            # 初始化代码代理并加载工具
            from src.tools.ls import ls_tool
            from src.tools.grep import grep_tool
            from src.tools.tree import tree_tool
            
            # 创建工具列表
            tools = [bash_tool, text_editor_tool, ls_tool, grep_tool, tree_tool]
            
            # 初始化代码代理
            terminal_view.write("$ 加载 MCP tools...")
            mcp_tools = await load_mcp()
            tool_count = len(mcp_tools)
            if tool_count > 0:
                terminal_view.write(f"- 已加载 MCP tools: {tool_count}\n", True)
            else:
                terminal_view.write(f"- 没有找到 MCP tools\n", True)
            self._coding_agent = create_code_agent(plugin_tools=mcp_tools)
            terminal_view.write("- 已加载基础工具：bash, text_editor, ls, grep, tree\n", True)
        except Exception as e:
            terminal_view.write(f"错误：无法加载工具 - {str(e)}")
            import traceback
            print(f"详细错误信息：\n{traceback.format_exc()}")

    @work(exclusive=True, thread=False)
    async def _handle_user_input(self, user_message: HumanMessage) -> None:
        self._process_outgoing_message(user_message)
        self.is_generating = True
        
        # 添加简单的加载动画
        loading_task = asyncio.create_task(self._show_loading_animation())
        
        try:
            async for chunk in self._coding_agent.astream(
                {"messages": [user_message]},
                stream_mode="updates",
                config={"recursion_limit": 100, "thread_id": "thread_1"},
            ):
                roles = chunk.keys() if hasattr(chunk, 'keys') else []
                for role in roles:
                    if hasattr(chunk[role], 'get'):
                        messages: list[AnyMessage] = chunk[role].get("messages", [])
                        for message in messages:
                            self._process_incoming_message(message)
        except Exception as e:
            error_message = f"处理请求时出错：{str(e)}"
            self.query_one("#chat-view", ChatView).add_message(AIMessage(content=error_message))
        finally:
            # 取消加载动画任务
            loading_task.cancel()
            try:
                await loading_task
            except asyncio.CancelledError:
                pass
            
            self.is_generating = False
            self.focus_input()
    
    async def _show_loading_animation(self):
        """显示加载动画"""
        animation = ["🤖 AI 正在思考", "🤖 AI 正在思考.", "🤖 AI 正在思考..", "🤖 AI 正在思考..."]
        index = 0
        try:
            while self.is_generating:
                chat_view = self.query_one("#chat-view", ChatView)
                indicator = chat_view.query_one("#loading-indicator", Static)
                indicator.update(animation[index % len(animation)])
                index += 1
                await asyncio.sleep(0.5)
        except asyncio.CancelledError:
            pass

    def _process_outgoing_message(self, message: HumanMessage) -> None:
        chat_view = self.query_one("#chat-view", ChatView)
        chat_view.add_message(message)

    def _process_incoming_message(self, message: AnyMessage) -> None:
        chat_view = self.query_one("#chat-view", ChatView)
        chat_view.add_message(message)
        if isinstance(message, AIMessage) and hasattr(message, 'tool_calls') and message.tool_calls:
            self._process_tool_call_message(message)
        if isinstance(message, ToolMessage):
            self._process_tool_message(message)

    _terminal_tool_calls: list[str] = []
    _mutable_text_editor_tool_calls: dict[str, str] = {}

    def _process_tool_call_message(self, message: AIMessage) -> None:
        terminal_view = self.query_one("#terminal-view", TerminalView)
        if hasattr(message, 'tool_calls') and message.tool_calls:
            terminal_view.write(f"\nAI 正在调用工具: {message.tool_calls[0].get('name', 'unknown')}")

    def _process_tool_message(self, message: ToolMessage) -> None:
        terminal_view = self.query_one("#terminal-view", TerminalView)
        terminal_view.write(f"\n工具返回结果: {message.content[:100]}..." if len(message.content) > 100 else f"\n工具返回结果: {message.content}")
        
        # 调用handle_tool_result方法处理工具执行结果
        # 注意：这里需要在一个异步任务中调用异步方法
        asyncio.create_task(self._call_handle_tool_result(message))
        
    async def _call_handle_tool_result(self, message: ToolMessage):
        """异步调用handle_tool_result的包装方法"""
        # 获取终端视图用于日志输出
        terminal_view = None
        try:
            if hasattr(self, "app") and self.app:
                terminal_view = self.app.query_one("#terminal-view", TerminalView)
            else:
                terminal_view = self.query_one("#terminal-view", TerminalView)
        except Exception as e:
            print(f"获取终端视图失败: {str(e)}")
        
        try:
            # 记录调用开始的日志
            if terminal_view:
                terminal_view.write(f"开始处理工具消息: {message.__class__.__name__}")
                terminal_view.write(f"消息内容预览: {message.content[:50]}...")
            
            # 提取工具名称并调用handle_tool_result
            tool_name = "unknown_tool"
            
            # 尝试从消息结构中直接获取工具名称（如果可用）
            if hasattr(message, 'name'):
                tool_name = message.name
                if terminal_view:
                    terminal_view.write(f"从message.name获取工具名称: {tool_name}")
            elif hasattr(message, 'tool_call_id'):
                # 如果有tool_call_id，可能需要其他方式获取工具名称
                if terminal_view:
                    terminal_view.write(f"消息包含tool_call_id: {message.tool_call_id}")
            elif hasattr(message, 'additional_kwargs'):
                # 尝试从additional_kwargs获取
                if 'name' in message.additional_kwargs:
                    tool_name = message.additional_kwargs['name']
                    if terminal_view:
                        terminal_view.write(f"从additional_kwargs获取工具名称: {tool_name}")
            
            # 如果仍然未知，尝试从内容中提取
            if tool_name == "unknown_tool":
                # 尝试从消息内容中提取工具名称
                import re
                tool_match = re.search(r'\$ (\w+) 命令执行结果:', message.content)
                if tool_match:
                    tool_name = tool_match.group(1)
                    if terminal_view:
                        terminal_view.write(f"从内容中提取工具名称: {tool_name}")
                elif "text_editor" in message.content:
                    tool_name = "text_editor"
                    if terminal_view:
                        terminal_view.write(f"检测到text_editor内容")
                elif "bash" in message.content:
                    tool_name = "bash"
                    if terminal_view:
                        terminal_view.write(f"检测到bash内容")
                elif "ls" in message.content:
                    tool_name = "ls"
                    if terminal_view:
                        terminal_view.write(f"检测到ls内容")
                elif "grep" in message.content:
                    tool_name = "grep"
                    if terminal_view:
                        terminal_view.write(f"检测到grep内容")
                elif "tree" in message.content:
                    tool_name = "tree"
                    if terminal_view:
                        terminal_view.write(f"检测到tree内容")
            
            # 提取tool_call_id（如果存在）
            tool_call_id = getattr(message, 'tool_call_id', None)
            if tool_call_id is None and hasattr(message, 'additional_kwargs'):
                tool_call_id = message.additional_kwargs.get('tool_call_id')
            
            # 记录即将调用handle_tool_result
            if terminal_view:
                terminal_view.write(f"准备调用handle_tool_result，工具名称: {tool_name}, tool_call_id: {tool_call_id}")
            
            # 调用handle_tool_result方法
            await self.handle_tool_result(tool_name, message.content, tool_call_id)
            
            # 记录调用成功
            if terminal_view:
                terminal_view.write(f"handle_tool_result调用成功完成")
                
        except Exception as e:
            # 记录详细的错误信息
            error_message = f"调用handle_tool_result时出错: {str(e)}"
            print(error_message)
            import traceback
            print(f"详细错误堆栈:\n{traceback.format_exc()}")
            
            # 在终端视图中显示错误
            # if terminal_view:
            #     terminal_view.write(error_message, is_result=True)
            #     terminal_view.write(f"错误类型: {type(e).__name__}", is_result=True)
            #     terminal_view.write(f"错误堆栈预览: {str(traceback.format_exc()).splitlines()[0]}", is_result=True)

def main():
    """主入口函数"""
    app = CodeAgentConsole()
    app.run()


if __name__ == "__main__":
    main()