"""MCP 工具管理模块"""
import json
import os
import httpx


class MCPToolManager:
    def __init__(self, config_path: str = None):
        if config_path is None:
            config_path = os.path.join(os.path.dirname(__file__), "mcpconfig.json")
        self.config_path = config_path
        self.config = self._load_config()
    
    def _load_config(self) -> dict:
        """加载 MCP 配置"""
        if os.path.exists(self.config_path):
            with open(self.config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {"mcpServers": {}}
    
    def reload(self):
        """重新加载配置"""
        self.config = self._load_config()
    
    def get_openai_tools(self) -> list | None:
        """将 MCP 配置转换为 OpenAI tools 格式"""
        tools = []
        for server_config in self.config.get("mcpServers", {}).values():
            for tool in server_config.get("tools", []):
                tools.append({
                    "type": "function",
                    "function": {
                        "name": tool["name"],
                        "description": tool["description"],
                        "parameters": {
                            "type": "object",
                            "properties": tool.get("parameters", {}),
                            "required": list(tool.get("parameters", {}).keys())
                        }
                    }
                })
        return tools if tools else None
    
    def call_tool(self, tool_name: str, arguments: dict) -> str:
        """调用 MCP 工具"""
        for server_config in self.config.get("mcpServers", {}).values():
            for tool in server_config.get("tools", []):
                if tool["name"] == tool_name:
                    base_url = server_config["baseUrl"]
                    endpoint = tool["endpoint"]
                    method = tool.get("method", "GET").upper()
                    
                    try:
                        with httpx.Client(timeout=120) as client:
                            if method == "GET":
                                resp = client.get(f"{base_url}{endpoint}", params=arguments)
                            else:
                                resp = client.post(f"{base_url}{endpoint}", json=arguments)
                            return json.dumps(resp.json(), ensure_ascii=False)
                    except Exception as e:
                        return json.dumps({"error": str(e)}, ensure_ascii=False)
        
        return json.dumps({"error": f"工具 {tool_name} 未找到"}, ensure_ascii=False)
