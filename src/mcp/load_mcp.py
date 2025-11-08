from src.config.config import get_config_section
from langchain_mcp_adapters.client import MultiServerMCPClient

async def load_mcp():
    servers = get_config_section(["tools", "mcp_servers"])
    if not servers:
        return []
    client = MultiServerMCPClient(servers)
    return await client.get_tools()


