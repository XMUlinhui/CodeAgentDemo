import sys
import os

# 获取当前文件所在目录（项目根目录）
project_root = os.path.dirname(os.path.abspath(__file__))

# 将项目根目录添加到Python路径中
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.cli.console_app import CodeAgentConsole

if __name__ == "__main__":
    # chat_model = init_chat_model()
    # print(chat_model.invoke("法国首都是哪里?"))
    app = CodeAgentConsole()
    app.run()