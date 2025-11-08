# CodeAgentDemo

这是一个代码代理演示应用程序，提供了基于命令行的交互式界面，让用户能够通过聊天方式与AI代理交互，执行代码操作、文件编辑等功能。

## 系统要求

- **Python版本**: Python 3.12 或更高版本
- **操作系统**: Windows、Linux或macOS

## 安装步骤

1. 克隆或下载本项目到本地

2. 安装依赖包
   ```bash
   pip install -r requirements.txt
   ```

   > 如果没有requirements.txt文件，请根据项目使用的库手动安装：
   > ```bash
   > pip install textual langchain langchain-deepseek langchain-openai
   > ```

## 配置说明

1. 直接编辑`config.yaml`文件

2. **重要**: 请将API密钥设置为环境变量，而不是直接硬编码在配置文件中

   **配置文件示例**：
   ```yaml
   models:
     chat_model:
       type: doubao
       model: 'doubao-seed-1-6-251015'
       api_base: 'https://ark.cn-beijing.volces.com/api/v3'
       api_key: $DOUBAO_API_KEY  # 使用环境变量
       temperature: 0
       max_tokens: 8192
       extra_body:
         reasoning_effort: 'medium'

   tools:
     mcp_servers:
       context7:
         transport: 'streamable_http'
         url: 'https://mcp.context7.com/mcp'
   ```

3. **设置环境变量**：
   - 如果直接修改config.yaml，可以跳过这一步 
   - Windows: 
     ```cmd
     setx DOUBAO_API_KEY "your_actual_api_key_here"
     ```
   - Linux/macOS:
     ```bash
     export DOUBAO_API_KEY="your_actual_api_key_here"
     ```

## 使用方法

运行应用程序：

```bash
python run.py
```

### 主要功能

- **聊天交互**: 在左侧聊天区域输入命令或问题，与AI代理交互
- **文件编辑**: 在右侧编辑器区域可以查看和编辑文件
- **终端操作**: 在底部终端标签页可以查看系统输出和执行结果

## 注意事项

- 请妥善保管您的API密钥，不要将其提交到代码仓库中
- 如果遇到连接问题，请检查网络设置和API密钥配置
- 本应用目前支持中文界面和交互
