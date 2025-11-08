from langgraph.checkpoint.memory import InMemorySaver

from src.agents.code_agent import create_code_agent
from src.cli.console_app import CodeAgentConsole
from src.models.chat_model import init_chat_model

if __name__ == "__main__":
    # chat_model = init_chat_model()
    # print(chat_model.invoke("法国首都是哪里?"))
    app = CodeAgentConsole()
    app.run()