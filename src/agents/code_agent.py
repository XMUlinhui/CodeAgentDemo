from langchain.agents import create_agent
from langchain.tools import BaseTool
from src.models.chat_model import init_chat_model

from src.tools.grep import grep_tool
from src.tools.ls import ls_tool
from src.tools.tree import tree_tool
from src.tools.bash import bash_tool
from src.tools.text_editor import text_editor_tool
from src.prompt.load_prompt import apply_prompt_template
import os



# 创建agent
def create_code_agent(plugin_tools: list[BaseTool] = [], **kwargs):
    return create_agent(
        model = init_chat_model(),
        tools=[
            bash_tool,
            ls_tool,
            text_editor_tool,
            tree_tool,
            grep_tool,
            *plugin_tools,
        ],
        system_prompt=apply_prompt_template("agent_prompt", PROJECT_ROOT=os.getcwd()),
        name="code_agent",
        **kwargs,
    )